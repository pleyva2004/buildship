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
_PENDING: set[str] = set()  # in-flight guard: an area is researched ONCE, ever

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


GENERAL = "walkability, parks, overall vibe"


def _key(area: str, kind: str) -> str:
    return f"{area}|{kind}"


def has(area: str, kind: str = "general") -> bool:
    return _key(area, kind) in _CACHE


def pending(area: str, kind: str = "general") -> bool:
    return _key(area, kind) in _PENDING


def status(area: str) -> str:
    """Across ALL kinds for an area: pending | done | unknown. Terminal either
    way except 'pending' — research_and_store always clears _PENDING, so a
    poller never sticks."""
    if any(k.split("|", 1)[0] == area for k in _PENDING):
        return "pending"
    if any(k.split("|", 1)[0] == area for k in _CACHE):
        return "done"
    return "unknown"


def research_and_store(profile_id: str, area: str, memory, focus: str = GENERAL, kind: str = "general") -> None:
    """Background worker: research -> cache -> mem0 area fact (clean tag).
    Deduped: skips the mem0 write if this area already has a research fact."""
    import time
    t0 = time.time()
    print(f"[vista:research] researching {area!r} (focus: {focus})")
    try:
        intel = research_area(area, focus, kind)
        first = intel.split(".")[0].strip()
        tag = first if len(first) <= 90 else first[:87] + "…"
        prefix = f"{area} — " if kind == "general" else f"{area} (for you) — "
        existing = [m["text"] for m in memory.all(profile_id)]
        # general: one fact per area. focused passes: dedupe on exact content,
        # so the agent can dig the same area from different angles.
        dup = (any(t.startswith(prefix) for t in existing) if kind == "general"
               else (prefix + tag) in existing)
        if not dup:
            memory.add(profile_id, prefix + tag, "area_research", source="researched")
        print(f"[vista:research] {area} done in {time.time()-t0:.1f}s -> mem0: {tag[:60]}")
    except Exception as exc:
        print(f"[vista:research] background research failed ({exc})")
    finally:
        _PENDING.discard(_key(area, kind))


def dispatch(profile_id: str, area: str, memory, focus: str = GENERAL, kind: str = "general") -> None:
    """Fire-and-forget research — deduped per (area, kind). kind='general'
    fires on first mention; any focused kind (e.g. 'focus:schools nearby') can
    fire whenever the agent judges it useful — identical repeats are no-ops,
    new angles always go through (Jake: agent dispatches at will)."""
    if has(area, kind) or pending(area, kind):
        return
    _PENDING.add(_key(area, kind))
    import threading
    threading.Thread(target=research_and_store, args=(profile_id, area, memory, focus, kind), daemon=True).start()


def research_area(area: str, focus: str = GENERAL, kind: str = "general") -> str:
    k = _key(area, kind)
    if k in _CACHE:
        return _CACHE[k]
    intel = _research(area, focus)
    _CACHE[k] = intel
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
