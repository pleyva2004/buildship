"""Harness tools + per-turn state (design 07 §1).

TurnState rides the SDK's RunContext through one turn(). Tools record UI
actions into it instead of emitting <action> tags; turn() reads them back out.
Tool return values are for the MODEL (compact strings); the app only ever sees
state.action / state.recalled.
"""

import json
import re
from dataclasses import dataclass, field

from agents import RunContextWrapper, function_tool

from agent.clients import tavily_client
from agent.clients.mem0_client import Mem0Client

VALID_ACTIONS = {"recommend", "generate_tour"}

# Llama ignores "STOP calling tools" written into tool RESULTS — the only
# reliable brake is removing the tools. Once a turn's work is done (action set,
# blind research dispatched, budget spent, or a repeated call), wrap_up=True and
# the harness forces tool_choice="none" on the next model call, so the only
# move left is writing the reply.
TOOL_BUDGET = 6  # tool calls per turn before the forced wrap-up

# mirror of core.GENERATE_RE plus tour-ish phrasings — generate_tour may only
# fire when the CLIENT asked for it this turn, never as a model improvisation
TOUR_INTENT_RE = re.compile(
    r"show me|my version|my style|in (?:my|our) (?:style|taste)|tour|restyle", re.I)


def _log(tool: str, detail: str) -> None:
    print(f"[vista:tool] {tool}: {detail}")


TRACE_LABEL = {
    "recall_memories": "recalled memories",
    "search_web_listings": "searched the market",
    "recommend_listings": "picked homes",
    "generate_tour": "started your tour",
    "save_memory": "saved to memory",
    "revise_memory": "updated a memory",
    "research_area": "researched",
    "whats_nearby": "checked what's nearby",
}


def _trace(state, tool: str, suffix: str = "") -> None:
    state.tool_calls += 1
    if state.tool_calls >= TOOL_BUDGET:
        state.wrap_up = True
    entry = TRACE_LABEL.get(tool, tool) + (f" {suffix}" if suffix else "")
    if entry not in state.trace:
        state.trace.append(entry)


def _soft_wrap(state, grace: int = 2) -> None:
    """Shrink the remaining tool budget to `grace` calls — enough for a
    save_memory or a recall, not enough for a spiral."""
    state.tool_calls = max(state.tool_calls, TOOL_BUDGET - grace)


@dataclass
class TurnState:
    profile_id: str
    memory: Mem0Client
    user_msg: str = ""  # the raw client message this turn (tool guards read it)
    recalled: list = field(default_factory=list)  # facts shown in the memory rail
    action: dict | None = None  # at most one UI action per turn; last write wins
    new_facts: list = field(default_factory=list)  # learned this turn → "✓ Saved" chips
    researching: list = field(default_factory=list)  # areas dispatched in background
    trace: list = field(default_factory=list)  # human-readable tool activity (UI "behind the scenes")
    # research dispatched with NO prior intel: hold cards this turn — the UI's
    # follow-up turn presents them once the intel lands (two-phase turn)
    research_blind: bool = False
    tool_calls: int = 0  # per-turn count; TOOL_BUDGET trips the wrap-up
    wrap_up: bool = False  # harness forces tool_choice="none" on the next model call
    researched: set = field(default_factory=set)  # (area, kind) asked this turn — repeats wrap up


@function_tool
def recall_memories(ctx: RunContextWrapper[TurnState], query: str) -> str:
    """Search everything you remember about this client (taste, life situation,
    mood boards). Use when you need more context than you already have."""
    _log("recall_memories", query)
    _trace(ctx.context, "recall_memories")
    state = ctx.context
    seen = {m["id"] for m in state.recalled}
    found = [
        m for m in state.memory.search(state.profile_id, query, k=6)
        if m["category"] != "constraint"  # render rules, not conversation material
    ]
    state.recalled.extend(m for m in found if m["id"] not in seen)
    if not found:
        return "No memories matched that query."
    return "\n".join(f"- ({m['category']}) {m['text']}" for m in found)


