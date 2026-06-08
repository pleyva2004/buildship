"""Offline tests for the harness loop (buildship_core), using fake adapters.

These exercise the control-flow discipline — validation gate, reuse, self-
correction feedback, bounded budget, and the key/def-name decoupling — without
any network or vendor SDKs.
"""

from buildship.buildship_core import (
    Harness,
    ToolContract,
    ToolRegistry,
    VerificationRecord,
)

# Trivial, exec-able tool code (no matplotlib needed — the sandbox is faked here).
TRIVIAL_CODE = "def make_bar_chart(data, out_path):\n    return out_path\n"


def contract(name="make_bar_chart", code=TRIVIAL_CODE):
    return ToolContract(
        name=name,
        signature="def make_bar_chart(data: dict, out_path: str) -> str:",
        docstring="render a chart",
        code=code,
        self_test='print("SELF_TEST_OK")\n',
        requires=[],
    )


class FakeLLM:
    def __init__(self, contracts):
        self._contracts = list(contracts)
        self.feedbacks = []
        self.calls = 0

    def write_tool(self, task, research, feedback, current_tools):
        self.calls += 1
        self.feedbacks.append(feedback)
        return self._contracts.pop(0)


class FakeSandbox:
    def __init__(self, results):
        self._results = list(results)  # queued (passed, output)
        self.sources = []

    def run(self, source):
        self.sources.append(source)
        return self._results.pop(0)


class FakeSearcher:
    def search(self, query):
        return "RESEARCH:" + query


class FakeAction:
    def __init__(self):
        self.calls = []

    def execute(self, tool_name, tool):
        self.calls.append(tool_name)
        return f"acted:{tool_name}"


def make_harness(llm, sandbox, action=None, registry=None):
    return Harness(
        llm=llm,
        sandbox=sandbox,
        searcher=FakeSearcher(),
        action=action or FakeAction(),
        registry=registry or ToolRegistry("lib.json"),
    )


def test_build_then_reuse_keys_off_needed_tool():
    llm = FakeLLM([contract()])
    sandbox = FakeSandbox([(True, "SELF_TEST_OK")])
    action = FakeAction()
    registry = ToolRegistry("lib.json")
    h = make_harness(llm, sandbox, action, registry)

    r1 = h.run("plot a bar chart", "bar_chart_png")
    r2 = h.run("plot a bar chart", "bar_chart_png")

    assert r1.startswith("[built]")
    assert r2.startswith("[reused]")
    assert llm.calls == 1            # second run reused; did NOT rebuild
    assert len(sandbox.sources) == 1
    assert registry.list_names() == ["bar_chart_png"]   # keyed by capability
    assert action.calls == ["bar_chart_png", "bar_chart_png"]


def test_callable_resolves_when_key_differs_from_def_name():
    registry = ToolRegistry("lib.json")
    registry.admit(contract(name="make_bar_chart"), VerificationRecord(status="passed"),
                   key="bar_chart_png")
    fn = registry.callable("bar_chart_png")     # key != def name
    assert callable(fn)
    assert fn({"A": 1}, "/tmp/out.png") == "/tmp/out.png"


def test_gate_rejects_failing_tool_and_exhausts_budget():
    llm = FakeLLM([contract(), contract(), contract()])
    sandbox = FakeSandbox([(False, "Traceback (most recent call last)\nAssertionError")] * 3)
    action = FakeAction()
    registry = ToolRegistry("lib.json")
    h = make_harness(llm, sandbox, action, registry)

    result = h.run("plot a bar chart", "bar_chart_png")

    assert result.startswith("[exhausted_budget]")
    assert llm.calls == 3                 # bounded retry budget (default max_attempts=3)
    assert registry.list_names() == []    # nothing admitted through the gate
    assert action.calls == []             # action never fired


def test_self_correction_feeds_back_the_traceback():
    llm = FakeLLM([contract(), contract()])
    sandbox = FakeSandbox([(False, "BOOM_TRACEBACK"), (True, "SELF_TEST_OK")])
    h = make_harness(llm, sandbox)

    result = h.run("plot a bar chart", "bar_chart_png")

    assert result.startswith("[built]")
    assert llm.calls == 2
    assert llm.feedbacks[0] == ""               # first attempt: no feedback
    assert "BOOM_TRACEBACK" in llm.feedbacks[1]  # retry carries the prior traceback
    assert "do not repeat" in llm.feedbacks[1].lower()


def test_admit_refuses_unpassed_tool():
    registry = ToolRegistry("lib.json")
    try:
        registry.admit(contract(), VerificationRecord(status="failed"), key="x")
        raised = False
    except ValueError:
        raised = True
    assert raised
