import json
import logging
from typing import Any, Dict, List, Optional
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
        Generates conversational response using configured provider:
        1. Google Gemini (fastest, free tier, <400ms)
        2. Groq (ultra-fast Llama-3.3-70B, <300ms)
        3. OpenAI / compatible
        4. Local Ollama (fallback)
        """
        # 1. Google Gemini Cloud API
        if settings.GEMINI_API_KEY:
            resp = self._call_gemini_chat(prompt)
            if resp:
                return resp

        # 2. Groq Cloud API (Llama 3.3 70B)
        if settings.GROQ_API_KEY:
            resp = self._call_openai_compatible_chat(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL,
                prompt=prompt,
            )
            if resp:
                return resp

        # 3. OpenAI Cloud API
        if settings.OPENAI_API_KEY:
            resp = self._call_openai_compatible_chat(
                base_url=settings.OPENAI_BASE_URL,
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                prompt=prompt,
            )
            if resp:
                return resp

        # 4. Local Ollama instance (fallback)
        return self._call_ollama_chat(prompt)

    def _get_gemini_models(self) -> List[str]:
        configured = settings.GEMINI_MODEL or "gemini-3.8-flash"
        defaults = [
            configured,
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-3.5-flash",
            "gemini-flash-latest",
        ]
        seen = set()
        return [x for x in defaults if not (x in seen or seen.add(x))]

    def _call_gemini_chat(self, prompt: str) -> Optional[str]:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY,
        }
        payload = {
            "contents": [
                {
                    "parts": [{"text": f"{CHAT_SYSTEM_PROMPT}\n\nUser request: {prompt}"}]
                }
            ],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 400},
        }

        for model_name in self._get_gemini_models():
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            try:
                with httpx.Client(timeout=6.0, headers=headers) as client:
                    resp = client.post(f"{url}?key={settings.GEMINI_API_KEY}", json=payload)
                    if resp.status_code in (404, 500, 503, 429):
                        logger.info(f"Gemini {model_name} returned {resp.status_code}; trying next candidate.")
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip()
            except Exception as e:
                logger.warning(f"Error calling Gemini with model {model_name}: {e}")

        return None

    def _call_openai_compatible_chat(
        self, base_url: str, api_key: str, model: str, prompt: str
    ) -> Optional[str]:
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 400,
        }
        try:
            with httpx.Client(base_url=base_url, timeout=6.0, headers=headers) as client:
                resp = client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.warning(f"Error calling cloud LLM at {base_url}: {e}")
        return None

    def _call_ollama_chat(self, prompt: str) -> Optional[str]:
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
            with httpx.Client(base_url=self.base_url, timeout=4.0) as client:
                resp = client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "").strip()
                if content:
                    return content
        except Exception as e:
            logger.debug(f"Local Ollama server not reachable for chat at {self.base_url}: {e}")
            return None

    def extract_file_parameters(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Extracts structured JSON parameters using Cloud LLM or local Ollama.
        """
        # 1. Google Gemini
        if settings.GEMINI_API_KEY:
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": settings.GEMINI_API_KEY,
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"{EXTRACTION_SYSTEM_PROMPT}\n\nCommand: {prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json",
                },
            }

            for model_name in self._get_gemini_models():
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                try:
                    with httpx.Client(timeout=6.0, headers=headers) as client:
                        resp = client.post(f"{url}?key={settings.GEMINI_API_KEY}", json=payload)
                        if resp.status_code in (404, 500, 503, 429):
                            continue
                        resp.raise_for_status()
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            parsed = json.loads(text)
                            return {k: v for k, v in parsed.items() if v is not None}
                except Exception as e:
                    logger.warning(f"Error extracting parameters with Gemini ({model_name}): {e}")

        # 2. Local Ollama fallback
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
            with httpx.Client(base_url=self.base_url, timeout=4.0) as client:
                resp = client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                parsed = json.loads(content)
                return {k: v for k, v in parsed.items() if v is not None}
        except Exception as e:
            logger.debug(f"Local Ollama server not reachable at {self.base_url}: {e}")
            return None


llm_extractor = LLMToolExtractor()
