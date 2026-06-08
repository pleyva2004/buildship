"""Held-out eval benchmark: tasks requiring a tool the agent lacks, each with an
automatic verifier.

A verifier receives the freshly-built tool as a callable and returns
``(ok, detail)``. Each task states the EXACT function signature so codegen and the
verifier agree on how the tool is called. Categories span compute, transform, and
chart/artifact tools (per stages.md Stage 2).
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class EvalTask:
    id: str
    category: str           # "compute" | "transform" | "chart"
    task: str               # the prompt; includes the required signature
    needed_tool: str        # capability key (registry key / reuse key)
    verify: Callable[[Callable[..., Any]], "tuple[bool, str]"]


def _expect(got: Any, want: Any) -> "tuple[bool, str]":
    return got == want, f"got {got!r}, want {want!r}"


def _verify_png(fn: Callable[..., Any]) -> "tuple[bool, str]":
    """Call a (data: dict, out_path: str) chart tool and confirm it wrote a real PNG."""
    out = os.path.join(tempfile.mkdtemp(), "chart.png")
    try:
        produced = fn({"A": 3, "B": 7, "C": 5}, out)
    except Exception as exc:  # noqa: BLE001
        return False, f"tool raised: {exc!r}"
    path = produced if isinstance(produced, str) and produced else out
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False, f"no non-empty file at {path!r}"
    with open(path, "rb") as handle:
        head = handle.read(8)
    if head != b"\x89PNG\r\n\x1a\n":
        return False, "output is not a PNG"
    return True, f"valid PNG ({os.path.getsize(path)} bytes)"


BENCHMARK: list[EvalTask] = [
    # --- compute ---
    EvalTask(
        "compute_sum", "compute",
        "Implement `def sum_numbers(numbers: list) -> float` that returns the sum of a list of numbers.",
        "sum_numbers", lambda fn: _expect(fn([1, 2, 3, 4]), 10),
    ),
    EvalTask(
        "compute_mean", "compute",
        "Implement `def mean_of(numbers: list) -> float` that returns the arithmetic mean of a list.",
        "mean_of", lambda fn: _expect(fn([2, 4, 6]), 4),
    ),
    EvalTask(
        "compute_factorial", "compute",
        "Implement `def factorial(n: int) -> int` that returns n! (with 0! == 1).",
        "factorial", lambda fn: _expect(fn(5), 120),
    ),
    EvalTask(
        "compute_fib", "compute",
        "Implement `def fib(n: int) -> int` returning the nth Fibonacci number with fib(0)=0, fib(1)=1.",
        "fib", lambda fn: _expect(fn(10), 55),
    ),
    EvalTask(
        "compute_c_to_f", "compute",
        "Implement `def celsius_to_fahrenheit(c: float) -> float` converting Celsius to Fahrenheit.",
        "celsius_to_fahrenheit", lambda fn: _expect(fn(100), 212),
    ),
    EvalTask(
        "compute_is_prime", "compute",
        "Implement `def is_prime(n: int) -> bool` returning whether n is a prime number.",
        "is_prime", lambda fn: _expect((fn(7), fn(8), fn(2), fn(1)), (True, False, True, False)),
    ),
    # --- transform ---
    EvalTask(
        "transform_snake", "transform",
        "Implement `def to_snake_case(s: str) -> str` converting CamelCase to snake_case (e.g. 'HelloWorld' -> 'hello_world').",
        "to_snake_case", lambda fn: _expect(fn("HelloWorld"), "hello_world"),
    ),
    EvalTask(
        "transform_reverse_words", "transform",
        "Implement `def reverse_words(s: str) -> str` that reverses the order of words in a string.",
        "reverse_words", lambda fn: _expect(fn("the quick brown"), "brown quick the"),
    ),
    EvalTask(
        "transform_csv", "transform",
        "Implement `def csv_to_records(csv_text: str) -> list` parsing CSV text with a header row into a list of dicts (values as strings).",
        "csv_to_records",
        lambda fn: _expect(fn("a,b\n1,2\n3,4"), [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]),
    ),
    EvalTask(
        "transform_wordcount", "transform",
        "Implement `def word_count(text: str) -> dict` returning a dict of word -> count, case-insensitive, split on whitespace.",
        "word_count", lambda fn: _expect(fn("a A b"), {"a": 2, "b": 1}),
    ),
    # --- chart / artifact ---
    EvalTask(
        "chart_bar", "chart",
        "Implement `def make_bar_chart(data: dict, out_path: str) -> str` saving a bar chart PNG of the dict (label->value) to out_path with matplotlib (Agg backend) and returning out_path.",
        "make_bar_chart", _verify_png,
    ),
    EvalTask(
        "chart_line", "chart",
        "Implement `def make_line_chart(data: dict, out_path: str) -> str` saving a line chart PNG of the dict (label->value) to out_path with matplotlib (Agg backend) and returning out_path.",
        "make_line_chart", _verify_png,
    ),
]


def by_category() -> dict[str, list[EvalTask]]:
    groups: dict[str, list[EvalTask]] = {}
    for task in BENCHMARK:
        groups.setdefault(task.category, []).append(task)
    return groups