@function_tool
def search_web_listings(ctx: RunContextWrapper[TurnState], query: str) -> str:
    """Search the live market for home listings. Use for market color and to
    ground your discovery story; only ever recommend homes from your INVENTORY."""
    _log("search_web_listings", query)
    _trace(ctx.context, "search_web_listings")
    results = tavily_client.search(query, max_results=3)
    if not results:
        return "No listings found."
    return "\n".join(f"- {r['title']} — {r['content'][:160]} ({r['url']})" for r in results)


@function_tool
def recommend_listings(ctx: RunContextWrapper[TurnState], listing_ids: list[str]) -> str:
    """Present specific listings to the client. Call this whenever your reply
    names listings — the UI renders their cards from it, IN YOUR ORDER, best
    match first. Re-call it whenever the client's ask changes what should rank
    first (e.g. "the cheapest" -> reorder by price). Use inventory ids."""
    _log("recommend_listings", ", ".join(listing_ids))
    _trace(ctx.context, "recommend_listings")
    if ctx.context.research_blind:
        # two-phase turn: cards wait for the research; steer the model to wrap up
        _soft_wrap(ctx.context, grace=1)
        return ("Cards are HELD until your research lands — you'll present them in "
                "your next reply. Stop calling tools and answer in prose now: tell "
                "the client what you're looking into.")
    if (ctx.context.action or {}).get("type") == "recommend":
        ctx.context.wrap_up = True
        return "Cards are already displayed. STOP calling tools — write your final reply now."
    listing_ids = listing_ids[:3]
    ctx.context.action = {"type": "recommend", "listing_ids": listing_ids}
    ctx.context.wrap_up = True  # the turn's job is done — all that's left is prose
    return f"Cards displayed for: {', '.join(listing_ids)}. Now write your final reply in prose."


@function_tool
def generate_tour(ctx: RunContextWrapper[TurnState], listing_id: str) -> str:
    """Generate the client's personalized restyled tour of a home. Call this when
    they ask to see a home in their style / their version."""
    _log("generate_tour", listing_id)
    _trace(ctx.context, "generate_tour")
    if not TOUR_INTENT_RE.search(ctx.context.user_msg):
        # spiral guard: the model reaches for the tour when other tools refuse —
        # it may only fire on an explicit ask from the client
        return ("The client has NOT asked to see a home in their style — do not "
                "start a tour. Answer their actual question in prose.")
    ctx.context.action = {"type": "generate_tour", "listing_id": listing_id}
    ctx.context.wrap_up = True
    return f"Tour generation started for {listing_id}. Tell the client it's rendering in their taste."


@function_tool
def save_memory(ctx: RunContextWrapper[TurnState], text: str,
                category: str = "life_situation", source: str = "inferred") -> str:
    """Save something NEW you just learned about the client. text is a short
    distilled tidbit at the PREFERENCE level ("Character beats new-build polish
    for them"), never listing-level ("liked alt1") and never a raw quote.
    category: life_situation | taste | materials | mood_board | other.
    source: stated (they said it) | inferred (you read between the lines)."""
    _log("save_memory", text)
    state = ctx.context
    _trace(state, "save_memory")
    state.memory.add(state.profile_id, text, category, source=source)
    state.new_facts.append({"text": text, "category": category, "provenance": source})
    return f"Saved to memory: {text}"


@function_tool
def revise_memory(ctx: RunContextWrapper[TurnState], old_fact: str, new_text: str, why: str) -> str:
    """The client's preference CHANGED or contradicts what you knew — replace the
    old fact instead of piling up a conflict. old_fact: the remembered fact to
    revise (your best recollection of its wording). new_text: the short distilled
    replacement. Acknowledge the revision out loud in your reply, naturally."""
    _log("revise_memory", f"{old_fact!r} -> {new_text!r}")
    state = ctx.context
    _trace(state, "revise_memory")
    matches = state.memory.search(state.profile_id, old_fact, k=1)
    if matches:
        state.memory.update(state.profile_id, matches[0]["id"], new_text)
        category = matches[0]["category"]
    else:  # nothing close enough — record the new truth rather than dropping it
        category = "taste"
        state.memory.add(state.profile_id, new_text, category, source="inferred")
    state.new_facts.append(
        {"text": new_text, "category": category, "provenance": "inferred", "revised": True}
    )
    return f"Memory updated: {new_text} (was: {old_fact})"


