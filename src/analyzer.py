"""Anthropic synthesis layer for OSINT dossiers."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY
from templates import HARDWARE_OSINT_TEMPLATE, select_system_prompt

logger = logging.getLogger(__name__)

SYNTHESIS_TIMEOUT_SECONDS = 45.0
MODEL_NAME = "claude-sonnet-4-6"
MAX_TOKENS = 1500
TEMPERATURE = 0.2
CONCISE_SYSTEM = (
    "You are a concise OSINT research analyst. "
    "Output crisp, well-formatted Markdown tables without fluff."
)

_anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

_COMPETITOR_RE = re.compile(
    r"(Gatebox|Desktop Goose|AI Avatars?|AI Pin|software desktop companions?|"
    r"flat-screen software companions?|desktop software companions?)",
    re.IGNORECASE,
)


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


def _as_items(raw_results: list[Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for entry in raw_results or []:
        if not isinstance(entry, dict):
            text = str(entry).strip()
            if text:
                items.append(
                    {
                        "title": text[:120],
                        "url": "",
                        "content": text,
                        "credibility_tier": "",
                    }
                )
            continue
        content = str(
            entry.get("content")
            or entry.get("snippet")
            or entry.get("detail")
            or entry.get("summary")
            or ""
        ).strip()
        items.append(
            {
                "title": str(entry.get("title") or entry.get("name") or "").strip(),
                "url": str(entry.get("url") or entry.get("link") or "").strip(),
                "content": content,
                "credibility_tier": str(entry.get("credibility_tier") or "").strip(),
            }
        )
    return items


def _md_cell(value: str) -> str:
    cleaned = " ".join((value or "").replace("|", "/").split())
    return cleaned or "—"


def _corpus(items: list[dict[str, str]]) -> str:
    return " ".join(part for item in items for part in (item["title"], item["content"]) if part)


def _first_match(pattern: str, text: str, flags: int = re.IGNORECASE) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(0).strip() if match else None


def _source_type(item: dict[str, str]) -> str:
    blob = f"{item['credibility_tier']} {item['title']}".casefold()
    if "official" in blob or re.search(r"\bpr\b", blob):
        return "PR"
    if "leak" in blob:
        return "Leak"
    if "bench" in blob or "market" in blob or "analysis" in blob:
        return "Bench"
    return "Bench"


def _credibility_rating(item: dict[str, str]) -> str:
    tier = item["credibility_tier"]
    match = re.match(r"\s*(High|Medium|Low)\b", tier, re.IGNORECASE)
    if match:
        return match.group(1).title()
    source_type = _source_type(item)
    if source_type == "PR":
        return "High"
    if source_type in {"Leak", "Bench"}:
        return "Medium"
    return "Medium"


def _extract_spec_rows(items: list[dict[str, str]]) -> list[tuple[str, str, str]]:
    text = _corpus(items)
    display_bits: list[str] = []
    for pattern in (
        r"\d+(?:\.\d+)?\s*(?:inch|in)\s+3D holographic display",
        r"\d+(?:\.\d+)?\s*(?:inch|in)[^\.]{0,60}display",
        r"3D holographic display",
        r"animated [^\.]{0,80}display",
        r"volumetric presence",
        r"integrated camera, microphone, and speaker array",
    ):
        hit = _first_match(pattern, text)
        if hit and hit not in display_bits:
            display_bits.append(hit)

    engine_bits: list[str] = []
    for pattern in (
        r"hybrid architecture[^\.]{0,160}",
        r"local micro-models[^\.]{0,120}",
        r"deep LLM processing offloads to cloud endpoints",
        r"real-time audio and vision sensing",
    ):
        hit = _first_match(pattern, text)
        if hit and hit not in engine_bits:
            engine_bits.append(hit.rstrip(" ."))

    latency_bits: list[str] = []
    for pattern in (
        r"\d+\s*ms local response latency",
        r"\d+\s*ms full cloud cycles?",
        r"\d+\s*ms[^\.]{0,40}",
    ):
        hit = _first_match(pattern, text)
        if hit and hit not in latency_bits:
            latency_bits.append(hit)

    power_bits: list[str] = []
    for pattern in (
        r"camera, microphone, and speaker array",
        r"cloud endpoints",
        r"consumer peripheral price point",
    ):
        hit = _first_match(pattern, text)
        if hit and hit not in power_bits:
            power_bits.append(hit)

    comparison_display = (
        "Physical 3D volumetric desk presence vs flat-screen software avatars"
        if re.search(r"flat-screen|volumetric|holograph", text, re.I)
        else "Form-factor comparisons drawn from cached snippets"
    )
    comparison_engine = (
        "Local wake/vision path with cloud LLM offload vs fully on-device or fully cloud peers"
        if re.search(r"hybrid|cloud|local micro-models", text, re.I)
        else "Architecture notes drawn from cached snippets"
    )
    comparison_latency = (
        "Local path vs full cloud cycle as reported in cached benchmarks"
        if re.search(r"\bms\b|latency", text, re.I)
        else "No latency figures in cached snippets"
    )
    comparison_power = (
        "Desk-peripheral I/O with cloud-backed inference where snippets mention connectivity"
        if power_bits
        else "No explicit power envelope in cached snippets"
    )

    def _join(parts: list[str], empty: str) -> str:
        return "; ".join(parts) if parts else empty

    return [
        (
            "Display / Form Factor",
            _join(display_bits, "No display or form-factor details in cached snippets"),
            comparison_display,
        ),
        (
            "AI Engine",
            _join(engine_bits, "No AI-engine details in cached snippets"),
            comparison_engine,
        ),
        (
            "Latency",
            _join(latency_bits, "No latency measurements in cached snippets"),
            comparison_latency,
        ),
        (
            "Power / Connectivity",
            _join(power_bits, "No power or connectivity details in cached snippets"),
            comparison_power,
        ),
    ]


def _extract_competitor_bullets(items: list[dict[str, str]]) -> list[str]:
    bullets: list[str] = []
    seen: set[str] = set()
    for item in items:
        blob = f"{item['title']}. {item['content']}".strip()
        if not _COMPETITOR_RE.search(blob):
            continue
        sentences = re.split(r"(?<=[.!?])\s+", blob)
        matched = [sentence.strip() for sentence in sentences if _COMPETITOR_RE.search(sentence)]
        excerpt = " ".join(matched) if matched else blob
        citation = item["title"] or item["url"]
        line = f"- {excerpt}"
        if citation:
            line += f" ({citation})"
        key = excerpt.casefold()
        if key in seen:
            continue
        seen.add(key)
        bullets.append(line)
    if not bullets:
        bullets.append(
            "- No competitor names (for example Gatebox or software desktop companions) "
            "appeared in the cached OSINT snippets."
        )
    return bullets


def _contradiction_blockquote(items: list[dict[str, str]]) -> str:
    pr_bits = [item["content"] for item in items if _source_type(item) == "PR" and item["content"]]
    other_bits = [
        item["content"]
        for item in items
        if _source_type(item) in {"Leak", "Bench"} and item["content"]
    ]
    if pr_bits and other_bits:
        pr_cloud = bool(re.search(r"cloud|latency|hybrid", " ".join(pr_bits), re.I))
        other_cloud = bool(re.search(r"cloud|latency|hybrid|teardown|leak", " ".join(other_bits), re.I))
        if other_cloud and not pr_cloud:
            return (
                "> Official PR frames an interactive 3D desktop avatar with on-desk sensing, "
                "while benchmark/leak snippets describe a hybrid stack (local micro-models for "
                "wake/vision versus cloud LLM cycles and published millisecond timings). "
                "Treat cloud-offload and latency figures as unverified against the official page."
            )
        return (
            "> Cached Official PR, benchmark, and leak/market snippets emphasize different layers "
            "(product experience vs architecture vs competitive price/form factor). "
            "Those are complementary cuts of the same record unless a spec is stated twice and disagrees."
        )
    if items:
        return (
            "> No direct Official PR vs benchmark vs leak clash was extractable from the cached "
            "snippets; claims below stay tagged to their source tier."
        )
    return (
        "> No cached sources were available to compare Official PR, benchmarks, and leaks."
    )


def build_offline_dossier(topic: str, raw_results: list) -> str:
    """Build a Discord-ready Markdown dossier from cached OSINT items (no live LLM)."""
    items = _as_items(raw_results)
    titles = [item["title"] for item in items if item["title"]]
    headline = titles[0] if titles else topic
    source_count = len(items)

    if source_count:
        summary = (
            f"**{topic}** is synthesized from **{source_count} cached OSINT source"
            f"{'s' if source_count != 1 else ''}** (offline fallback; Anthropic did not generate "
            f"this dossier). Public record centers on {headline}, with hardware, architecture, "
            "and competitive claims taken only from those cached snippets."
        )
    else:
        summary = (
            f"**{topic}** is synthesized from cached OSINT data, but this query had no stored "
            "search items. No live model output is included."
        )

    spec_rows = _extract_spec_rows(items)
    spec_table = [
        "| Dimension | Subject Device | Comparison Notes |",
        "| --- | --- | --- |",
    ]
    for dimension, subject, notes in spec_rows:
        spec_table.append(
            f"| {_md_cell(dimension)} | {_md_cell(subject)} | {_md_cell(notes)} |"
        )

    cred_table = [
        "| Source URL | Type | Credibility Rating | Rationale |",
        "| --- | --- | --- | --- |",
    ]
    if items:
        for item in items:
            url = item["url"] or item["title"] or "Cached source without URL"
            source_type = _source_type(item)
            rating = _credibility_rating(item)
            rationale = item["credibility_tier"] or item["title"] or "Cached OSINT snippet"
            cred_table.append(
                f"| {_md_cell(url)} | {_md_cell(source_type)} | {_md_cell(rating)} | {_md_cell(rationale)} |"
            )
    else:
        cred_table.append(
            "| No cached source URL | — | — | No cached OSINT items were stored for this query |"
        )

    sections = [
        "## Executive Summary",
        "",
        summary,
        "",
        "## ⚠️ Contradiction & Discrepancy Alert",
        "",
        _contradiction_blockquote(items),
        "",
        "## Form Factor & Technical Specs Matrix",
        "",
        *spec_table,
        "",
        "## Competitive Positioning",
        "",
        *_extract_competitor_bullets(items),
        "",
        "## Source Credibility & Verification Tier",
        "",
        *cred_table,
        "",
    ]
    return "\n".join(sections)


HEALTH_PING_TIMEOUT_SECONDS = 2.0


async def check_anthropic_health() -> str:
    """Fast Anthropic reachability check. Returns Online or Degraded."""
    if not ANTHROPIC_API_KEY:
        return "Degraded"

    async def _ping() -> None:
        models = getattr(_anthropic_client, "models", None)
        list_models = getattr(models, "list", None) if models is not None else None
        if callable(list_models):
            await list_models()
            return
        await _anthropic_client.messages.create(
            model=MODEL_NAME,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )

    try:
        await asyncio.wait_for(_ping(), timeout=HEALTH_PING_TIMEOUT_SECONDS)
        return "Online"
    except Exception:
        logger.warning("Anthropic health ping failed or timed out", exc_info=True)
        return "Degraded"


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
            temperature=TEMPERATURE,
            system=f"{CONCISE_SYSTEM}\n\n{system_prompt}",
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
            logger.error("Anthropic API Error: empty model response")
            return build_offline_dossier(topic, search_results)
        return dossier
    except asyncio.TimeoutError:
        logger.error("Anthropic API Error: Request timed out after 45s")
        return build_offline_dossier(topic, search_results)
    except Exception as e:
        logger.error(f"Anthropic API Error: {type(e).__name__} - {e}")
        return build_offline_dossier(topic, search_results)
