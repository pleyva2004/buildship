"""The interview engine — "Getting to Know You" (designs 08b §6, 09 §3).

Stateless surface, two backends:

  MOCK (INTERVIEW_BACKEND=mock, the default via VISTA_BACKEND): a faithful port
  of app/src/mock/interview.js — same branching script, same trait effects, same
  scorer. Mock and the app's local twin MUST agree turn-for-turn, or the demo
  re-rank differs between online and offline.

  LIVE: one structured Nebius completion per answer (extraction + planning in a
  single call, design 09 §3.1). The planner emits facts, trait effects for the
  scorer, and the next adaptive question. Facts are written to mem0 with
  provenance. ANY live failure degrades to the scripted step — never stalls.

Ranking is ALWAYS the deterministic scorer (§3.5) — live answers contribute
LLM-judged trait weights, but ordering logic and tie-breaks are pure code.

Terminal REPL: `make interview` / `make interview-live`.
"""

import json
import re

from agent import config
from agent.clients import nebius
from agent.clients.mem0_client import Mem0Client

INTERVIEW_LENGTH = 6  # must match app/src/mock/interview.js

TRAITS = [
    "bright", "cozy", "yard", "walkable", "office", "hosting",
    "character", "quiet", "turnkey", "parks", "downtown",
]

MUST_LABELS = {"yard": "real yard", "bright": "bright interiors", "walkable": "walkable"}


def _listings() -> list[dict]:
    index = json.loads((config.ASSETS_DIR / "listings" / "index.json").read_text())
    return index["listings"]


# ---------------------------------------------------------------------------
# MOCK twin — port of app/src/mock/interview.js. Keep in lockstep.
# ---------------------------------------------------------------------------

def _fx(weights=None, must=None, facts=None):
    return {"weights": weights or {}, "must": must or [], "facts": facts or []}


def _fx_who(raw: str) -> dict:
    a = raw.lower()
    if re.search(r"dog|puppy|daisy", a):
        return _fx({"yard": 3}, ["yard"], [
            {"category": "life_situation", "provenance": "stated", "text": f"Household: {raw}"},
            {"category": "life_situation", "provenance": "inferred", "text": "Must-have: outdoor space for the dog"},
        ])
    if re.search(r"kids|family", a):
        return _fx({"yard": 2, "quiet": 2}, [], [
            {"category": "life_situation", "provenance": "stated", "text": f"Household: {raw}"},
        ])
    return _fx({}, [], [{"category": "life_situation", "provenance": "stated", "text": f"Household: {raw}"}])


def _fx_dog(raw: str) -> dict:
    a = raw.lower()
    out = _fx({"yard": 1})
    if re.search(r"walk", a):
        out["weights"]["walkable"] = 2
    if re.search(r"yard", a):
        out["weights"]["yard"] = 3
        out["must"].append("yard")
    if re.search(r"park", a):
        out["weights"]["parks"] = 2
    out["facts"].append({"category": "life_situation", "provenance": "stated", "text": f"Dog routine: {a}"})
    return out


def _fx_saturday(raw: str) -> dict:
    a = raw.lower()
    if re.search(r"host|friends|dinner|guests", a):
        return _fx({"hosting": 3}, [], [
            {"category": "life_situation", "provenance": "stated", "text": "Hosts friends at home most weekends"},
            {"category": "taste", "provenance": "inferred", "text": "Needs rooms that gather people"},
        ])
    if re.search(r"coffee|reading|light", a):
        return _fx({"bright": 2}, [], [
            {"category": "taste", "provenance": "inferred", "text": "Slow mornings — values reading light"},
        ])
    if re.search(r"cook|meal", a):
        return _fx({"hosting": 2}, [], [
            {"category": "life_situation", "provenance": "stated", "text": "Cooks long meals — the kitchen is the room"},
        ])
    return _fx({"quiet": 1}, [], [{"category": "life_situation", "provenance": "stated", "text": f"Saturdays: {a}"}])


def _fx_light(raw: str) -> dict:
    a = raw.lower()
    if re.search(r"bright|airy", a):
        return _fx({"bright": 3, "cozy": -2}, [], [
            {"category": "taste", "provenance": "stated", "text": "bright and airy over cozy and dark"},
        ])
    if re.search(r"cozy|warm", a):
        return _fx({"cozy": 3, "character": 2}, [], [
            {"category": "taste", "provenance": "stated", "text": "cozy and warm over bright and stark"},
        ])
    return _fx({"bright": 1}, [], [
        {"category": "taste", "provenance": "stated", "text": "somewhere between bright and cozy"},
    ])


