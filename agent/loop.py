"""VISTA agent — terminal REPL, a thin shell over AgentSession (agent/core.py).

Run:  make agent                       (all-mock, zero keys)
      PROFILE=pablo_v1 make agent      (other persona)
      VISTA_BACKEND=live make agent    (everything live)
"""

import os
import sys

from agent import config
from agent.core import AgentSession


def run() -> None:
    profile_id = os.environ.get("PROFILE", "jake_v1")
    session = AgentSession(profile_id)
    known = session.memory.all(profile_id)

    print(
        f"VISTA agent — profile: {profile_id} | "
        f"llm: {config.backend('nebius')} | memory: {config.backend('mem0')}"
    )
    print(f"[context] {len(known)} memories loaded\n")

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

        turn = session.turn(user_msg)
        if turn["recalled"]:
            print("[recall] " + " • ".join(m["text"] for m in turn["recalled"]))
        if turn["action"]:
            print(f"[action] {turn['action']}")
        print(f"agent> {turn['reply']}\n")


if __name__ == "__main__":
    sys.exit(run())
