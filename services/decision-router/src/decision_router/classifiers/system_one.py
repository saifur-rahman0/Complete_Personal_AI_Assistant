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
        re.compile(r"\b(search|find|locate|look for|where is)\b", re.IGNORECASE),
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

        # 1. Check Reminder intent
        if self._matches(text, self.REMINDER_PATTERNS):
            latency = (time.perf_counter() - start_time) * 1000
            return RouteDecision(
                intent=IntentType.REMINDER,
                confidence=0.92,
                target_service="automation-service",
                requires_deep_reasoning=False,
                structured_action="create_reminder",
                structured_payload={"text": text},
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

        # 4. Default: General query requiring LLM conversation
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
            # Extract pattern like *.pdf or pdf files
            ext_match = re.search(r"\b(\w+)\s+files?\b", text, re.IGNORECASE)
            pattern = f"*.{ext_match.group(1).lower()}" if ext_match else "*"
            target = detected_folder or KNOWN_FOLDERS["downloads"]
            return (
                "search_files",
                {
                    "directory_path": target,
                    "pattern": pattern,
                    "recursive": True,
                },
                0.90,
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


system_one_classifier = SystemOneClassifier()