def _fx_dealbreaker(raw: str) -> dict:
    a = raw.lower()
    out = _fx()
    if re.search(r"dark", a):
        out["weights"]["bright"] = 2
        out["must"].append("bright")
    if re.search(r"yard", a):
        out["weights"]["yard"] = 2
        out["must"].append("yard")
    if re.search(r"commute", a):
        out["weights"]["walkable"] = 2
        out["must"].append("walkable")
    if re.search(r"renovation", a):
        out["weights"]["turnkey"] = 2
    out["facts"].append({"category": "life_situation", "provenance": "stated", "text": f"Deal-breaker: {a}"})
    return out


def _fx_center(raw: str) -> dict:
    a = raw.lower()
    out = _fx()
    if re.search(r"walk|caf|shop", a):
        out["weights"]["walkable"] = 3
        out["must"].append("walkable")
    if re.search(r"quiet", a):
        out["weights"]["quiet"] = 3
    if re.search(r"park|trail", a):
        out["weights"]["parks"] = 3
    if re.search(r"downtown", a):
        out["weights"]["downtown"] = 3
    out["facts"].append({"category": "life_situation", "provenance": "stated", "text": f"Life centers on: {a}"})
    return out


def _fx_anything(raw: str) -> dict:
    a = raw.lower()
    out = _fx()
    if re.search(r"park|trail|outdoor|hik", a):
        out["weights"]["parks"] = 2
    if re.search(r"walk|coffee|caf|restaurant|bar", a):
        out["weights"]["walkable"] = 2
    if re.search(r"quiet|peace", a):
        out["weights"]["quiet"] = 2
    if re.search(r"host|guest|friends|entertain", a):
        out["weights"]["hosting"] = 2
    if re.search(r"downtown|city", a):
        out["weights"]["downtown"] = 2
    if re.search(r"yard|garden", a):
        out["weights"]["yard"] = 2
    out["facts"].append({"category": "other", "provenance": "stated", "text": f"Also important: {raw}"})
    return out


SCRIPT = {
    "q_who": {
        "prompt": "Who’s making this move with you?",
        "chips": ["Just me", "Me + partner", "Family with kids", "Partner + a dog"],
        "optional": False,
        "effects": _fx_who,
        "next": lambda a: "q_dog" if re.search(r"dog|puppy|daisy", a) else "q_saturday",
    },
    "q_dog": {
        "prompt": "Tell me about the dog — what do walks look like?",
        "chips": ["Long daily walks", "Quick trips + a real yard", "Dog park regular"],
        "optional": False,
        "effects": _fx_dog,
        "next": lambda a: "q_saturday",
    },
    "q_saturday": {
        "prompt": "What does a great Saturday at home look like?",
        "chips": ["Slow coffee and reading light", "Hosting friends for dinner", "Cooking a long meal", "Out all day, home to recharge"],
        "optional": False,
        "effects": _fx_saturday,
        "next": lambda a: "q_light",
    },
    "q_light": {
        "prompt": "Bright and airy, or cozy and warm?",
        "chips": ["Bright & airy", "Cozy & warm", "Somewhere between"],
        "optional": False,
        "effects": _fx_light,
        "next": lambda a: "q_dealbreaker",
    },
    "q_dealbreaker": {
        "prompt": "Any deal-breakers I should never show you?",
        "chips": ["No dark interiors", "No tiny yards", "No long commutes", "No major renovations"],
        "optional": True,
        "effects": _fx_dealbreaker,
        "next": lambda a: "q_center",
    },
    "q_center": {
        "prompt": "Where does life center for you?",
        "chips": ["Walkable cafés and shops", "Quiet streets", "Near parks and trails", "Close to downtown"],
        "optional": True,
        "effects": _fx_center,
        "next": lambda a: "q_anything",
    },
    # The standing final question — ALWAYS asked last, whatever path got here.
    "q_anything": {
        "prompt": "Last one — what else do you want out of your new home? Activities you love, things you want nearby, anything at all.",
        "chips": ["Near a dog park", "Space for hobbies", "Good coffee close by", "Room for guests"],
        "optional": True,
        "effects": _fx_anything,
        "next": lambda a: None,
    },
}


def _effects(question_id: str, answer: str) -> dict:
    q = SCRIPT.get(question_id)
    if not q:
        return _fx()
    return q["effects"](answer)


