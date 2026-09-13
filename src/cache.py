"""Thread-safe JSON cache for OSINT query results."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

CACHE_PATH = Path(__file__).resolve().parent.parent / "cache.json"

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
}


class CacheManager:
    """Thread-safe on-disk cache backed by a local JSON file."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else CACHE_PATH
        self._lock = threading.Lock()
        self._ensure_file()

    def get(self, query_key: str) -> Any | None:
        with self._lock:
            store = self._read_unlocked()
            return store.get(query_key)

    def set(self, query_key: str, data: Any) -> None:
        with self._lock:
            store = self._read_unlocked()
            store[query_key] = data
            self._write_unlocked(store)

    def _ensure_file(self) -> None:
        with self._lock:
            if not self._path.exists():
                self._write_unlocked(dict(SEED_DATA))
                return
            store = self._read_unlocked()
            changed = False
            for key, value in SEED_DATA.items():
                if key not in store:
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
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _write_unlocked(self, store: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(store, indent=2, ensure_ascii=False) + "\n"
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(serialized, encoding="utf-8")
        tmp_path.replace(self._path)
