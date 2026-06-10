"""demo_trace.py — render a buildship run trajectory as a watchable demo narrative.

Terminal-first. Spotlights the two money beats:
  • SELF-DEBUG — a tool fails its self-test, reads the traceback, fixes itself, passes.
  • REUSE      — a capability is served from the library instantly, with zero new builds.

Usage:
    python demo_trace.py trajectories/<id>.json   # render one run
    python demo_trace.py --latest                 # render the most recent trajectory
    python demo_trace.py --demo                   # render the bundled fixtures (both beats)
"""

from __future__ import annotations

import glob
import json
import os
import sys

_ANSI = sys.stdout.isatty()  # color only when attached to a terminal


def _c(code: str) -> str:
    return f"\033[{code}m" if _ANSI else ""


RESET, BOLD, DIM = _c("0"), _c("1"), _c("2")
RED, GREEN, YELLOW, CYAN, MAGENTA = _c("31"), _c("32"), _c("33"), _c("36"), _c("35")
RULE = "─" * 72


def render(traj: dict, out=print) -> None:
    """Render one trajectory dict as a sequence of beats."""
    events = traj.get("events", [])
    task = traj.get("task", "")
    outcome = traj.get("outcome", "?")
    needed = next((e.get("needed_tool") for e in events if e.get("kind") == "task"), "?")

    out(f"{BOLD}{CYAN}buildship ▸ {needed}{RESET}")
    if task:
        out(f"{DIM}{task[:86]}{RESET}")
    out(RULE)

    fails = 0
    for e in events:
        kind = e.get("kind")
        if kind == "gap":
            out(f"  {CYAN}gap{RESET}       no tool for `{e.get('tool')}` — must build it")
        elif kind == "research":
            lines = (e.get("result", "") or "").strip().splitlines()
            out(f"  {CYAN}research{RESET}   {(lines[0][:62] if lines else '')}  {DIM}(Tavily){RESET}")
        elif kind == "reuse":
            out(f"  {BOLD}{MAGENTA}⚡ REUSE{RESET}   `{e.get('tool')}` already in the library — "
                f"{BOLD}0 new builds{RESET}")
        elif kind == "codegen":
            out(f"  {CYAN}codegen{RESET}   attempt {e.get('attempt')} → `{e.get('name')}`  "
                f"{DIM}(Nebius){RESET}")
        elif kind == "test":
            if e.get("passed"):
                if fails:
                    out(f"            {BOLD}{GREEN}✓ SELF-DEBUG — passed after "
                        f"{fails} fix{'es' if fails > 1 else ''}{RESET}")
                else:
                    out(f"            {GREEN}✓ test passed{RESET}")
            else:
                fails += 1
                tail = (e.get("output", "") or "").strip().splitlines()
                why = tail[-1][:60] if tail else "failed"
                out(f"            {RED}✗ test failed{RESET}  {DIM}{why}{RESET}  → traceback fed back")
        elif kind == "admit":
            out(f"  {GREEN}admit ✓{RESET}   gated into the library as `{e.get('tool')}`")
        elif kind == "action":
            out(f"  {CYAN}action{RESET}    {(e.get('result', '') or '')[:64]}")

    color = GREEN if outcome in ("built", "reused") else RED
    out(RULE)
    out(f"  outcome   {BOLD}{color}[{outcome}]{RESET}\n")


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _latest(directory: str = "trajectories") -> str | None:
    files = glob.glob(os.path.join(directory, "*.json"))
    return max(files, key=os.path.getmtime) if files else None


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    arg = argv[0]
    if arg == "--demo":
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ("self_debug.json", "reuse.json"):
            render(_load(os.path.join(here, "demo_traces", name)))
        print(f"{BOLD}It wrote a tool, self-corrected when it failed, then reused that "
              f"capability instantly — the library compounds.{RESET}")
        return 0
    if arg == "--latest":
        path = _latest()
        if not path:
            print("no trajectories found in ./trajectories")
            return 1
        render(_load(path))
        return 0
    render(_load(arg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
