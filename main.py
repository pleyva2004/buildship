"""Buildship entrypoint.

Run from the repo root:

    uv run main.py

Loads `.env` and reports which provider keys are present so you can confirm
your environment before kicking off the build loop.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Vendor keys the harness needs to do real work.
REQUIRED_KEYS = ["NEBIUS_API_KEY", "TAVILY_API_KEY", "COMPOSIO_API_KEY"]


def main() -> None:
    print("Buildship — config check\n")

    missing = []
    for key in REQUIRED_KEYS:
        present = bool(os.getenv(key))
        print(f"  {'✓' if present else '✗'} {key}")
        if not present:
            missing.append(key)

    if missing:
        print(
            f"\nMissing {len(missing)} key(s). "
            "Copy .env.example to .env and fill them in."
        )
    else:
        print("\nAll keys present. Ready to build tools.")


if __name__ == "__main__":
    main()
