import json
import logging
from typing import Any, Dict, Optional
import httpx
from decision_router.config import settings

logger = logging.getLogger("decision_router.llm")

EXTRACTION_SYSTEM_PROMPT = """You are an AI tool parameter extractor for a personal assistant.
Given a user command, extract structured parameters for file operations.
Return ONLY valid JSON matching this schema:
{
  "action": "list_directory" | "search_files" | "move_file" | "organize_folder",
  "directory_path": "string path or null",
  "source_path": "string path or null",
  "destination_path": "string path or null",
  "pattern": "string pattern or null",
  "strategy": "by_extension" | "by_date" | null,
  "dry_run": boolean
}
Do not include any conversational text or explanation. Only return JSON.
"""


CHAT_SYSTEM_PROMPT = """You are Jarvis, a capable, polite, and responsive personal AI assistant for Windows and mobile devices.
Assist the user concisely and helpfully.
If the user greets you or asks who you are, greet them warmly and briefly mention what you can do (file management, desktop automation, reminders, web research).
Keep your answers direct, friendly, and under 3-4 sentences unless asked for more details."""


class LLMToolExtractor:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL

    def generate_chat_response(self, prompt: str) -> Optional[str]:
        """
        Queries local Ollama instance (Qwen 2.5) for conversational responses.
        Returns generated text or None if Ollama is unreachable.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.7},
        }

        try:
            with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
                resp = client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "").strip()
                if content:
                    return content
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.debug(f"Local Ollama server not reachable for chat at {self.base_url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error during Ollama chat generation: {e}")
            return None
        return None

    def extract_file_parameters(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Queries local Ollama instance with Qwen 2.5 to extract structured JSON parameters.
        Returns extracted dictionary, or None if Ollama is unreachable.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0},
        }

        try:
            with httpx.Client(base_url=self.base_url, timeout=5.0) as client:
                resp = client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                parsed = json.loads(content)
                return {k: v for k, v in parsed.items() if v is not None}
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.debug(f"Local Ollama server not reachable at {self.base_url}: {e}")
            return None
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error parsing Ollama output: {e}")
            return None


llm_extractor = LLMToolExtractor()
