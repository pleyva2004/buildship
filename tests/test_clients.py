"""Client smoke tests — mock backends only (zero network)."""

from agent.clients import nebius, tavily_client
from agent.clients.mem0_client import Mem0Client, flatten_profile, PROFILE_FILES
import json


def test_nebius_mock_keyword_match_ignores_context_block():
    msgs = [{"role": "user", "content": "[context — blah Austin blah]\n\n[client says]\nshow me my version"}]
    reply = nebius.chat_mock(msgs)
    assert "Generating your tour" in reply  # S3, not the Austin turn


def test_tavily_mock_search_and_extract():
    results = tavily_client.search("4 bedroom austin", max_results=2)
    assert len(results) == 2 and results[0]["url"]
    page = tavily_client.extract(results[0]["url"])
    assert page["images"], "hero extract should carry photo urls"
    assert tavily_client.extract("https://unknown.example")["images"] == []


def test_mem0_mock_lifecycle():
    m = Mem0Client()
    assert len(m.all("jake_v1")) == 14  # both profiles self-seed
    assert m.all("guest_v1") == []  # cold start really is cold

    fact = m.add("guest_v1", "Must-have: pottery studio", "life_situation", source="stated")
    assert fact["source"] == "stated"
    hits = m.search("guest_v1", "pottery studio space")
    assert hits and hits[0]["text"] == "Must-have: pottery studio"

    m.update("guest_v1", hits[0]["id"], "Must-have: garage workshop")
    assert m.all("guest_v1")[0]["text"] == "Must-have: garage workshop"
    m.delete("guest_v1", hits[0]["id"])
    assert m.all("guest_v1") == []


def test_flatten_profile_categories():
    profile = json.loads(PROFILE_FILES["jake_v1"].read_text())
    facts = flatten_profile(profile)
    cats = {f["category"] for f in facts}
    assert cats == {"life_situation", "taste", "mood_board", "constraint"}
    assert any(f["text"].startswith("Must-have:") for f in facts)
