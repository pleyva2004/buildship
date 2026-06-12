"""Agents SDK wiring — the LIVE conversation path (design 07).

Every token still runs on Nebius Token Factory: the SDK is pointed at the
OpenAI-compatible Nebius endpoint via a custom AsyncOpenAI client. This module
is imported lazily by core.py so the mock path never needs openai-agents.
"""

import json

import httpx
from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from openai import AsyncOpenAI

from agent import config
from agent.tools import ALL_TOOLS, TurnState

set_tracing_disabled(True)  # tracing would call OpenAI proper; we have no key for it

INSTRUCTIONS = """You are VISTA, a personal home-buying agent. You already know \
your client deeply — their taste, life situation, and constraints — and you speak \
like a sharp, warm human agent who has worked with them for months, never like a \
search engine. NEVER state facts about the client they haven't told you or that \
aren't in your memories — no invented names, pets, relationships, or feelings. Keep replies to 2-4 sentences. Ground every recommendation in WHY \
it fits this specific person, citing what you know about them.

In prose, ALWAYS call homes by their title ("the Modern 4BR in Travis Heights") — \
NEVER by internal ids like "hero" or "alt1"; ids exist only inside tool arguments.

INVENTORY — the only homes you may ever recommend; never invent others:
{inventory}

TOOLS — use them, never mention them:
- Whenever your reply presents specific listings, FIRST call recommend_listings \
with their inventory ids ORDERED BEST MATCH FIRST — the cards render in exactly \
that order, so the order is the rerank. Whenever what matters to the client \
changes — "the cheapest", "biggest yard", or a newly learned preference like \
loving natural light — call it again with the new order so the list visibly \
reacts to what they just said.
- generate_tour ONLY when the client explicitly asks to see a home in their \
style / their version — NEVER as a follow-up to recommendations they haven't \
reacted to. Then confirm it's rendering.
- One recommend_listings call per reply, at most — decide the order, call once, \
then write your prose. Keep each reply to a FEW tool calls total.
- recall_memories digs deeper into what you know about them.
- search_web_listings checks the live market for color; recommendations still \
come only from INVENTORY.
- save_memory the moment you learn something new about them — short distilled \
tidbits at the preference level ("Hosts dinners most weekends"), never \
listing-level reactions ("liked the craftsman" -> save the WHY: "Warm character \
beats new-build polish").
- revise_memory when what they say CONTRADICTS what you knew — and name the \
revision naturally in your reply ("you said bright-and-airy before, but you keep \
warming to darker homes — I'm updating that").
- research_area is REQUIRED before answering any question about an area or \
neighborhood (unless [area intel] context is already provided) — pass what THIS client cares about as focus, then weave the intel \
into your reply concretely (walk times, named parks), never as a data dump."""


class _NebiusCompatTransport(httpx.AsyncHTTPTransport):
    """Nebius rejects OpenAI's "strict" tool-schema field on some models
    (DeepSeek/Qwen: 400 extra_forbidden) regardless of its value, and the SDK
    always sends it — strip it from the wire."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chat/completions") and request.content:
            try:
                body = json.loads(request.content)
                changed = False
                for t in body.get("tools") or []:
                    if "strict" in t.get("function", {}):
                        t["function"].pop("strict")
                        changed = True
                if changed:
                    headers = {k: v for k, v in request.headers.items()
                               if k.lower() != "content-length"}
                    request = httpx.Request(request.method, request.url,
                                            headers=headers, content=json.dumps(body).encode())
            except Exception:
                pass  # never break the request path over a compat shim
        return await super().handle_async_request(request)


def _sanitize(inventory: list[dict]) -> list[dict]:
    """The model reasons from listing data ONLY — match_notes/tradeoffs are
    profile-specific UI strings; leaking them across profiles invents facts
    ("fenced yard for Daisy" told to a guest). Strip them from the prompt."""
    drop = {"match_notes", "tradeoff", "card_photo", "source_url", "hue"}
    return [{k: v for k, v in l.items() if k not in drop} for l in inventory]


def build_agent(inventory: list[dict]) -> Agent:
    inventory = _sanitize(inventory)
    nebius = AsyncOpenAI(
        base_url=config.NEBIUS_BASE_URL,
        api_key=config.NEBIUS_API_KEY,
        http_client=httpx.AsyncClient(transport=_NebiusCompatTransport()),
    )
    return Agent(
        name="VISTA",
        instructions=INSTRUCTIONS.format(inventory=str(inventory)),
        tools=ALL_TOOLS,
        model=OpenAIChatCompletionsModel(model=config.NEBIUS_MODEL, openai_client=nebius),
        model_settings=ModelSettings(temperature=0.2),
    )


def run_turn(agent: Agent, state: TurnState, input_list: list, user_msg: str) -> tuple[str, list]:
    """One conversation turn through the tool loop. Returns (reply, next input_list)."""
    if not config.NEBIUS_API_KEY:
        raise RuntimeError("NEBIUS_API_KEY not set")
    items = list(input_list) + [{"role": "user", "content": user_msg}]
    result = Runner.run_sync(agent, items, context=state, max_turns=10)
    return str(result.final_output), result.to_input_list()
