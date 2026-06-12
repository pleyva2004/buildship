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


ALL_TOOLS = [recall_memories, search_web_listings, recommend_listings, generate_tour]
