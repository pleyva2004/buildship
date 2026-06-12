"""Catch-all enforcement (pure logic, no LLM) + finish->style_spec."""

from agent.interview import (
    INTERVIEW_LENGTH, _enforce_catchall, finish_profile, HARD_CONSTRAINTS,
)


def answers(n, ids=None):
    ids = ids or [f"q{i}" for i in range(n)]
    return [{"questionId": i, "answer": "x"} for i in ids[:n]]


def test_planner_stops_early_catchall_served():
    nxt = _enforce_catchall(None, answers(2), "q2")
    assert nxt["id"] == "final.anything_else"


def test_planner_overruns_catchall_served_then_end():
    over = answers(INTERVIEW_LENGTH - 1)  # this answer fills the budget
    nxt = _enforce_catchall({"id": "x", "prompt": "More?"}, over, "qx")
    assert nxt["id"] == "final.anything_else"
    assert nxt["asked"] == INTERVIEW_LENGTH


def test_final_slot_question_replaced_with_catchall():
    near = answers(INTERVIEW_LENGTH - 2)
    nxt = _enforce_catchall({"id": "taste.x", "prompt": "Another taste q?"}, near, "qx")
    assert nxt["id"] == "final.anything_else"


def test_no_repeat_after_catchall_answered():
    done = answers(INTERVIEW_LENGTH - 1) + [{"questionId": "final.anything_else", "answer": "x"}]
    assert _enforce_catchall(None, done[:-1], "final.anything_else") is None
    assert _enforce_catchall({"id": "y", "prompt": "y?"}, done, "y") is None  # overrun + done


def test_midway_question_passes_through():
    nxt = _enforce_catchall({"id": "taste.light", "prompt": "Bright or cozy?"}, answers(1), "q1")
    assert nxt["id"] == "taste.light" and nxt["asked"] == 3


def test_spec_reflects_bright_answer():
    spec = finish_profile("guest_v1", [{"questionId": "q_light", "answer": "Bright & airy"}])
    assert spec["aesthetic_name"] == "bright & airy modern"
    assert spec["hard_constraints"] == HARD_CONSTRAINTS
    assert spec["profile_id"] == "guest_v1"


def test_spec_differs_for_cozy_answer():
    bright = finish_profile("g", [{"questionId": "q_light", "answer": "Bright & airy"}])
    cozy = finish_profile("g", [{"questionId": "q_light", "answer": "Cozy & warm"}])
    assert bright["palette_hex"] != cozy["palette_hex"]
    assert bright["aesthetic_name"] != cozy["aesthetic_name"]


def test_spec_hosting_adds_gathering_furniture():
    spec = finish_profile("g", [{"questionId": "q_saturday", "answer": "Hosting friends for dinner"}])
    assert "long gathering table" in spec["furniture_vocabulary"]
