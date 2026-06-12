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
    assert q["id"] == "q_who"
    assert q["asked"] == 1 and q["total"] == interview.INTERVIEW_LENGTH
    assert q["chips"]


def test_dog_branch():
    res = interview.record_answer("test", [], "q_who", "Partner + a dog")
    assert res["next"]["id"] == "q_dog"
    texts = [f["text"] for f in res["new_facts"]]
    assert "Must-have: outdoor space for the dog" in texts


def test_no_dog_skips_dog_question():
    res = interview.record_answer("test", [], "q_who", "Just me")
    assert res["next"]["id"] == "q_saturday"


def test_catchall_is_always_last_dog_path():
    seq = [
        ("q_who", "Partner + a dog"),
        ("q_dog", "Long daily walks"),
        ("q_saturday", "Hosting friends for dinner"),
        ("q_light", "Bright & airy"),
        ("q_dealbreaker", "No dark interiors"),
    ]
    _, results, _ = run_interview(seq)
    assert results[-1]["next"]["id"] == "q_anything"


def test_catchall_is_always_last_no_dog_path():
    seq = [
        ("q_who", "Just me"),
        ("q_saturday", "Quiet"),
        ("q_light", "Cozy & warm"),
        ("q_dealbreaker", "No long commutes"),
        ("q_center", "Quiet streets"),
    ]
    _, results, _ = run_interview(seq)
    assert results[-1]["next"]["id"] == "q_anything"


def test_interview_ends_after_catchall():
    seq = [
        ("q_who", "Partner + a dog"),
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
    res = interview.record_answer("test", [], "q_who", "Partner + a dog")
    order = [r["listing_id"] for r in res["ranked"]]
    assert order == ["alt1", "alt3", "hero", "alt4", "alt2"]
    top = res["ranked"][0]
    assert top["met"] == ["real yard"] and top["unmet"] == []
    sunk = res["ranked"][-1]
    assert "real yard" in sunk["unmet"]


def test_rank_with_no_answers_is_price_ascending():
    ranked = interview.rank_listings({}, [])
    assert [r["listing_id"] for r in ranked] == ["alt4", "alt1", "alt3", "alt2", "hero"]
