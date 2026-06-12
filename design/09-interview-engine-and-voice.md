# Design 09 — The Dynamic Interview Engine & Voice

> The brain and the voice plumbing behind design 08b ("Getting to Know You").
> 08b owns look/feel and the screen contract; THIS doc owns the conversation engine,
> the agent/API surface, the voice pipeline, and the staging.
>
> **Scope decision (locked, Jake):** v1 is **text questions + voice answers** — VISTA's
> questions render as on-screen text (08b already shows the question as a large caption
> in voice mode), the user replies by holding the mic. **Voice-to-voice (VISTA speaking)
> is a later optimization**, staged below, polished only for the demo.

---

## 1. Principles

1. **One brain, any mouth.** Voice and text are I/O layers over the same
   `InterviewSession`. Chips, typed answers, and transcribed speech enter through the
   identical `record_answer` path. Nothing about the engine knows or cares which.
2. **Adaptive, finite, warm.** The agent chooses between *diving deeper* and *moving on*
   against a coverage map and a question budget. The interviewer's judgment is the
   feature; the cap is the safety rail.
3. **Mock-first survives.** The deterministic `SCRIPT[]` twin (already in
   `app/src/mock/interview.js`) remains the zero-network stage fallback. The engine is
   the live path. Same pattern as design 07.
4. **Latency hides in `thinking`.** 08b's state machine already has a `thinking` phase
   with a deliberate beat (§9: "the rhythm makes the agent feel considered"). Live agent
   latency (1–3s) replaces the fixed timer; floors keep the rhythm when the model is fast.

## 2. Architecture

```
InterviewView (voice-in | text)            MemoryRail / RerankPanel / Passport
      │   chips · composer · mic(STT)            ▲ facts · palette · ranked
      ▼                                          │
 /api/interview/next · /answer · /finish   (FastAPI, thin routes)
      ▼
 agent/interview.py — InterviewSession (modality-agnostic brain)
      │  one structured harness run per answer (Nebius, design 07 SDK)
      ├─ coverage map + budget + never-re-ask list
      ├─ mem0 writes (atomic facts, provenance)
      ├─ rerank scorer (server port of mock/interview.js)
      └─ style_spec assembly on finish (closes design 02)

 Voice v1:  hold-to-speak (MediaRecorder) → POST /api/voice/transcribe (local
            faster-whisper, offline, zero keys) → answer text
 Voice v2:  streaming captions while speaking (Deepgram) — optional polish
 Voice v3:  WS streaming TTS — VISTA speaks (warm voice)   ← the demo optimization
```

## 3. The conversation engine (`agent/interview.py`)

### 3.1 One run per answer

Each user answer triggers ONE structured harness run that does extraction + planning
together (halves round-trips vs. separate extract/next calls):

```json
{
  "facts": [{"text": "…", "category": "Taste", "source": "stated|inferred"}],
  "profile_delta": {"palette_add": ["#E9E4DB"], "aesthetic": "bright Scandinavian" | null},
  "next_question": {"id": "taste.light_vs_cozy", "prompt": "…", "chips": ["…"],
                    "category": "Taste", "optional": false} | null,
  "move": "deepen" | "advance" | "finish",
  "why": "one line — logged, never shown"
}
```

`next_question: null` ⇒ interview complete ⇒ UI goes to `done` → passport.

### 3.2 What the model sees per run

- The coverage map: per-area (Life / Taste / Materials / Must-haves) fact count +
  a coarse confidence the prompt asks it to maintain.
- Full Q/A transcript so far + the never-re-ask list (asked ids and semantic topics).
- Anything already known from mem0 (returning users start warm — recognition, not
  amnesia).
- The budget: ~6 core questions + up to 2 deepeners, hard stop at 8. Deepen only when
  an answer opens a door (dog → yard; "we host dinners" → dining/kitchen ritual).
- 08b §10's script ships in the prompt as STYLE EXEMPLARS (tone, length, chip shape) —
  the model writes its own questions in that voice; it does not recite the script.

