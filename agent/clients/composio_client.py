"""Composio client — MOCK | LIVE (the context bus: Maps now, Notion import next).

nearby_places(area, interests) -> small list of named places with walk times.
LIVE: Composio v3 tool execution (Google Maps toolkit) — requires an activated
COMPOSIO_API_KEY + a connected Google Maps toolkit in the dashboard. MOCK:
canned POIs per neighborhood (agent/mocks/nearby.json) — deterministic, the
stage fallback. Any live failure degrades to mock.
"""

import json
import urllib.request

from agent import config

API_BASE = "https://backend.composio.dev/api/v3"

_NEARBY = None


def _canned() -> dict:
    global _NEARBY
    if _NEARBY is None:
        _NEARBY = json.loads((config.MOCKS_DIR / "nearby.json").read_text())
    return _NEARBY


def _mock(area: str, interests: list[str]) -> list[dict]:
    data = _canned()
    key = next((k for k in data if k.lower() in area.lower() or area.lower() in k.lower()), "default")
    places = data[key]
    if interests:  # personalized ordering: interest-matched kinds first
        wants = [i.lower() for i in interests]
        places = sorted(places, key=lambda p: 0 if any(w in p["kind"] for w in wants) else 1)
    return places[:5]


def nearby_places(area: str, interests: list[str] | None = None) -> list[dict]:
    """-> [{name, kind, walk}] best-first for this client's interests."""
    interests = interests or []
    if config.backend("composio") == "live":
        try:
            return _live(area, interests)
        except Exception as exc:
            print(f"[vista:nearby] live lookup failed ({exc}); using canned places")
    return _mock(area, interests)


def _live(area: str, interests: list[str]) -> list[dict]:
    if not config.COMPOSIO_API_KEY:
        raise RuntimeError("COMPOSIO_API_KEY not set")
    query = f"{', '.join(interests) or 'cafes and parks'} near {area}, Austin TX"
    req = urllib.request.Request(
        f"{API_BASE}/tools/execute/GOOGLEMAPS_TEXT_SEARCH",
        data=json.dumps({"arguments": {"query": query}, "user_id": "vista"}).encode(),
        headers={"x-api-key": config.COMPOSIO_API_KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    places = (data.get("data") or {}).get("places") or []
    out = [{"name": p.get("displayName", {}).get("text") or p.get("name", "?"),
            "kind": (p.get("types") or ["place"])[0].replace("_", " "),
            "walk": ""} for p in places[:5]]
    if not out:
        raise RuntimeError("no places returned")
    return out
