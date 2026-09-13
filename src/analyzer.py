"""Anthropic synthesis layer for OSINT dossiers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY
from templates import HARDWARE_OSINT_TEMPLATE, select_system_prompt

logger = logging.getLogger(__name__)

SYNTHESIS_TIMEOUT_SECONDS = 12.0
MODEL_NAME = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 2000

_anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


def _format_search_results(search_results: list[Any]) -> str:
    try:
        return json.dumps(search_results, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(search_results)


def _prepare_discord_markdown(text: str) -> str:
    """Strip a wrapping fence so Discord splits clean Markdown, not a code block."""
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[: -3].rstrip()
    return stripped.strip()


def _degraded_fallback(topic: str, reason: str, search_results: list[Any]) -> str:
    preview = _format_search_results(search_results)
    if len(preview) > 1200:
        preview = preview[:1200] + "\n... [truncated]"
    return (
        "## Executive Summary\n\n"
        f"Anthropic API degradation ({reason}) blocked live synthesis for **{topic}**. "
        "Treat the tables below as structural placeholders, not verified intelligence.\n\n"
        "## ⚠️ Contradiction & Discrepancy Alert\n\n"
        "> Contradiction mapping was not evaluated because the cognitive engine timed out or failed. "
        "Official PR, benchmark, and leak claims could not be cross-checked.\n\n"
        "## Form Factor & Technical Specs Matrix\n\n"
        "| Dimension | Subject Device | Comparison Notes |\n"
        "| --- | --- | --- |\n"
        "| Display / Form Factor | Not evidenced in sources | Analyzer offline |\n"
        "| AI Engine | Not evidenced in sources | Analyzer offline |\n"
        "| Latency | Not evidenced in sources | Analyzer offline |\n"
        "| Power / Connectivity | Not evidenced in sources | Analyzer offline |\n\n"
        "## Competitive Positioning\n\n"
        "- Gatebox: not evaluated (API degradation).\n"
        "- Software desktop companions: not evaluated (API degradation).\n\n"
        "## Source Credibility & Verification Tier\n\n"
        "| Source URL | Type | Credibility Rating | Rationale |\n"
        "| --- | --- | --- | --- |\n"
        "| Not evidenced in sources | Bench | Low | Live ratings unavailable due to API degradation |\n\n"
        "Cached or raw search context for manual review:\n\n"
        f"```json\n{preview}\n```\n"
    )


async def synthesize_dossier(topic: str, search_results: list) -> str:
    """Ask Claude 3.5 Sonnet to produce a Markdown OSINT dossier."""
    system_prompt = select_system_prompt(topic) or HARDWARE_OSINT_TEMPLATE
    user_prompt = (
        f"Investigate this topic:\n{topic}\n\n"
        "Search results (JSON):\n"
        f"{_format_search_results(search_results)}\n\n"
        "Follow the system template exactly. Output valid Markdown only, ready to post in Discord."
    )

    async def _create_message() -> Any:
        return await _anthropic_client.messages.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
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
        dossier = _prepare_discord_markdown("\n".join(texts))
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
