"""Tavily client — MOCK | LIVE (designs 03, 07).

Interface: search(query) / extract(url). Two consumers:
  - agent/listings.py — one-time B2 discovery (writes index.draft.json)
  - agent/tools.py    — the harness's search_web_listings tool (live path)

MOCK: canned responses from agent/mocks/tavily.json — deterministic, zero keys.
LIVE: Tavily REST API (stdlib urllib, zero deps).
"""

import json
import urllib.request

from agent import config

API_BASE = "https://api.tavily.com"

_CANNED = None  # lazy-loaded mock responses


def search(query: str, max_results: int = 5) -> list[dict]:
    """-> [{title, url, content, score}], best first."""
    if config.backend("tavily") == "live":
        data = _api("/search", {"query": query, "max_results": max_results, "include_images": True})
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
            }
            for r in data.get("results", [])
        ]
    return _canned()["search"][:max_results]


def extract(url: str) -> dict:
    """-> {url, raw_content, images} for one listing page."""
    if config.backend("tavily") == "live":
        data = _api("/extract", {"urls": [url], "include_images": True})
        results = data.get("results", [])
        if not results:
            raise RuntimeError(f"tavily extract returned nothing for {url}")
        r = results[0]
        return {
            "url": r.get("url", url),
            "raw_content": r.get("raw_content", ""),
            "images": r.get("images", []),
        }
    canned = _canned()["extract"]
    return canned.get(url, canned["default"])


def _canned() -> dict:
    global _CANNED
    if _CANNED is None:
        _CANNED = json.loads((config.MOCKS_DIR / "tavily.json").read_text())
    return _CANNED


def _api(path: str, body: dict):
    if not config.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY not set")
    req = urllib.request.Request(
        API_BASE + path,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {config.TAVILY_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)
