"""Discord client for the OSINT Intelligence Detective bot."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import discord

from analyzer import synthesize_dossier
from config import DISCORD_TOKEN
from search import execute_web_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

COMMAND_PREFIX = "!investigate"
DISCORD_MESSAGE_LIMIT = 2000

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


def _chunk_message(text: str, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text] if text else [""]
    chunks: list[str] = []
    remaining = text
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


@client.event
async def on_ready() -> None:
    user = client.user
    if user is None:
        print("OSINT Detective bot is connected, but user metadata is unavailable.")
        return
    print(f"OSINT Detective online as {user} (ID: {user.id})")
    logger.info("Logged in as %s (%s)", user, user.id)


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
        title="OSINT Intelligence Detective",
        description="🔍 Phase 1/3: Querying Tavily...",
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
        search_payload = await execute_web_search(query)
        results = search_payload.get("results") or []
        if not isinstance(results, list):
            results = [results]

        if search_payload.get("fallback"):
            if search_payload.get("cache_hit"):
                phase2 = (
                    "🧠 Phase 2/3: Cross-Referencing... "
                    "(Tavily unavailable — using cached fallback)"
                )
            else:
                phase2 = (
                    "🧠 Phase 2/3: Cross-Referencing... "
                    "(Tavily unavailable — cache miss, proceeding with empty results)"
                )
        else:
            phase2 = "🧠 Phase 2/3: Cross-Referencing..."

        embed.description = phase2
        try:
            await status_msg.edit(embed=embed)
        except Exception:
            logger.exception("Failed to update status embed to phase 2")

        dossier = await synthesize_dossier(query, results)

        embed.description = "✅ Phase 3/3: Dossier ready."
        if search_payload.get("fallback"):
            embed.color = discord.Color.gold()
        try:
            await status_msg.edit(embed=embed)
        except Exception:
            logger.exception("Failed to update status embed to phase 3")

        for chunk in _chunk_message(dossier):
            await message.reply(chunk)
    except Exception:
        logger.exception("Investigation pipeline failed for query: %s", query)
        embed.description = "Investigation failed due to an unexpected error."
        embed.color = discord.Color.red()
        try:
            await status_msg.edit(embed=embed)
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
