"""Harness tools + per-turn state (design 07 §1).

TurnState rides the SDK's RunContext through one turn(). Tools record UI
actions into it instead of emitting <action> tags; turn() reads them back out.
Tool return values are for the MODEL (compact strings); the app only ever sees
state.action / state.recalled.
"""

import json
from dataclasses import dataclass, field

from agents import RunContextWrapper, function_tool

from agent.clients import tavily_client
from agent.clients.mem0_client import Mem0Client

VALID_ACTIONS = {"recommend", "generate_tour"}


@dataclass
class TurnState:
    profile_id: str
    memory: Mem0Client
    recalled: list = field(default_factory=list)  # facts shown in the memory rail
    action: dict | None = None  # at most one UI action per turn; last write wins
    new_facts: list = field(default_factory=list)  # learned this turn → "✓ Saved" chips


@function_tool
def recall_memories(ctx: RunContextWrapper[TurnState], query: str) -> str:
    """Search everything you remember about this client (taste, life situation,
    mood boards). Use when you need more context than you already have."""
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
    results = tavily_client.search(query, max_results=3)
    if not results:
        return "No listings found."
    return "\n".join(f"- {r['title']} — {r['content'][:160]} ({r['url']})" for r in results)


@function_tool
def recommend_listings(ctx: RunContextWrapper[TurnState], listing_ids: list[str]) -> str:
    """Present specific listings to the client. Call this whenever your reply
    names listings — the UI renders their cards from it. Use inventory ids."""
    ctx.context.action = {"type": "recommend", "listing_ids": listing_ids}
    return f"Cards displayed for: {', '.join(listing_ids)}. Now give your reasoning in prose."


@function_tool
def generate_tour(ctx: RunContextWrapper[TurnState], listing_id: str) -> str:
    """Generate the client's personalized restyled tour of a home. Call this when
    they ask to see a home in their style / their version."""
    ctx.context.action = {"type": "generate_tour", "listing_id": listing_id}
    return f"Tour generation started for {listing_id}. Tell the client it's rendering in their taste."


@function_tool
def save_memory(ctx: RunContextWrapper[TurnState], text: str,
                category: str = "life_situation", source: str = "inferred") -> str:
    """Save something NEW you just learned about the client. text is a short
    distilled tidbit at the PREFERENCE level ("Character beats new-build polish
    for them"), never listing-level ("liked alt1") and never a raw quote.
    category: life_situation | taste | materials | mood_board | other.
    source: stated (they said it) | inferred (you read between the lines)."""
    state = ctx.context
    state.memory.add(state.profile_id, text, category, source=source)
    state.new_facts.append({"text": text, "category": category, "provenance": source})
    return f"Saved to memory: {text}"


@function_tool
def revise_memory(ctx: RunContextWrapper[TurnState], old_fact: str, new_text: str, why: str) -> str:
    """The client's preference CHANGED or contradicts what you knew — replace the
    old fact instead of piling up a conflict. old_fact: the remembered fact to
    revise (your best recollection of its wording). new_text: the short distilled
    replacement. Acknowledge the revision out loud in your reply, naturally."""
    state = ctx.context
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


ALL_TOOLS = [recall_memories, search_web_listings, recommend_listings, generate_tour,
             save_memory, revise_memory]