### 3.3 Contract with 08b §6

Implements `next_question` / `record_answer` / `style_spec` with one pragmatic merge:
**`record_answer` returns the next question inline** (the engine already planned it in
the same run). `next_question` exists for entry/resume; calling it never burns budget.

### 3.4 Facts, categories, provenance

- Facts are atomic, human-readable, written to mem0 with `infer=False` and metadata
  `{category, source, question_id}`.
- **Category canon extends to:** `life_situation | taste | materials | must_have |
  mood_board | constraint`. 08b's panel groups map 1:1 (Life→life_situation,
  Taste→taste, Materials→materials, Must-haves→must_have). Migration note: seeded
  profiles use `Must-have:`-prefixed life_situation facts; `flatten_profile()` and the
  two rails update to the new canon in the same PR (small, mechanical).
- `source: stated | inferred` flows to the UI marks (honest provenance, 08b §7).
  Inferred facts the user removes are deleted from mem0 (hygiene endpoints, design 08).

### 3.5 Rerank

`record_answer` also returns `ranked: listing_id[]` from a server-side port of the
trait scorer in `app/src/mock/interview.js` (ties price-ascending, same as mock — the
two must agree or the demo reorder differs between mock and live).

### 3.6 `finish` → the style spec (closes design 02)

On finish (or explicit "Profile ready"): one LLM call over all facts → `style_spec`
JSON validated against `specs/schema.json` (retry once with the validator error, then
fall back to nearest frozen spec + log). Written to `specs/<profile_id>.json` ONLY on
user confirm in the passport, and never over `jake_v1`/`pablo_v1` (frozen, CLAUDE.md §4)
— dynamic sessions get fresh ids (`<name>_dyn1`).

### 3.7 Session state & resumability

In-process per-profile dict (same as chat sessions). Facts live in mem0; the client
passes its `answers[]` on every call (design 08 kept the surface stateless) — so a
server restart or mode switch mid-interview rebuilds cleanly. Skip/resume (08b §13)
falls out: resume = `next_question` with existing mem0 + answers.

## 3.8 Dynamic memory beyond the interview (Jake's requirement)

