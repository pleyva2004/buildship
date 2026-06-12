"""AgentSession — the transport-agnostic agent brain (design 04).

No HTTP imports here, ever. The terminal REPL (loop.py) and the FastAPI bridge
(server.py) are both thin shells over this class. One LLM call per turn:
recall from mem0 -> inject context -> chat -> parse <action> tag.
"""

import json
import re

from agent import config
from agent.clients import nebius
from agent.clients.mem0_client import Mem0Client

SYSTEM_PROMPT = """You are VISTA, a personal home-buying agent. You already know \
your client deeply — their taste, life situation, and constraints — and you speak \
like a sharp, warm human agent who has worked with them for months, never like a \
search engine. Keep replies to 2-4 sentences. Ground every recommendation in WHY \
it fits this specific person, citing what you know about them.

INVENTORY — the only listings that exist; never invent others:
{inventory}

ACTIONS — append at most ONE tag, as the very last thing in your reply:
- When you present specific listings to the client:
  <action>{{"type": "recommend", "listing_ids": ["hero", "alt1"]}}</action>
- When the client asks to see a home in their style / their version:
  <action>{{"type": "generate_tour", "listing_id": "hero"}}</action>
Never mention the tags or the word "action" in your prose."""

ACTION_RE = re.compile(r"<action>\s*(\{.*?\})\s*</action>", re.S)
# Keyword backstop (design 04 §2): the tour moment can never fail to fire.
GENERATE_RE = re.compile(r"show me|my version|my style", re.I)


def load_listings() -> dict:
    return json.loads((config.ASSETS_DIR / "listings" / "index.json").read_text())


def parse_action(raw: str) -> tuple[str, dict | None]:
    """Strip a trailing <action> tag; forgiving — bad JSON means no action."""
    match = ACTION_RE.search(raw)
    if not match:
        return raw.strip(), None
    reply = ACTION_RE.sub("", raw).strip()
    try:
        return reply, json.loads(match.group(1))
    except json.JSONDecodeError:
        return reply, None


def build_turn_message(user_msg: str, recalled: list[dict]) -> str:
    if not recalled:
        return user_msg
    facts = "\n".join(f"- ({m['category']}) {m['text']}" for m in recalled)
    return (
        f"[context — what you remember about this client, most relevant first]\n"
        f"{facts}\n\n[client says]\n{user_msg}"
    )


class AgentSession:
    """One conversation. History lives in-process (single-user demo, no DB)."""

    def __init__(self, profile_id: str, memory: Mem0Client | None = None):
        self.profile_id = profile_id
        self.memory = memory or Mem0Client()
        inventory = json.dumps(load_listings()["listings"], indent=None)
        self.history: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT.format(inventory=inventory)}
        ]

    def turn(self, user_msg: str) -> dict:
        """-> {reply, action, recalled} — the exact shape the app consumes."""
        # constraints are render rules for the restyle pipeline, not conversation
        # material (e.g. "no people" read as "wants seclusion")
        recalled = [
            m for m in self.memory.search(self.profile_id, user_msg, k=6)
            if m["category"] != "constraint"
        ][:4]

        self.history.append({"role": "user", "content": build_turn_message(user_msg, recalled)})
        raw = nebius.chat(self.history)
        reply, action = parse_action(raw)

        if action is None and GENERATE_RE.search(user_msg):
            action = {"type": "generate_tour", "listing_id": "hero"}

        self.history.append({"role": "assistant", "content": reply})
        return {"reply": reply, "action": action, "recalled": recalled}
