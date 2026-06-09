"""Offline tests for the ablation hooks (gate / budget / feedback) and the eval
runner with injected fake adapters — no network, no keys.
"""

from buildship.buildship_core import Harness, ToolContract, ToolRegistry
from buildship.eval.runner import Arm, run_eval
from buildship.eval.tasks import BENCHMARK

TRIVIAL = "def make_bar_chart(data, out_path):\n    return out_path\n"


def _contract(name="make_bar_chart", code=TRIVIAL):
    return ToolContract(name, "def make_bar_chart(d, p):", "doc", code,
                        'print("SELF_TEST_OK")\n', [])


class _LLM:
    def __init__(self, contracts):
        self._c = list(contracts)
        self.feedbacks = []
        self.calls = 0

    def write_tool(self, task, research, feedback, current_tools):
        self.calls += 1
        self.feedbacks.append(feedback)
        return self._c.pop(0)


class _Sandbox:
    def __init__(self, results):
        self._r = list(results)

    def run(self, source):
        return self._r.pop(0)


class _Searcher:
    def search(self, query):
        return "notes"


class _Action:
    def execute(self, tool_name, tool):
        return f"acted:{tool_name}"


def _harness(llm, sandbox, **kw):
    return Harness(llm=llm, sandbox=sandbox, searcher=_Searcher(), action=_Action(),
                   registry=ToolRegistry("lib.json"), **kw)


# ---- gate ablation ----
def test_no_gate_admits_failing_tool():
    llm = _LLM([_contract()])
    h = _harness(llm, _Sandbox([(False, "self-test failed")]), gate=False)
    result = h.run("plot a chart", "bar_chart_png")
    assert result.startswith("[built]")     # admitted despite failing self-test
    assert llm.calls == 1                    # no retry loop in ungated mode
    entry = h.registry.get("bar_chart_png")
    assert entry is not None
    assert entry.verification.status == "failed"   # record keeps the true status


def test_gated_failing_tool_is_not_admitted():
    llm = _LLM([_contract(), _contract()])
    h = _harness(llm, _Sandbox([(False, "x"), (False, "y")]), gate=True, max_attempts=2)
    result = h.run("plot a chart", "bar_chart_png")
    assert result.startswith("[exhausted_budget]")
    assert h.registry.get("bar_chart_png") is None


# ---- budget ablation ----
def test_max_attempts_one_is_build_or_fail_fast():
    llm = _LLM([_contract()])
    h = _harness(llm, _Sandbox([(False, "fail")]), gate=True, max_attempts=1)
    result = h.run("plot a chart", "bar_chart_png")
    assert result.startswith("[exhausted_budget]")
    assert llm.calls == 1


# ---- feedback (rejected-buffer) ablation ----
def test_feedback_mode_none_sends_no_feedback_on_retry():
    llm = _LLM([_contract(), _contract()])
    h = _harness(llm, _Sandbox([(False, "TB1"), (True, "ok")]), feedback_mode="none")
    h.run("plot a chart", "bar_chart_png")
    assert llm.calls == 2
    assert llm.feedbacks[1] == ""             # retry starts from scratch


def test_feedback_mode_traceback_has_no_rejected_count():
    llm = _LLM([_contract(), _contract()])
    h = _harness(llm, _Sandbox([(False, "TB1"), (True, "ok")]), feedback_mode="traceback")
    h.run("plot a chart", "bar_chart_png")
    assert "TB1" in llm.feedbacks[1]
    assert "Rejected attempts so far" not in llm.feedbacks[1]


def test_feedback_mode_full_includes_rejected_count():
    llm = _LLM([_contract(), _contract()])
    h = _harness(llm, _Sandbox([(False, "TB1"), (True, "ok")]), feedback_mode="full")
    h.run("plot a chart", "bar_chart_png")
    assert "TB1" in llm.feedbacks[1]
    assert "Rejected attempts so far" in llm.feedbacks[1]


# ---- eval runner end-to-end (offline, injected fakes) ----
_SUM_CODE = "def sum_numbers(numbers):\n    return sum(numbers)\n"


def _sum_llm():
    class L:
        def write_tool(self, *a, **k):
            return ToolContract("sum_numbers", "def sum_numbers(numbers: list) -> float:",
                                "doc", _SUM_CODE, "assert sum_numbers([1,2])==3\n", [])
    return L()


def _sum_task():
    return [t for t in BENCHMARK if t.id == "compute_sum"]


