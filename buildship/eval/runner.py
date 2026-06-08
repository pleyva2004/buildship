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


def run_eval(tasks: list[EvalTask] | None = None, searcher: Any = None) -> EvalReport:
    """Run the benchmark with live adapters. Returns an EvalReport."""
    from buildship.adapters import NebiusLLMClient, TavilySearcher, make_sandbox

    tasks = tasks or BENCHMARK
    registry = ToolRegistry(os.environ.get("BUILDSHIP_EVAL_LIBRARY", "eval_library.json"))
    llm = _CountingLLM(NebiusLLMClient())
    harness = Harness(
        llm=llm,
        sandbox=make_sandbox(),
        searcher=searcher or TavilySearcher(),
        action=NoOpAction(),
        registry=registry,
    )

    results: list[TaskResult] = []
    for task in tasks:
        before_calls, before_tokens = llm.calls, llm.total_tokens
        try:
            res = harness.run(task.task, task.needed_tool)
            match = _OUTCOME.match(res)
            outcome = match.group(1) if match else "unknown"
        except Exception as exc:  # noqa: BLE001
            outcome, res = "error", repr(exc)

        e2e_ok, detail = False, res
        if registry.has(task.needed_tool):
            try:
                e2e_ok, detail = task.verify(registry.callable(task.needed_tool))
            except Exception as exc:  # noqa: BLE001
                e2e_ok, detail = False, f"verify raised: {exc!r}"

        results.append(
            TaskResult(
                id=task.id, category=task.category, needed_tool=task.needed_tool,
                outcome=outcome, attempts=llm.calls - before_calls,
                e2e_ok=e2e_ok, detail=detail[:300], tokens=llm.total_tokens - before_tokens,
            )
        )
        flag = "OK " if e2e_ok else "XX "
        print(f"  {flag}{task.id:24s} {outcome:16s} attempts={results[-1].attempts} "
              f"tokens={results[-1].tokens}  {detail[:60]}")

    return _aggregate(results)


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    missing = [k for k in ("NEBIUS_API_KEY", "TAVILY_API_KEY", "COMPOSIO_API_KEY")
               if not os.getenv(k)]
    if missing:
        print("Missing keys: " + ", ".join(missing) + ". Fill in .env and re-run.")
        return 1

    print(f"buildship eval — {len(BENCHMARK)} tasks, sandbox="
          f"{os.getenv('BUILDSHIP_SANDBOX', 'composio')}\n")
    report = run_eval()

    out = Path(os.environ.get("BUILDSHIP_EVAL_REPORT", "eval_report.json"))
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
