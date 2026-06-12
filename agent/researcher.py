"""Area research subagent (design 10b / task: Tavily area intel).

research_area(area, focus) -> short neighborhood intel grounded in the user's
criteria. LIVE: Tavily search -> Nebius distill (one completion — a true
sub-call the main agent invokes as a tool). MOCK: canned notes from
agent/mocks/areas.json — deterministic, zero keys. Any live failure degrades
to mock. Findings are meant to feed narration + mem0 area facts.
"""

import json
import re

from agent import config
from agent.clients import nebius, tavily_client

_AREAS = None
_CACHE: dict[str, str] = {}  # per-process: repeat questions never re-burn Tavily

DISTILL = """You are VISTA's area researcher. From the search results below, write \
2-3 short sentences of neighborhood intel about {area} for a home buyer who cares \
about: {focus}. Concrete and specific (walk times, named parks/streets/cafés), warm \
but factual, no hype words. If results are thin, say what you do know confidently.

RESULTS:
{results}"""


def _canned() -> dict:
    global _AREAS
    if _AREAS is None:
        _AREAS = json.loads((config.MOCKS_DIR / "areas.json").read_text())
    return _AREAS


def _mock(area: str) -> str:
    notes = _canned()
    key = next((k for k in notes if k.lower() in area.lower() or area.lower() in k.lower()), None)
    return notes[key] if key else notes["default"]


def research_area(area: str, focus: str = "walkability, parks, overall vibe") -> str:
    if area in _CACHE:
        return _CACHE[area]
    intel = _research(area, focus)
    _CACHE[area] = intel
    return intel


def _research(area: str, focus: str) -> str:
    if config.backend("tavily") == "live":
        try:
            results = tavily_client.search(
                f"{area} Austin neighborhood guide {focus}", max_results=4
            )
            blob = "\n".join(f"- {r['title']}: {r['content'][:280]}" for r in results)
            reply = nebius.chat(
                [{"role": "system", "content": DISTILL.format(area=area, focus=focus, results=blob)},
                 {"role": "user", "content": "Write the intel now."}],
                temperature=0.3,
            )
            reply = re.sub(r"\s+", " ", reply).strip()
            if len(reply) > 40:  # canned-turn fallback from nebius.chat won't pass this shape check
                return reply
        except Exception as exc:
            print(f"[researcher] live research failed ({exc}); using canned notes")
    return _mock(area)
