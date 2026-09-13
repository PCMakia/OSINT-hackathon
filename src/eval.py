"""Automated evaluation harness for the OSINT investigation pipeline."""

from __future__ import annotations

import asyncio
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

_SRC_DIR = Path(__file__).resolve().parent
_ROOT = _SRC_DIR.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from analyzer import synthesize_dossier
from search import execute_web_search

REPORT_PATH = _ROOT / "EVALUATION_REPORT.md"

STRUCTURE_CHECKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Executive Summary", re.compile(r"##\s+Executive Summary", re.I)),
    ("Contradiction Alert", re.compile(r"Contradiction", re.I)),
    ("Matrix Table", re.compile(r"Form Factor & Technical Specs Matrix", re.I)),
    ("Source Credibility Tier", re.compile(r"Source Credibility", re.I)),
)

TABLE_ROW = re.compile(r"\|.+\|.+\|")


@dataclass
class TestCase:
    number: int
    name: str
    query: str
    simulate_api_error: bool
    expect_fallback: bool | None
    notes: str


@dataclass
class TestResult:
    case: TestCase
    latency_ms: float
    fallback_triggered: bool
    cache_hit: bool
    structure: dict[str, bool] = field(default_factory=dict)
    passed: bool = False
    error: str | None = None
    dossier_preview: str = ""


CASES: list[TestCase] = [
    TestCase(
        1,
        "Exact target match",
        'target="razer ava ai companion"',
        simulate_api_error=False,
        expect_fallback=None,
        notes="Canonical Discord command form.",
    ),
    TestCase(
        2,
        "Normalized alias match",
        "razer ava",
        simulate_api_error=False,
        expect_fallback=None,
        notes="Alias should resolve to razer ava ai companion cache key.",
    ),
    TestCase(
        3,
        "Second domain target",
        "xz utils backdoor",
        simulate_api_error=False,
        expect_fallback=None,
        notes="Cybersecurity OSINT fixture (CVE-2024-3094).",
    ),
    TestCase(
        4,
        "Simulated API error / offline fallback",
        'target="razer ava ai companion"',
        simulate_api_error=True,
        expect_fallback=True,
        notes="Tavily + Anthropic forced down; cache must still produce a dossier.",
    ),
    TestCase(
        5,
        "Unknown query fallback handling",
        "unknown widget zzyzx-eval-999",
        simulate_api_error=True,
        expect_fallback=True,
        notes="Cache miss + API outage must not crash; structured offline dossier required.",
    ),
]


