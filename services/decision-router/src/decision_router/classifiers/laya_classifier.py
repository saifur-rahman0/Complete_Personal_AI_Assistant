"""
Neural Laya System One Decision Classifier.
Uses Convai Innovations' Laya (ModernBERT-large based non-autoregressive decision model)
for zero-shot semantic intent routing and structured tool classification without LLM tokens.
"""
from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from contracts.router.models import IntentType, RouteDecision, RouteRequest
from decision_router.classifiers.base import BaseClassifier
from decision_router.classifiers.system_one import KNOWN_EXTENSIONS, system_one_classifier

logger = logging.getLogger("decision_router.classifiers.laya")

USER_HOME = Path.home()
EXTENDED_FOLDERS: Dict[str, str] = {
    "downloads": str(USER_HOME / "Downloads"),
    "download": str(USER_HOME / "Downloads"),
    "documents": str(USER_HOME / "Documents"),
    "document": str(USER_HOME / "Documents"),
    "desktop": str(USER_HOME / "Desktop"),
    "pictures": str(USER_HOME / "Pictures"),
    "picture": str(USER_HOME / "Pictures"),
    "images": str(USER_HOME / "Downloads" / "Images") if (USER_HOME / "Downloads" / "Images").exists() else str(USER_HOME / "Pictures"),
    "image": str(USER_HOME / "Downloads" / "Images") if (USER_HOME / "Downloads" / "Images").exists() else str(USER_HOME / "Pictures"),
    "videos": str(USER_HOME / "Videos"),
    "video": str(USER_HOME / "Videos"),
    "music": str(USER_HOME / "Music"),
}


