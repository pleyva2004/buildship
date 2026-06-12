"""Agents SDK wiring — the LIVE conversation path (design 07).

Every token still runs on Nebius Token Factory: the SDK is pointed at the
OpenAI-compatible Nebius endpoint via a custom AsyncOpenAI client. This module
is imported lazily by core.py so the mock path never needs openai-agents.
"""

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from openai import AsyncOpenAI

from agent import config
from agent.tools import ALL_TOOLS, TurnState

set_tracing_disabled(True)  # tracing would call OpenAI proper; we have no key for it

INSTRUCTIONS = """You are VISTA, a personal home-buying agent. You already know \
your client deeply — their taste, life situation, and constraints — and you speak \
like a sharp, warm human agent who has worked with them for months, never like a \
search engine. Keep replies to 2-4 sentences. Ground every recommendation in WHY \
it fits this specific person, citing what you know about them.

INVENTORY — the only homes you may ever recommend; never invent others:
{inventory}

TOOLS — use them, never mention them:
- Whenever your reply presents specific listings, FIRST call recommend_listings \
with their inventory ids so the client sees the cards.
- When the client asks to see a home in their style / their version, call \
generate_tour, then confirm it's rendering.
- recall_memories digs deeper into what you know about them.
- search_web_listings checks the live market for color; recommendations still \
come only from INVENTORY.
- save_memory the moment you learn something new about them — short distilled \
tidbits at the preference level ("Hosts dinners most weekends"), never \
listing-level reactions ("liked the craftsman" -> save the WHY: "Warm character \
beats new-build polish").
- revise_memory when what they say CONTRADICTS what you knew — and name the \
revision naturally in your reply ("you said bright-and-airy before, but you keep \
warming to darker homes — I'm updating that")."""


def build_agent(inventory: list[dict]) -> Agent:
    nebius = AsyncOpenAI(base_url=config.NEBIUS_BASE_URL, api_key=config.NEBIUS_API_KEY)
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
    result = Runner.run_sync(agent, items, context=state, max_turns=6)
    return str(result.final_output), result.to_input_list()
