"""Chain-reaction hero demo — the tool library COMPOUNDING.

Run from the repo root with live keys + network (the proxy blocks it inside
Claude Code, so run it in a real shell):

    uv run --python /opt/homebrew/opt/python@3.12/bin/python3.12 demo_chain.py

This is a standalone, narrated demo (sibling to smoke_hero.py). It builds a
small library of tools, then re-runs the SAME tasks and shows REUSE hits with
zero new builds. The beat: "it couldn't do this a minute ago; now it's
permanent and instant." The library compounds.

Needs live keys (Nebius / Tavily / Composio) and network access.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

REQUIRED_KEYS = ["NEBIUS_API_KEY", "TAVILY_API_KEY", "COMPOSIO_API_KEY"]

# The chain of (task, needed_tool) steps. ROUND 1 builds each capability from a
# clean library; ROUND 2 re-runs the identical steps and should reuse them.
STEPS = [
    ("Implement `def aggregate_by_key(rows: list, key: str, value: str) -> dict` that, given a "
     "list of dicts, returns a dict summing each row's `value` field grouped by its `key` field.",
     "aggregate_by_key"),
    ("Implement `def make_bar_chart(data: dict, out_path: str) -> str` that saves a bar chart PNG "
     "of the dict (label -> numeric value) to out_path using matplotlib (Agg backend) and returns "
     "out_path.", "make_bar_chart"),
]


class PrintAction:
    """Demo action: confirms the freshly-built tool is callable, no signature assumptions."""

    def execute(self, tool_name, tool):
        return f"action: would fire `{tool_name}` (callable={callable(tool)})"


def main() -> int:
    missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        print("Missing required key(s): " + ", ".join(missing))
        print("Copy .env.example to .env and fill them in, then re-run.")
        return 1

    # Imported lazily so the key check above runs before any SDK client init.
    # Build the harness directly (NOT build_harness): its ComposioAction assumes
    # the chart (data, out_path) signature and would break on a non-chart tool
    # like aggregate_by_key. PrintAction works for ANY tool.
    from buildship.buildship_core import Harness, ToolRegistry
    from buildship.adapters import NebiusLLMClient, TavilySearcher, make_sandbox

    # Start from a clean, persistent library each run so ROUND 1 actually builds
    # and the demo is repeatable.
    lib = "demo_library.json"
    if os.path.exists(lib):
        os.remove(lib)

    harness = Harness(
        llm=NebiusLLMClient(),
        sandbox=make_sandbox(),
        searcher=TavilySearcher(),
        action=PrintAction(),
        registry=ToolRegistry(lib),
    )

    print("buildship — chain-reaction demo (the library compounds)\n")
    print(f"  sandbox : {os.getenv('BUILDSHIP_SANDBOX', 'composio')}")
    print(f"  model   : {os.getenv('NEBIUS_MODEL', 'deepseek-ai/DeepSeek-V3')}")
    print(f"  library : {lib} (reset)\n")

    # ROUND 1 — build each capability from scratch. Expect [built].
    print("ROUND 1 — build (empty library, every step is a gap):")
    for task, needed in STEPS:
        result = harness.run(task, needed)
        print(f"  [1] {needed}: {result}")

    # ROUND 2 — re-run the identical steps. Expect [reused] (zero new builds).
    print("\nROUND 2 — reuse (same tasks; capabilities now exist):")
    reuse_hits = 0
    for task, needed in STEPS:
        result = harness.run(task, needed)
        print(f"  [2] {needed}: {result}")
        if result.startswith("[reused]"):
            reuse_hits += 1

    # Summary — the compounding story.
    print("\n=== SUMMARY ===")
    print(f"  library now holds: {harness.registry.list_names()}")
    print(f"  round 2 reuse hits: {reuse_hits} / {len(STEPS)}")
    print(
        "  These capabilities didn't exist a minute ago — now they're permanent "
        "and reused instantly. The library compounds."
    )

    return 0 if reuse_hits == len(STEPS) else 2


if __name__ == "__main__":
    raise SystemExit(main())
