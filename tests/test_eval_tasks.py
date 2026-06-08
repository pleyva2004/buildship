"""Offline validation of the eval benchmark: each task's verifier must accept a
correct reference implementation and reject a wrong one. No codegen / network.
"""

import csv
import io
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import pytest  # noqa: E402

from buildship.eval.tasks import BENCHMARK  # noqa: E402


# --- reference (correct) implementations, keyed by task id ---
def _sum_numbers(numbers): return sum(numbers)
def _mean_of(numbers): return sum(numbers) / len(numbers)
def _factorial(n): return math.factorial(n)
def _fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
def _c_to_f(c): return c * 9 / 5 + 32
def _is_prime(n):
    if n < 2:
        return False
    return all(n % d for d in range(2, int(n ** 0.5) + 1))
def _to_snake(s):
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()
def _reverse_words(s): return " ".join(reversed(s.split()))
def _csv_to_records(t): return list(csv.DictReader(io.StringIO(t)))
def _word_count(text):
    counts = {}
    for w in text.lower().split():
        counts[w] = counts.get(w, 0) + 1
    return counts
def _make_chart(data, out_path):
    fig, ax = plt.subplots()
    ax.bar(list(data), list(data.values()))
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


REFERENCE = {
    "compute_sum": _sum_numbers,
    "compute_mean": _mean_of,
    "compute_factorial": _factorial,
    "compute_fib": _fib,
    "compute_c_to_f": _c_to_f,
    "compute_is_prime": _is_prime,
    "transform_snake": _to_snake,
    "transform_reverse_words": _reverse_words,
    "transform_csv": _csv_to_records,
    "transform_wordcount": _word_count,
    "chart_bar": _make_chart,
    "chart_line": _make_chart,
}


def test_every_benchmark_task_has_a_reference():
    assert {t.id for t in BENCHMARK} == set(REFERENCE)


@pytest.mark.parametrize("task", BENCHMARK, ids=lambda t: t.id)
def test_verifier_accepts_correct_reference(task):
    ok, detail = task.verify(REFERENCE[task.id])
    assert ok, f"{task.id}: verifier rejected a correct impl: {detail}"


def test_verifier_rejects_wrong_compute_impl():
    sum_task = next(t for t in BENCHMARK if t.id == "compute_sum")
    ok, _ = sum_task.verify(lambda numbers: 0)  # wrong
    assert ok is False


def test_verifier_rejects_non_png_chart():
    bar_task = next(t for t in BENCHMARK if t.id == "chart_bar")

    def bad_tool(data, out_path):
        with open(out_path, "w") as f:
            f.write("not a png")
        return out_path

    ok, _ = bar_task.verify(bad_tool)
    assert ok is False


def test_benchmark_spans_three_categories():
    assert {t.category for t in BENCHMARK} == {"compute", "transform", "chart"}


def test_aggregate_metrics():
    from buildship.eval.runner import TaskResult, _aggregate

    rows = [
        TaskResult("a", "compute", "a", "built", 1, True, "", 100),
        TaskResult("b", "compute", "b", "built", 2, False, "", 200),
        TaskResult("c", "chart", "c", "reused", 1, True, "", 0),
        TaskResult("d", "transform", "d", "exhausted_budget", 3, False, "", 300),
    ]
    rep = _aggregate(rows)
    assert rep.total == 4
    assert rep.build_success_rate == 0.75   # built/reused: a, b, c
    assert rep.e2e_success_rate == 0.5       # verified: a, c
    assert rep.reuse_rate == 0.25            # reused: c
    assert rep.mean_attempts_to_success == 1.0  # e2e-ok attempts: a=1, c=1
    assert rep.total_tokens == 600
    assert rep.by_category["compute"] == {"total": 2, "built": 2, "e2e": 1}


def test_summarize_averages_repeats():
    from buildship.eval.runner import EvalReport, _summarize

    def rep(build, e2e, tokens):
        return EvalReport(
            total=2, build_success_rate=build, e2e_success_rate=e2e, reuse_rate=0.0,
            mean_attempts_to_success=1.0, total_tokens=tokens, by_category={}, results=[],
        )

    s = _summarize("full", [rep(1.0, 1.0, 100), rep(0.5, 0.5, 300)])
    assert s.repeats == 2
    assert s.build_mean == 0.75
    assert s.e2e_mean == 0.75
    assert s.tokens_mean == 200
    assert s.build_runs == [1.0, 0.5]
