"""Offline tests for the demo trace presenter (demo_trace.py). No network."""

import os

import demo_trace
from demo_trace import _latest, _load, render

HERE = os.path.dirname(os.path.abspath(demo_trace.__file__))


def _capture(traj) -> str:
    lines: list[str] = []
    render(traj, out=lines.append)
    return "\n".join(lines)


def test_self_debug_beat_is_spotlighted():
    txt = _capture(_load(os.path.join(HERE, "demo_traces", "self_debug.json")))
    assert "test failed" in txt          # the failure
    assert "SELF-DEBUG" in txt           # the highlighted recovery
    assert "action" in txt               # the real action fired
    assert "[built]" in txt


def test_reuse_beat_is_spotlighted():
    txt = _capture(_load(os.path.join(HERE, "demo_traces", "reuse.json")))
    assert "REUSE" in txt
    assert "0 new builds" in txt
    assert "[reused]" in txt


def test_render_handles_empty_trajectory():
    render({"task": "x", "outcome": "built", "events": []}, out=lambda s: None)


def test_latest_picks_newest(tmp_path, monkeypatch):
    d = tmp_path / "trajectories"
    d.mkdir()
    (d / "old.json").write_text("{}")
    (d / "new.json").write_text("{}")
    os.utime(d / "old.json", (1, 1))   # make old.json older
    monkeypatch.chdir(tmp_path)
    assert _latest().endswith("new.json")
