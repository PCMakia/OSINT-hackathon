# OSINT Pipeline Evaluation Report

Generated: **2026-09-13 22:12:04Z**

**Overall:** 5/5 tests passed (100%).

## Summary matrix

| Test | Scenario | Latency (ms) | Fallback Trigger | Executive Summary | Matrix Table | Contradiction Alert | Source Credibility | Result |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| 1 | Exact target match | 30066 | False | PASS | PASS | PASS | PASS | PASS |
| 2 | Normalized alias match | 31239 | False | PASS | PASS | PASS | PASS | PASS |
| 3 | Second domain target | 20751 | False | PASS | PASS | PASS | PASS | PASS |
| 4 | Simulated API error / offline fallback | 8 | True | PASS | PASS | PASS | PASS | PASS |
| 5 | Unknown query fallback handling | 2 | True | PASS | PASS | PASS | PASS | PASS |

## Per-test detail

### Test 1: Exact target match

- Query: `target="razer ava ai companion"`
- Notes: Canonical Discord command form.
- Latency: **30066 ms**
- Fallback triggered: **False** (cache_hit=False)
- Structural completeness:
  - Executive Summary: yes
  - Contradiction Alert: yes
  - Matrix Table: yes
  - Source Credibility Tier: yes
- Preview: ## Executive Summary Razer AVA (evolved from the CES 2026 "Project AVA" concept) is a dual-mode AI companion that manifests as either an animated 5.5-inch 3D holographic desk unit or an on-screen desktop character, powered by cloud-assisted AI inferencing with a beta software lay

### Test 2: Normalized alias match

- Query: `razer ava`
- Notes: Alias should resolve to razer ava ai companion cache key.
- Latency: **31239 ms**
- Fallback triggered: **False** (cache_hit=False)
- Structural completeness:
  - Executive Summary: yes
  - Contradiction Alert: yes
  - Matrix Table: yes
  - Source Credibility Tier: yes
- Preview: ## Executive Summary Razer AVA is a 5.5-inch 3D holographic desk companion and on-screen AI agent that pairs local hardware (USB-C tethered to a Windows PC) with cloud LLM inference (currently xAI Grok, with a multi-model roadmap). The public record is primarily official Razer PR

### Test 3: Second domain target

- Query: `xz utils backdoor`
- Notes: Cybersecurity OSINT fixture (CVE-2024-3094).
- Latency: **20751 ms**
- Fallback triggered: **False** (cache_hit=False)
- Structural completeness:
  - Executive Summary: yes
  - Contradiction Alert: yes
  - Matrix Table: yes
  - Source Credibility Tier: yes
- Preview: ## Executive Summary A sophisticated, multi-year software supply chain attack embedded a remote code execution backdoor (CVE-2024-3094, CVSS 10.0) into XZ Utils versions 5.6.0 and 5.6.1, targeting Linux systems via OpenSSH. The threat actor, operating as "Jia Tan," spent approxim

### Test 4: Simulated API error / offline fallback

- Query: `target="razer ava ai companion"`
- Notes: Tavily + Anthropic forced down; cache must still produce a dossier.
- Latency: **8 ms**
- Fallback triggered: **True** (cache_hit=True)
- Expected fallback: **True**
- Structural completeness:
  - Executive Summary: yes
  - Contradiction Alert: yes
  - Matrix Table: yes
  - Source Credibility Tier: yes
- Preview: ## Executive Summary **target="razer ava ai companion"** is synthesized from **5 cached OSINT sources** (offline fallback; Anthropic did not generate this dossier). Public record centers on Razer AVA: 3D Hologram AI Companion | Razer United States, with hardware, architecture, an

### Test 5: Unknown query fallback handling

- Query: `unknown widget zzyzx-eval-999`
- Notes: Cache miss + API outage must not crash; structured offline dossier required.
- Latency: **2 ms**
- Fallback triggered: **True** (cache_hit=False)
- Expected fallback: **True**
- Structural completeness:
  - Executive Summary: yes
  - Contradiction Alert: yes
  - Matrix Table: yes
  - Source Credibility Tier: yes
- Preview: ## Executive Summary **unknown widget zzyzx-eval-999** is synthesized from cached OSINT data, but this query had no stored search items. No live model output is included. ## ⚠️ Contradiction & Discrepancy Alert > No cached sources were available to compare Official PR, benchmarks

## Method

- Tests 1–3 execute `execute_web_search` then `synthesize_dossier` (live APIs with cache fallback).
- Test 4 patches Tavily search and Anthropic `messages.create` to raise, forcing offline cache synthesis for Razer AVA.
- Test 5 uses an unknown query with the same simulated outage to verify cache-miss fallback still returns a structured dossier.

