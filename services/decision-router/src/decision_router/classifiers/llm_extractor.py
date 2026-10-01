import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from decision_router.config import settings

logger = logging.getLogger("decision_router.llm")

EXTRACTION_SYSTEM_PROMPT = """You are an AI tool parameter extractor for a personal assistant.
Given the current user command and recent conversation context (such as previously searched or listed files), extract structured parameters for file operations.
If the user refers to previous files (e.g. "open the first one", "read the resume", "delete it", "show that file"), resolve the exact file path from the conversation history.

Return ONLY valid JSON matching this schema:
{
  "action": "list_directory" | "search_files" | "read_file" | "open_file" | "move_file" | "rename_file" | "delete_file" | "organize_folder",
  "file_path": "string absolute path or null",
  "new_name": "string new filename with extension or null",
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

    def generate_chat_response(
        self, prompt: str, history: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """
        Generates conversational response using configured provider with multi-turn context:
        1. Google Gemini (gemini-3.8-flash)
        2. Groq (Llama-3.3-70B)
        3. OpenAI / compatible
        4. Local Ollama (fallback)
        """
        # 1. Google Gemini Cloud API
        if settings.GEMINI_API_KEY:
            resp = self._call_gemini_chat(prompt, history=history)
            if resp:
                return resp

        # 2. Groq Cloud API (Llama 3.3 70B)
        if settings.GROQ_API_KEY:
            resp = self._call_openai_compatible_chat(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL,
                prompt=prompt,
                history=history,
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
                history=history,
            )
            if resp:
                return resp

        # 4. Local Ollama instance (fallback)
        return self._call_ollama_chat(prompt, history=history)

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

    @staticmethod
    def prune_text(text: str, max_chars: int = 300) -> str:
        """
        Prunes raw file dumps, markdown link collections, and long file paths
        to reduce token consumption by up to 90%.
        """
        import re
        if not text:
            return ""
        # Collapse lists of markdown file links into a compact summary
        links = re.findall(r"\[([^\]]+)\]\((?:file:///)?([^\)]+)\)", text)
        if len(links) > 2:
            summary = f"[{len(links)} files listed: {', '.join(links[:3])}...]"
            text = re.sub(r"(•\s*)?\[[^\]]+\]\((?:file:///)?([^\)]+)\)(\s*[—\-•]\s*`?[^`\n]*`?)?", "", text)
            text = text.strip() + " " + summary

        # Collapse excess whitespace
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "..."
        return text

    def _call_gemini_chat(
        self, prompt: str, history: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY,
        }

        # Format alternating user and model turns for Gemini with pruned context
        formatted_turns = []
        last_role = None
        if history:
            for turn in history[-4:]:
                role = "user" if turn.get("role") == "user" else "model"
                raw_text = turn.get("text", "").strip()
                if not raw_text:
                    continue
                text = self.prune_text(raw_text, max_chars=300)
                if role == last_role and formatted_turns:
                    formatted_turns[-1]["parts"][0]["text"] += f"\n{text}"
                else:
                    formatted_turns.append({"role": role, "parts": [{"text": text}]})
                    last_role = role

        # Ensure first turn is from user
        if formatted_turns and formatted_turns[0]["role"] == "model":
            formatted_turns.pop(0)

        # Append current user prompt
        if formatted_turns and formatted_turns[-1]["role"] == "user":
            formatted_turns[-1]["parts"][0]["text"] += f"\n{prompt}"
        else:
            formatted_turns.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "systemInstruction": {
                "parts": [{"text": CHAT_SYSTEM_PROMPT}]
            },
            "contents": formatted_turns,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 450},
        }

        for model_name in self._get_gemini_models():
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            try:
                with httpx.Client(timeout=6.0, headers=headers) as client:
                    resp = client.post(f"{url}?key={settings.GEMINI_API_KEY}", json=payload)
                    # If systemInstruction returned 400 on older endpoint, fallback without systemInstruction
                    if resp.status_code == 400 and "systemInstruction" in payload:
                        fallback_payload = {
                            "contents": [
                                {"parts": [{"text": f"{CHAT_SYSTEM_PROMPT}\n\nContext history: {history}\n\nUser: {prompt}"}]}
                            ],
                            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 450},
                        }
                        resp = client.post(f"{url}?key={settings.GEMINI_API_KEY}", json=fallback_payload)

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
        self,
        base_url: str,
        api_key: str,
        model: str,
        prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        headers = {"Authorization": f"Bearer {api_key}"}
        messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        if history:
            for turn in history[-4:]:
                messages.append({
                    "role": "user" if turn.get("role") == "user" else "assistant",
                    "content": self.prune_text(turn.get("text", ""), max_chars=300),
                })
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
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

    def _call_ollama_chat(
        self, prompt: str, history: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        if history:
            for turn in history[-4:]:
                messages.append({
                    "role": "user" if turn.get("role") == "user" else "assistant",
                    "content": self.prune_text(turn.get("text", ""), max_chars=300),
                })
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
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

    def extract_file_parameters(
        self, prompt: str, history: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts structured JSON parameters using Cloud LLM or local Ollama with pruned conversational history.
        """
        history_context = ""
        if history:
            history_lines = []
            for h in history[-3:]:
                r = "User" if h.get("role") == "user" else "Assistant"
                raw_t = h.get("text", "").strip()
                if raw_t:
                    t = self.prune_text(raw_t, max_chars=250)
                    history_lines.append(f"{r}: {t}")
            if history_lines:
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

        prompt_with_context = f"{history_context}Current Command: {prompt}"

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
                                "text": f"{EXTRACTION_SYSTEM_PROMPT}\n\n{prompt_with_context}"
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
                {"role": "user", "content": prompt_with_context},
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

    def synthesize_file_reply(
        self,
        prompt: str,
        files: List[Dict[str, Any]],
        folder: str = "Downloads",
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """
        Gives the file list to Gemini/LLM to construct a natural, conversational reply with clickable file links.
        """
        if not files:
            return None

        file_lines = []
        for f in files[:25]:
            name = f.get("name", "")
            path = f.get("path", "")
            size = f.get("size_formatted", "")
            file_lines.append(f"- {name} (Path: {path}, Size: {size})")

        files_text = "\n".join(file_lines)

        synthesis_prompt = f"""The user asked: "{prompt}"

Here are the files found on the user's workstation in {folder}:
{files_text}

Instructions:
1. Directly and helpfully answer the user's question based on the files found.
2. For each relevant file, format it as a markdown link: [{'{filename}'}](file:///{'{path}'}) followed by its size so the user can click to interact with it.
3. Keep your response friendly, clear, and concise (2-3 sentences).
"""

        # 1. Google Gemini
        if settings.GEMINI_API_KEY:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": settings.GEMINI_API_KEY,
                }
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": synthesis_prompt}]}],
                    "generationConfig": {"temperature": 0.4, "maxOutputTokens": 450},
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
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts and "text" in parts[0]:
                                    return parts[0]["text"].strip()
                    except Exception as e:
                        logger.warning(f"Error synthesizing file reply with Gemini ({model_name}): {e}")
            except Exception as e:
                logger.warning(f"Error in Gemini synthesize_file_reply: {e}")

        # 2. Local Ollama fallback
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful desktop AI assistant. Answer directly and format files as markdown links."},
                    {"role": "user", "content": synthesis_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.4},
            }
            with httpx.Client(base_url=self.base_url, timeout=4.0) as client:
                resp = client.post("/api/chat", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("message", {}).get("content", "").strip()
                    if content:
                        return content
        except Exception:
            pass

        return None


llm_extractor = LLMToolExtractor()
