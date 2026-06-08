"""buildship Stage 2 — eval harness.

A held-out benchmark of tasks the agent lacks a tool for, each with an automatic
verifier, plus a runner that drives the Harness over them and reports metrics
(build-success, attempts-to-success, reuse, end-to-end success, tokens).
"""

from buildship.eval.tasks import BENCHMARK, EvalTask

__all__ = ["BENCHMARK", "EvalTask"]
