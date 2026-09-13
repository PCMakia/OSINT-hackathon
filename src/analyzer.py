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

SYSTEM_PROMPT = """You are an OSINT Intelligence Detective. Synthesize open-source findings into a clean Markdown dossier.

Required structure:
1. **Executive Summary** — 2–4 sentences on what is known from the supplied sources.
2. **Key Findings** — grouped bullets, each citing the source title or URL when available.
3. **Source Credibility** — a table or bullet list rating every source High / Medium / Low, with a one-line justification (publisher reputation, recency, primary vs secondary, corroboration).
4. **Contradiction Detection** — explicitly call out conflicting claims across sources. If none, state "No material contradictions detected."
5. **Intelligence Gaps** — what could not be verified from the provided material.
6. **Disclaimer** — this is open-source research, not legal, financial, or operational advice.

Rules:
- Use only the supplied search results. Do not invent URLs, quotes, or facts.
- If results are empty, cached, or marked as fallback/degraded, say so clearly at the top.
- Keep the dossier concise and scannable.
- Prefer professional, neutral intelligence language.
"""


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
            system=SYSTEM_PROMPT,
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
