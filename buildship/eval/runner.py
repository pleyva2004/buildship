"""Eval runner: drive the Harness over the benchmark and report metrics.

Needs live keys (Nebius codegen + the chosen sandbox), so run it from a terminal
with network:

    uv run --python /opt/homebrew/opt/python@3.12/bin/python3.12 -m buildship.eval

It uses a no-op action (the benchmark verifies the built tool directly rather than
firing a real Slack action per task) and a fresh tool library per run.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from buildship.buildship_core import Harness, ToolRegistry
from buildship.eval.tasks import BENCHMARK, EvalTask

_OUTCOME = re.compile(r"^\[(\w+)\]")


class NoOpAction:
    """Action stub for eval — the verifier exercises the built tool directly."""

    def execute(self, tool_name: str, tool: Any) -> str:
        return f"noop:{tool_name}"


class _CountingLLM:
    """Wrap an LLMClient to count write_tool calls (attempts) per task."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.calls = 0

    def write_tool(self, *args: Any, **kwargs: Any):
        self.calls += 1
        return self.inner.write_tool(*args, **kwargs)

    @property
    def total_tokens(self) -> int:
        return int(getattr(self.inner, "total_tokens", 0) or 0)


@dataclass
class TaskResult:
    id: str
    category: str
    needed_tool: str
    outcome: str        # built | reused | exhausted_budget | error | unknown
    attempts: int
    e2e_ok: bool
    detail: str
    tokens: int


@dataclass
class EvalReport:
    total: int
    build_success_rate: float      # outcome in {built, reused}
    e2e_success_rate: float        # verifier passed
    reuse_rate: float              # outcome == reused
    mean_attempts_to_success: float
    total_tokens: int
    by_category: dict[str, dict[str, float]]
    results: list[dict[str, Any]]


def _aggregate(results: list[TaskResult]) -> EvalReport:
    total = len(results)
    built = [r for r in results if r.outcome in ("built", "reused")]
    e2e = [r for r in results if r.e2e_ok]
    reused = [r for r in results if r.outcome == "reused"]
    solved_attempts = [r.attempts for r in results if r.e2e_ok and r.attempts > 0]

    cats: dict[str, dict[str, float]] = {}
    for r in results:
        c = cats.setdefault(r.category, {"total": 0, "built": 0, "e2e": 0})
        c["total"] += 1
        c["built"] += 1 if r.outcome in ("built", "reused") else 0
        c["e2e"] += 1 if r.e2e_ok else 0

    def _rate(n: int, d: int) -> float:
        return round(n / d, 3) if d else 0.0

    return EvalReport(
        total=total,
        build_success_rate=_rate(len(built), total),
        e2e_success_rate=_rate(len(e2e), total),
        reuse_rate=_rate(len(reused), total),
        mean_attempts_to_success=(
            round(sum(solved_attempts) / len(solved_attempts), 2) if solved_attempts else 0.0
        ),
        total_tokens=sum(r.tokens for r in results),
        by_category=cats,
        results=[asdict(r) for r in results],
    )


@dataclass
class Arm:
    """An ablation configuration for the harness."""
    name: str
    gate: bool = True
    max_attempts: int = 3
    feedback_mode: str = "full"


# The pre-registered ablation arms (stages.md Stage 2): full vs no-gate vs
# bounded-1 vs no-rejected-buffer.
ABLATION_ARMS = [
    Arm("full"),                                # gate on, 3 attempts, full feedback
    Arm("no_gate", gate=False),                 # admit first codegen regardless of self-test
    Arm("budget_1", max_attempts=1),            # build-or-fail-fast (no self-correction)
    Arm("no_feedback", feedback_mode="none"),   # retries start from scratch
]


