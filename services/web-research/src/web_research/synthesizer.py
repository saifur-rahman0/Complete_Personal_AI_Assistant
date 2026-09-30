import logging
import uuid
from datetime import datetime, timezone
from typing import List
import httpx
from contracts.research.models import ResearchReport, WebSourceResult
from web_research.config import settings

logger = logging.getLogger("web_research.synthesizer")


class ResearchSynthesizer:
    def synthesize_report(
        self,
        query: str,
        sources: List[WebSourceResult],
    ) -> ResearchReport:
        """Synthesizes multiple crawled sources into a structured research report."""
        report_id = str(uuid.uuid4())
        valid_sources = [s for s in sources if s.status == "success" and s.content_markdown]

        if not valid_sources:
            return ResearchReport(
                id=report_id,
                query=query,
                summary=f"No accessible public web sources could be retrieved for query '{query}'.",
                key_findings=["All target sources were blocked by security policies or unreachable."],
                sources=sources,
                created_at=datetime.now(timezone.utc),
            )

        # 1. Try local LLM synthesis if Ollama is available
        llm_summary = self._call_ollama_synthesis(query, valid_sources)
        if llm_summary:
            summary_text, bullet_points = llm_summary
        else:
            # 2. Heuristic extraction fallback
            summary_text, bullet_points = self._heuristic_synthesis(query, valid_sources)

        return ResearchReport(
            id=report_id,
            query=query,
            summary=summary_text,
            key_findings=bullet_points,
            sources=sources,
            created_at=datetime.now(timezone.utc),
        )

    def _call_ollama_synthesis(
        self,
        query: str,
        sources: List[WebSourceResult],
    ):
        """Attempts to invoke Ollama for structured report synthesis."""
        combined_context = "\n\n---\n\n".join(
            [f"Source: {s.title} ({s.url})\n\n{s.content_markdown[:1500]}" for s in sources[:3]]
        )

        prompt = (
            f"You are a research assistant synthesizing web findings for the query: '{query}'.\n"
            f"Here are the source excerpts:\n{combined_context}\n\n"
            f"Provide a 2-paragraph summary followed by 3-5 concise key takeaways."
        )

        try:
            with httpx.Client(base_url=settings.OLLAMA_BASE_URL, timeout=10.0) as client:
                res = client.post(
                    "/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                if res.status_code == 200:
                    text = res.json().get("response", "").strip()
                    lines = text.split("\n")
                    bullets = [l.lstrip("-* ").strip() for l in lines if l.strip().startswith(("-", "*"))]
                    return text, bullets or ["Synthesized with local LLM."]
        except Exception:
            pass

        return None

    def _heuristic_synthesis(
        self,
        query: str,
        sources: List[WebSourceResult],
    ):
        """Clean heuristic synthesis when running offline."""
        summary = (
            f"Research investigation for '{query}' successfully gathered information from "
            f"{len(sources)} source(s). Sources include {', '.join([s.title or s.url for s in sources])}."
        )

        bullets = []
        for s in sources:
            snippet = s.snippet or "Key reference material."
            bullets.append(f"[{s.title or 'Source'}] {snippet}")

        return summary, bullets


research_synthesizer = ResearchSynthesizer()
