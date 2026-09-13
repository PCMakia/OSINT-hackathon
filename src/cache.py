"""Thread-safe JSON cache for OSINT query results."""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_PATH = Path(__file__).resolve().parent.parent / "cache.json"

_TARGET_RE = re.compile(
    r"""target\s*=\s*(?P<q>["'])(?P<val>.*?)(?P=q)""",
    re.IGNORECASE | re.DOTALL,
)

RAZER_AVA_KEY = "razer ava ai companion"
XZ_UTILS_KEY = "xz utils backdoor"

SEED_DATA: dict[str, Any] = {
    "test-competitor": {
        "query": "test-competitor",
        "source": "offline-seed",
        "status": "verified-fallback",
        "summary": (
            "Dummy competitor OSINT briefing for offline / timeout fallback. "
            "Acme Rival Labs (fictional) positions as a mid-market threat-intel "
            "vendor with public web presence, conference talks, and job postings "
            "indicating expansion into Discord-based alerting."
        ),
        "findings": [
            {
                "category": "corporate",
                "detail": "Public site lists HQ in Austin, TX and a 40–60 person team.",
            },
            {
                "category": "product",
                "detail": "Marketing pages describe automated OSINT digests and Slack/Discord bots.",
            },
            {
                "category": "hiring",
                "detail": "Open roles: OSINT analyst, Python backend, community manager.",
            },
        ],
        "confidence": "seed",
        "disclaimer": "Synthetic fixture data. Not a live investigation.",
    },
    "test-security": {
        "query": "test-security",
        "source": "offline-seed",
        "status": "verified-fallback",
        "summary": (
            "Dummy security OSINT briefing for offline / timeout fallback. "
            "Fictional org 'Northwind Payments' has a typical public attack surface: "
            "corporate site, status page, GitHub org, and leaked-credential chatter "
            "in open paste samples used only as training data."
        ),
        "findings": [
            {
                "category": "exposure",
                "detail": "Public GitHub org contains two archived demo repos with no secrets.",
            },
            {
                "category": "infrastructure",
                "detail": "Status page reports historical CDN incidents; no current outage.",
            },
            {
                "category": "hygiene",
                "detail": "SPF/DKIM records present on the primary domain (fixture values).",
            },
        ],
        "confidence": "seed",
        "disclaimer": "Synthetic fixture data. Not a live investigation.",
    },
    RAZER_AVA_KEY: {
        "topic": "Razer AVA AI Companion",
        "timestamp": "2026-09-13T12:00:00Z",
        "raw_results": [
            {
                "title": "Project AVA: 3D Hologram AI Desk Companion - Razer",
                "url": "https://www.razer.com/concepts/project-ava",
                "content": (
                    "Razer AVA features an animated 5.5 inch 3D holographic display "
                    "with integrated camera, microphone, and speaker array. Operates "
                    "as an interactive 3D desktop avatar with real-time audio and vision sensing."
                ),
                "credibility_tier": "High (Official PR)",
            },
            {
                "title": "Hardware Analysis: Local Edge AI vs Cloud Dependencies in Desk Companions",
                "url": "https://techbenchmarks.example/hardware/razer-ava-architecture",
                "content": (
                    "Early teardowns and hardware leaks indicate Razer AVA utilizes a hybrid "
                    "architecture: local micro-models handle vision/audio wake words, while deep "
                    "LLM processing offloads to cloud endpoints. Benchmarks show 180ms local "
                    "response latency versus 850ms full cloud cycles."
                ),
                "credibility_tier": "Medium (Tech Benchmarks / Leaks)",
            },
            {
                "title": "Desktop AI Hardware Battle: Gatebox vs Razer AVA vs Desktop Software Companions",
                "url": "https://hardware-review.example/desktop-ai-market-2026",
                "content": (
                    "Razer AVA enters a market previously dominated by Japan's Gatebox "
                    "(costing $1,500+) and flat-screen software companions like Desktop Goose/AI "
                    "Avatars. AVA bridges the gap by offering physical 3D volumetric presence at "
                    "a consumer peripheral price point."
                ),
                "credibility_tier": "Medium (Market Analysis)",
            },
        ],
    },
    XZ_UTILS_KEY: {
        "topic": "XZ Utils Backdoor (CVE-2024-3094)",
        "timestamp": "2026-09-13T12:00:00Z",
        "raw_results": [
            {
                "title": "oss-security: backdoor in upstream xz/liblzma leading to sshd compromise",
                "url": "https://www.openwall.com/lists/oss-security/2024/03/29/4",
                "content": (
                    "CVE-2024-3094 describes a malicious injection in the XZ Utils build of liblzma "
                    "(versions 5.6.0 and 5.6.1). Obfuscated test files in the tarball extracted extra "
                    "object code during Debian/RPM builds, silently modifying liblzma. The implanted "
                    "logic was designed to interfere with OpenSSH sshd when it is linked against the "
                    "compromised library, enabling an authentication bypass for a designated attacker "
                    "key rather than a generic crash-only bug."
                ),
                "credibility_tier": "High (Primary researcher / oss-security)",
            },
            {
                "title": "CISA Alert: Reported Supply Chain Compromise Affecting XZ Utils (CVE-2024-3094)",
                "url": "https://www.cisa.gov/news-events/alerts/2024/03/29/reported-supply-chain-compromise-affecting-xz-utils-data-compression-library-cve-2024-3094",
                "content": (
                    "Government and distro advisories frame CVE-2024-3094 as a supply-chain compromise: "
                    "the backdoor shipped through the official xz tarball and downstream Linux packages, "
                    "not a post-compromise host implant. sshd on systemd-based distributions that pull in "
                    "liblzma was the high-value target. Operators were advised to downgrade to 5.4.x "
                    "lineage, audit for 5.6.0/5.6.1, and treat the event as a maintainer-trust failure "
                    "across the open-source compression stack."
                ),
                "credibility_tier": "High (Official advisory)",
            },
            {
                "title": "Jia Tan maintainer timeline: multi-year social engineering of XZ Utils",
                "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-3094",
                "content": (
                    "Open reporting on the Jia Tan identity describes a years-long pressure campaign: "
                    "new contributor activity from 2021–2022, growing commit rights, and eventual "
                    "handoff pressure on original maintainer Lasse Collin. The timeline is used in "
                    "OSINT as a case study in supply-chain social engineering — patient reputation "
                    "building, mailing-list coercion, and a delayed payload in liblzma — rather than "
                    "a single opportunistic commit."
                ),
                "credibility_tier": "Medium (NVD / secondary timeline synthesis)",
            },
        ],
    },
}

