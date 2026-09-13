# 🕵️ Autonomous OSINT Intelligence Detective

This is not a chat window glued to a search API. It is an **investigation agent**: it gathers open-source claims, **cross-examines them for conflicts**, and delivers a **workspace inside Discord** (or a terminal dossier) instead of a pasted SERP.

An autonomous Open-Source Intelligence agent bridging **Discord**, **Tavily AI**, and **Anthropic Claude 3.5 Sonnet** to produce structured, cross-referenced hardware, market, and cybersecurity dossiers.

**External app usage** Cursor for implementation helper, Tavily for API web search, Claude API for summary, Discord API for display

---

## 2-Minute Demo Video

**Link:** [https://youtu.be/L10Tf27bXgo](https://youtu.be/L10Tf27bXgo)

---



## Judge Quickstart & Testing Command (using my deployed app for hackathon)

```text
https://discord.com/oauth2/authorize?client_id=1548760414928642250&permissions=309237763072&integration_type=0&scope=bot
```

Invite the bot to a server (using link above), then in any channel type:

```text
!investigate target="razer ava ai companion"
```

Equivalent triggers (`razer ava`, `razer ava ai companion`) resolve to the same cached topic. Alternate domain: `!investigate xz utils backdoor` or `!demo`.

**Zero-downtime fallback is the default safety net** if live API credits or networks fail — the dossier still renders from local structured OSINT, not an error bubble.

### Integration checklist (multi-app)


| Surface                                        | Role                                                                                 |
| ---------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Discord API** (`discord.py`)                 | Micro-workspace: live embeds, buttons, ephemeral overlays, threads, QuickChart       |
| **Tavily AI API**                              | Web sensor (`max_results=5`, 8s timeout)                                             |
| **Anthropic Claude API** (`claude-sonnet-4-6`) | Cognitive engine (45s timeout, `max_tokens=1500`) with contradiction-first templates |


---



## Three innovations (not a search wrapper)



### 1. Automated Discrepancy & Contradiction Detection Engine

Unlike standard summarizers, the agent cross-references official marketing claims against hardware leaks/benchmarks and surfaces conflicting data in a high-priority warning banner.

Every dossier includes **⚠️ Contradiction & Discrepancy Alert** — a first-class section, not an afterthought. Official PR, benchmark/leak write-ups, and market analysis are tagged by credibility tier, then compared (for example Razer AVA’s on-desk holographic story vs hybrid local/cloud latency figures). Judges should look for the blockquote banner before the spec matrix.

### 2. Smart Zero-Downtime Fallback Architecture

Under API rate limits or network drops, the agent dynamically switches from LLM synthesis to a local structured intelligence parser without crashing or showing error messages.

Tavily is capped at **8s** and Claude at **45s**. On timeout, `AuthenticationError`, or `APIError`, `build_offline_dossier` still emits the same Markdown contract from `cache.json` (normalized keys such as `razer ava` → `razer ava ai companion`). Users see a complete investigation card, not a stack trace or empty “analyzer offline” stub.

### 3. In-Chat OSINT Micro-Workspace

Rather than outputting wall-of-text responses, the bot deploys dynamic QuickChart radar visuals, ephemeral spec comparison overlays, and dedicated thread routing directly inside Discord.

The channel stays a **≤1,500-character** summary card. **📊 Gatebox Comparison** opens an ephemeral spec table plus a QuickChart radar (Price Value, Portability, Local Compute, Form Factor, Ecosystem). Overflow and the full report live in `OSINT-Dossier-<Target>` threads; **📄 Export Markdown** attaches `Topic_Dossier.md`. `!demo` is a dropdown launcher for hardware vs CVE-2024-3094 cybersecurity tracks.

## Short System & Reliability Brief

**Architecture:** Interactive Portal (Discord micro-workspace) → Web Sensor (Tavily AI) → Cognitive Engine (Anthropic Claude 3.5 Sonnet) → Contradiction banner + structured parser fallback.

**Reliability safeguards:**

- Strict async timeouts (`asyncio.wait_for` at **8s search** / **45s synthesis**).
- Smart zero-downtime fallback (`src/cache.py` + `cache.json`), with normalized keys (`target="..."` and aliases such as `razer ava`).
- Channel card **≤1,500 characters**; un-truncated report routed into an automatic Discord thread.
- Anthropic failures return a structured offline dossier from cached snippets — never raw JSON or user-facing exception text.

---



## Tech Stack & Installation


| Component | Package / model                                                                  |
| --------- | -------------------------------------------------------------------------------- |
| Discord   | `discord.py==2.4.0`                                                              |
| Search    | `tavily-python==0.5.0`                                                           |
| LLM       | `anthropic==0.34.0` · `claude-sonnet-4-6` (`max_tokens=1500`, `temperature=0.2`) |
| Config    | `python-dotenv==1.0.1`                                                           |




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

No Discord? Run directly in terminal: python src/cli.py --target 'razer ava ai companion'

(`-t` is equivalent; default target is `razer ava ai companion`.) Offline sample dossiers: `samples/Razer_AVA_OSINT_Dossier.md` and `samples/XZ_Utils_OSINT_Dossier.md`.

Pipeline eval (latency, fallback, dossier structure): `python src/eval.py`
