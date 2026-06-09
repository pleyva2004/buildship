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

# Transient API failures (network blips, timeouts, 5xx, rate limits) are retried so a
# flaky call isn't counted as a failed tool build, which would pollute the metrics.
_TRANSIENT_RETRIES = int(os.environ.get("BUILDSHIP_TRANSIENT_RETRIES", "2"))
_TRANSIENT_ERRORS = {
    "APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError",
    "APIError", "ConnectionError", "Timeout", "TimeoutError", "ReadTimeout", "ConnectError",
    "ProxyError", "MaxRetryError",
}


def _is_transient(exc: BaseException) -> bool:
    return bool({c.__name__ for c in type(exc).__mro__} & _TRANSIENT_ERRORS)


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

    def write_test(self, *args: Any, **kwargs: Any):
        return self.inner.write_test(*args, **kwargs)

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
    self_test_passed: bool | None = None


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
    independent_gate: bool = False


# The pre-registered ablation arms (stages.md Stage 2): full vs no-gate vs
# bounded-1 vs no-rejected-buffer vs independent-verifier gate.
ABLATION_ARMS = [
    Arm("full"),                                  # gate on, 3 attempts, full feedback
    Arm("no_gate", gate=False),                   # admit first codegen regardless of self-test
    Arm("budget_1", max_attempts=1),              # build-or-fail-fast (no self-correction)
    Arm("no_feedback", feedback_mode="none"),     # retries start from scratch
    Arm("independent_gate", independent_gate=True),  # gate on an author-INDEPENDENT test
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
    # On the independent-gate arm, the gate's test is written by a SEPARATE model call
    # that never sees the implementation (not the code author's own self-test).
    independent_verifier = (
        (lambda t, c: counting.write_test(t, c)) if arm.independent_gate else None
    )
    harness = Harness(
        llm=counting, sandbox=sandbox, searcher=searcher,
        action=action or NoOpAction(), registry=registry,
        gate=arm.gate, max_attempts=arm.max_attempts, feedback_mode=arm.feedback_mode,
        independent_verifier=independent_verifier,
    )

    results: list[TaskResult] = []
    for task in tasks:
        outcome, res = "error", ""
        for t_try in range(_TRANSIENT_RETRIES + 1):
            before_calls, before_tokens = counting.calls, counting.total_tokens
            try:
                res = harness.run(task.task, task.needed_tool)
                match = _OUTCOME.match(res)
                outcome = match.group(1) if match else "unknown"
                break
            except Exception as exc:  # noqa: BLE001
                if _is_transient(exc) and t_try < _TRANSIENT_RETRIES:
                    continue
                outcome, res = "error", repr(exc)
                break

        e2e_ok, detail = False, res
        # Capture BOTH signals: the gate's (self-test status, preserved even when the
        # no_gate arm force-admits a failing tool) and ground truth (the verifier).
        entry = registry.get(task.needed_tool)
        self_test_passed = entry.verification.status == "passed" if entry is not None else None
        if entry is not None:
            try:
                e2e_ok, detail = task.verify(registry.callable(task.needed_tool))
            except Exception as exc:  # noqa: BLE001
                e2e_ok, detail = False, f"verify raised: {exc!r}"

        results.append(
            TaskResult(
                id=task.id, category=task.category, needed_tool=task.needed_tool,
                outcome=outcome, attempts=counting.calls - before_calls,
                e2e_ok=e2e_ok, detail=detail[:300], tokens=counting.total_tokens - before_tokens,
                self_test_passed=self_test_passed,
            )
        )
        if not quiet:
            flag = "OK " if e2e_ok else "XX "
            print(f"  {flag}{task.id:24s} {outcome:16s} attempts={results[-1].attempts} "
                  f"tokens={results[-1].tokens}  {detail[:60]}")

    return _aggregate(results)


def run_ablation(tasks: list[EvalTask] | None = None, repeats: int = 1) -> dict[str, "ArmSummary"]:
    """Run every ablation arm `repeats` times (fresh library each run) and return
    {arm_name: ArmSummary} averaging the metrics across repeats (single runs are noisy)."""
    summary: dict[str, ArmSummary] = {}
    for arm in ABLATION_ARMS:
        reps: list[EvalReport] = []
        for i in range(max(1, repeats)):
            print(f"\n--- arm: {arm.name} [{i + 1}/{repeats}] (gate={arm.gate}, "
                  f"max_attempts={arm.max_attempts}, feedback={arm.feedback_mode}) ---")
            reps.append(run_eval(tasks, arm=arm))
        summary[arm.name] = _summarize(arm.name, reps)
    return summary


@dataclass
class ArmSummary:
    name: str
    repeats: int
    build_mean: float
    e2e_mean: float
    reuse_mean: float
    attempts_mean: float
    tokens_mean: float
    build_runs: list[float]
    e2e_runs: list[float]


def _summarize(name: str, reports: list[EvalReport]) -> ArmSummary:
    n = len(reports)

    def _mean(vals: list[float]) -> float:
        return round(sum(vals) / n, 3) if n else 0.0

    return ArmSummary(
        name=name,
        repeats=n,
        build_mean=_mean([r.build_success_rate for r in reports]),
        e2e_mean=_mean([r.e2e_success_rate for r in reports]),
        reuse_mean=_mean([r.reuse_rate for r in reports]),
        attempts_mean=_mean([r.mean_attempts_to_success for r in reports]),
        tokens_mean=round(sum(r.total_tokens for r in reports) / n) if n else 0,
        build_runs=[r.build_success_rate for r in reports],
        e2e_runs=[r.e2e_success_rate for r in reports],
    )


@dataclass
class AlignmentReport:
    n: int
    admit_correct: int      # self-test pass, verifier pass
    false_positive: int     # self-test pass, verifier FAIL (gate would admit a dud)
    false_negative: int     # self-test FAIL, verifier pass (gate rejects a correct tool)
    correct_reject: int     # self-test fail, verifier fail
    false_negative_rate: float
    false_positive_rate: float
    gate_precision: float
    gate_recall: float
    agreement: float
    false_negative_ids: list[str]
    false_positive_ids: list[str]


def compute_alignment(results: list[TaskResult]) -> AlignmentReport:
    rows = [r for r in results if r.self_test_passed is not None]
    tp = [r for r in rows if r.self_test_passed and r.e2e_ok]
    fp = [r for r in rows if r.self_test_passed and not r.e2e_ok]
    fn = [r for r in rows if not r.self_test_passed and r.e2e_ok]
    tn = [r for r in rows if not r.self_test_passed and not r.e2e_ok]

    def _r(num: int, den: int) -> float:
        return round(num / den, 3) if den else 0.0

    correct = len(tp) + len(fn)        # tools the verifier accepts
    admitted = len(tp) + len(fp)       # tools the gate (self-test) admits
    return AlignmentReport(
        n=len(rows), admit_correct=len(tp), false_positive=len(fp),
        false_negative=len(fn), correct_reject=len(tn),
        false_negative_rate=_r(len(fn), correct),
        false_positive_rate=_r(len(fp), len(fp) + len(tn)),
        gate_precision=_r(len(tp), admitted),
        gate_recall=_r(len(tp), correct),
        agreement=_r(len(tp) + len(tn), len(rows)),
        false_negative_ids=[r.id for r in fn],
        false_positive_ids=[r.id for r in fp],
    )


def run_alignment(tasks: list[EvalTask] | None = None, repeats: int = 1) -> AlignmentReport:
    """Measure the gate signal (self-test) vs ground truth (verifier). Runs the no_gate
    arm so EVERY tool is admitted with its true self-test status preserved, giving both
    signals for every task."""
    rows: list[TaskResult] = []
    for _ in range(max(1, repeats)):
        rep = run_eval(tasks, arm=Arm("no_gate"))
        rows.extend(TaskResult(**r) for r in rep.results)
    return compute_alignment(rows)


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

    if "alignment" in sys.argv[1:]:
        a = sys.argv[1:]
        i = a.index("alignment")
        repeats = int(a[i + 1]) if i + 1 < len(a) and a[i + 1].isdigit() else 1
        print(f"buildship eval — ALIGNMENT (self-test vs verifier) x{repeats}, "
              f"{len(BENCHMARK)} tasks, sandbox={os.getenv('BUILDSHIP_SANDBOX', 'composio')}")
        rep = run_alignment(repeats=repeats)
        out.write_text(json.dumps(asdict(rep), indent=2))
        print(f"\n=== SELF-TEST vs VERIFIER CONFUSION (n={rep.n}) ===")
        print(f"  pass/pass  (correct admit) : {rep.admit_correct}")
        print(f"  pass/FAIL  (FALSE POSITIVE): {rep.false_positive}  {rep.false_positive_ids}")
        print(f"  FAIL/pass  (FALSE NEGATIVE): {rep.false_negative}  {rep.false_negative_ids}")
        print(f"  FAIL/FAIL  (correct reject): {rep.correct_reject}")
        print(f"  agreement={rep.agreement} precision={rep.gate_precision} recall={rep.gate_recall} "
              f"FN_rate={rep.false_negative_rate} FP_rate={rep.false_positive_rate}")
        print(f"\nreport written to {out}")
        return 0

    if "ablation" in sys.argv[1:]:
        args = sys.argv[1:]
        idx = args.index("ablation")
        repeats = int(args[idx + 1]) if idx + 1 < len(args) and args[idx + 1].isdigit() else 1
        print(f"buildship eval — ABLATION across {len(ABLATION_ARMS)} arms x{repeats}, "
              f"{len(BENCHMARK)} tasks, sandbox={os.getenv('BUILDSHIP_SANDBOX', 'composio')}")
        summaries = run_ablation(repeats=repeats)
        out.write_text(json.dumps({k: asdict(v) for k, v in summaries.items()}, indent=2))
        print(f"\n=== ABLATION SUMMARY (mean over {repeats} run(s); the claim: full beats the rest) ===")
        print(f"  {'arm':12s} {'build':>6s} {'e2e':>6s} {'reuse':>6s} {'attempts':>9s} {'tokens':>8s}   runs(e2e)")
        for s in summaries.values():
            print(f"  {s.name:12s} {s.build_mean:6.3f} {s.e2e_mean:6.3f} {s.reuse_mean:6.3f} "
                  f"{s.attempts_mean:9.2f} {s.tokens_mean:8d}   {s.e2e_runs}")
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
