"""VISTA agent — terminal chat loop with mem0 recall (design 04, v2).

Run:  make agent                       (all-mock, zero keys)
      PROFILE=pablo_v1 make agent      (other persona)
      MEM0_BACKEND=live make agent     (real memory, mock LLM)
      VISTA_BACKEND=live make agent    (everything live)

Each turn: recall top-k facts from mem0 -> print [recall] -> inject into the
prompt -> one LLM call. The {reply, recalled} shape here is exactly what the
HTTP layer will hand the app's memory rail.
"""

import os
import sys

from agent import config
from agent.clients import nebius
from agent.clients.mem0_client import Mem0Client

SYSTEM_PROMPT = """You are VISTA, a personal home-buying agent. You already know \
your client deeply — their taste, life situation, and constraints — and you speak \
like a sharp, warm human agent who has worked with them for months, never like a \
search engine. Keep replies to 2-4 sentences. Ground every recommendation in WHY \
it fits this specific person, citing what you know about them. When they ask to \
see a home "in their style" or "their version", confirm you are generating their \
personalized tour."""


def build_turn_message(user_msg: str, recalled: list[dict]) -> str:
    """Inject recalled memories as context the model must ground its reply in."""
    if not recalled:
        return user_msg
    facts = "\n".join(f"- ({m['category']}) {m['text']}" for m in recalled)
    return (
        f"[context — what you remember about this client, most relevant first]\n"
        f"{facts}\n\n[client says]\n{user_msg}"
    )


def run() -> None:
    profile_id = os.environ.get("PROFILE", "jake_v1")
    memory = Mem0Client()
    known = memory.all(profile_id)

    print(
        f"VISTA agent — profile: {profile_id} | "
        f"llm: {config.backend('nebius')} | memory: {config.backend('mem0')}"
    )
    print(f"[context] {len(known)} memories loaded\n")

    history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        try:
            user_msg = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_msg:
            continue
        if user_msg.lower() in {"exit", "quit"}:
            break

        # constraints are render rules for the restyle pipeline, not conversation
        # material — keep them out of recall or the LLM over-interprets them
        # (e.g. "no people" read as "wants seclusion")
        recalled = [m for m in memory.search(profile_id, user_msg, k=6) if m["category"] != "constraint"][:4]
        if recalled:
            print("[recall] " + " • ".join(m["text"] for m in recalled))

        history.append({"role": "user", "content": build_turn_message(user_msg, recalled)})
        reply = nebius.chat(history)
        history.append({"role": "assistant", "content": reply})
        print(f"agent> {reply}\n")


if __name__ == "__main__":
    sys.exit(run())
