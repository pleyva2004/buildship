"""Seed mem0 with both profiles (B1).

  make seed                       # mock (sanity-check flattening)
  MEM0_BACKEND=live make seed     # real mem0 — wipes + re-seeds both profiles
"""

import json

from agent.clients.mem0_client import Mem0Client, PROFILE_FILES, flatten_profile


def main() -> None:
    client = Mem0Client()
    mode = "live" if client.live else "mock"
    for pid, path in PROFILE_FILES.items():
        facts = flatten_profile(json.loads(path.read_text()))
        if client.live:
            client.delete_all(pid)  # idempotent re-seed
            client.seed(pid, facts)
        print(f"[{mode}] {pid}: seeded {len(facts)} facts")
        for mem in client.all(pid):
            print(f"    [{mem['category']:>14}] {mem['text']}")


if __name__ == "__main__":
    main()
