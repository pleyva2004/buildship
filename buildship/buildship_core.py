"""
Forge — Stage 0 core (task-agnostic, dependency-free).

This is the *state-externalizing harness*: the model makes the semantic
decisions, the harness owns the durable state — the tool library, a
verification record per tool, and a build budget — and writes one trajectory
log per run.

Stage 0 items implemented here:
  (2) state-externalized harness:  ToolRegistry + VerificationRecord + BuildBudget
  (3) structured trajectory log:   TrajectoryLogger
  (4) the tool contract:           ToolContract

Stage 0 item (5) — Nebius / Composio / Tavily — plugs in via the four adapter
Protocols below (LLMClient, Sandbox, Searcher, Action). Implement those in
Stage 1 with your keys; nothing in this file needs to change.
"""

from __future__ import annotations

import ast
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Protocol, Optional, Any, Callable


# ---------------------------------------------------------------------------
# (4) Tool contract — every generated tool must conform to this shape.
# Constrained codegen (typed signature + docstring + self-test) is far more
# reliable than freeform, and gives Stage 2's "tool-authoring skill" a clear
# object to optimize.
# ---------------------------------------------------------------------------
@dataclass
class ToolContract:
    name: str                 # snake_case identifier; also the registry key
    signature: str            # e.g. "def make_bar_chart(data: dict, out_path: str) -> str:"
    docstring: str            # what it does, args, returns
    code: str                 # full Python source of the function
    self_test: str            # Python that calls the function and asserts on the output
    requires: list[str] = field(default_factory=list)   # pip deps the tool needs

    def source(self) -> str:
        """The full module text the sandbox executes (function + its self-test)."""
        return f"{self.code}\n\n# --- self-test ---\n{self.self_test}\n"


# ---------------------------------------------------------------------------
# Verification record — first-class state, one per tool (the Harness-1 idea).
# ---------------------------------------------------------------------------
@dataclass
class VerificationRecord:
    status: str = "untested"          # untested | passed | failed
    attempts: int = 0
    last_output: str = ""             # stdout/stderr from the last test run
    updated_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# (2) Tool registry — the externalized, recoverable tool library.
# Persists to disk as JSON so capabilities survive across runs and sessions.
# Callables are reconstructed from `code` on load.
# ---------------------------------------------------------------------------
@dataclass
class ToolEntry:
    contract: ToolContract
    verification: VerificationRecord = field(default_factory=VerificationRecord)


