"""End-to-end smoke test of the buildship chart hero task.

This drives the FULL Stage-1 loop against live services:

    gap detected -> Tavily research -> Nebius codegen -> sandbox self-test
    (Composio remote workbench, or local) -> validation gate -> register
    -> fire a real Composio action (post the chart to Slack).

It needs live API keys and network, so it is a script you run manually — not a
unit test. Drop your keys in first:

    cp .env.example .env        # then fill in NEBIUS / TAVILY / COMPOSIO keys
    uv run --python /opt/homebrew/opt/python@3.12/bin/python3.12 smoke_hero.py

Tip: to validate everything except the literal Composio sandbox call on your
first run, set BUILDSHIP_SANDBOX=local in .env, then switch back to composio.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

REQUIRED_KEYS = ["NEBIUS_API_KEY", "TAVILY_API_KEY", "COMPOSIO_API_KEY"]

HERO_TASK = (
    "Plot a dict of daily values as a bar chart and save it as a PNG file, "
    "so it can be posted to Slack."
)
NEEDED_TOOL = "bar_chart_png"  # the capability gap label (the LLM names the actual tool)


def main() -> int:
    missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        print("Missing required key(s): " + ", ".join(missing))
        print("Copy .env.example to .env and fill them in, then re-run.")
        return 1

    # Imported lazily so the key check above runs before any SDK client init.
    from buildship.adapters import build_harness

    print("buildship — chart hero task (end to end)\n")
    print(f"  task         : {HERO_TASK}")
    print(f"  needed_tool  : {NEEDED_TOOL}")
    print(f"  sandbox      : {os.getenv('BUILDSHIP_SANDBOX', 'composio')}")
    print(f"  model        : {os.getenv('NEBIUS_MODEL', 'deepseek-ai/DeepSeek-V3')}")
    print(f"  action slug  : {os.getenv('BUILDSHIP_ACTION_SLUG', 'SLACK_SENDS_A_MESSAGE_TO_A_CHANNEL')}\n")

    harness = build_harness()
    result = harness.run(HERO_TASK, NEEDED_TOOL)

    print("\n=== RESULT ===")
    print(result)
    # Outcome is encoded as "[built|reused|exhausted_budget|...] ..." by the harness.
    return 0 if result.startswith(("[built]", "[reused]")) else 2


if __name__ == "__main__":
    sys.exit(main())