def _bool_cell(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _evaluate_structure(dossier: str) -> dict[str, bool]:
    flags = {label: bool(pattern.search(dossier or "")) for label, pattern in STRUCTURE_CHECKS}
    flags["Markdown table rows"] = bool(TABLE_ROW.search(dossier or ""))
    return flags


def _structure_complete(flags: dict[str, bool]) -> bool:
    required = [label for label, _ in STRUCTURE_CHECKS]
    return all(flags.get(key) for key in required)


async def _run_pipeline(query: str) -> tuple[dict[str, Any], str]:
    payload = await execute_web_search(query)
    results = payload.get("results") or []
    if not isinstance(results, list):
        results = [results]
    dossier = await synthesize_dossier(query, results)
    return payload, dossier


async def _run_case(case: TestCase) -> TestResult:
    started = time.perf_counter()
    result = TestResult(case=case, latency_ms=0.0, fallback_triggered=False, cache_hit=False)
    try:
        if case.simulate_api_error:
            with (
                patch(
                    "search._search_sync",
                    side_effect=RuntimeError("simulated Tavily outage"),
                ),
                patch(
                    "analyzer._anthropic_client.messages.create",
                    side_effect=RuntimeError("simulated Anthropic outage"),
                ),
            ):
                payload, dossier = await _run_pipeline(case.query)
        else:
            payload, dossier = await _run_pipeline(case.query)

        result.latency_ms = (time.perf_counter() - started) * 1000.0
        result.fallback_triggered = bool(payload.get("fallback"))
        result.cache_hit = bool(payload.get("cache_hit"))
        result.structure = _evaluate_structure(dossier)
        result.dossier_preview = " ".join((dossier or "").split())[:280]
        structure_ok = _structure_complete(result.structure)
        fallback_ok = True
        if case.expect_fallback is True:
            fallback_ok = result.fallback_triggered
        result.passed = structure_ok and fallback_ok and not result.error
    except Exception as exc:
        result.latency_ms = (time.perf_counter() - started) * 1000.0
        result.error = f"{type(exc).__name__}: {exc}"
        result.structure = {label: False for label, _ in STRUCTURE_CHECKS}
        result.structure["Markdown table rows"] = False
        result.passed = False
    return result


def _terminal_matrix(results: list[TestResult]) -> str:
    headers = (
        "Test",
        "Scenario",
        "Latency ms",
        "Fallback",
        "Exec Summary",
        "Matrix",
        "Contradiction",
        "Credibility",
        "Result",
    )
    rows: list[tuple[str, ...]] = []
    for item in results:
        struct = item.structure
        rows.append(
            (
                str(item.case.number),
                item.case.name,
                f"{item.latency_ms:.0f}",
                "True" if item.fallback_triggered else "False",
                _bool_cell(bool(struct.get("Executive Summary"))),
                _bool_cell(bool(struct.get("Matrix Table"))),
                _bool_cell(bool(struct.get("Contradiction Alert"))),
                _bool_cell(bool(struct.get("Source Credibility Tier"))),
                "PASS" if item.passed else "FAIL",
            )
        )
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def fmt(row: tuple[str, ...]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    rule = "-+-".join("-" * w for w in widths)
    lines = [fmt(headers), rule, *[fmt(row) for row in rows]]
    passed = sum(1 for item in results if item.passed)
    lines.append("")
    lines.append(f"Score: {passed}/{len(results)} tests passed")
    return "\n".join(lines)


def _markdown_report(results: list[TestResult]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    passed = sum(1 for item in results if item.passed)
    total = len(results)
    pct = (passed / total * 100.0) if total else 0.0
    lines = [
        "# OSINT Pipeline Evaluation Report",
        "",
        f"Generated: **{now}**",
        "",
        f"**Overall:** {passed}/{total} tests passed ({pct:.0f}%).",
        "",
        "## Summary matrix",
        "",
        "| Test | Scenario | Latency (ms) | Fallback Trigger | Executive Summary | Matrix Table | Contradiction Alert | Source Credibility | Result |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        struct = item.structure
        lines.append(
            "| {num} | {name} | {lat:.0f} | {fb} | {ex} | {mx} | {cd} | {cr} | {ok} |".format(
                num=item.case.number,
                name=item.case.name,
                lat=item.latency_ms,
                fb="True" if item.fallback_triggered else "False",
                ex=_bool_cell(bool(struct.get("Executive Summary"))),
                mx=_bool_cell(bool(struct.get("Matrix Table"))),
                cd=_bool_cell(bool(struct.get("Contradiction Alert"))),
                cr=_bool_cell(bool(struct.get("Source Credibility Tier"))),
                ok="PASS" if item.passed else "FAIL",
            )
        )
    lines.extend(["", "## Per-test detail", ""])
    for item in results:
        lines.append(f"### Test {item.case.number}: {item.case.name}")
        lines.append("")
        lines.append(f"- Query: `{item.case.query}`")
        lines.append(f"- Notes: {item.case.notes}")
        lines.append(f"- Latency: **{item.latency_ms:.0f} ms**")
        lines.append(
            f"- Fallback triggered: **{item.fallback_triggered}** "
            f"(cache_hit={item.cache_hit})"
        )
        if item.case.expect_fallback is True:
            lines.append("- Expected fallback: **True**")
        if item.error:
            lines.append(f"- Error: `{item.error}`")
        lines.append("- Structural completeness:")
        for label, _ in STRUCTURE_CHECKS:
            lines.append(f"  - {label}: {'yes' if item.structure.get(label) else 'no'}")
        if item.dossier_preview:
            lines.append(f"- Preview: {item.dossier_preview}")
        lines.append("")
    lines.extend(
        [
            "## Method",
            "",
            "- Tests 1–3 execute `execute_web_search` then `synthesize_dossier` (live APIs with cache fallback).",
            "- Test 4 patches Tavily search and Anthropic `messages.create` to raise, forcing offline cache synthesis for Razer AVA.",
            "- Test 5 uses an unknown query with the same simulated outage to verify cache-miss fallback still returns a structured dossier.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


async def run_evaluation() -> list[TestResult]:
    results: list[TestResult] = []
    for case in CASES:
        print(f"Running test {case.number}/5: {case.name}...", flush=True)
        results.append(await _run_case(case))
    return results


def main() -> int:
    logging.getLogger("search").setLevel(logging.CRITICAL)
    logging.getLogger("analyzer").setLevel(logging.CRITICAL)
    results = asyncio.run(run_evaluation())
    matrix = _terminal_matrix(results)
    print()
    print(matrix)
    REPORT_PATH.write_text(_markdown_report(results), encoding="utf-8")
    print()
    print(f"Wrote {REPORT_PATH}", flush=True)
    return 0 if all(item.passed for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