class ToolRegistry:
    def __init__(self, path: str | Path = "forge_library.json"):
        self.path = Path(path)
        self.tools: dict[str, ToolEntry] = {}
        if self.path.exists():
            self.load()

    def has(self, name: str) -> bool:
        e = self.tools.get(name)
        return e is not None and e.verification.status == "passed"

    def get(self, name: str) -> Optional[ToolEntry]:
        return self.tools.get(name)

    def admit(
        self,
        contract: ToolContract,
        verification: VerificationRecord,
        key: str | None = None,
        force: bool = False,
    ) -> None:
        """Validation gate: only call this once a tool has PASSED its test.

        `key` is the registry / capability key (e.g. the requested `needed_tool`),
        defaulting to the tool's own name. Keeping the key distinct from the
        function's def name lets reuse hit on the requested capability even when
        the model named the function something else.
        `force=True` bypasses the pass requirement — used only by the no-gate
        ablation arm to admit the first codegen regardless of its self-test."""
        if not force and verification.status != "passed":
            raise ValueError("refusing to admit a tool that did not pass its test")
        self.tools[key or contract.name] = ToolEntry(contract, verification)
        self.save()

    def callable(self, name: str) -> Callable[..., Any]:
        """Materialize the stored tool as a live Python callable.
        The registry key may differ from the function's def name (the key is the
        requested capability), so fetch by the contract's name and fall back to the
        sole top-level function defined in the code.
        NOTE: in production, run even the *use* step inside the Sandbox adapter;
        this in-process exec is fine for the demo because the tool already passed."""
        entry = self.tools[name]
        ns: dict[str, Any] = {}
        exec(entry.contract.code, ns)  # noqa: S102
        fn = ns.get(entry.contract.name)
        if fn is None:
            defs = [
                node.name
                for node in ast.parse(entry.contract.code).body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            if len(defs) == 1:
                fn = ns.get(defs[0])
        if fn is None:
            raise KeyError(f"tool function for {name!r} not found in its code")
        return fn

    def list_names(self) -> list[str]:
        return [n for n, e in self.tools.items() if e.verification.status == "passed"]

    def save(self) -> None:
        data = {
            n: {"contract": asdict(e.contract), "verification": asdict(e.verification)}
            for n, e in self.tools.items()
        }
        self.path.write_text(json.dumps(data, indent=2))

    def load(self) -> None:
        data = json.loads(self.path.read_text())
        for n, e in data.items():
            self.tools[n] = ToolEntry(
                ToolContract(**e["contract"]),
                VerificationRecord(**e["verification"]),
            )


# ---------------------------------------------------------------------------
# (2) Build budget — bounded effort; also the cost metric for Stage 2.
# ---------------------------------------------------------------------------
@dataclass
class BuildBudget:
    max_attempts: int = 3             # the "bounded edit" cap on retries
    max_tokens: int = 100_000
    attempts: int = 0
    tokens: int = 0

    def can_retry(self) -> bool:
        return self.attempts < self.max_attempts and self.tokens < self.max_tokens

    def charge(self, attempts: int = 0, tokens: int = 0) -> None:
        self.attempts += attempts
        self.tokens += tokens


# ---------------------------------------------------------------------------
# (3) Trajectory log — one JSON per run. Demo trace + eval data + paper data.
# ---------------------------------------------------------------------------
class TrajectoryLogger:
    def __init__(self, run_dir: str | Path = "trajectories"):
        self.dir = Path(run_dir)
        self.dir.mkdir(exist_ok=True)
        self.run_id = uuid.uuid4().hex[:8]
        self.events: list[dict] = []

    def log(self, kind: str, **payload: Any) -> None:
        self.events.append({"t": time.time(), "kind": kind, **payload})

    def save(self, task: str, outcome: str) -> Path:
        path = self.dir / f"{self.run_id}.json"
        path.write_text(json.dumps(
            {"run_id": self.run_id, "task": task, "outcome": outcome, "events": self.events},
            indent=2,
        ))
        return path


# ---------------------------------------------------------------------------
# (5) Adapter slots — implement these in Stage 1 with your keys.
# The core above never imports Nebius / Composio / Tavily; only these do.
# ---------------------------------------------------------------------------
class LLMClient(Protocol):
    def write_tool(
        self, task: str, research: str, feedback: str, current_tools: list[str]
    ) -> ToolContract:
        """Nebius codegen. `feedback` carries the last traceback + rejected buffer."""
        ...


class Sandbox(Protocol):
    def run(self, source: str) -> tuple[bool, str]:
        """Composio remote workbench. Returns (passed, combined_stdout_stderr)."""
        ...


class Searcher(Protocol):
    def search(self, query: str) -> str:
        """Tavily. Returns an API/usage docs snippet."""
        ...


class Action(Protocol):
    def execute(self, tool_name: str, tool: Callable[..., Any]) -> str:
        """Fire the real-world Composio action using the freshly-built tool."""
        ...


# ---------------------------------------------------------------------------
# Harness orchestrator — the loop. Control flow + discipline live here; the
# four semantic / IO steps are delegated to the adapters.
# ---------------------------------------------------------------------------
class Harness:
    def __init__(
        self,
        llm: LLMClient,
        sandbox: Sandbox,
        searcher: Searcher,
        action: Action,
        registry: ToolRegistry | None = None,
        *,
        gate: bool = True,
        max_attempts: int = 3,
        feedback_mode: str = "full",
        independent_verifier: Callable[[str, "ToolContract"], str] | None = None,
    ):
        self.llm = llm
        self.sandbox = sandbox
        self.searcher = searcher
        self.action = action
        self.registry = registry or ToolRegistry()
        # Ablation hooks — defaults preserve standard behavior:
        #   gate=False        admit the first codegen regardless of its self-test
        #   max_attempts=N    bounded edit budget (1 == build-or-fail-fast)
        #   feedback_mode     "full" | "traceback" | "none" (rejected-buffer ablation)
        #   independent_verifier(task, contract) -> test source: when set, the gate runs
        #     the tool's code against THIS independently-written test instead of the
        #     model's own self-test (tests whether an author-independent verifier helps).
        self.gate = gate
        self.max_attempts = max_attempts
        self.feedback_mode = feedback_mode
        self.independent_verifier = independent_verifier

    def run(self, task: str, needed_tool: str) -> str:
        log = TrajectoryLogger()
        log.log("task", task=task, needed_tool=needed_tool)

        # Reuse before building — the library compounds.
        if self.registry.has(needed_tool):
            log.log("reuse", tool=needed_tool)
            result = self.action.execute(needed_tool, self.registry.callable(needed_tool))
            return self._finish(log, task, "reused", result)

        # Gap detected -> research once.
        log.log("gap", tool=needed_tool)
        query = f"how to {task} in python"
        research = self.searcher.search(query)
        log.log("research", query=query, result=research[:500])

        budget = BuildBudget(max_attempts=self.max_attempts)
        rejected: list[str] = []   # the rejected-edit buffer (negative feedback)
        feedback = ""

        while budget.can_retry():
            budget.charge(attempts=1)
            contract = self.llm.write_tool(task, research, feedback, self.registry.list_names())
            log.log("codegen", attempt=budget.attempts, name=contract.name)

            # The gate signal: the model's own self-test, OR — when configured — an
            # independently-written test that never saw this implementation.
            if self.independent_verifier is not None:
                gate_source = (
                    f"{contract.code}\n\n# --- independent test ---\n"
                    f"{self.independent_verifier(task, contract)}\n"
                )
            else:
                gate_source = contract.source()
            passed, output = self.sandbox.run(gate_source)
            verification = VerificationRecord(
                status="passed" if passed else "failed",
                attempts=budget.attempts,
                last_output=output,
            )
            log.log("test", attempt=budget.attempts, passed=passed, output=output[:500])

            if passed or not self.gate:  # ---- validation gate (ablatable) ----
                self.registry.admit(
                    contract, verification, key=needed_tool, force=not self.gate
                )
                log.log("admit", tool=needed_tool, function=contract.name,
                        gated=self.gate, passed=passed)
                result = self.action.execute(
                    needed_tool, self.registry.callable(needed_tool)
                )
                return self._finish(log, task, "built", result)

            # Failed -> buffer as negative feedback, retry per feedback_mode.
            rejected.append(output)
            feedback = self._make_feedback(output, rejected)
            log.log("reject", attempt=budget.attempts)

        return self._finish(log, task, "exhausted_budget", "")

    def _make_feedback(self, output: str, rejected: list[str]) -> str:
        """Build retry feedback. `feedback_mode` ablates the rejected-edit buffer:
        'full' = traceback + rejected count + don't-repeat; 'traceback' = just the
        traceback; 'none' = no feedback (each retry starts from scratch)."""
        if self.feedback_mode == "none":
            return ""
        if self.feedback_mode == "traceback":
            return f"Previous attempt failed its self-test.\nTraceback:\n{output}"
        return (
            "Previous attempt failed its self-test. Do NOT repeat these errors.\n"
            f"Traceback:\n{output}\n"
            f"Rejected attempts so far: {len(rejected)}."
        )

    def _finish(self, log: TrajectoryLogger, task: str, outcome: str, result: str) -> str:
        path = log.save(task, outcome)
        return f"[{outcome}] {result}  (trajectory: {path})"
