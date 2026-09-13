"""Tavily web-search integration with timeout and cache fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from tavily import TavilyClient

from cache import CacheManager
from config import TAVILY_API_KEY

logger = logging.getLogger(__name__)

SEARCH_TIMEOUT_SECONDS = 8.0
MAX_RESULTS = 5

_tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
_cache = CacheManager()


def _normalize_results(payload: Any) -> list[Any]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("raw_results", "results", "findings"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return nested
        return [payload]
    return [payload]


def _fallback_payload(
    query: str,
    *,
    error: str,
    cached: Any | None,
) -> dict[str, Any]:
    if cached is not None:
        return {
            "query": query,
            "results": _normalize_results(cached),
            "fallback": True,
            "cache_hit": True,
            "error": error,
        }
    return {
        "query": query,
        "results": [],
        "fallback": True,
        "cache_hit": False,
        "error": error,
    }


def _search_sync(query: str) -> Any:
    return _tavily_client.search(query=query, max_results=MAX_RESULTS)


async def execute_web_search(query: str) -> dict:
    """Run a Tavily search with an 8s timeout and cache fallback."""
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(_search_sync, query),
            timeout=SEARCH_TIMEOUT_SECONDS,
        )
        results = _normalize_results(response)
        payload: dict[str, Any] = {
            "query": query,
            "results": results,
            "fallback": False,
            "cache_hit": False,
            "error": None,
        }
        if isinstance(response, dict) and "answer" in response:
            payload["answer"] = response.get("answer")
        try:
            _cache.set(query, payload)
        except Exception:
            logger.exception("Failed to persist Tavily results to cache")
        return payload
    except asyncio.TimeoutError:
        logger.exception("Tavily search timed out after %.1fs: %s", SEARCH_TIMEOUT_SECONDS, query)
        cached = _cache.get(query)
        logger.warning(
            "Tavily fallback cache_%s for query=%s",
            "hit" if cached is not None else "miss",
            query,
        )
        return _fallback_payload(
            query,
            error=f"Tavily search timed out after {SEARCH_TIMEOUT_SECONDS:.1f}s",
            cached=cached,
        )
    except Exception as exc:
        logger.exception("Tavily search failed: %s", query)
        cached = _cache.get(query)
        logger.warning(
            "Tavily fallback cache_%s for query=%s",
            "hit" if cached is not None else "miss",
            query,
        )
        return _fallback_payload(
            query,
            error=f"Tavily search failed: {exc}",
            cached=cached,
        )