def test_run_eval_full_arm_offline():
    rep = run_eval(
        _sum_task(), arm=Arm("full"),
        llm=_sum_llm(), sandbox=_Sandbox([(True, "SELF_TEST_OK")]),
        searcher=_Searcher(), registry=ToolRegistry("eval_lib.json"), quiet=True,
    )
    assert rep.total == 1
    assert rep.build_success_rate == 1.0
    assert rep.e2e_success_rate == 1.0       # verifier ran the built sum tool: fn([1,2,3,4])==10


def test_run_eval_ungated_arm_verifies_even_when_selftest_fails():
    # The codegen produces a CORRECT sum tool, but the sandbox reports a failed
    # self-test. The no-gate arm admits it anyway; the e2e verifier then passes.
    rep = run_eval(
        _sum_task(), arm=Arm("no_gate", gate=False),
        llm=_sum_llm(), sandbox=_Sandbox([(False, "flaky self-test")]),
        searcher=_Searcher(), registry=ToolRegistry("eval_lib2.json"), quiet=True,
    )
    assert rep.build_success_rate == 1.0     # ungated admits on attempt 1
    assert rep.e2e_success_rate == 1.0       # but the verifier is the real judge


# ---- independent-verifier gate ----
class _RecordingSandbox:
    def __init__(self, results):
        self._r = list(results)
        self.sources = []

    def run(self, source):
        self.sources.append(source)
        return self._r.pop(0)


def test_independent_gate_runs_independent_test_not_self_test():
    contract = ToolContract("make_bar_chart", "def make_bar_chart(d, p):", "doc",
                            TRIVIAL, 'print("SELF_MARK")\n', [])
    rec = _RecordingSandbox([(True, "ok")])
    h = _harness(_LLM([contract]), rec,
                 independent_verifier=lambda task, c: 'print("INDEP_MARK")')
    h.run("plot a chart", "bar_chart_png")
    src = rec.sources[0]
    assert "INDEP_MARK" in src          # gate ran the independent test
    assert "SELF_MARK" not in src       # not the author's self-test


def test_independent_gate_catches_a_false_positive_the_self_test_misses():
    """The killer case: buggy code + a weak self-test (passes) — the self-test gate
    admits it, but an independent test catches the bug and the gate rejects."""
    from buildship.adapters import LocalSandbox

    buggy = "def round_half_up(value, decimals):\n    m = 10 ** decimals\n    return round(value * m) / m\n"
    weak_selftest = 'assert round_half_up(2.0, 0) == 2.0\nprint("SELF_TEST_OK")\n'   # passes on buggy code
    strong_test = 'assert round_half_up(1.005, 2) == 1.01\nprint("SELF_TEST_OK")\n'  # fails on buggy code

    class LLM2:
        def __init__(self):
            self.calls = 0

        def write_tool(self, task, research, feedback, current_tools):
            self.calls += 1
            return ToolContract("round_half_up", "def round_half_up(value, decimals):",
                                "round half up", buggy, weak_selftest, [])

        def write_test(self, task, contract=None):
            return strong_test

    def harness(independent, lib):
        return Harness(llm=LLM2(), sandbox=LocalSandbox(), searcher=_Searcher(),
                       action=_Action(), registry=ToolRegistry(lib),
                       gate=True, max_attempts=1,
                       independent_verifier=(lambda t, c: strong_test) if independent else None)

    # self-test gate: the weak self-test passes -> the broken tool is admitted (false positive)
    assert harness(False, "lib_fp_a.json").run("round half up", "round_half_up").startswith("[built]")
    # independent gate (fresh library): the independent test fails -> the broken tool is rejected
    assert harness(True, "lib_fp_b.json").run("round half up", "round_half_up").startswith("[exhausted_budget]")


def test_oracle_gate_check_bypasses_sandbox_and_gates():
    class _BoomSandbox:
        def run(self, source):
            raise AssertionError("sandbox must not be called when gate_check is set")

    # gate_check rejects -> exhausted_budget (sandbox never consulted)
    h_reject = Harness(llm=_LLM([_contract(), _contract()]), sandbox=_BoomSandbox(),
                       searcher=_Searcher(), action=_Action(), registry=ToolRegistry("ora_a.json"),
                       gate=True, max_attempts=2, gate_check=lambda c: (False, "nope"))
    assert h_reject.run("t", "cap").startswith("[exhausted_budget]")

    # gate_check accepts -> built
    h_accept = Harness(llm=_LLM([_contract()]), sandbox=_BoomSandbox(),
                       searcher=_Searcher(), action=_Action(), registry=ToolRegistry("ora_b.json"),
                       gate=True, max_attempts=1, gate_check=lambda c: (True, "ok"))
    assert h_accept.run("t", "cap").startswith("[built]")
