"""
Neural Laya System One Decision Classifier.
Uses Convai Innovations' Laya (ModernBERT-large based non-autoregressive decision model)
for zero-shot semantic intent routing and structured tool classification.
"""
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, Optional

from contracts.router.models import IntentType, RouteDecision, RouteRequest
from decision_router.classifiers.base import BaseClassifier
from decision_router.classifiers.system_one import system_one_classifier

logger = logging.getLogger("decision_router.classifiers.laya")


class NeuralLayaClassifier(BaseClassifier):
    """
    Adapter for the open-weights 'convaiinnovations/laya' ModernBERT-large classifier.
    Performs zero-shot intent routing across assistant capabilities:
      - file_management       -> windows-agent (File tools)
      - desktop_automation    -> windows-agent (Telemetry & Apps)
      - reminder              -> automation-service
      - web_research          -> web-research
      - general_query         -> local Ollama conversational chat
    """

    def __init__(self, model_name: str = "convaiinnovations/laya"):
        self.model_name = model_name
        self._agent = None
        self._load_error: Optional[str] = None
        self._is_loaded = False

    def is_available(self) -> bool:
        """Checks if the laya library is installed and available in python."""
        if self._is_loaded and self._agent is not None:
            return True
        try:
            import laya  # noqa: F401
            return True
        except ImportError:
            return False

    def load_model(self) -> bool:
        """Loads the weights into RAM/VRAM if not already loaded."""
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

    def classify(self, request: RouteRequest) -> RouteDecision:
        """
        Classifies intent using neural ModernBERT-large weights.
        Gracefully falls back to heuristic System One if the model fails or is unready.
        """
        start_time = time.perf_counter()
        text = request.prompt.strip()

        # If neural model is unavailable or failed to load, transparently fall back
        if not self.is_available() or not self.load_model():
            logger.warning(
                "Neural Laya unavailable (%s); using heuristic System One.",
                self._load_error or "package not installed",
            )
            return system_one_classifier.classify(request)

        try:
            import laya
            res = laya.decide(
                self._agent,
                text,
                questions={
                    "intent": {
                        "instructions": "What type of assistant task or tool should handle this request?",
                        "type": "choice",
                        "criteria": [
                            "file_management",
                            "desktop_automation",
                            "reminder",
                            "web_research",
                            "general_query",
                        ],
                    }
                },
            )
            intent_res = res.get("intent", {})
            choice = intent_res.get("choice", "general_query")
            confidence = float(intent_res.get("confidence", 0.85))
            latency = (time.perf_counter() - start_time) * 1000

            # 1. File Management
            if choice == "file_management":
                file_decision = system_one_classifier._classify_file_action(text)
                if file_decision:
                    action, payload, file_conf = file_decision
                else:
                    action = "list_directory"
                    payload = {"directory_path": system_one_classifier.KNOWN_FOLDERS.get("downloads")}
                return RouteDecision(
                    intent=IntentType.FILE_MANAGEMENT,
                    confidence=max(confidence, 0.85),
                    target_service="windows-agent",
                    requires_deep_reasoning=False,
                    structured_action=action,
                    structured_payload=payload,
                    latency_ms=round(latency, 2),
                )

            # 2. Reminder
            elif choice == "reminder":
                payload = system_one_classifier._extract_reminder_payload(text)
                return RouteDecision(
                    intent=IntentType.REMINDER,
                    confidence=max(confidence, 0.88),
                    target_service="automation-service",
                    requires_deep_reasoning=False,
                    structured_action="create_reminder",
                    structured_payload=payload,
                    latency_ms=round(latency, 2),
                )

            # 3. Desktop Automation
            elif choice == "desktop_automation":
                desktop_decision = system_one_classifier._classify_desktop_action(text)
                if desktop_decision:
                    action, payload, desk_conf = desktop_decision
                else:
                    action = "system_telemetry"
                    payload = {"action": "system_telemetry"}
                return RouteDecision(
                    intent=IntentType.DESKTOP_AUTOMATION,
                    confidence=max(confidence, 0.85),
                    target_service="windows-agent",
                    requires_deep_reasoning=False,
                    structured_action=action,
                    structured_payload=payload,
                    latency_ms=round(latency, 2),
                )

            # 4. Web Research
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

            # 5. General Query / LLM Chat
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
