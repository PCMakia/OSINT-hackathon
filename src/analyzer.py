"""Anthropic synthesis layer for OSINT dossiers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

SYNTHESIS_TIMEOUT_SECONDS = 12.0
MODEL_NAME = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 2000

_anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

ANALYSIS_SYSTEM_PROMPT = """You are an elite OSINT Intelligence Analyst specializing in consumer hardware and AI agents.
Analyze the provided web search context and generate a Markdown Intelligence Dossier.

For hardware and AI agent queries, you MUST extract and evaluate:
1. **Form Factor Matrix:** Compare physical hardware specs (e.g., 5.5" 3D Holographic Display vs. Flat Screen AI Avatars).
2. **Architecture:** Evaluate compute routing (Local Edge LLM execution vs. Cloud API dependencies & latency).
3. **Competitive Landscape:** Position against key competitors (e.g., Gatebox, Software Desktop Companions, AI Pin/Wearables).
4. **Source Credibility & Contradiction Mapping:** Rate each source (High/Medium/Low) and highlight discrepancies between Official PR, Tech Benchmarks, and Leaks.

Format with clear headers, bulleted takeaways, and source credibility tags."""


def _format_search_results(search_results: list[Any]) -> str:
    try:
        return json.dumps(search_results, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(search_results)


def _degraded_fallback(topic: str, reason: str, search_results: list[Any]) -> str:
    preview = _format_search_results(search_results)
    if len(preview) > 1200:
        preview = preview[:1200] + "\n... [truncated]"
    return (
        "## Investigation Degraded\n\n"
        f"**Status:** Anthropic API unavailable ({reason})\n"
        f"**Topic:** {topic}\n\n"
        "The cognitive engine timed out or failed. No live dossier could be synthesized. "
        "Raw search context is attached below for manual review.\n\n"
        "### Source Credibility\n"
        "- Live ratings unavailable due to API degradation.\n\n"
        "### Contradiction Detection\n"
        "- Not evaluated (analyzer offline).\n\n"
        "### Raw Search Context\n"
        f"```json\n{preview}\n```\n"
    )


async def synthesize_dossier(topic: str, search_results: list) -> str:
    """Ask Claude 3.5 Sonnet to produce a Markdown OSINT dossier."""
    user_prompt = (
        f"Investigate this topic:\n{topic}\n\n"
        "Search results (JSON):\n"
        f"{_format_search_results(search_results)}"
    )

    async def _create_message() -> Any:
        return await _anthropic_client.messages.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

    try:
        message = await asyncio.wait_for(
            _create_message(),
            timeout=SYNTHESIS_TIMEOUT_SECONDS,
        )
        blocks = getattr(message, "content", None) or []
        texts: list[str] = []
        for block in blocks:
            text = getattr(block, "text", None)
            if text:
                texts.append(text)
        dossier = "\n".join(texts).strip()
        if not dossier:
            return _degraded_fallback(topic, "empty model response", search_results)
        return dossier
    except asyncio.TimeoutError:
        logger.exception(
            "Anthropic synthesis timed out after %.1fs: %s",
            SYNTHESIS_TIMEOUT_SECONDS,
            topic,
        )
        return _degraded_fallback(
            topic,
            f"timeout after {SYNTHESIS_TIMEOUT_SECONDS:.1f}s",
            search_results,
        )
    except Exception as exc:
        logger.exception("Anthropic synthesis failed: %s", topic)
        return _degraded_fallback(topic, str(exc), search_results)
