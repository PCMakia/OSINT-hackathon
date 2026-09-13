"""Discord client for the OSINT Intelligence Detective bot."""

from __future__ import annotations

import asyncio
import io
import logging
import re
import sys
import time
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

import discord

from analyzer import check_anthropic_health, synthesize_dossier
from cache import cache_storage_stats, normalize_query_key
from config import ANTHROPIC_API_KEY, DISCORD_TOKEN, TAVILY_API_KEY
from search import execute_web_search

COMMAND_PREFIX = "!investigate"
STATUS_COMMAND = "!status"
CHANNEL_CARD_LIMIT = 1500
THREAD_CHUNK_LIMIT = 1900
EXPORT_FILENAME = "Razer_AVA_Dossier.md"
TELEMETRY_COLOR = 0x2B2D31
STATUS_HEALTH_TIMEOUT_SECONDS = 2.5

total_requests = 0
successful_requests = 0
failed_requests = 0
execution_latencies: list[float] = []

GATEBOX_COMPARISON_TABLE = (
    "**Razer AVA vs Gatebox (cached OSINT)**\n\n"
    "| Spec | Razer AVA | Gatebox |\n"
    "| --- | --- | --- |\n"
    "| Price | $300–$500 target | $1,500+ |\n"
    "| Form factor | 5.5\" 3D holographic desk companion | Premium enclosed holographic companion |\n"
    "| Presence | Consumer peripheral; volumetric desk avatar | High-end physical companion (Japan-origin) |\n"
    "| AI routing | Hybrid: local micro-models + cloud LLM | App/cloud-linked companion stack |\n"
    "| Latency (cached) | ~180ms local / ~850ms full cloud cycle | Not evidenced in this dossier |\n"
    "| I/O | Camera, microphone, speaker array | Enclosed display + companion I/O |\n"
    "| Positioning | Bridges Gatebox price gap vs flat-screen software avatars | Category incumbent at luxury price |\n"
)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
_active_views: set[discord.ui.View] = set()


def _chunk_message(text: str, limit: int = THREAD_CHUNK_LIMIT) -> list[str]:
    payload = text or ""
    if len(payload) <= limit:
        return [payload] if payload else [""]
    chunks: list[str] = []
    remaining = payload
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    return chunks


def _sanitize_target(query: str) -> str:
    key = normalize_query_key(query) or (query or "Target")
    cleaned = re.sub(r"[^\w\s\-]+", "", key, flags=re.UNICODE).strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    if not cleaned:
        cleaned = "Target"
    return cleaned[:60]


def _thread_name(query: str) -> str:
    return f"OSINT-Dossier-{_sanitize_target(query)}"[:100]


def _section_text(dossier: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, dossier, re.MULTILINE | re.IGNORECASE)
    if not match:
        return ""
    rest = dossier[match.end() :]
    nxt = re.search(r"^##\s+", rest, re.MULTILINE)
    body = rest[: nxt.start()] if nxt else rest
    return body.strip()


def _build_summary_card(
    topic: str,
    dossier: str,
    *,
    fallback: bool,
    cache_hit: bool,
    thread: discord.Thread | None,
) -> str:
    header = "✨ Step 3/3: Intelligence Dossier Complete"
    source_line = "Live Tavily + Claude"
    if fallback and cache_hit:
        source_line = "Cached OSINT fallback (Tavily unavailable)"
    elif fallback:
        source_line = "Degraded run (search cache miss)"

    executive = _section_text(dossier, "Executive Summary")
    if not executive:
        executive = " ".join((dossier or "").split())

    overflow_note = ""
    if thread is not None:
        overflow_note = (
            f"\n\nFull un-truncated dossier is in thread **{thread.name}** "
            f"({thread.mention})."
        )
    elif len(dossier) > CHANNEL_CARD_LIMIT:
        overflow_note = (
            "\n\nFull dossier exceeds the channel card limit — use "
            "**Open Thread** or **Export Markdown**."
        )

    card = (
        f"{header}\n\n"
        f"**Target:** {topic}\n"
        f"**Collection:** {source_line}\n\n"
        f"{executive}"
        f"{overflow_note}\n\n"
        "Use the buttons below to export Markdown, open a dossier thread, "
        "or view the Gatebox comparison."
    )
    if len(card) <= CHANNEL_CARD_LIMIT:
        return card

    overhead = len(card) - len(executive)
    keep = max(200, CHANNEL_CARD_LIMIT - overhead - 20)
    trimmed = executive[:keep].rsplit(" ", 1)[0] + "…"
    card = (
        f"{header}\n\n"
        f"**Target:** {topic}\n"
        f"**Collection:** {source_line}\n\n"
        f"{trimmed}"
        f"{overflow_note}\n\n"
        "Use the buttons below to export Markdown, open a dossier thread, "
        "or view the Gatebox comparison."
    )
    return card[:CHANNEL_CARD_LIMIT]


async def _post_dossier_to_thread(thread: discord.Thread, dossier: str) -> None:
    for index, chunk in enumerate(_chunk_message(dossier, THREAD_CHUNK_LIMIT)):
        prefix = f"**Dossier part {index + 1}**\n" if index else ""
        await thread.send(f"{prefix}{chunk}")