def _accumulate(answers: list[dict]) -> tuple[dict, list]:
    """Scripted effects only — used for ranking in mock mode and on cold resume.
    must preserves insertion order (JS Set semantics) so chip order matches."""
    weights: dict[str, int] = {}
    must: dict[str, None] = {}
    for entry in answers:
        fx = _effects(entry.get("questionId", ""), entry.get("answer", ""))
        for trait, w in fx["weights"].items():
            weights[trait] = weights.get(trait, 0) + w
        for m in fx["must"]:
            must[m] = None
    return weights, list(must)


def rank_listings(weights: dict, must: list) -> list[dict]:
    """The deterministic scorer — port of mock/interview.js rankListings.
    Ties break price-ascending; unmet hard filters sink a listing."""
    scored = []
    for l in _listings():
        score = sum(weights.get(t, 0) for t in l["traits"])
        score -= 4 * sum(1 for m in must if m not in l["traits"])
        price = int(re.sub(r"\D", "", l["price"]))
        scored.append((score, price, l))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [
        {
            "listing_id": l["listing_id"],
            "met": [MUST_LABELS.get(m, m) for m in must if m in l["traits"]],
            "unmet": [MUST_LABELS.get(m, m) for m in must if m not in l["traits"]],
        }
        for _, _, l in scored
    ]


def _question_payload(qid: str, asked: int) -> dict:
    q = SCRIPT[qid]
    return {
        "id": qid, "prompt": q["prompt"], "chips": q["chips"],
        "optional": q["optional"], "asked": asked, "total": INTERVIEW_LENGTH,
    }


def _next_mock(answers: list[dict]) -> dict | None:
    if len(answers) >= INTERVIEW_LENGTH:
        return None
    if not answers:
        return _question_payload("q_who", 1)
    last = answers[-1]
    asked_ids = {a.get("questionId") for a in answers}
    q = SCRIPT.get(last.get("questionId", ""))
    nxt = q["next"](last.get("answer", "").lower()) if q else None
    # The last slot ALWAYS holds the open catch-all (and it never repeats).
    if not nxt or len(answers) == INTERVIEW_LENGTH - 1:
        nxt = None if "q_anything" in asked_ids else "q_anything"
    if not nxt:
        return None
    return _question_payload(nxt, len(answers) + 1)


def _profile_delta_mock(question_id: str, answer: str) -> dict:
    """Mirror of app/src/mock/interview.js profileDelta — keep in lockstep."""
    if question_id != "q_light":
        return {"palette_add": [], "aesthetic": None}
    a = answer.lower()
    if re.search(r"bright|airy", a):
        return {"palette_add": ["#F5F3EF", "#D9D2C7", "#A7B5A0"], "aesthetic": "bright & airy modern"}
    if re.search(r"cozy|warm", a):
        return {"palette_add": ["#C8A27A", "#7A5C3E", "#2F3E46"], "aesthetic": "warm & collected"}
    return {"palette_add": ["#E9E4DB"], "aesthetic": None}


def _record_mock(answers: list[dict], question_id: str, answer: str) -> dict:
    fx = _effects(question_id, answer)
    all_answers = answers + [{"questionId": question_id, "answer": answer}]
    weights, must = _accumulate(all_answers)
    return {
        "new_facts": fx["facts"],
        "profile_delta": _profile_delta_mock(question_id, answer),
        "ranked": rank_listings(weights, must),
        "next": _next_mock(all_answers),
    }


# ---------------------------------------------------------------------------
# LIVE planner — one structured completion per answer (design 09 §3.1/§3.2)
# ---------------------------------------------------------------------------

