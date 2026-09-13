# OSINT Intelligence Dossier: Razer AVA AI Companion

**Target key:** `razer ava ai companion`  
**Collection:** Extracted from local `cache.json` (official Razer pages, GDC 2026 blog, Project AVA media) plus seeded hardware/leak/market fixtures used by the contradiction engine.  
**Mode:** Sample export for offline / non-Discord evaluation.

## Executive Summary

Razer AVA is positioned as a **5.5" 3D holographic desk companion** that also exists as an **on-screen Windows AI agent**, evolved from the 2025 Project AVA esports-coach concept. Official pages describe USB-C tethering, “PC Vision Mode,” and GDC 2026 **agentic** workflows (launch apps, coordinate with other companions). Independently, seeded hardware analysis still reports a **hybrid local-micro-model / cloud-LLM split** (≈180 ms local vs ≈850 ms full cloud). The public record is commercially active (US reservation deposit, H2 2026 availability claims) but **compute location, latency, and price** are not stated consistently across PR vs leak/benchmark fixtures.

## ⚠️ Contradiction & Discrepancy Alert

> **Official PR** (razer.com / GDC 2026) frames AVA as a 24/7 holographic *and* on-screen companion with agentic, multi-app outcomes and a wired USB-C PC link for low-latency screen vision. **Leak/benchmark fixtures** describe hybrid edge wake-word/vision models with **cloud LLM offload** and an order-of-magnitude gap between local (180 ms) and full-cloud (850 ms) cycles. **Market analysis** places AVA as a consumer-peripheral alternative to **Gatebox ($1,500+)** and flat-screen software avatars, implying a **$300–$500-class** price that **does not appear on the official product FAQ snippets**. Treat cloud-offload, millisecond timings, and street price as **unverified against the primary Razer pages**.

## Form Factor & Technical Specs Matrix

| Dimension | Subject Device | Comparison Notes |
| --- | --- | --- |
| Display / Form Factor | 5.5" animated 3D holographic desk unit; dual presence as desktop hologram and on-screen companion; character library (esports / anime-inspired) | Physical volumetric presence vs Gatebox enclosure vs flat-screen software avatars (Desktop Goose / AI Avatars) |
| AI Engine | Official: agentic planning, PC Vision Mode, app/service orchestration, companion-to-companion coordination. Seeded leak: local micro-models for wake/vision; deep LLM on cloud endpoints | Hybrid routing vs fully local or fully cloud desktop agents |
| Latency | Official: USB-C wired path “minimal latency” for screen analysis. Seeded bench: ~180 ms local response vs ~850 ms full cloud cycle | Local sensing path vs full generative cycle; figures are leak-tier, not PR |
| Power / Connectivity | USB Type-C to a Windows PC (required); camera, microphone, and speaker array on the desk unit; expanding app/chat integrations | Tethered Windows peripheral, not a standalone wireless appliance |

## Competitive Positioning

- **Gatebox ($1,500+):** Premium enclosed holographic companion; AVA is framed as bridging that physical-presence category at a consumer-peripheral price (market fixture), not as a like-for-like luxury enclosure.
- **Software desktop companions:** Flat-screen avatars and joke/desktop agents lack volumetric hardware; AVA’s differentiator is the 5.5" hologram plus USB-C PC vision.
- **Classic voice assistants:** GDC 2026 copy stresses *outcomes* (launch tools, multi-step workflows) rather than Q&A-only assistants.
- **Wearables / AI Pin class:** Not evidenced as AVA’s primary frame; positioning is **desk + Windows PC**, not pocket hardware.

## Source Credibility & Verification Tier

| Source URL | Type | Credibility Rating | Rationale |
| --- | --- | --- | --- |
| https://www.razer.com/razer-ava | PR | High | Official product page: hologram + on-screen companion, USB-C Windows, PC Vision Mode |
| https://www.razer.com/blog/razer-ava-goes-agentic-a-new-chapter-at-gdc-2026 | PR | High | First-party GDC 2026 agentic / multi-companion claims |
| https://www.razer.com/mena-en/concepts/project-ava | PR | High | Concept/availability: H2 2026, $20 US reservation deposit |
| https://www.youtube.com/watch?v=_QDthx_WjwE | PR | Medium | Official video: 5.5" desk companion, character library |
| https://www.instagram.com/reel/DTLB2h5goH9?hl=en | PR | Medium | Social PR; same 5.5" companion messaging, weaker as a primary spec source |
| https://techbenchmarks.example/hardware/razer-ava-architecture | Leak | Medium | Seeded teardown/bench: hybrid architecture, 180 ms vs 850 ms (not official) |
| https://hardware-review.example/desktop-ai-market-2026 | Bench | Medium | Seeded market note: Gatebox $1,500+ vs consumer peripheral positioning |