class OSINTView(discord.ui.View):
    """Interactive controls attached to a completed investigation embed."""

    def __init__(
        self,
        *,
        dossier: str,
        target: str,
        status_message: discord.Message,
        thread: discord.Thread | None = None,
    ) -> None:
        super().__init__(timeout=None)
        self.dossier = dossier
        self.target = target
        self.status_message = status_message
        self.thread = thread
        self._full_posted = thread is not None

    def _markdown_file(self) -> discord.File:
        buffer = io.BytesIO(self.dossier.encode("utf-8"))
        return discord.File(buffer, filename=EXPORT_FILENAME)

    @discord.ui.button(label="📄 Export Markdown", style=discord.ButtonStyle.secondary)
    async def export_markdown(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        try:
            logger.info("Exporting dossier as %s for target=%s", EXPORT_FILENAME, self.target)
            await interaction.response.send_message(
                content=f"Full raw dossier for **{self.target}** (`{EXPORT_FILENAME}`).",
                file=self._markdown_file(),
            )
        except Exception:
            logger.exception("Failed to export markdown dossier")
            if interaction.response.is_done():
                await interaction.followup.send(
                    "Could not attach the Markdown file.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "Could not attach the Markdown file.",
                    ephemeral=True,
                )

    @discord.ui.button(label="🧵 Open Thread", style=discord.ButtonStyle.primary)
    async def open_thread(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        try:
            if self.thread is not None:
                if not self._full_posted:
                    await _post_dossier_to_thread(self.thread, self.dossier)
                    self._full_posted = True
                await interaction.response.send_message(
                    f"Dossier thread: {self.thread.mention}",
                    ephemeral=True,
                )
                return

            thread = await self.status_message.create_thread(
                name=_thread_name(self.target),
                auto_archive_duration=1440,
            )
            self.thread = thread
            await _post_dossier_to_thread(thread, self.dossier)
            self._full_posted = True
            await interaction.response.send_message(
                f"Opened {thread.mention} and moved the extended dossier there.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("Failed to open OSINT dossier thread")
            message = (
                "Could not create a thread here. Export Markdown instead, "
                "or check the bot's thread permissions."
            )
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(label="📊 Gatebox Comparison", style=discord.ButtonStyle.success)
    async def gatebox_comparison(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        try:
            await interaction.response.send_message(
                GATEBOX_COMPARISON_TABLE,
                ephemeral=True,
            )
        except Exception:
            logger.exception("Failed to send Gatebox comparison")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Could not render the Gatebox comparison.",
                    ephemeral=True,
                )


def _avg_latency_ms() -> float:
    if not execution_latencies:
        return 0.0
    return sum(execution_latencies) / len(execution_latencies)


def _success_rate_pct() -> float:
    if total_requests <= 0:
        return 0.0
    return (successful_requests / total_requests) * 100.0


def _tavily_configured() -> bool:
    return bool(TAVILY_API_KEY)


async def _collect_health() -> tuple[str, str, dict]:
    """Non-blocking health snapshot; Anthropic ping is hard-capped."""
    cache_default: dict = {
        "key_count": 0,
        "seeded_records": 0,
        "size_kb": 0.0,
        "active": False,
    }

    async def _cache_snapshot() -> dict:
        return await asyncio.to_thread(cache_storage_stats)

    try:
        anthropic_status, cache_stats = await asyncio.wait_for(
            asyncio.gather(
                check_anthropic_health(),
                _cache_snapshot(),
            ),
            timeout=STATUS_HEALTH_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.warning("Status health collection timed out or failed", exc_info=True)
        anthropic_status = "Degraded" if ANTHROPIC_API_KEY else "Degraded"
        try:
            cache_stats = cache_storage_stats()
        except Exception:
            logger.exception("Cache stats failed during status fallback")
            cache_stats = cache_default

    if isinstance(anthropic_status, Exception):
        logger.warning("Anthropic health check raised", exc_info=anthropic_status)
        anthropic_status = "Degraded"
    if isinstance(cache_stats, Exception):
        logger.warning("Cache stats raised", exc_info=cache_stats)
        cache_stats = cache_default

    tavily_status = "Online" if _tavily_configured() else "Offline"
    if not isinstance(cache_stats, dict):
        cache_stats = cache_default
    return tavily_status, str(anthropic_status), cache_stats


async def send_system_telemetry(channel: discord.abc.Messageable) -> None:
    tavily_status, anthropic_status, cache_stats = await _collect_health()
    cache_engine = "Active" if cache_stats.get("active", True) else "Inactive"
    key_count = int(cache_stats.get("key_count") or 0)
    seeded = int(cache_stats.get("seeded_records") or key_count)
    size_kb = float(cache_stats.get("size_kb") or 0.0)

    embed = discord.Embed(
        title="⚙️ OSINT Detective — System Telemetry",
        color=TELEMETRY_COLOR,
    )
    embed.add_field(
        name="🟢 Service Health",
        value=(
            f"Tavily: **{tavily_status}**\n"
            f"Anthropic: **{anthropic_status}**\n"
            f"Local Cache Engine: **{cache_engine}**"
        ),
        inline=False,
    )
    embed.add_field(
        name="📊 Execution Performance",
        value=(
            f"Total Requests Served: **{total_requests}**\n"
            f"Success Rate: **{_success_rate_pct():.1f}%** "
            f"({successful_requests} ok / {failed_requests} failed)\n"
            f"Average Processing Latency: **{_avg_latency_ms():.0f} ms**"
        ),
        inline=False,
    )
    embed.add_field(
        name="💾 Cache Storage",
        value=(
            f"Total Seeded Records: **{seeded}** ({key_count} cached keys)\n"
            f"Disk Size: **{size_kb:.2f} KB**\n"
            f"Lookup Strategy: **Normalized Key Matching**"
        ),
        inline=False,
    )
    embed.set_footer(
        text="Host System: Operational | Async Timeout Ceiling: 8s Search / 12s LLM"
    )
    await channel.send(embed=embed)


async def run_investigation(query: str, message: discord.Message) -> None:
    """Drive Tavily + Claude while editing `message` in place."""
    global total_requests, successful_requests, failed_requests

    total_requests += 1
    started = time.perf_counter()
    succeeded = False

    try:
        embed = (
            message.embeds[0]
            if message.embeds
            else discord.Embed(
                title="🕵️ OSINT Investigation Started",
                color=discord.Color.blurple(),
            )
        )

        search_payload = await execute_web_search(query)
        results = search_payload.get("results") or []
        if not isinstance(results, list):
            results = [results]

        step2 = "🧠 Step 2/3: Cross-referencing data..."
        if search_payload.get("fallback") and search_payload.get("cache_hit"):
            step2 += "\nCached OSINT engaged (Tavily unavailable)."
        elif search_payload.get("fallback"):
            step2 += "\nSearch degraded — cache miss."
        embed.description = step2
        await message.edit(embed=embed)

        dossier = await synthesize_dossier(query, results)

        thread: discord.Thread | None = None
        if len(dossier) > CHANNEL_CARD_LIMIT:
            try:
                thread = await message.create_thread(
                    name=_thread_name(query),
                    auto_archive_duration=1440,
                )
                await _post_dossier_to_thread(thread, dossier)
            except Exception:
                logger.exception("Failed to auto-create dossier thread")
                thread = None

        embed.title = "🕵️ OSINT Investigation Started"
        embed.description = _build_summary_card(
            query,
            dossier,
            fallback=bool(search_payload.get("fallback")),
            cache_hit=bool(search_payload.get("cache_hit")),
            thread=thread,
        )
        embed.color = (
            discord.Color.gold() if search_payload.get("fallback") else discord.Color.green()
        )

        view = OSINTView(
            dossier=dossier,
            target=query,
            status_message=message,
            thread=thread,
        )
        _active_views.add(view)
        await message.edit(embed=embed, view=view)
        succeeded = True
    except Exception:
        failed_requests += 1
        raise
    else:
        successful_requests += 1
    finally:
        execution_latencies.append((time.perf_counter() - started) * 1000.0)
        logger.info(
            "Investigation finished success=%s latency_ms=%.0f totals=%s/%s/%s",
            succeeded,
            execution_latencies[-1],
            total_requests,
            successful_requests,
            failed_requests,
        )


@client.event
async def on_ready() -> None:
    user = client.user
    if user is None:
        logger.warning("OSINT Detective bot is connected, but user metadata is unavailable.")
        return
    logger.info("OSINT Detective online as %s (ID: %s)", user, user.id)


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    content = (message.content or "").strip()
    lowered = content.lower()
    if lowered == STATUS_COMMAND or lowered.startswith(STATUS_COMMAND + " "):
        try:
            await send_system_telemetry(message.channel)
        except Exception:
            logger.exception("Failed to send system telemetry")
            await message.reply("Could not collect system telemetry.")
        return
    if not lowered.startswith(COMMAND_PREFIX):
        return

    query = content[len(COMMAND_PREFIX) :].strip()
    if not query:
        await message.reply("Usage: `!investigate <query>`")
        return

    embed = discord.Embed(
        title="🕵️ OSINT Investigation Started",
        description="🔍 Step 1/3: Gathering intelligence...",
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=f"Query: {query[:200]}")

    try:
        status_msg = await message.channel.send(embed=embed)
    except Exception:
        logger.exception("Failed to send status embed")
        await message.reply("Could not start the investigation (Discord send failed).")
        return

    try:
        await run_investigation(query, status_msg)
    except Exception:
        logger.exception("Investigation pipeline failed for query: %s", query)
        fail = discord.Embed(
            title="🕵️ OSINT Investigation Started",
            description="Investigation failed due to an unexpected error.",
            color=discord.Color.red(),
        )
        fail.set_footer(text=f"Query: {query[:200]}")
        try:
            await status_msg.edit(embed=fail)
        except Exception:
            logger.exception("Failed to update status embed after pipeline error")
        try:
            await message.reply(
                "The investigation pipeline failed. Check bot logs for details."
            )
        except Exception:
            logger.exception("Failed to send pipeline error reply")


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
