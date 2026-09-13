"""Standalone CLI for OSINT dossiers (no Discord required)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from analyzer import synthesize_dossier
from search import execute_web_search

DEFAULT_TARGET = "razer ava ai companion"


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the OSINT Intelligence Detective pipeline in the terminal (no Discord).",
    )
    parser.add_argument(
        "-t",
        "--target",
        default=DEFAULT_TARGET,
        help='Investigation topic (default: "razer ava ai companion")',
    )
    return parser.parse_args(argv)


async def run_cli(target: str) -> str:
    print("🔍 [CLI] Phase 1/3: Searching Tavily / Checking Local Cache...", flush=True)
    search_payload = await execute_web_search(target)
    results = search_payload.get("results") or []
    if not isinstance(results, list):
        results = [results]

    print("🧠 [CLI] Phase 2/3: Synthesizing OSINT Intelligence...", flush=True)
    dossier = await synthesize_dossier(target, results)
    print("✨ [CLI] Phase 3/3: Dossier Complete.", flush=True)
    return dossier


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    logging.getLogger("search").setLevel(logging.CRITICAL)
    logging.getLogger("analyzer").setLevel(logging.CRITICAL)
    args = _parse_args(argv)
    target = (args.target or "").strip()
    if not target:
        print("error: --target must be a non-empty query", file=sys.stderr)
        return 2
    try:
        dossier = asyncio.run(run_cli(target))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Investigation failed: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(dossier if dossier.endswith("\n") else dossier + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
