"""Interview engine smoke tests — mock twin behavior, scorer, catch-all."""

from agent import interview


def run_interview(seq):
    answers = []
    results = []
    q = interview.next_question("test", answers)
    for qid, ans in seq:
        results.append(interview.record_answer("test", answers, qid, ans))
        answers.append({"questionId": qid, "answer": ans})
    return q, results, answers


def test_opener_is_scripted():
    q = interview.next_question("test", [])
    assert q["id"] == "q_basics"  # one conversational opener: where + budget + who
    assert q["asked"] == 1 and q["total"] == interview.INTERVIEW_LENGTH
    assert q["chips"]


def test_dog_branch():
    res = interview.record_answer("test", [], "q_basics", "Austin, $850k, partner + a dog")
    assert res["next"]["id"] == "q_dog"
    texts = [f["text"] for f in res["new_facts"]]
    assert "Must-have: outdoor space for the dog" in texts
    assert "Household: partner + a dog" in texts  # segment, never the raw blob


def test_no_dog_skips_dog_question():
    res = interview.record_answer("test", [], "q_basics", "Austin, $700k, just me")
    assert res["next"]["id"] == "q_saturday"


def test_missing_budget_gets_followup():
    res = interview.record_answer("test", [], "q_basics", "Austin close-in, me and my partner")
    assert res["next"]["id"] == "q_budget"


def test_vague_basics_produces_no_junk_facts():
    res = interview.record_answer("test", [], "q_basics", "Still deciding honestly")
    assert res["new_facts"] == []


def test_catchall_is_always_last_dog_path():
    seq = [
        ("q_basics", "Austin close-in, $850k, partner + a dog"),
        ("q_dog", "Long daily walks"),
        ("q_saturday", "Hosting friends for dinner"),
        ("q_light", "Bright & airy"),
        ("q_dealbreaker", "No dark interiors"),
        ("q_center", "Walkable cafés and shops"),
    ]
    _, results, _ = run_interview(seq)
    assert results[-1]["next"]["id"] == "q_anything"


def test_catchall_is_always_last_no_dog_path():
    seq = [
        ("q_basics", "Austin suburbs, just me"),
        ("q_budget", "Under $750k"),
        ("q_saturday", "Quiet"),
        ("q_light", "Cozy & warm"),
        ("q_dealbreaker", "No long commutes"),
        ("q_center", "Quiet streets"),
    ]
    _, results, _ = run_interview(seq)
    assert results[-1]["next"]["id"] == "q_anything"


def test_interview_ends_after_catchall():
    seq = [
        ("q_basics", "Austin close-in, $850k, partner + a dog"),
        ("q_dog", "Long daily walks"),
        ("q_saturday", "Hosting friends"),
        ("q_light", "Bright & airy"),
        ("q_dealbreaker", "No dark interiors"),
        ("q_anything", "Pottery, and hiking trails nearby"),
    ]
    _, results, _ = run_interview(seq)
    assert results[-1]["next"] is None
    fact = results[-1]["new_facts"][0]
    assert fact["category"] == "other"  # open lane, never forced into a section


def test_profile_delta_on_light_question():
    res = interview.record_answer("test", [], "q_light", "Bright & airy")
    assert res["profile_delta"]["aesthetic"] == "bright & airy modern"
    assert len(res["profile_delta"]["palette_add"]) == 3


def test_rank_unmet_must_sinks_and_ties_break_by_price():
    # dog answer -> yard is a must; alt4/alt2 (no yard) sink; yard ties price-asc
    res = interview.record_answer("test", [], "q_basics", "Partner + a dog")
    order = [r["listing_id"] for r in res["ranked"]]
    assert order == ["alt5", "alt1", "alt3", "hero", "alt4", "alt2", "alt6"]
    top = res["ranked"][0]
    assert top["met"] == ["real yard"] and top["unmet"] == []
    sunk = res["ranked"][-1]
    assert "real yard" in sunk["unmet"]


def test_rank_with_no_answers_is_price_ascending():
    ranked = interview.rank_listings({}, [])
    assert [r["listing_id"] for r in ranked] == ["alt5", "alt4", "alt1", "alt3", "alt2", "hero", "alt6"]


def test_done_signal_jumps_to_catchall():
    res = interview.record_answer("test", [{"questionId": "q_who", "answer": "Just me"}],
                                  "q_saturday", "Quiet mornings — that's everything, honestly")
    assert res["next"]["id"] == "q_anything"


def test_done_signal_after_catchall_ends():
    prior = [{"questionId": "q_who", "answer": "Just me"},
             {"questionId": "q_saturday", "answer": "that's all really"}]
    res = interview.record_answer("test", prior, "q_anything", "Nothing else, we're good")
    assert res["next"] is None


def test_done_regex_does_not_false_positive_on_chips():
    for chip in ["No dark interiors", "Just me", "Out all day, home to recharge",
                 "Quick trips + a real yard", "Bright & airy"]:
        assert not interview.DONE_RE.search(chip), chip


def test_budget_band_parses():
    res = interview.record_answer("test", [], "q_budget", "$750k–900k")
    assert any(f["text"] == "Budget band: 750k-900k" for f in res["new_facts"])
    res = interview.record_answer("test", [], "q_budget", "Under $750k")
    assert any(f["text"] == "Budget band: under 750k" for f in res["new_facts"])


def test_where_records_area_fact():
    res = interview.record_answer("test", [], "q_basics", "Austin — close in")
    assert any(f["text"] == "Area: Austin — close in" for f in res["new_facts"])
    assert res["next"]["id"] == "q_budget"  # budget missing -> follow up


def test_area_answer_triggers_research_to_memory():
    from agent.clients.mem0_client import Mem0Client
    mem = Mem0Client()
    interview.record_answer("guest_v1", [], "q_basics", "Travis Heights please", mem)
    texts = [m["text"] for m in mem.all("guest_v1")]
    assert any("South Congress" in t for t in texts), texts