@function_tool
def research_area(ctx: RunContextWrapper[TurnState], area: str, focus: str = "") -> str:
    """Research an Austin neighborhood for this client — walkability, parks,
    vibe, market color. Call WHENEVER intel would help — discussing an area,
    grounding a recommendation, or digging a new angle (schools, commute,
    nightlife). Repeat calls with a NEW focus are encouraged; identical
    repeats are free no-ops. focus: what THIS client cares about right now."""
    from agent import researcher  # lazy: keeps tools importable without the module chain

    state = ctx.context
    _log("research_area", f"{area} (focus: {focus or 'general'})")
    area = area.strip().title()[:28]
    personalized = bool(focus) and focus != researcher.GENERAL
    fkind = f"focus:{focus.strip().lower()[:48]}" if personalized else "general"
    # the model retries identical calls verbatim when told to wait — one strike
    # and the harness pulls the tools (Zilker × 8 was real)
    if (area, fkind) in state.researched:
        state.wrap_up = True
        return (f"You ALREADY researched {area} this turn. Write your final reply "
                f"now from what you have.")
    state.researched.add((area, fkind))
    if sum(1 for t in state.trace if t.startswith("researched")) >= 2:
        state.wrap_up = True
        return ("STOP researching — you have plenty. Write your final reply now "
                "using what you already learned.")
    _trace(state, "research_area", area)  # a place name, not a sentence — keep tags clean

    if researcher.has(area, "general"):
        intel = researcher.research_area(area)  # general intel, cached
        if personalized and researcher.has(area, fkind):
            return researcher.research_area(area, focus, fkind)  # this angle, cached
        # the agent may dig any NEW angle whenever it judges useful — identical
        # repeats are no-ops, fresh focuses always dispatch
        if personalized and not researcher.pending(area, fkind):
            researcher.dispatch(state.profile_id, area, state.memory, focus, kind=fkind)
            if area not in state.researching:
                state.researching.append(area)
            intel += f" (A tailored pass on {focus} is running — more shortly.)"
        return intel

    if researcher.pending(area, "general"):
        _soft_wrap(state, grace=1)  # nothing left to research — one call, then prose
        return (f"Research on {area} is already running — answer from what you know; "
                f"specifics arrive momentarily.")
    # first mention: dispatch the GENERAL pass; never block the reply
    researcher.dispatch(state.profile_id, area, state.memory)
    if area not in state.researching:
        state.researching.append(area)
    state.research_blind = True
    _soft_wrap(state)  # room to save a fact or two, then narrate and end the turn
    return (f"Research on {area} dispatched — results arrive shortly. Tell the client "
            f"you're digging into {area} right now and what you're checking for them. "
            f"Do NOT present or recommend listings this turn — you'll present them "
            f"once the research lands.")


@function_tool
def whats_nearby(ctx: RunContextWrapper[TurnState], area: str, interests: list[str] = None) -> str:
    """Named places with walk times near a neighborhood (via Composio Maps) —
    coffee, dog parks, groceries, nightlife. Call when grounding a listing or
    answering "what's around there?". interests: what THIS client cares about
    (from memory: dog -> dog park, hosts -> restaurants)."""
    from agent.clients import composio_client

    state = ctx.context
    area = area.strip().title()[:28]
    _log("whats_nearby", f"{area} (interests: {interests or '—'})")
    _trace(state, "whats_nearby", area)
    places = composio_client.nearby_places(area, interests or [])
    if not places:
        return f"No nearby data for {area}."
    lines = [f"{p['name']} ({p['kind']}{', ' + p['walk'] if p['walk'] else ''})" for p in places]
    top = "; ".join(lines[:3])
    fact = {"category": "area_research", "provenance": "researched", "text": f"{area} nearby — {top}"}
    if not any(f["text"] == fact["text"] for f in state.new_facts):
        existing = [m["text"] for m in state.memory.all(state.profile_id)]
        if fact["text"] not in existing:
            state.memory.add(state.profile_id, fact["text"], "area_research", source="researched")
        state.new_facts.append(fact)
    return "\n".join(f"- {l}" for l in lines)


ALL_TOOLS = [recall_memories, search_web_listings, recommend_listings, generate_tour,
             save_memory, revise_memory, research_area, whats_nearby]
