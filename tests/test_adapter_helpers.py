"""Offline tests for adapter helpers and the LocalSandbox (no network / no keys)."""

import pytest

from buildship.adapters import (
    LocalSandbox,
    _align_tool_name,
    _coerce_output,
    _looks_passed,
    _parse_tool_json,
)


def test_parse_tool_json_plain():
    assert _parse_tool_json('{"name": "x", "v": 1}') == {"name": "x", "v": 1}


def test_parse_tool_json_fenced():
    fenced = '```json\n{"name": "x"}\n```'
    assert _parse_tool_json(fenced) == {"name": "x"}


def test_parse_tool_json_embedded():
    noisy = 'Sure! Here it is:\n{"name": "x"}\nHope that helps.'
    assert _parse_tool_json(noisy) == {"name": "x"}


def test_parse_tool_json_invalid_raises():
    with pytest.raises(ValueError):
        _parse_tool_json("not json at all")


def test_align_tool_name_matches():
    assert _align_tool_name("make_chart", "def make_chart(d, p):\n    return p") == "make_chart"


def test_align_tool_name_defers_to_sole_def():
    # declared name doesn't match, but there's exactly one def -> use the real def name
    assert _align_tool_name("declared", "def actual_fn(d, p):\n    return p") == "actual_fn"


def test_align_tool_name_keeps_declared_when_ambiguous():
    assert _align_tool_name("declared", "def a(): pass\ndef b(): pass") == "declared"


def test_align_tool_name_keeps_declared_on_syntax_error():
    assert _align_tool_name("x", "def (:::") == "x"


def test_coerce_output_prefers_known_keys():
    assert _coerce_output({"output": "hello"}) == "hello"
    assert _coerce_output({"stdout": "a", "stderr": "b"}) == "a\nb"


def test_coerce_output_falls_back_to_json():
    out = _coerce_output({"weird": 1})
    assert "weird" in out


def test_looks_passed_exit_code():
    assert _looks_passed("anything", {"exit_code": 0}) is True
    assert _looks_passed("anything", {"exit_code": 1}) is False


def test_looks_passed_markers():
    assert _looks_passed("...SELF_TEST_OK...", {}) is True
    assert _looks_passed("Traceback (most recent call last)\nValueError", {}) is False
    assert _looks_passed("clean output, no markers", {}) is True


def test_local_sandbox_pass():
    passed, output = LocalSandbox().run("print('SELF_TEST_OK')\n")
    assert passed is True
    assert "SELF_TEST_OK" in output


def test_local_sandbox_fail():
    passed, output = LocalSandbox().run("assert False, 'boom'\n")
    assert passed is False
    assert "AssertionError" in output


def test_local_sandbox_runs_real_matplotlib_chart_tool():
    """The actual hero-tool path: matplotlib (Agg) source + self-test, run offline."""
    source = (
        'import matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt\n'
        "def make_bar_chart(data, out_path):\n"
        "    fig, ax = plt.subplots(); ax.bar(list(data), list(data.values()))\n"
        "    fig.savefig(out_path); plt.close(fig); return out_path\n"
        "\n# --- self-test ---\n"
        "import os, tempfile\n"
        'p = os.path.join(tempfile.mkdtemp(), "t.png")\n'
        'r = make_bar_chart({"A": 1, "B": 2, "C": 3}, p)\n'
        "assert os.path.exists(r) and os.path.getsize(r) > 0\n"
        'print("SELF_TEST_OK")\n'
    )
    passed, output = LocalSandbox().run(source)
    assert passed is True, output
    assert "SELF_TEST_OK" in output


# --- NebiusLLMClient JSON-retry behavior (client mocked; no network) ---
class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeUsage:
    total_tokens = 7


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage()


class _FakeCompletions:
    def __init__(self, contents):
        self._contents = list(contents)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return _FakeResponse(self._contents.pop(0))


def _fake_client(contents):
    comp = _FakeCompletions(contents)
    client = type("C", (), {"chat": type("Ch", (), {"completions": comp})()})()
    return client, comp


_GOOD_JSON = (
    '{"name": "f", "signature": "def f():", "docstring": "d", '
    '"code": "def f():\\n    return 1\\n", "self_test": "print(1)", "requires": []}'
)


def test_write_tool_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    from buildship.adapters import NebiusLLMClient

    llm = NebiusLLMClient()
    client, comp = _fake_client(["this is not json", _GOOD_JSON])
    llm._client = client

    contract = llm.write_tool("task", "research", "", [])
    assert contract.name == "f"
    assert comp.calls == 2            # retried once after the bad reply
    assert llm.total_tokens == 14     # tokens accrued on both calls


def test_write_tool_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    from buildship.adapters import NebiusLLMClient

    llm = NebiusLLMClient()
    client, comp = _fake_client(["nope", "still nope", "nope again"])
    llm._client = client

    import pytest as _pytest
    with _pytest.raises(ValueError):
        llm.write_tool("task", "research", "", [])
    assert comp.calls == 3            # respects BUILDSHIP_CODEGEN_JSON_RETRIES default