PLANNER_PROMPT = """You are VISTA, a warm personal home-buying agent, conducting a short \
get-to-know-you interview. You are NOT a form: acknowledge what you heard, then ask \
exactly one short question at a time, in a warm human voice (sentence case, no emoji, \
like: "What does a perfect Saturday at home actually look like for you?").

INTERVIEW STATE
- Question budget: {total} total. Questions asked so far: {asked}.
- Conversation so far:
{transcript}
- What you already know about this client (do NOT re-ask any of it):
{known}
- Never re-ask topics already covered above.

COVERAGE — by the end you want signal on: who's moving / daily life, light & mood \
preference, materials/textures, must-haves & deal-breakers, neighborhood feel. Deepen \
into a topic only when an answer opens a door (a dog -> yard & walks; hosting -> \
kitchen/dining). Otherwise advance to an uncovered area.
THE FINAL QUESTION is always the open catch-all, in your own warm words: what else do \
they want out of this home — activities they love, things they want nearby, any other \
consideration. Give it id "final.anything_else". Ask it when one slot remains in the \
budget, or sooner if coverage feels complete.

SCORING — candidate homes are ranked by trait weights. Allowed traits (use ONLY these):
{traits}
Translate EVERYTHING the answer reveals about the home they need into weights, including \
the obvious: a dog -> yard (and usually must); works from home -> office; hosts dinners \
-> hosting; loves walking to cafés -> walkable; hates dark rooms -> bright (must).

Respond with ONLY a JSON object, no prose, exactly this shape:
{{
  "facts": [{{"text": "atomic human-readable fact", "category": "life_situation|taste|materials|mood_board|other", "provenance": "stated|inferred"}}],
  "weights": {{"<trait>": -3..3}},
  "must": ["<trait that is now a hard requirement>"],
  "profile_delta": {{"palette_add": ["#hex once their light/mood/material taste shows"], "aesthetic": "2-4 word evolving aesthetic name, null until confident"}},
  "next_question": {{"id": "area.slug", "prompt": "...", "chips": ["…"], "optional": false}} or null
}}

Rules: facts are SHORT DISTILLED TIDBITS (max ~10 words), digestible at a glance — \
"Hosts dinners most weekends", "Woodworker — needs workshop space" — NEVER an echo of \
the raw answer and never meta ("user answered the question"). Use the "Must-have: " \
text prefix for hard requirements — category life_situation. If something clearly \
matters to them but fits no category (a hobby, a fear, a story), keep it with category \
"other" — NEVER force a bad fit and never drop it. provenance "stated" = they said it; \
"inferred" = you read between the lines. chips are 3-4 SHORT TAPPABLE ANSWERS in the client's own voice \
("Long daily walks", "Bright & airy") — never questions, never lowercase fragments. \
next_question = null when the budget is spent ({asked_next} >= {total}) \
or coverage feels complete."""


_sessions: dict[str, dict] = {}  # profile_id -> {"weights", "must"} accumulated live


def _session(profile_id: str) -> dict:
    return _sessions.setdefault(profile_id, {"weights": {}, "must": []})


def reset(profile_id: str) -> None:
    _sessions.pop(profile_id, None)


def _transcript(answers: list[dict]) -> str:
    if not answers:
        return "  (nothing yet — this is the opener)"
    lines = []
    for entry in answers:
        lines.append(f"  Q ({entry.get('questionId', '?')}): -> A: {entry.get('answer', '')}")
    return "\n".join(lines)


def _plan_live(profile_id: str, answers: list[dict], question_id: str, answer: str,
               memory: Mem0Client) -> dict:
    known = "\n".join(f"  - ({m['category']}) {m['text']}" for m in memory.all(profile_id)) or "  (nothing)"
    asked = len(answers) + 1
    prompt = PLANNER_PROMPT.format(
        total=INTERVIEW_LENGTH, asked=asked,
        transcript=_transcript(answers + [{"questionId": question_id, "answer": answer}]),
        known=known, traits=", ".join(TRAITS), asked_next=asked + 1,
    )
    raw = nebius.chat(
        [{"role": "system", "content": prompt},
         {"role": "user", "content": f"The client just answered {question_id!r} with: {answer!r}"}],
        temperature=0.4,
    )
    match = re.search(r"\{.*\}", raw, re.S)  # tolerant: model may wrap JSON in prose
    plan = json.loads(match.group(0) if match else raw)
    plan.setdefault("facts", [])
    plan.setdefault("weights", {})
    plan.setdefault("must", [])
    plan.setdefault("profile_delta", {})
    plan.setdefault("next_question", None)
    return plan


def _enforce_catchall(nxt: dict | None, answers: list[dict], question_id: str) -> dict | None:
    """The catch-all can NEVER be skipped (Jake's requirement). The planner is
    instructed, but instructions aren't guarantees — enforce in code:
      - planner stops early           -> serve the catch-all
      - planner overruns the budget   -> serve the catch-all (then end)
      - final slot holds another q    -> replace it with the catch-all
    Pure function so it's unit-testable without the LLM."""
    asked_next = len(answers) + 2  # prior answers + this answer + the next question
    asked_ids = {a.get("questionId", "") for a in answers} | {question_id}
    catchall_done = any("anything" in (i or "") for i in asked_ids)
    at_final_slot = asked_next == INTERVIEW_LENGTH
    overrun = asked_next > INTERVIEW_LENGTH

    if catchall_done and (overrun or nxt is None):
        return None
    if not catchall_done and (nxt is None or overrun or at_final_slot):
        nxt = {"id": "final.anything_else", "prompt": SCRIPT["q_anything"]["prompt"],
               "chips": SCRIPT["q_anything"]["chips"], "optional": True}
        asked_next = min(asked_next, INTERVIEW_LENGTH)
    if not nxt or not nxt.get("prompt"):
        return None
    return {
        "id": nxt.get("id") or f"dyn.{asked_next}",
        "prompt": nxt["prompt"],
        "chips": (nxt.get("chips") or [])[:4],
        "optional": bool(nxt.get("optional", False)),
        "asked": asked_next,
        "total": INTERVIEW_LENGTH,
    }


