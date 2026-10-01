from datetime import datetime, timedelta, timezone
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from contracts.router.models import IntentType, RouteDecision, RouteRequest
from decision_router.classifiers.base import BaseClassifier

# Standard user folders
USER_HOME = Path.home()
KNOWN_FOLDERS = {
    "downloads": str(USER_HOME / "Downloads"),
    "download": str(USER_HOME / "Downloads"),
    "documents": str(USER_HOME / "Documents"),
    "document": str(USER_HOME / "Documents"),
    "desktop": str(USER_HOME / "Desktop"),
}


class SystemOneClassifier(BaseClassifier):
    """
    Sub-millisecond System One non-autoregressive decision model.
    Classifies intent and extracts high-confidence parameters without LLM overhead.
    """

    FILE_ORGANIZE_PATTERNS = [
        re.compile(r"\b(organize|sort|clean|cleanup|group)\b", re.IGNORECASE),
    ]
    FILE_SEARCH_PATTERNS = [
        re.compile(r"\b(search|find|locate|look for|where is|is there|do we have|do i have|check for|show me)\b", re.IGNORECASE),
        re.compile(r"\b(present\s+any|any\s+\w+\s+(file|pdf|doc|document|image|photo|resume|sheet|receipt|invoice))\b", re.IGNORECASE),
        re.compile(r"\b(is\s+there\s+present)\b", re.IGNORECASE),
    ]
    FILE_MOVE_PATTERNS = [
        re.compile(r"\b(move|transfer|relocate|shift)\b", re.IGNORECASE),
    ]
    FILE_LIST_PATTERNS = [
        re.compile(r"\b(list|show files|view files|what is inside)\b", re.IGNORECASE),
    ]
    REMINDER_PATTERNS = [
        re.compile(r"\b(remind me|set reminder|reminder to|alert me|notify me at)\b", re.IGNORECASE),
    ]
    WEB_PATTERNS = [
        re.compile(r"\b(search the web|google|scrape|look up online|find on the internet)\b", re.IGNORECASE),
    ]

    def classify(self, request: RouteRequest) -> RouteDecision:
        start_time = time.perf_counter()
        text = request.prompt.strip()

        # 0. Fast-path conversational greetings, identity, and pleasantries (<0.01ms, 0 tokens)
        prompt_lower = text.lower()
        if (
            re.match(r"^(hi|hello|hey|greetings|howdy|good\s+(morning|afternoon|evening))[!.,? ]*$", prompt_lower)
            or any(q == prompt_lower.rstrip("?!., ") for q in ["who are you", "what can you do", "help", "capabilities", "what are you", "how are you", "thank you", "thanks", "thanks a lot", "great job", "awesome"])
        ):
            latency = (time.perf_counter() - start_time) * 1000
            return RouteDecision(
                intent=IntentType.GENERAL_QUERY,
                confidence=1.0,
                target_service="llm-chat",
                requires_deep_reasoning=False,
                structured_action="chat_completion",
                structured_payload={"prompt": text},
                latency_ms=round(latency, 2),
            )

        # 1. Check Reminder intent
        if self._matches(text, self.REMINDER_PATTERNS):
            latency = (time.perf_counter() - start_time) * 1000
            payload = self._extract_reminder_payload(text)
            return RouteDecision(
                intent=IntentType.REMINDER,
                confidence=0.92,
                target_service="automation-service",
                requires_deep_reasoning=False,
                structured_action="create_reminder",
                structured_payload=payload,
                latency_ms=round(latency, 2),
            )

        # 2. Check Web Research intent
        if self._matches(text, self.WEB_PATTERNS):
            latency = (time.perf_counter() - start_time) * 1000
            return RouteDecision(
                intent=IntentType.WEB_RESEARCH,
                confidence=0.88,
                target_service="web-research",
                requires_deep_reasoning=True,
                structured_action="search_web",
                structured_payload={"query": text},
                latency_ms=round(latency, 2),
            )

        # 3. Check File Management intents
        file_decision = self._classify_file_action(text)
        if file_decision:
            action, payload, confidence = file_decision
            latency = (time.perf_counter() - start_time) * 1000
            return RouteDecision(
                intent=IntentType.FILE_MANAGEMENT,
                confidence=confidence,
                target_service="windows-agent",
                requires_deep_reasoning=False,
                structured_action=action,
                structured_payload=payload,
                latency_ms=round(latency, 2),
            )

        # 4. Check Desktop Automation intents
        desktop_decision = self._classify_desktop_action(text)
        if desktop_decision:
            action, payload, confidence = desktop_decision
            latency = (time.perf_counter() - start_time) * 1000
            return RouteDecision(
                intent=IntentType.DESKTOP_AUTOMATION,
                confidence=confidence,
                target_service="windows-agent",
                requires_deep_reasoning=False,
                structured_action=action,
                structured_payload=payload,
                latency_ms=round(latency, 2),
            )

        # 5. Default: General query requiring LLM conversation
        latency = (time.perf_counter() - start_time) * 1000
        return RouteDecision(
            intent=IntentType.GENERAL_QUERY,
            confidence=0.70,
            target_service="llm-chat",
            requires_deep_reasoning=True,
            structured_action="chat_completion",
            structured_payload={"prompt": text},
            latency_ms=round(latency, 2),
        )

    def _matches(self, text: str, patterns: list) -> bool:
        return any(p.search(text) for p in patterns)

    def _classify_file_action(self, text: str) -> Optional[Tuple[str, Dict[str, Any], float]]:
        # Detect target folder
        detected_folder = None

        # Check for explicit paths in quotes or standard path formats
        path_match = re.search(r'["\']([a-zA-Z]:[\\/][^"\']+)["\']', text) or re.search(r'["\'](/[^"\']+)["\']', text)
        if not path_match:
            path_match = re.search(r'\b([a-zA-Z]:[\\/][^\s"\']+)', text)

        if path_match:
            detected_folder = path_match.group(1).strip()
        else:
            for name, path in KNOWN_FOLDERS.items():
                if re.search(rf"\b{name}\b", text, re.IGNORECASE):
                    detected_folder = path
                    break

        # Fallback to Downloads if folder isn't explicitly mentioned but "folder" is
        if not detected_folder and "folder" in text.lower():
            detected_folder = KNOWN_FOLDERS["downloads"]

        # Organize folder
        if self._matches(text, self.FILE_ORGANIZE_PATTERNS):
            target = detected_folder or KNOWN_FOLDERS["downloads"]
            dry_run = "preview" in text.lower() or "dry run" in text.lower() or "what would" in text.lower()
            return (
                "organize_folder",
                {
                    "directory_path": target,
                    "strategy": "by_extension",
                    "dry_run": dry_run,
                },
                0.95,
            )

        # Move file
        if self._matches(text, self.FILE_MOVE_PATTERNS):
            return (
                "move_file",
                {"raw_instruction": text},
                0.85,
            )

        # Search files
        if self._matches(text, self.FILE_SEARCH_PATTERNS):
            # 1. Check for explicit file extension
            ext_match = re.search(r"\b(\.?[a-zA-Z0-9]+)\s+files?\b", text, re.IGNORECASE)
            pattern_ext = f"*.{ext_match.group(1).lstrip('.').lower()}" if ext_match else None

            # 2. Extract specific subject keywords (e.g. "resume", "invoice", "taxes", "report")
            clean_subject = re.sub(
                r"\b(is|there|present|any|do|we|i|you|have|search|find|locate|look|for|where|check|show|me|all|the|in|from|on|folder|directory|files?|download|documents?|desktop)\b",
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()
            clean_subject = re.sub(r"[?!.,;:]", "", clean_subject).strip()

            if clean_subject and pattern_ext:
                raw_ext = pattern_ext.lstrip("*").lstrip(".").lower()
                if clean_subject.lower() == raw_ext:
                    pattern = pattern_ext
                else:
                    pattern = f"*{clean_subject}*{pattern_ext.replace('*', '')}"
            elif clean_subject:
                pattern = f"*{clean_subject}*"
            elif pattern_ext:
                pattern = pattern_ext
            else:
                pattern = "*"

            target = detected_folder or KNOWN_FOLDERS["downloads"]
            return (
                "search_files",
                {
                    "directory_path": target,
                    "pattern": pattern,
                    "recursive": True,
                },
                0.92,
            )

        # List directory
        if self._matches(text, self.FILE_LIST_PATTERNS) or (detected_folder and "what" in text.lower()):
            target = detected_folder or KNOWN_FOLDERS["downloads"]
            return (
                "list_directory",
                {
                    "directory_path": target,
                    "recursive": False,
                },
                0.88,
            )

        return None

    def _extract_reminder_payload(self, text: str) -> Dict[str, Any]:
        clean_text = text
        for prefix in [
            "remind me to",
            "remind me",
            "set reminder to",
            "set reminder",
            "alert me to",
            "alert me",
            "notify me to",
            "notify me at",
        ]:
            if clean_text.lower().startswith(prefix):
                clean_text = clean_text[len(prefix):].strip()
                break

        # Check relative time: "in 10 minutes", "in 1 hour", "in 30s"
        rel_match = re.search(
            r"\bin\s+(\d+)\s*(s|sec|seconds?|m|mins?|minutes?|h|hrs?|hours?|d|days?)\b",
            text,
            re.IGNORECASE,
        )
        delta_seconds = 3600  # Default 1 hour if not specified
        if rel_match:
            val = int(rel_match.group(1))
            unit = rel_match.group(2).lower()
            if unit.startswith("s"):
                delta_seconds = val
            elif unit.startswith("m"):
                delta_seconds = val * 60
            elif unit.startswith("h"):
                delta_seconds = val * 3600
            elif unit.startswith("d"):
                delta_seconds = val * 86400

            # Strip the relative duration part from clean title
            clean_text = re.sub(
                r"\bin\s+\d+\s*(s|sec|seconds?|m|mins?|minutes?|h|hrs?|hours?|d|days?)\b",
                "",
                clean_text,
                flags=re.IGNORECASE,
            ).strip()

        if clean_text.lower().startswith("to "):
            clean_text = clean_text[3:].strip()

        title = clean_text.capitalize() if clean_text else "Reminder"
        trigger_at = datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)

        return {
            "title": title,
            "trigger_at": trigger_at.isoformat(),
            "original_prompt": text,
        }

    def _classify_desktop_action(self, text: str) -> Optional[Tuple[str, Dict[str, Any], float]]:
        # 1. Telemetry check
        if re.search(r"\b(system status|telemetry|battery|cpu usage|ram usage|how much memory|what windows are open)\b", text, re.IGNORECASE):
            return "system_telemetry", {"action": "system_telemetry"}, 0.95

        # 2. App launch check
        m_launch = re.search(r"\b(?:open|launch|start)\s+(notepad|calculator|calc|code|vscode|explorer|taskmgr|terminal)\b", text, re.IGNORECASE)
        if m_launch:
            app_raw = m_launch.group(1).lower()
            return "app_launch", {"action": "app_launch", "app_name": app_raw}, 0.96

        # 3. App close check
        m_close = re.search(r"\b(?:close|terminate|kill)\s+(notepad|calculator|calc|code|vscode|explorer|taskmgr|terminal)\b", text, re.IGNORECASE)
        if m_close:
            app_raw = m_close.group(1).lower()
            return "app_close", {"action": "app_close", "target": app_raw, "force": False, "require_approval": True}, 0.96

        return None


system_one_classifier = SystemOneClassifier()

