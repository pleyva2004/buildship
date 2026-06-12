"""VISTA agent — v1 terminal chat loop (design 04, stage v1: chat only).

Run:  make agent          (mock backend, zero keys needed)
      VISTA_BACKEND=live make agent   (once NEBIUS_API_KEY is in .env)

v1 scope: system prompt + rolling history + one LLM call per turn. The mem0
recall step, listing index, and <action> tags from design 04 land in v2 —
this file is the spine they plug into.
"""

import sys

from agent import config
from agent.clients import nebius

SYSTEM_PROMPT = """You are VISTA, a personal home-buying agent. You already know \
your client deeply — their taste, life situation, and constraints — and you speak \
like a sharp, warm human agent who has worked with them for months, never like a \
search engine. Keep replies to 2-4 sentences. Ground every recommendation in WHY \
it fits this specific person. When they ask to see a home "in their style" or \
"their version", confirm you are generating their personalized tour."""


def run() -> None:
    mode = config.backend("nebius")
    print(f"VISTA agent v1 — backend: {mode} (model: {config.NEBIUS_MODEL})")
    print("Type 'exit' to quit.\n")

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

        history.append({"role": "user", "content": user_msg})
        reply = nebius.chat(history)
        history.append({"role": "assistant", "content": reply})
        print(f"agent> {reply}\n")


if __name__ == "__main__":
    sys.exit(run())