def _record_live(profile_id: str, answers: list[dict], question_id: str, answer: str,
                 memory: Mem0Client) -> dict:
    plan = _plan_live(profile_id, answers, question_id, answer, memory)

    facts = []
    for f in plan["facts"]:
        if not f.get("text"):
            continue
        category = f.get("category", "life_situation")
        if category == "constraint" and not f["text"].lower().startswith("no "):
            category = "life_situation"  # constraint is render rules only; rails hide it
        provenance = f.get("provenance", "stated")
        memory.add(profile_id, f["text"], category, source=provenance, question_id=question_id)
        facts.append({"category": category, "provenance": provenance, "text": f["text"]})

    sess = _session(profile_id)
    for trait, w in plan["weights"].items():
        if trait in TRAITS and isinstance(w, (int, float)):
            sess["weights"][trait] = sess["weights"].get(trait, 0) + int(w)
    for t in plan["must"]:
        if t in TRAITS and t not in sess["must"]:
            sess["must"].append(t)

    nxt = _enforce_catchall(plan["next_question"], answers, question_id)

    delta = plan["profile_delta"] or {}
    palette = [h for h in (delta.get("palette_add") or [])
               if isinstance(h, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", h)][:4]
    aesthetic = delta.get("aesthetic")

    return {
        "new_facts": facts,
        "profile_delta": {
            "palette_add": palette,
            "aesthetic": aesthetic if isinstance(aesthetic, str) and aesthetic else None,
        },
        "ranked": rank_listings(sess["weights"], sess["must"]),
        "next": nxt,
    }


# ---------------------------------------------------------------------------
# finish -> the style spec (design 09 §3.6, closes design 02). The passport is
# the human face of this object — it must reflect THIS conversation.
# ---------------------------------------------------------------------------

HARD_CONSTRAINTS = ["preserve architecture", "preserve windows/doors",
                    "preserve room geometry", "no people"]

SPEC_PROMPT = """You are VISTA's taste distiller. From everything known about this \
client, produce their locked style spec — the single object that will drive every \
room restyle. Ground EVERY field in their actual words below; do not default to a \
generic aesthetic.

WHAT YOU KNOW (interview answers + remembered facts):
{facts}

Respond with ONLY a JSON object:
{{
  "aesthetic_name": "2-4 words, theirs, specific (e.g. 'sunlit japandi calm')",
  "palette_hex": ["#......", 4-5 hexes derived from their stated light/material/mood taste],
  "materials": ["3-5 materials they'd actually touch"],
  "furniture_vocabulary": ["3-4 furniture phrases for restyle prompts"],
  "lighting_mood": "one phrase, theirs"
}}"""


def _spec_mock(profile_id: str, answers: list[dict]) -> dict:
    """Deterministic spec from the scripted answers — mirrors mock/interview.js
    buildSpec. Varies with the light/mood answer so cold runs aren't identical."""
    light = next((a.get("answer", "") for a in answers
                  if a.get("questionId") in ("q_light",)), "").lower()
    hosts = any(re.search(r"host|friends|dinner|guests", a.get("answer", "").lower())
                for a in answers)
    if re.search(r"bright|airy", light):
        spec = {"aesthetic_name": "bright & airy modern",
                "palette_hex": ["#F5F3EF", "#D9D2C7", "#A7B5A0", "#1C1C1C"],
                "materials": ["pale oak", "linen", "ceramic"],
                "lighting_mood": "bright, even daylight"}
    elif re.search(r"cozy|warm", light):
        spec = {"aesthetic_name": "warm & collected",
                "palette_hex": ["#C8A27A", "#7A5C3E", "#2F3E46", "#E9E4DB"],
                "materials": ["walnut", "wool", "brushed brass"],
                "lighting_mood": "warm, golden hour"}
    else:
        spec = {"aesthetic_name": "balanced & natural",
                "palette_hex": ["#E9E4DB", "#D9D2C7", "#A7B5A0", "#6F6557"],
                "materials": ["oak", "linen", "stone"],
                "lighting_mood": "soft natural light"}
    spec["furniture_vocabulary"] = (["long gathering table"] if hosts else []) + ["low-profile sofa"]
    return {"profile_id": profile_id, **spec, "hard_constraints": list(HARD_CONSTRAINTS)}


def _spec_live(profile_id: str, answers: list[dict], memory: Mem0Client) -> dict:
    known = [m["text"] for m in memory.all(profile_id)]
    qa = [f"Q {a.get('questionId')}: A: {a.get('answer')}" for a in answers]
    facts = "\n".join(f"  - {t}" for t in qa + known) or "  (nothing)"
    raw = nebius.chat(
        [{"role": "system", "content": SPEC_PROMPT.format(facts=facts)},
         {"role": "user", "content": "Produce the locked style spec now."}],
        temperature=0.5,
    )
    match = re.search(r"\{.*\}", raw, re.S)
    spec = json.loads(match.group(0) if match else raw)
    palette = [h for h in (spec.get("palette_hex") or [])
               if isinstance(h, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", h)][:5]
    if not spec.get("aesthetic_name") or len(palette) < 3:
        raise ValueError("spec missing aesthetic_name or a usable palette")
    return {
        "profile_id": profile_id,
        "aesthetic_name": str(spec["aesthetic_name"]),
        "palette_hex": palette,
        "materials": [str(m) for m in (spec.get("materials") or [])][:5],
        "furniture_vocabulary": [str(f) for f in (spec.get("furniture_vocabulary") or [])][:4],
        "lighting_mood": str(spec.get("lighting_mood") or "soft natural light"),
        "hard_constraints": list(HARD_CONSTRAINTS),  # never negotiable, never LLM-authored
    }


def finish_profile(profile_id: str, answers: list[dict], memory: Mem0Client | None = None) -> dict:
    """The interview's exit artifact. NEVER writes /specs (frozen, CLAUDE.md §4) —
    returning it to the UI is the passport; persisting is a deliberate human act."""
    if config.backend("interview") == "live":
        try:
            return _spec_live(profile_id, answers, memory or Mem0Client())
        except Exception as exc:
            print(f"[interview] live spec failed ({exc}); falling back to scripted spec")
    return _spec_mock(profile_id, answers)


# ---------------------------------------------------------------------------
# Public surface (server.py routes call these)
# ---------------------------------------------------------------------------

def next_question(profile_id: str, answers: list[dict]) -> dict | None:
    """Entry/resume. Opener is scripted even in live mode (deterministic first
    beat, design 09 §3); adaptivity starts with the first answer."""
    return _next_mock(answers)


def record_answer(profile_id: str, answers: list[dict], question_id: str, answer: str,
                  memory: Mem0Client | None = None) -> dict:
    if config.backend("interview") == "live":
        try:
            return _record_live(profile_id, answers, question_id, answer, memory or Mem0Client())
        except Exception as exc:  # never stall — degrade to the scripted step
            print(f"[interview] live step failed ({exc}); falling back to scripted step")
    return _record_mock(answers, question_id, answer)


# ---------------------------------------------------------------------------
# Terminal REPL — iterate on the interviewer without the app
# ---------------------------------------------------------------------------

def _repl() -> None:
    import os

    profile_id = os.environ.get("PROFILE", "jake_v1")
    memory = Mem0Client()
    answers: list[dict] = []
    print(
        f"VISTA interview — profile: {profile_id} | "
        f"engine: {config.backend('interview')} | memory: {config.backend('mem0')}\n"
    )
    q = next_question(profile_id, answers)
    while q:
        print(f"[{q['asked']}/{q['total']}] {q['prompt']}")
        if q["chips"]:
            print(f"        chips: {' | '.join(q['chips'])}")
        try:
            answer = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not answer or answer.lower() in {"exit", "quit"}:
            return
        res = record_answer(profile_id, answers, q["id"], answer, memory)
        answers.append({"questionId": q["id"], "answer": answer})
        for f in res["new_facts"]:
            print(f"  [fact:{f['provenance']:>8}] ({f['category']}) {f['text']}")
        order = " > ".join(r["listing_id"] for r in res["ranked"])
        print(f"  [rank] {order}\n")
        q = res["next"]
    print("Interview complete.")


if __name__ == "__main__":
    _repl()