class NeuralLayaClassifier(BaseClassifier):
    """
    Adapter for the open-weights 'convaiinnovations/laya' ModernBERT-large classifier.
    Performs zero-shot intent routing and multi-question structured tool decisions:
      - Intent: file_management, desktop_automation, reminder, web_research, general_query
      - File Action: search_files, list_directory, organize_folder, open_file, read_file, delete_file
      - Target Directory: downloads, documents, desktop, pictures, etc.
      - File Candidate Resolution: Resolves conversational references (e.g. "open the first one")
    """

    def __init__(self, model_name: str = "convaiinnovations/laya"):
        self.model_name = model_name
        self._agent = None
        self._load_error: Optional[str] = None
        self._is_loaded = False
        self._is_loading = False

    def is_available(self) -> bool:
        """Checks if the laya library is installed and available in python."""
        if self._is_loaded and self._agent is not None:
            return True
        try:
            import laya  # noqa: F401
            return True
        except ImportError:
            return False

    def load_model_background(self) -> None:
        """Starts asynchronous background loading of Laya weights so HTTP requests are never blocked."""
        if self._is_loaded or self._is_loading:
            return
        import threading
        self._is_loading = True
        thread = threading.Thread(target=self._do_load, daemon=True)
        thread.start()

    def _do_load(self) -> None:
        try:
            import laya
            logger.info("Loading neural Laya model weights in background from '%s'...", self.model_name)
            self._agent = laya.load(self.model_name)
            self._is_loaded = True
            self._is_loading = False
            logger.info("Neural Laya model loaded successfully and ready.")
        except Exception as e:
            self._load_error = str(e)
            self._is_loading = False
            logger.error("Failed to load Laya model '%s': %s", self.model_name, e)

    def load_model(self) -> bool:
        """Loads the weights synchronously into RAM/VRAM if not already loaded."""
        if self._is_loaded and self._agent is not None:
            return True
        try:
            import laya
            logger.info("Loading neural Laya model weights from '%s'...", self.model_name)
            self._agent = laya.load(self.model_name)
            self._is_loaded = True
            logger.info("Neural Laya model loaded successfully.")
            return True
        except Exception as e:
            self._load_error = str(e)
            logger.error("Failed to load Laya model '%s': %s", self.model_name, e)
            return False

    def _extract_recent_files_from_history(self, history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
        """Extracts candidate files mentioned in recent assistant turns (e.g. from markdown links)."""
        if not history:
            return []
        candidates: List[Dict[str, str]] = []
        seen_paths = set()
        # Look backwards across the last 3 assistant turns
        for turn in reversed(history[-4:]):
            if turn.get("role") != "assistant":
                continue
            text = turn.get("text", "")
            # Find markdown links: [name](file:///path) or [name](path)
            matches = re.findall(r"\[([^\]]+)\]\((?:file:///)?([^\)]+)\)", text)
            for name, path in matches:
                norm_path = path.replace("/", "\\")
                if norm_path not in seen_paths:
                    seen_paths.add(norm_path)
                    candidates.append({"name": name.strip(), "path": norm_path.strip()})
        return candidates

    def _detect_folder_in_text(self, text: str) -> Optional[str]:
        """Detects explicit folder keywords in user prompt."""
        lower = text.lower()
        for folder_key in ["downloads", "download", "documents", "document", "desktop", "pictures", "picture", "images", "videos", "music"]:
            if re.search(rf"\b{folder_key}\b", lower):
                return EXTENDED_FOLDERS.get(folder_key)
        return None

    def _extract_folder_from_history(self, history: Optional[List[Dict[str, Any]]]) -> Optional[str]:
        if not history:
            return None
        for turn in reversed(history[-4:]):
            t = turn.get("text", "")
            m = re.search(r'\b([a-zA-Z]:[\\/][a-zA-Z0-9_\-\. \\/]+)', t)
            if m:
                cand = m.group(1).strip().rstrip(":*?").strip()
                p = Path(cand)
                if p.is_dir():
                    return str(p.resolve())
                if p.parent.is_dir():
                    return str(p.parent.resolve())
            for name, path in EXTENDED_FOLDERS.items():
                if re.search(rf"\b{name}\b", t, re.IGNORECASE):
                    return path
        return None

    def _extract_search_pattern(self, text: str) -> str:
        """Extracts search query term by removing conversational filler words and folder mentions."""
        # 1. Check known extension or category
        for ext_key, glob_pat in KNOWN_EXTENSIONS.items():
            if re.search(rf"\b{ext_key}s?\b", text, re.IGNORECASE):
                clean = re.sub(rf"\b{ext_key}s?\b", "", text, flags=re.IGNORECASE)
                clean_subj = re.sub(
                    r"\b(is|are|there|present|any|do|we|i|you|have|search|find|locate|look|for|where|check|show|me|get|list|give|tell|what|display|view|see|all|the|in|inside|from|on|of|this|that|these|current|here|folder|directory|files?|download|downloads|documents?|desktop|pictures?|images?)\b",
                    "",
                    clean,
                    flags=re.IGNORECASE,
                ).strip()
                clean_subj = re.sub(r"[?!.,;:]", "", clean_subj).strip()
                if clean_subj:
                    return f"*{clean_subj}*{glob_pat.replace('*', '')}"
                return glob_pat

        # 2. General subject
        clean = re.sub(
            r"\b(is|are|there|present|any|do|we|i|you|have|search|find|locate|look|for|where|check|show|me|get|list|give|tell|what|display|view|see|all|the|in|inside|from|on|of|this|that|these|current|here|folder|directory|files?|download|downloads|documents?|desktop|pictures?|images?)\b",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        clean = re.sub(r"[?!.,;:]", "", clean).strip()
        return f"*{clean}*" if clean else "*"

    def classify(self, request: RouteRequest) -> RouteDecision:
        """
        Classifies intent and extracts structured parameters using neural ModernBERT-large weights.
        Answers multiple structured questions in a single ~25ms forward pass without LLM tokens.
        If weights are still warming up in the background, serves via fast-path System One heuristics.
        """
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

        # If neural model is not yet loaded into memory, trigger background load
        # and immediately serve the user via sub-millisecond System One heuristics without blocking!
        if not self.is_available() or not self._is_loaded or self._agent is None:
            if not self._is_loading and self.is_available():
                self.load_model_background()
            return system_one_classifier.classify(request)

        try:
            import laya

            # 1. Multi-question structured zero-shot decision configuration
            questions: Dict[str, Dict[str, Any]] = {
                "intent": {
                    "instructions": "What type of assistant capability should handle this request?",
                    "type": "choice",
                    "criteria": [
                        "conversation_or_greeting",
                        "file_management",
                        "desktop_automation",
                        "reminder",
                        "web_research",
                        "general_query",
                    ],
                },
                "file_action": {
                    "instructions": "If this involves files or folders, what specific action is requested?",
                    "type": "choice",
                    "criteria": [
                        "search_files",
                        "list_directory",
                        "organize_folder",
                        "open_file",
                        "read_file",
                        "delete_file",
                        "not_file_action",
                    ],
                },
                "target_folder": {
                    "instructions": "Which directory or folder is targeted or implied?",
                    "type": "choice",
                    "criteria": [
                        "downloads",
                        "documents",
                        "desktop",
                        "pictures",
                        "videos",
                        "music",
                        "unspecified",
                    ],
                },
            }

            # 2. If recent candidate files exist in chat history, enable zero-token reference resolution
            candidate_files = self._extract_recent_files_from_history(request.history)
            if candidate_files:
                criteria_names = [f["name"] for f in candidate_files[:8]] + ["none"]
                questions["selected_file"] = {
                    "instructions": "Which file from recent search or list results is the user referring to?",
                    "type": "choice",
                    "criteria": criteria_names,
                }

            # 3. Single-pass non-autoregressive neural inference (~25 ms)
            res = laya.decide(self._agent, text, questions=questions)

            intent_res = res.get("intent", {})
            choice = intent_res.get("choice", "general_query")
            confidence = float(intent_res.get("confidence", 0.88))

            file_action_res = res.get("file_action", {})
            file_action_choice = file_action_res.get("choice", "not_file_action")

            target_folder_res = res.get("target_folder", {})
            folder_choice = target_folder_res.get("choice", "downloads")

            latency = (time.perf_counter() - start_time) * 1000

            # -------------------------------------------------------------
            # Branch 0: Conversational / Greetings / Pleasantries
            # -------------------------------------------------------------
            if choice == "conversation_or_greeting":
                return RouteDecision(
                    intent=IntentType.GENERAL_QUERY,
                    confidence=max(confidence, 0.95),
                    target_service="llm-chat",
                    requires_deep_reasoning=False,
                    structured_action="chat_completion",
                    structured_payload={"prompt": text},
                    latency_ms=round(latency, 2),
                )

            # -------------------------------------------------------------
            # Branch 1: File Management (Zero-Token Parameter Extraction)
            # -------------------------------------------------------------
            has_file_keywords = any(
                w in prompt_lower for w in [
                    "file", "folder", "directory", "download", "document", "desktop", "pdf",
                    "doc", "docx", "txt", "xlsx", "csv", "image", "photo", "video",
                    "organize", "sort", "move", "clean"
                ]
            ) or (candidate_files and any(w in prompt_lower for w in ["open", "read", "view", "see", "show", "preview", "delete", "first", "second", "last", "that", "it"]))

            if choice == "file_management" or (has_file_keywords and file_action_choice != "not_file_action"):
                # Check heuristic first for explicit paths or patterns
                file_decision = system_one_classifier._classify_file_action(text, history=request.history)
                if file_decision and file_decision[2] >= 0.85:
                    action, payload, file_conf = file_decision
                else:
                    # Resolve folder path
                    explicit_folder = self._detect_folder_in_text(text)
                    if not explicit_folder and re.search(r"\b(this|current|here)\b", text, re.IGNORECASE) and request.history:
                        explicit_folder = self._extract_folder_from_history(request.history)

                    folder_path = (
                        explicit_folder
                        or EXTENDED_FOLDERS.get(folder_choice)
                        or EXTENDED_FOLDERS.get("downloads", str(USER_HOME / "Downloads"))
                    )

                    # Resolve action
                    action = file_action_choice if file_action_choice != "not_file_action" else "search_files"

                    # If the prompt targets a specific extension or file category, it MUST be search_files
                    has_search_target = any(
                        re.search(rf"\b{k}s?\b", prompt_lower) for k in KNOWN_EXTENSIONS.keys()
                    ) or any(w in prompt_lower for w in ["search", "find", "locate", "look for", "is there", "where", "filter", "show all"])

                    if action == "list_directory" and has_search_target:
                        action = "search_files"

                    if action == "organize_folder":
                        payload = {"directory_path": folder_path, "strategy": "by_extension"}

                    elif action == "list_directory":
                        payload = {"directory_path": folder_path}

                    elif action in ("open_file", "read_file", "delete_file"):
                        # Check if user selected one from candidates (e.g. "open the first one" or by name)
                        selected_name = res.get("selected_file", {}).get("choice")
                        target_file_path = None
                        if selected_name and selected_name != "none":
                            for cand in candidate_files:
                                if cand["name"] == selected_name:
                                    target_file_path = cand["path"]
                                    break
                        if not target_file_path and candidate_files:
                            # Ordinal heuristics: "first", "second", "last"
                            if "first" in prompt_lower or "1st" in prompt_lower:
                                target_file_path = candidate_files[0]["path"]
                            elif "second" in prompt_lower or "2nd" in prompt_lower and len(candidate_files) > 1:
                                target_file_path = candidate_files[1]["path"]
                            elif "last" in prompt_lower:
                                target_file_path = candidate_files[-1]["path"]

                        # Check if explicit file path or filename is mentioned in text
                        if not target_file_path:
                            path_match = re.search(r'["\']([a-zA-Z]:[\\/][^"\']+)["\']', text) or re.search(r'["\'](/[^"\']+)["\']', text)
                            if not path_match:
                                path_match = re.search(r'\b([a-zA-Z]:[\\/][^\s"\']+)', text)
                            if path_match:
                                target_file_path = path_match.group(1).strip()

                        # Defensive check: if target_file_path is missing, avoid broken open_file execution
                        if not target_file_path:
                            if any(w in prompt_lower for w in ["search", "find", "locate", "look for", "show", "is there", "where"]):
                                action = "search_files"
                                pattern = self._extract_search_pattern(text)
                                payload = {"directory_path": folder_path, "pattern": pattern, "query": pattern, "recursive": True}
                            elif any(w in prompt_lower for w in ["list", "what is inside", "show files"]):
                                action = "list_directory"
                                payload = {"directory_path": folder_path}
                            else:
                                return RouteDecision(
                                    intent=IntentType.GENERAL_QUERY,
                                    confidence=0.85,
                                    target_service="llm-chat",
                                    requires_deep_reasoning=False,
                                    structured_action="chat_completion",
                                    structured_payload={"prompt": text},
                                    latency_ms=round(latency, 2),
                                )
                        else:
                            payload = {
                                "file_path": target_file_path,
                                "path": target_file_path,
                                "directory_path": folder_path,
                            }

                    else:  # default: search_files
                        action = "search_files"
                        pattern = self._extract_search_pattern(text)
                        payload = {
                            "directory_path": folder_path,
                            "pattern": pattern,
                            "query": pattern,
                            "recursive": True,
                        }

                return RouteDecision(
                    intent=IntentType.FILE_MANAGEMENT,
                    confidence=max(confidence, 0.92),
                    target_service="windows-agent",
                    requires_deep_reasoning=False,
                    structured_action=action,
                    structured_payload=payload,
                    latency_ms=round(latency, 2),
                )

            # -------------------------------------------------------------
            # Branch 2: Scheduled Reminders
            # -------------------------------------------------------------
            elif choice == "reminder":
                payload = system_one_classifier._extract_reminder_payload(text)
                return RouteDecision(
                    intent=IntentType.REMINDER,
                    confidence=max(confidence, 0.90),
                    target_service="automation-service",
                    requires_deep_reasoning=False,
                    structured_action="create_reminder",
                    structured_payload=payload,
                    latency_ms=round(latency, 2),
                )

            # -------------------------------------------------------------
            # Branch 3: Desktop Automation & System Telemetry
            # -------------------------------------------------------------
            elif choice == "desktop_automation":
                desktop_decision = system_one_classifier._classify_desktop_action(text)
                if desktop_decision:
                    action, payload, desk_conf = desktop_decision
                elif any(w in prompt_lower for w in ["telemetry", "battery", "cpu", "ram", "memory", "system status", "system", "hardware"]):
                    action = "system_telemetry"
                    payload = {"action": "system_telemetry"}
                else:
                    return RouteDecision(
                        intent=IntentType.GENERAL_QUERY,
                        confidence=confidence,
                        target_service="llm-chat",
                        requires_deep_reasoning=True,
                        structured_action="chat_completion",
                        structured_payload={"prompt": text},
                        latency_ms=round(latency, 2),
                    )
                return RouteDecision(
                    intent=IntentType.DESKTOP_AUTOMATION,
                    confidence=max(confidence, 0.88),
                    target_service="windows-agent",
                    requires_deep_reasoning=False,
                    structured_action=action,
                    structured_payload=payload,
                    latency_ms=round(latency, 2),
                )

            # -------------------------------------------------------------
            # Branch 4: Web Research
            # -------------------------------------------------------------
            elif choice == "web_research":
                return RouteDecision(
                    intent=IntentType.WEB_RESEARCH,
                    confidence=max(confidence, 0.85),
                    target_service="web-research",
                    requires_deep_reasoning=True,
                    structured_action="search_web",
                    structured_payload={"query": text},
                    latency_ms=round(latency, 2),
                )

            # -------------------------------------------------------------
            # Branch 5: General Query (LLM Chat)
            # -------------------------------------------------------------
            else:
                return RouteDecision(
                    intent=IntentType.GENERAL_QUERY,
                    confidence=confidence,
                    target_service="llm-chat",
                    requires_deep_reasoning=True,
                    structured_action="chat_completion",
                    structured_payload={"prompt": text},
                    latency_ms=round(latency, 2),
                )

        except Exception as e:
            logger.error("Laya neural inference failed (%s); falling back to heuristic System One", e)
            return system_one_classifier.classify(request)


# Singleton instance for the service
neural_laya_classifier = NeuralLayaClassifier()
