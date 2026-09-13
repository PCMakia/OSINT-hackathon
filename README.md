# 🕵️ Autonomous OSINT Intelligence Detective

An autonomous Open-Source Intelligence agent bridging **Discord**, **Tavily AI**, and **Anthropic Claude 3.5 Sonnet** to produce structured, cross-referenced hardware and market dossiers.

---

## Judge Quickstart & Testing Command

Invite the bot to a server (Message Content Intent enabled), then in any channel type:

```text
!investigate target="razer ava ai companion"
```

Equivalent triggers (`razer ava`, `razer ava ai companion`) resolve to the same cached topic.

**Offline / cached fallback is active if live API credits or networks fail.** Seeded Razer AVA OSINT in `cache.json` plus `build_offline_dossier` still produce a complete Markdown dossier (form factor, architecture, Gatebox positioning, source tiers) when Tavily times out or Anthropic returns `AuthenticationError` / `APIError` / timeout.

### Integration checklist (multi-app)

| Surface | Role |
| --- | --- |
| **Discord API** (`discord.py`) | Interactive portal, live embed edits, buttons, threads |
| **Tavily AI API** | Web sensor (`max_results=5`, 8s timeout) |
| **Anthropic Claude API** (Claude 3.5 Sonnet) | Cognitive engine (12s timeout, hardware OSINT template) |

---

## 2-Minute Demo Video

**Link:** [Insert YouTube / Loom Link Here]

### Script breakdown

| Time | Beat |
| --- | --- |
| **0:00–0:25 — Trigger & live embed edits** | Send `!investigate target="razer ava ai companion"`. Show the single embed titled “OSINT Investigation Started” stepping **1/3 Gathering intelligence → 2/3 Cross-referencing → 3/3 Dossier complete** via in-place `message.edit`. |
| **0:25–1:10 — Dossier & contradiction alert** | Walk the summary card (≤1,500 characters). Open the auto-created `OSINT-Dossier-<Target>` thread and highlight **⚠️ Contradiction & Discrepancy Alert** (Official PR vs hybrid/cloud latency leaks vs market analysis). |
| **1:10–1:40 — Ephemeral Gatebox comparison & threading** | Click **📊 Gatebox Comparison** (ephemeral AVA $300–$500 vs Gatebox $1,500+ table). Click **🧵 Open Thread** if needed. Click **📄 Export Markdown** and confirm the attachment is **`Razer_AVA_Dossier.md`**. |
| **1:40–2:00 — Reliability & cache fallback** | Call out 8s / 12s `asyncio.wait_for` guards and the zero-downtime `src/cache.py` store. Optionally note that the same command still completes a dossier when live keys or networks fail. |

---

## Short System & Reliability Brief

**Architecture:** Interactive Portal (Discord API) → Web Sensor (Tavily AI) → Cognitive Engine (Anthropic Claude 3.5 Sonnet).

**Reliability safeguards:**

- Strict async timeouts (`asyncio.wait_for` at **8s search** / **12s synthesis**).
- Zero-downtime cache fallback store (`src/cache.py` + `cache.json`), with normalized keys (`target="..."` and aliases such as `razer ava`).
- Dynamic **1,500-character** Discord channel card; overflow is posted **un-truncated** into an automatically created thread.
- Anthropic failures (`TimeoutError`, `AuthenticationError`, `APIError`) return a structured offline dossier from cached snippets — never raw JSON dumps.

---

## Tech Stack & Installation

| Component | Package / model |
| --- | --- |
| Discord | `discord.py==2.4.0` |
| Search | `tavily-python==0.5.0` |
| LLM | `anthropic==0.34.0` · Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`) |
| Config | `python-dotenv==1.0.1` |

### Setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Fill `.env` (never commit this file):

```text
DISCORD_TOKEN=
TAVILY_API_KEY=
ANTHROPIC_API_KEY=
```

In the [Discord Developer Portal](https://discord.com/developers/applications), enable **Message Content Intent**. Grant the bot permission to send messages, embed links, attach files, and **create public threads**.

```bash
python src/bot.py
```

Then run the judge command:

```text
!investigate target="razer ava ai companion"
```