QUERY_ALIASES: dict[str, str] = {
    "razer ava": RAZER_AVA_KEY,
    "razer ava ai": RAZER_AVA_KEY,
    "razer ava companion": RAZER_AVA_KEY,
    "project ava": RAZER_AVA_KEY,
    "project ava razer": RAZER_AVA_KEY,
    "xz utils": XZ_UTILS_KEY,
    "xz backdoor": XZ_UTILS_KEY,
    "xz utils backdoor": XZ_UTILS_KEY,
    "cve-2024-3094": XZ_UTILS_KEY,
    "cve 2024 3094": XZ_UTILS_KEY,
}


def normalize_query_key(query_key: str) -> str:
    """Canonicalize a lookup key (case, whitespace, and target=\"...\" forms)."""
    raw = (query_key or "").strip()
    match = _TARGET_RE.search(raw)
    if match:
        raw = match.group("val")
    collapsed = re.sub(r"\s+", " ", raw).strip().strip("\"'")
    return collapsed.casefold()


def _canonical_key(query_key: str) -> str:
    normalized = normalize_query_key(query_key)
    return QUERY_ALIASES.get(normalized, normalized)


def _resolve_store_key(store: dict[str, Any], query_key: str) -> str | None:
    needle = _canonical_key(query_key)
    if not needle:
        return None

    indexed: dict[str, str] = {}
    for stored in store:
        indexed[normalize_query_key(stored)] = stored

    if needle in indexed:
        return indexed[needle]

    tokens = needle.split()
    if len(tokens) < 2:
        return None

    prefix_hits: list[str] = []
    for normalized, original in indexed.items():
        if normalized.startswith(needle + " ") or needle.startswith(normalized + " "):
            if len(normalized.split()) >= 2:
                prefix_hits.append(original)
    if not prefix_hits:
        return None
    return max(prefix_hits, key=lambda key: len(normalize_query_key(key)))


class CacheManager:
    """Thread-safe on-disk cache backed by a local JSON file."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else CACHE_PATH
        self._lock = threading.Lock()
        self._ensure_file()

    def get(self, query_key: str) -> Any | None:
        with self._lock:
            store = self._read_unlocked()
            resolved = _resolve_store_key(store, query_key)
            if resolved is None:
                return None
            return store.get(resolved)

    def set(self, query_key: str, data: Any) -> None:
        with self._lock:
            store = self._read_unlocked()
            resolved = _resolve_store_key(store, query_key)
            write_key = resolved if resolved is not None else _canonical_key(query_key)
            store[write_key] = data
            self._write_unlocked(store)

    def _ensure_file(self) -> None:
        with self._lock:
            if not self._path.exists():
                self._write_unlocked(dict(SEED_DATA))
                return
            store = self._read_unlocked()
            changed = False
            for key, value in SEED_DATA.items():
                if _resolve_store_key(store, key) is None:
                    store[key] = value
                    changed = True
            if changed:
                self._write_unlocked(store)

    def _read_unlocked(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8").strip()
            if not raw:
                return {}
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to read cache file %s", self._path)
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _write_unlocked(self, store: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(store, indent=2, ensure_ascii=False) + "\n"
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            tmp_path.write_text(serialized, encoding="utf-8")
            tmp_path.replace(self._path)
        except OSError:
            logger.exception("Failed to persist cache file %s", self._path)
            raise

    def stats(self) -> dict[str, Any]:
        """Return key count and on-disk size for telemetry."""
        with self._lock:
            store = self._read_unlocked()
            key_count = len(store)
            seeded_records = sum(
                1 for seed_key in SEED_DATA if _resolve_store_key(store, seed_key) is not None
            )
        size_bytes = 0
        try:
            if self._path.exists():
                size_bytes = self._path.stat().st_size
        except OSError:
            logger.exception("Failed to stat cache file %s", self._path)
        return {
            "key_count": key_count,
            "seeded_records": seeded_records,
            "size_kb": size_bytes / 1024.0,
            "active": True,
        }


def cache_storage_stats() -> dict[str, Any]:
    """Snapshot of the local cache engine (safe to run in a worker thread)."""
    return CacheManager().stats()
