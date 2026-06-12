"""Chat brain smoke tests — mock path, action parsing, turn shape."""

from agent.core import AgentSession, parse_action, build_turn_message


def test_mock_demo_script_actions():
    session = AgentSession("jake_v1")
    t1 = session.turn("We're finally ready to look in Austin")
    assert t1["action"] is None and "Austin" in t1["reply"]
    t2 = session.turn("what did you find")
    assert t2["action"]["type"] == "recommend"
    t3 = session.turn("show me my version")
    assert t3["action"] == {"type": "generate_tour", "listing_id": "hero"}


def test_generate_backstop_fires_on_keywords():
    session = AgentSession("jake_v1")
    turn = session.turn("ok now show me my version please")
    assert turn["action"]["type"] == "generate_tour"


def test_turn_shape_has_new_facts():
    turn = AgentSession("jake_v1").turn("hello")
    assert set(turn) == {"reply", "action", "recalled", "new_facts", "researching"}
    assert turn["new_facts"] == []  # mock path never extracts


def test_recall_excludes_constraints():
    session = AgentSession("jake_v1")
    turn = session.turn("tell me about light and people and architecture")
    assert all(m["category"] != "constraint" for m in turn["recalled"])


def test_parse_action_is_forgiving():
    reply, action = parse_action('Sure!\n<action>{"type": "recommend", "listing_ids": ["hero"]}</action>')
    assert reply == "Sure!" and action["type"] == "recommend"
    reply, action = parse_action("<action>{not json}</action> hi")
    assert action is None
    reply, action = parse_action("no tag at all")
    assert (reply, action) == ("no tag at all", None)


def test_context_injection_format():
    msg = build_turn_message("hi", [{"category": "taste", "text": "pale woods"}])
    assert "[context" in msg and "[client says]\nhi" in msg
    assert build_turn_message("hi", []) == "hi"
