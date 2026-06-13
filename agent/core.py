"""AgentSession — the transport-agnostic agent brain (designs 04, 07).

No HTTP imports here, ever. The terminal REPL (loop.py) and the FastAPI bridge
(server.py) are both thin shells over this class. Two paths per turn:

  MOCK (default): recall -> inject context -> canned turn -> parse <action> tag
  LIVE: recall -> inject context -> Agents SDK tool loop on Nebius (harness.py)

A live failure on any turn degrades to the mock turn — the demo never stalls.
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
- When you present specific listings to the client (ids ordered best match
  first — the UI shows their cards in exactly this order):
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
        self._agent = None  # lazy-built SDK agent (live path only)
        self._sdk_input: list = []  # SDK-shaped conversation (result.to_input_list())

    def turn(self, user_msg: str) -> dict:
        """-> {reply, action, recalled} — the exact shape the app consumes."""
        # constraints are render rules for the restyle pipeline, not conversation
        # material (e.g. "no people" read as "wants seclusion")
        recalled = [
            m for m in self.memory.search(self.profile_id, user_msg, k=6)
            if m["category"] != "constraint"
        ][:4]

        if config.backend("nebius") == "live":
            try:
                return self._turn_live(user_msg, recalled)
            except Exception as exc:  # never stall the demo
                print(f"[harness] live turn failed ({exc}); falling back to mock turn")
        return self._turn_mock(user_msg, recalled)

    # -- mock: canned keyword turns + <action> tags (the stage fallback) ----

    def _turn_mock(self, user_msg: str, recalled: list[dict]) -> dict:
        self.history.append({"role": "user", "content": build_turn_message(user_msg, recalled)})
        reply, action = parse_action(nebius.chat_mock(self.history))
        action = action or self._backstop(user_msg)
        self.history.append({"role": "assistant", "content": reply})
        return {"reply": reply, "action": action, "recalled": recalled, "new_facts": [], "researching": [], "trace": []}

    # -- live: Agents SDK tool loop on Nebius (design 07) -------------------

    def _turn_live(self, user_msg: str, recalled: list[dict]) -> dict:
        from agent import harness  # lazy: mock path never needs openai-agents
        from agent.tools import TurnState

        if self._agent is None:
            self._agent = harness.build_agent(load_listings()["listings"])
        state = TurnState(profile_id=self.profile_id, memory=self.memory,
                          user_msg=user_msg, recalled=list(recalled))

        msg = build_turn_message(user_msg, recalled)
        # Jake's hook #2: the client asked about an area -> research is GUARANTEED.
        # Cached intel injects instantly; a cache miss DISPATCHES research in the
        # background and the agent answers now (never feels stuck) — the intel
        # lands in mem0 + cache for the rail refresh and the next turn.
        intel_block, dispatched = self._area_intel(user_msg)
        if intel_block:
            msg = f"{intel_block}\n\n{msg}"
        if dispatched:
            state.researching.extend(dispatched)
            state.research_blind = True
            msg = (f"[note: fresh research on {', '.join(dispatched)} is running — tell the "
                   f"client you're looking into it and what you're checking for them; do NOT "
                   f"present or recommend listings yet — you'll present them once the "
                   f"research lands]\n\n{msg}")
        import time
        t0 = time.time()
        print(f"[vista:turn] live turn start — profile={self.profile_id} model={config.NEBIUS_MODEL} recalled={len(recalled)}")
        reply, self._sdk_input = harness.run_turn(self._agent, state, self._sdk_input, msg)
        print(f"[vista:turn] done in {time.time()-t0:.1f}s — action={(state.action or {}).get('type')} "
              f"facts={len(state.new_facts)} researching={state.researching or '—'}")
        action = state.action
        # Two-phase turn: research is running with no prior intel — hold any
        # model-initiated action (cards wait for the intel; a spurious tour
        # must not hijack the turn). The UI sends a follow-up turn once the
        # intel lands, and THAT reply presents the listings grounded in it.
        REFUSAL = ("not able to", "outside of the scope", "as an ai", "i cannot", "unable to")
        if state.research_blind and (len(reply) < 30 or any(r in reply.lower() for r in REFUSAL)):
            areas = ", ".join(state.researching) or "the area"
            reply = (f"Let me pull what's current on {areas} for you — one moment. "
                     f"I'll come right back with what I find and the homes that fit.")
        if state.research_blind and action:
            print(f"[vista:turn] holding {action.get('type')} — presenting after research lands")
            action = None
        # keyword backstop AFTER the hold: an explicit "show me my version"
        # still always fires the tour (design 04 §2).
        action = action or self._backstop(user_msg)

        # mirror into mock history so a mid-conversation fallback keeps context
        self.history.append({"role": "user", "content": msg})
        self.history.append({"role": "assistant", "content": reply})
        return {
            "reply": reply,
            "action": action,
            "recalled": state.recalled,
            "new_facts": state.new_facts,  # save_memory/revise_memory writes this turn
            "researching": state.researching,  # background research underway (UI narrates + refreshes)
            "trace": state.trace,  # truthful "behind the scenes" line in the UI
        }

    def _area_intel(self, user_msg: str) -> tuple[str | None, list[str]]:
        """Mentioned neighborhoods -> (cached intel to inject, areas dispatched)."""
        if config.backend("tavily") != "live" and config.backend("nebius") != "live":
            return None, []
        from agent import researcher

        low = user_msg.lower()
        hoods = {l.get("neighborhood", "") for l in load_listings()["listings"]}
        hits = [h for h in hoods if h and h.lower() in low][:2]
        cached = [h for h in hits if researcher.has(h)]
        dispatched = []
        for h in hits:
            if not researcher.has(h) and not researcher.pending(h):
                print(f"[vista:research] dispatching background research: {h}")
                researcher.dispatch(self.profile_id, h, self.memory)
                dispatched.append(h)
        if not cached:
            return None, dispatched
        notes = "\n".join(f"- {h}: {researcher.research_area(h)}" for h in cached)
        return f"[area intel — fresh research, weave in naturally]\n{notes}", dispatched

    @staticmethod
    def _backstop(user_msg: str) -> dict | None:
        if GENERATE_RE.search(user_msg):
            return {"type": "generate_tour", "listing_id": "hero"}
        return None
