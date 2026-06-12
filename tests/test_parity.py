"""JS ↔ Python mock-twin parity — the app's offline fallback and the server's
mock mode MUST produce byte-identical interview behavior (design 09 §3).

Runs the same conversation through app/src/mock/interview.js (node) and
agent/interview.py and diffs the JSON. Skipped when node isn't available.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agent import interview

REPO = Path(__file__).resolve().parent.parent

SEQS = {
    "full-dog-path": [
        ("q_basics", "Austin close-in, $750k–900k, me, my partner and our dog Daisy"),
        ("q_dog", "Long daily walks and she needs a real yard"),
        ("q_saturday", "Hosting friends for dinner"),
        ("q_light", "Bright & airy"),
        ("q_dealbreaker", "No dark interiors"),
        ("q_anything", "I do pottery and love being near hiking trails"),
    ],
    "early-done-signal": [
        ("q_basics", "Still deciding the area, just me"),
        ("q_saturday", "Cooking long meals — that's everything, honestly"),
        ("q_anything", "A spot for my records. Nothing else, we're good"),
    ],
}

NODE_RUNNER = """
import {{ nextQuestion, recordAnswer, buildSpec }} from '{module}'
const seq = {seq}
let answers = []
const out = [nextQuestion(answers)]
for (const [qid, a] of seq) {{
  out.push(recordAnswer(answers, qid, a))
  answers.push({{ questionId: qid, answer: a }})
}}
out.push(buildSpec('parity', answers))
console.log(JSON.stringify(out))
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("seq", SEQS.values(), ids=SEQS.keys())
def test_mock_twins_exact_parity(tmp_path, seq):
    runner = tmp_path / "runner.mjs"
    runner.write_text(NODE_RUNNER.format(
        module=REPO / "app/src/mock/interview.js",
        seq=json.dumps([list(s) for s in seq]),
    ))
    js = json.loads(subprocess.run(
        ["node", str(runner)], capture_output=True, text=True, check=True
    ).stdout)

    answers = []
    out = [interview.next_question("parity", answers)]
    for qid, ans in seq:
        out.append(interview.record_answer("parity", answers, qid, ans))
        answers.append({"questionId": qid, "answer": ans})
    out.append(interview.finish_profile("parity", answers))
    py = json.loads(json.dumps(out))

    assert js == py