The interview *starts* the profile; **conversation about real homes is where
preferences get tested and revised.** Reacting to listings ("the craftsman feels
right, actually — I thought I wanted new-build") teaches the agent things no
questionnaire can. This must update memory dynamically, mid-conversation.

Mechanism — the CHAT agent (design 07 harness) gains memory tools, shared with the
interview engine (one write path, one brain):

| Tool | Behavior |
|---|---|
| `save_memory(text, category, source)` | New fact learned mid-conversation → mem0 + this turn's `new_facts` |
| `revise_memory(old_id, new_text, why)` | Preference revision/contradiction → supersede, never silently append a conflict |

- **Reactions become trait-level facts**, not listing-level ones. Instructions:
  never store "disliked alt1"; store the *why* at the preference level —
  "darker interiors are a dealbreaker (confirmed passing on the Zilker craftsman)"
  — with `source: inferred` + the listing id in metadata. Trait-level facts transfer
  to homes the user hasn't seen yet; listing-level ones don't.
- **Contradiction handling:** the prompt instructs the agent to *notice* revisions
  ("you told me bright-and-airy, but you've now warmed to two darker homes — updating
  that") and call `revise_memory` — naming the revision out loud is both honest UX and
  a demo moment. On live mem0, dynamic adds may additionally use `infer=True` so mem0's
  own reconciliation (add/update/delete) merges drift — that's the strongest possible
  sponsor line: "preference drift is handled by mem0 itself." Verify behavior in step 1;
  seeds stay `infer=False` (verbatim).
- **Surface:** `/api/chat` adds `new_facts: Memory[]` (design 08 already specced it;
  ChatView already renders "✓ Saved to memory" chips and the rail already animates
  fresh facts). `recall → rerank` then uses the updated memory on the next turn, so a
  revision visibly reorders the pool — the learn→re-rank proof, now in free conversation.
- **Mock twin:** `mock/brain.js`'s naive fact extraction already simulates this; the
  server mock mirrors it.

## 4. The API surface (`agent/server.py`)

| Route | Body → Returns |
|---|---|
| `POST /api/interview/next` | `{profile_id, answers?}` → `Question` \| `{done: true}` |
| `POST /api/interview/answer` | `{profile_id, question_id, answer, mode}` → `{facts, profile_delta, ranked, next}` |
| `POST /api/interview/finish` | `{profile_id, confirm}` → `{style_spec}` (writes spec only if `confirm`) |
| `POST /api/voice/transcribe` *(v1)* | audio blob → `{text}` (local faster-whisper) |
| `WS /api/voice` *(v3)* | bidirectional events + TTS audio chunks (see §6) |

Shapes match 08b §6 TS types exactly. The app's `api.js` already calls the interview
routes with mock fallback — when these land, the frontend changes by zero lines
(design 08's bet, now collected).

Mock twins: each route has a deterministic server-side mock (the `SCRIPT[]` ported to
Python) selected by `INTERVIEW_BACKEND=mock|live` — `/api` parity in both modes, and
`make agent`-style terminal testing of the interview brain without the app
(`make interview` REPL, mirrors `loop.py`).

## 5. Voice v1 — voice answers, text questions (BUILD NOW)

**Decision (Jake): MediaRecorder + local Whisper, not Web Speech API.** Web Speech
auto-endpoints on silence (fights hold-to-speak), degrades in noise (the stage case),
streams audio to Google (off-story, needs network), and is Chrome-only. Local
`faster-whisper` (small model) transcribes a 10s clip in ~1s on the dev Mac, offline,
zero keys, and MediaRecorder maps exactly to press/release. ~1h more work, demo-grade.

- `ask` phase, voice mode: hold-to-speak (08b §5 — press-and-hold desktop, tap-toggle
  touch) drives **MediaRecorder**; release → audio blob → `POST /api/voice/transcribe`
  (faster-whisper, new dep) → transcript renders as the italic caption (08b shows the
  transcript after capture — matches) → submitted through the SAME `recordAnswer` path
  as a chip tap. Transcript is editable before submit (cheap insurance for mis-hears).
- The orb/waveform states in 08b §3 map directly: `listening` while held,
  `thinking` covers transcribe + engine, question caption renders on `next`.
- **Fallbacks (08b §13):** mic denied / no MediaRecorder / transcribe error → auto
  text mode with a one-line note; never dead-end. Whisper runs locally, so voice
  works with stage wifi down.
- Web Speech API survives only as `STT_BACKEND=webspeech` curiosity if ever needed;
  not on any critical path.

Definition of "try it": hold the mic, say "we're finally ready to look in Austin —
we've got a dog and I work from home", watch facts slide into the panel, the pool
re-rank, and an adaptive follow-up about the yard appear. Questions silent, on screen.

## 6. Voice v2/v3 — the later optimization (demo polish)

- **v2 — live captions while speaking (optional):** streaming STT (Deepgram Nova-3,
  free credit) behind `STT_BACKEND=whisper|deepgram` if word-by-word captions during
  hold prove worth it. Nebius hosts no STT (checked June 12) — no sponsor angle either
  way. Client switch is one function in `api.js`.
- **v3 — VISTA speaks (voice-to-voice):** WS `/api/voice`; server streams
  `transcript → facts → rerank → speak_start → audio chunks → next_question`.
  TTS = ElevenLabs Flash / Cartesia streaming (warm, ~75–90ms), first sentence
  synthesized while the rest generates; instant canned acknowledgments ("Mm — got it…")
  cover engine latency. `VOICE_BACKEND=cheap|warm`: robotic/free for prep, warm flipped
  on for rehearsals + stage (ElevenLabs free tier ≈ 10 min of speech — prep would burn
  it; demo + 2 rehearsals fits).
- **Future-work slide, not built:** full-duplex open mic with barge-in + semantic turn
  detection (LiveKit Agents / Pipecat; native speech-to-speech models as the far end).
  Explicitly out of scope per 08b §12.

## 7. Build order

| # | What | Proves | Status |
|---|---|---|---|
| 1 | `agent/interview.py` engine + structured runs + mem0 writes + server rerank + mock twins + routes + `make interview` REPL | the brain, testable in terminal | ✅ shipped, parity-tested |
| 2 | Voice v1: `POST /api/voice/transcribe` (faster-whisper) + MediaRecorder hold-to-speak in `InterviewView` + fallbacks | **the thing Jake wants to try** | ✅ shipped, human-verified |
| 3 | Chat-agent memory tools (`save_memory`/`revise_memory`, §3.8) + `new_facts` in `/api/chat` | learning during property talk | ✅ shipped, live-tested |
| 4 | `finish` → style_spec → passport confirm flow | closes design 02; the exit artifact | ✅ shipped — passport reflects the conversation; spec returned, never persisted |
| 5 | v2 streaming captions (only if wanted) | polish | pending |
| 6 | v3 warm TTS voice-to-voice | the demo wow; only stage that touches paid voice | pending |

**Amendments shipped with steps 1–3 (Jake, June 12):**
- **The catch-all final question** — the interview ALWAYS ends with an open "what else
  do you want out of your new home — activities, things nearby, anything at all"
  (scripted `q_anything` in both twins, `final.anything_else` instruction + null-backstop
  live). `INTERVIEW_LENGTH` is 6.
- **Distilled tidbits** — live facts are ≤~10-word digestible tidbits, never raw-answer
  echoes (mock twins keep templates; they're the deterministic fallback by design).
- **Open category lane** — facts that fit no target section carry category `other` and
  render under "Also worth knowing"; never forced into a bad fit, never dropped.
- **Spacebar push-to-talk** — hold space to talk, release to send (guarded against key
  repeat and typing in inputs); the mic button still works.
- **Guest profile (`guest_v1`)** — cold start with zero seeded memories, selectable in
  the topbar, for testing without preloaded persona data.
- **Smoke tests** — `make test` (`tests/`): twin parity (node↔python), engine behavior,
  scorer invariants, every API route, transcribe contract. All mock, zero network.
- **Catch-all enforced in code** (`_enforce_catchall`, unit-tested): planner stopping
  early, overrunning the budget, or filling the final slot with another question all
  resolve to the catch-all. Prompts instruct; code guarantees.
- **Brain badge** — the interview topbar shows `live` / `scripted fallback` /
  `offline · local mock` from `/api/health`, so a stale or mock backend can never
  masquerade as the live agent (root cause of the "questions look hardcoded" report:
  a stale pre-catch-all mock server was holding :8001).
- **Fresh entry** — "Things changed — let's catch up" resets session answers and the
  server's interview accumulators (memories persist); re-running the interview no
  longer resumes into a finished state.

Steps 1–2 are one work session; nothing in them is throwaway for v3 (the WS layer
wraps the same engine events).

## 8. Risks & open decisions

- **Structured output on Nebius/Llama:** the SDK's `output_type` uses
  `response_format` json-schema — verify Nebius honors it for Llama 3.3 70B; fallback
  is JSON-in-prompt + tolerant parse + one retry (the design 07 muscle). Test first in
  step 1.
- **Question quality drift** (repetitive/robotic phrasing): coverage map + exemplars +
  never-re-ask list; iterate in the `make interview` REPL where a round-trip costs
  seconds, not clicks.
- **Latency rhythm:** target ≤2.5s per `thinking`; if Llama runs longer, the v1 UI
  absorbs it (text), but v3 needs the filler-ack pattern — design it into the event
  protocol now (`speak_start` is separate from `audio` for exactly this).
- **Decisions for Jake:** (a) v3 voice/persona choice (ElevenLabs vs Cartesia, which
  preset); (b) whether dynamic profiles can ever overwrite a frozen spec (current
  answer: never); (c) when categories migrate (§3.4) — suggest with step 1.