def run_eval(
    tasks: list[EvalTask] | None = None,
    *,
    arm: Arm | None = None,
    registry: ToolRegistry | None = None,
    llm: Any = None,
    sandbox: Any = None,
    searcher: Any = None,
    action: Any = None,
    quiet: bool = False,
) -> EvalReport:
    """Run the benchmark for one ablation arm.

    Adapters default to the live ones (Nebius / sandbox / Tavily), but each can be
    injected for offline testing. A fresh tool library is used per call so arms
    don't contaminate each other.
    """
    arm = arm or Arm("full")
    tasks = tasks or BENCHMARK

    if llm is None or sandbox is None or searcher is None:
        from buildship.adapters import NebiusLLMClient, TavilySearcher, make_sandbox

        llm = llm or NebiusLLMClient()
        sandbox = sandbox or make_sandbox()
        searcher = searcher or TavilySearcher()

    counting = _CountingLLM(llm)
    if registry is None:
        registry = ToolRegistry(os.path.join(tempfile.mkdtemp(), "eval_library.json"))
    harness = Harness(
        llm=counting, sandbox=sandbox, searcher=searcher,
        action=action or NoOpAction(), registry=registry,
        gate=arm.gate, max_attempts=arm.max_attempts, feedback_mode=arm.feedback_mode,
    )

    results: list[TaskResult] = []
    for task in tasks:
        before_calls, before_tokens = counting.calls, counting.total_tokens
        try:
            res = harness.run(task.task, task.needed_tool)
            match = _OUTCOME.match(res)
            outcome = match.group(1) if match else "unknown"
        except Exception as exc:  # noqa: BLE001
            outcome, res = "error", repr(exc)

        e2e_ok, detail = False, res
        # Verify any admitted tool (incl. ungated arm's failing-self-test tools),
        # so the end-to-end verifier — not the gate — judges correctness.
        if registry.get(task.needed_tool) is not None:
            try:
                e2e_ok, detail = task.verify(registry.callable(task.needed_tool))
            except Exception as exc:  # noqa: BLE001
                e2e_ok, detail = False, f"verify raised: {exc!r}"

        results.append(
            TaskResult(
                id=task.id, category=task.category, needed_tool=task.needed_tool,
                outcome=outcome, attempts=counting.calls - before_calls,
                e2e_ok=e2e_ok, detail=detail[:300], tokens=counting.total_tokens - before_tokens,
            )
        )
        if not quiet:
            flag = "OK " if e2e_ok else "XX "
            print(f"  {flag}{task.id:24s} {outcome:16s} attempts={results[-1].attempts} "
                  f"tokens={results[-1].tokens}  {detail[:60]}")

    return _aggregate(results)


def run_ablation(tasks: list[EvalTask] | None = None) -> dict[str, EvalReport]:
    """Run every ablation arm (fresh library each) and return {arm_name: EvalReport}."""
    reports: dict[str, EvalReport] = {}
    for arm in ABLATION_ARMS:
        if True:  # per-arm banner
            print(f"\n--- arm: {arm.name} (gate={arm.gate}, max_attempts={arm.max_attempts}, "
                  f"feedback={arm.feedback_mode}) ---")
        reports[arm.name] = run_eval(tasks, arm=arm)
    return reports


def main() -> int:
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    missing = [k for k in ("NEBIUS_API_KEY", "TAVILY_API_KEY", "COMPOSIO_API_KEY")
               if not os.getenv(k)]
    if missing:
        print("Missing keys: " + ", ".join(missing) + ". Fill in .env and re-run.")
        return 1

    out = Path(os.environ.get("BUILDSHIP_EVAL_REPORT", "eval_report.json"))

    if "ablation" in sys.argv[1:]:
        print(f"buildship eval — ABLATION across {len(ABLATION_ARMS)} arms, "
              f"{len(BENCHMARK)} tasks, sandbox={os.getenv('BUILDSHIP_SANDBOX', 'composio')}")
        reports = run_ablation()
        out.write_text(json.dumps({k: asdict(v) for k, v in reports.items()}, indent=2))
        print("\n=== ABLATION SUMMARY (the pre-registered claim: full beats the rest) ===")
        print(f"  {'arm':12s} {'build':>6s} {'e2e':>6s} {'reuse':>6s} {'attempts':>9s} {'tokens':>8s}")
        for name, rep in reports.items():
            print(f"  {name:12s} {rep.build_success_rate:6.3f} {rep.e2e_success_rate:6.3f} "
                  f"{rep.reuse_rate:6.3f} {rep.mean_attempts_to_success:9.2f} {rep.total_tokens:8d}")
        print(f"\nreport written to {out}")
        return 0

    print(f"buildship eval — {len(BENCHMARK)} tasks, sandbox="
          f"{os.getenv('BUILDSHIP_SANDBOX', 'composio')}\n")
    report = run_eval()
    out.write_text(json.dumps(asdict(report), indent=2))
    print("\n=== METRICS ===")
    print(f"  build-success rate : {report.build_success_rate}")
    print(f"  end-to-end success : {report.e2e_success_rate}")
    print(f"  reuse rate         : {report.reuse_rate}")
    print(f"  mean attempts→succ : {report.mean_attempts_to_success}")
    print(f"  total tokens       : {report.total_tokens}")
    print(f"  by category        : {report.by_category}")
    print(f"\nreport written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
