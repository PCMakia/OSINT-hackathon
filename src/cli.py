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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the OSINT Intelligence Detective pipeline in the terminal.",
    )
    parser.add_argument(
        "--target",
        required=True,
        help='Investigation topic, e.g. "razer ava ai companion"',
    )
    return parser.parse_args(argv)


async def run_cli(target: str) -> str:
    print("🔍 Phase 1/3: Searching Tavily & Loading Cache...", flush=True)
    search_payload = await execute_web_search(target)
    results = search_payload.get("results") or []
    if not isinstance(results, list):
        results = [results]

    print("🧠 Phase 2/3: Cross-Referencing Sources & Fact-Checking...", flush=True)
    print("✨ Phase 3/3: Synthesizing Dossier...", flush=True)
    dossier = await synthesize_dossier(target, results)
    return dossier


def main(argv: list[str] | None = None) -> int:
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
    print(dossier, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
