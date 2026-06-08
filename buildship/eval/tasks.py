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


def _expect_cases(fn: Callable[..., Any], cases: "list") -> "tuple[bool, str]":
    for args, expected in cases:
        try:
            got = fn(*args)
        except Exception as exc:  # noqa: BLE001
            return False, f"fn{args!r} raised {exc!r}"
        if got != expected:
            return False, f"fn{args!r} -> {got!r}, want {expected!r}"
    return True, f"{len(cases)} cases ok"


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
    # --- adversarial (spec traps: a careless first attempt fails; a faithful self-test catches it) ---
    EvalTask(
        "adv_round_half_up", "adversarial",
        "Implement `def round_half_up(value: float, decimals: int) -> float` that rounds value to "
        "decimals decimal places using HALF-UP rounding (a trailing 5 always rounds away from zero), "
        "NOT Python's built-in banker's rounding. E.g. round_half_up(2.5, 0) == 3.0, "
        "round_half_up(1.5, 0) == 2.0, round_half_up(2.25, 1) == 2.3.",
        "round_half_up",
        lambda fn: _expect_cases(fn, [((2.5, 0), 3.0), ((1.5, 0), 2.0), ((2.45, 1), 2.5),
                                      ((2.25, 1), 2.3), ((1.005, 2), 1.01), ((0.5, 0), 1.0), ((3.5, 0), 4.0)]),
    ),
    EvalTask(
        "adv_slugify", "adversarial",
        "Implement `def slugify(s: str) -> str` that converts text to a URL-safe slug: "
        "(1) lowercase; (2) replace every non-alphanumeric character with a hyphen; (3) collapse "
        "consecutive hyphens into one; (4) strip leading/trailing hyphens. E.g. 'Hello World!' -> "
        "'hello-world', 'Foo---Bar' -> 'foo-bar', '--test--' -> 'test'.",
        "slugify",
        lambda fn: _expect_cases(fn, [(("Hello World!",), "hello-world"), (("Foo---Bar",), "foo-bar"),
                                      (("--test--",), "test"), (("a@b_c-d",), "a-b-c-d"), (("___",), ""),
                                      (("A",), "a"), (("test-123-abc",), "test-123-abc"), (("a  b  c",), "a-b-c")]),
    ),
    EvalTask(
        "adv_roman", "adversarial",
        "Implement `def int_to_roman(n: int) -> str` converting an integer (1 <= n <= 3999) "
        "to a Roman numeral using subtractive notation (IV=4, IX=9, XL=40, XC=90, CD=400, CM=900). "
        "E.g. 4 -> 'IV', 9 -> 'IX', 58 -> 'LVIII', 1994 -> 'MCMXCIV'.",
        "int_to_roman",
        lambda fn: _expect_cases(fn, [((1,), "I"), ((4,), "IV"), ((9,), "IX"), ((27,), "XXVII"),
                                      ((58,), "LVIII"), ((1994,), "MCMXCIV"), ((3999,), "MMMCMXCIX"),
                                      ((444,), "CDXLIV"), ((2023,), "MMXXIII")]),
    ),
    EvalTask(
        "adv_dedupe", "adversarial",
        "Implement `def dedupe_preserving_order(items: list) -> list` that removes duplicates "
        "while preserving the order of FIRST occurrence. E.g. [3, 1, 3, 2, 1] -> [3, 1, 2].",
        "dedupe_preserving_order",
        lambda fn: _expect_cases(fn, [(([1, 2, 2, 3, 1, 4],), [1, 2, 3, 4]), (([3, 1, 3, 2, 1],), [3, 1, 2]),
                                      (([],), []), (([1],), [1]), (([1, 1, 1, 1],), [1]),
                                      ((["b", "a", "b", "c"],), ["b", "a", "c"])]),
    ),
    EvalTask(
        "adv_flatten", "adversarial",
        "Implement `def flatten_one_level(nested: list) -> list` that flattens exactly ONE level: "
        "if an element is a list, merge its items in; otherwise append the element unchanged (do NOT "
        "iterate strings/tuples). E.g. [[1, 2], [3, 4], 5] -> [1, 2, 3, 4, 5]; "
        "[['a','b'], 'cd', ('x','y')] -> ['a', 'b', 'cd', ('x', 'y')].",
        "flatten_one_level",
        lambda fn: _expect_cases(fn, [(([[1, 2], [3, 4], 5],), [1, 2, 3, 4, 5]),
                                      (([["a", "b"], "cd", ("x", "y")],), ["a", "b", "cd", ("x", "y")]),
                                      (([],), []), (([[], [1], []],), [1]), (([[1, [2, 3]], 4],), [1, [2, 3], 4])]),
    ),
    EvalTask(
        "adv_median", "adversarial",
        "Implement `def median(numbers: list) -> float` returning the median: the middle value "
        "of the sorted list when the count is odd, or the average of the two middle values when even. "
        "Must work regardless of input order.",
        "median",
        lambda fn: _expect_cases(fn, [(([1, 2, 3, 4],), 2.5), (([1, 2, 3],), 2.0), (([5, 1, 3, 2],), 2.5),
                                      (([1],), 1.0), (([1, 2],), 1.5), (([1, 3, 5, 7],), 4.0), (([10, 20],), 15.0)]),
    ),
]


def by_category() -> dict[str, list[EvalTask]]:
    groups: dict[str, list[EvalTask]] = {}
    for task in BENCHMARK:
        groups.setdefault(task.category, []).append(task)
    return groups
