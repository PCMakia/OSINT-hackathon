"""Discord client for the OSINT Intelligence Detective bot."""

from __future__ import annotations

import io
import logging
import re
import sys
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

from analyzer import synthesize_dossier
from cache import normalize_query_key
from config import DISCORD_TOKEN
from search import execute_web_search

COMMAND_PREFIX = "!investigate"
CHANNEL_CARD_LIMIT = 1500
THREAD_CHUNK_LIMIT = 1900
EXPORT_FILENAME = "Razer_AVA_Dossier.md"

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


async def run_investigation(query: str, message: discord.Message) -> None:
    """Drive Tavily + Claude while editing `message` in place."""
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
    if not content.lower().startswith(COMMAND_PREFIX):
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
