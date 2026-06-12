# Design 08 — "Getting to Know You" (the taste-profile interview)

> The opening stage where VISTA learns who you are by talking with you — voice or text —
> and assembles a taste profile in real time. Output: a locked taste profile (the `style_spec`)
> + categorized mem0 facts that downstream steps rank and restyle against.
>
> **Visual source of truth:** the working prototype at
> `experiences/getting-to-know-you/index.html` (design-system project). This doc is the
> integration spec; when prototype and prose disagree, the prototype wins on look/feel and
> this doc wins on contracts/data.

---

## 1. Purpose & success criteria

This stage replaces the hackathon assumption that the profile is pre-seeded (design 05 / CLAUDE.md §5).
The agent now **earns** its understanding. It must:

1. Feel like a warm, human conversation — not a form, not a generic chatbot.
2. Make *being understood* visible: every answer lands in the profile panel as the user watches.
3. Produce a coherent, locked **taste profile** good enough to drive recommendations + restyle.
4. Work hands-free (**voice**) or **text**, switchable mid-conversation with no loss of state.
5. Be short, finite, skippable, and resumable.

Done = a populated taste profile (the passport) the user confirms, handed to step 05 (Recommendations).

---

## 2. Where it sits

```
01 Welcome ──► 02 GETTING TO KNOW YOU ──► 04 Taste Profile / 05 Recommendations ──► …
                     │
   returning user ◄──┘ (skip; deepen later)
```

- **Entry:** first-time user after Welcome, OR explicit "tell VISTA more about me" later.
- **Exit (complete):** taste passport confirmed → `Find my homes` → Recommendations.
- **Exit (skip):** "Skip for now" → straight to chat/recommendations with a thin/empty profile;
  the interview can resume anytime and deepens the profile incrementally.
- **Returning user:** Welcome recognizes them (design 07 §01) and bypasses this stage.

---

## 3. State machine

One screen, five phases (plus a pre-start intro). Phase drives what the conversation pane shows.

```
            ┌─────────┐  pick mode      ┌──────────┐  q rendered   ┌─────┐
  intro ───►│ (start) │ ───────────────►│ speaking │ ─────────────►│ ask │
            └─────────┘                 └──────────┘               └──┬──┘
                                             ▲                        │ answer (chip / text / voice)
                                  next step  │                        ▼
                              ┌──────────┐   │                  ┌───────────┐
                              │ thinking │◄──┴──────────────────│ listening │ (voice only)
                              └────┬─────┘                      └───────────┘
                                   │ last step
                                   ▼
                               ┌──────┐
                               │ done │ → taste passport overlay
                               └──────┘
```

| Phase | Meaning | Voice UI | Text UI |
|---|---|---|---|
| `intro` | mode choice | two cards: Talk / Type | same |
| `speaking` | VISTA poses the question | orb breathes, "VISTA is asking…" | typing dots, then question bubble |
| `ask` | awaiting user | mic = "Hold to speak" + hint | answer chips + composer |
| `listening` | capturing voice | mic = "Listening…", waveform, orb ripples | n/a (text has no listening phase) |
| `thinking` | extracting + advancing | mic disabled "VISTA is thinking…" | composer disabled "VISTA is thinking…" |
| `done` | profile complete | — | — |

State held: `{ mode: 'voice'|'text', step: int, phase, messages[], profile{}, palette[], aesthetic, caption, ready, showPassport }`.

---

## 4. Layout & responsive

Two-pane on web (desktop-first per product decision):

```
┌───────────────────────────────────────────────┬───────────────────────┐
│  topbar: VISTA · "Getting to know you" · progress · [Voice|Text] · Skip │
├───────────────────────────────────────────────┼───────────────────────┤
│                                                │  YOUR TASTE,          │
│   CONVERSATION PANE                            │  TAKING SHAPE         │
│   (voice: orb + question + mic)                │   Aesthetic: ——       │
│   (text: thread + chips + composer)            │   ● ● ● ●  (palette)  │
│                                                │   Life / Taste /      │
│                                                │   Materials /         │
│                                                │   Must-haves          │
│                                                │   [Profile ready →]   │
└───────────────────────────────────────────────┴───────────────────────┘
        flexible (minmax(0,1fr))                        360px fixed
```

- **Breakpoint:** `< 820px` collapses to one column and **hides the profile panel** (mobile is a
  later surface; on mobile, surface the profile as a slide-up sheet between questions instead).
- Conversation pane vertically centers content (voice) or bottom-anchors the composer (text).
- Topbar is persistent across phases; progress dots = `SCRIPT.length`.

---

## 5. Modes

### Voice (hero)
- **Orb**: idle = static; `speaking` = slow breathe; `listening` = scale-up + 3 expanding rings.
- **Waveform**: 9 bars, animate only while `listening`.
- **Mic control** (single button, label tracks phase): `Hold to speak` → `Listening… release when done` → `VISTA is thinking…`.
- **Captions**: VISTA's question shown large (always); user's transcribed answer shown as an italic caption after capture.
- **Interaction model decision (open):** prototype uses **hold-to-speak**. Alternatives: tap-to-toggle, or always-listening with VAD. Recommend **press-and-hold on desktop, tap-to-toggle on touch**.

### Text
- **Thread** of bubbles: agent = paper card + serif for questions; user = clay bubble.
- **Answer chips** (warm-starts) above the composer during `ask`; tapping a chip = submitting it.
- **Composer**: free text, disabled outside `ask`.

### Switching modes
- Toggle is live at any phase. Switching to text mid-`ask` must ensure the current question exists
  as a thread bubble (so the user has context). Switching to voice re-shows the orb + current question.
- **State is shared** — `step`, `profile`, `messages` persist across the switch.

---

## 6. The conversation engine (agent contract)

The prototype runs a static `SCRIPT[]`. Production replaces it with adaptive agent calls.
Add to `agent/core.py:AgentSession` (transport-agnostic; thin shells in `server.py`/`loop.py`):

| Method | Returns | Notes |
|---|---|---|
| `next_question(session)` | `Question` or `null` (interview complete) | adaptive; branches on prior answers; tracks asked-count to stay finite |
| `record_answer(session, answer)` | `{ facts: Memory[], rerank: listing_id[], profile_delta }` | writes mem0, returns what changed so the UI can animate |
| `style_spec(session)` | `StyleSpec` | the locked passport (CLAUDE.md §4) once enough is known |

```ts
type Question = {
  id: string;            // stable id, e.g. "life.move_reason"
  prompt: string;        // the spoken/displayed question
  chips?: string[];      // optional warm-start answers (text mode)
  category: 'Life'|'Taste'|'Materials'|'Must-haves';
  optional?: boolean;    // can be skipped without harming the profile
};

type Memory = {           // mirrors existing mem0 atomic-fact shape
  id: string;
  category: 'Life'|'Taste'|'Materials'|'Must-haves'|'constraint';
  text: string;           // human-readable, shown in the panel
  source: 'stated'|'inferred';
  question_id?: string;
};

type ProfileDelta = {
  palette_add?: string[];     // hex values to pop into the panel palette
  aesthetic?: string | null;  // evolving name; null until confident
};
```

**Adaptivity rules**
- Branch on answers (mention a dog → ask about yard/walks; "relocating" → ask timeline/area).
- Keep it finite: hard cap (~6 core questions) + optional deepeners; `next_question` returns `null` to end.
- `constraint`-category facts (render rules like "no people") are excluded from conversational
  recall but still written (design decision log, CLAUDE.md §8).
- **Mock-first** (CLAUDE.md §7): deterministic MOCK twins for all three methods so the stage runs
  zero-network. The prototype's `SCRIPT[]` is exactly that mock.

---

## 7. Profile panel behavior

- Four groups, fixed order: **Life · Taste · Materials · Must-haves**. Empty group = "VISTA is still listening…".
- On each `record_answer`: append `facts` to their group (slide-in, checkmark), `palette_add` pops
  swatches in, `aesthetic` updates the name (resolves from "——" to the final name at `done`).
- **No numeric score** anywhere (data-slop rule, design 07).
- **Stated vs inferred**: render a subtle mark distinguishing the two (honest provenance).
- **Editable** (production): tapping a fact lets the user confirm / edit / remove (also cleans mem0).
- Panel scrolls independently; `Profile ready` bar pins to the bottom when the interview completes.

---

## 8. Exit artifact — the taste passport

On `done`, the panel's `Profile ready → See your taste profile` opens the passport overlay.
This is the human face of the `style_spec` and the A↔B contract (CLAUDE.md §4):

| Passport field | Maps to `style_spec` |
|---|---|
| Aesthetic name | `aesthetic_name` |
| Palette swatches | `palette_hex[]` |
| Light | `lighting_mood` |
| Materials | `materials[]` |
| Life | (mem0 Life facts — context, not in spec) |
| Must-haves | hard filters for ranking (not restyle) |
| (hidden) | `furniture_vocabulary[]`, `hard_constraints[]` |

Actions: **Refine it** (back into nudge controls / conversation) · **Find my homes →** (to Recommendations).
Footer: "Built from your conversation · editable anytime" (provenance + reversibility).

---

## 9. Timing constants (from the prototype — tune, don't guess)

| Transition | Voice | Text |
|---|---|---|
| question appears after entering `speaking` | 1400ms (orb speaks) | 900ms (typing dots) → bubble |
| `listening` capture window | 1700ms (then transcript) | n/a |
| transcript shown → commit | 700ms | — |
| facts land after answer (`thinking`) | +600ms | +300ms |
| `thinking` → next question | 1500ms | 1100ms |
| last answer → `done`/ready | 1200ms | 1200ms |

Replace the fixed windows with real STT/agent timing in production; keep the *rhythm* (a beat of
"thinking" before the next question makes the agent feel considered, not instant).

---

## 10. Copy deck (current prototype script — starting point, refine with content)

| # | Category | Question | Warm-start chips |
|---|---|---|---|
| 1 | Life | "Before we look at a single home, I'd love to understand you. What's prompting the move?" | A growing family · First place of my own · Relocating for work · Ready for an upgrade |
| 2 | Life | "What does a perfect Saturday at home actually look like for you?" | Slow mornings, lots of light · Cooking for friends · Out in the neighborhood · Quiet & unplugged |
| 3 | Taste | "When you walk into a room and instantly love it — is it bright and airy, or warm and cozy?" | Bright & airy · Warm & cozy · Somewhere in between · Depends on the room |
| 4 | Materials | "Any materials or textures you're drawn to? Wood, stone, soft textiles…?" | Pale woods · Natural linen & wool · Matte black accents · Lots of greenery |
| 5 | Must-haves | "What's one thing a home absolutely must have for you?" | A home office with light · An open kitchen · Outdoor space · Walkable area |
| 6 | Must-haves | "Last one — where are you hoping to land?" | Walkable & central · Quiet & leafy · Near good coffee · Close to nature |

Voice/tone: warm, first-person-singular VISTA ("I'd love to…"), second-person to the user, no emoji,
sentence case, one question at a time. (Matches the app's existing voice; see design 07 §ContentFundamentals.)

---

## 11. Design tokens

Built entirely on the VISTA design system (`styles.css`). Key tokens in use:
`--accent`/`--accent-hover` (clay) for the orb, mic, user bubbles, CTAs · `--surface-card` for agent
bubbles/cards · `--match`/`--match-text`/`--match-wash` (moss) for fact checkmarks · `--font-serif`
(Fraunces) for questions + aesthetic name · `--radius-md`/`--radius-pill` · `--shadow-sm`/`--shadow-md`/`--shadow-lg`
· `--ease-soft` + `--dur-*` for all motion. See the design-system project's Type/Colors/Components cards.

**Motion gotcha (learned in the prototype):** entrance animations must be **transform-only** with the
element's resting state fully visible (`opacity: 1` base) — do **not** rely on `opacity:0 → 1` keyframes
with `fill-mode: both`, or elements can get trapped invisible under React re-renders. Animate position/scale, never opacity-from-zero, for anything that persists.

---

## 12. Voice implementation notes

- Prototype voice is **simulated** (scripted transcripts) to demo the flow end-to-end with no perms.
- Production: browser **SpeechRecognition** (Web Speech API) for STT where available; server STT fallback.
  TTS for VISTA's questions (voice choice TBD) — or text-only captions if TTS is out of scope.
- Handle **no mic permission** gracefully: fall back to text mode with a one-line note; never dead-end.
- Barge-in / interrupt is out of scope for v1.

---

## 13. Edge cases

- **Skip** at any point → exit with partial profile; resumable later.
- **Switch mode mid-question** → preserve step/answer-in-progress; ensure question context visible.
- **Back / re-answer** → allow editing a prior fact from the panel; re-run `rerank`.
- **Empty / nonsense answer** → agent reflects/clarifies rather than forcing a fact.
- **Mic denied / unsupported** → auto-fallback to text.
- **Very fast clicker** → disable inputs during `thinking`/`speaking` (prototype does this).

---

## 14. Acceptance

- **A:** Full interview completable in BOTH voice and text on MOCK backend; mode switchable mid-flow
  with state intact; profile panel fills live; passport opens with a coherent `style_spec`.
- **B:** Wired to `next_question`/`record_answer`/`style_spec` with live mem0 writes; deterministic
  mock twins still pass A; graceful mic-denied fallback.
- Skippable + resumable; no dead-ends; no numeric scores; reduced-motion respected (no infinite loops
  on content; entrance motion degrades to instant).

---

## 15. Build order

1. Static screen on the prototype's `SCRIPT[]` (mock) — both modes, profile panel, passport. ✅ (prototype)
2. `AgentSession.next_question` / `record_answer` / `style_spec` + MOCK twins.
3. Wire panel to `record_answer` deltas (facts, palette, aesthetic).
4. Real STT/TTS behind the voice UI; mic-permission fallback.
5. Editable facts + `rerank` hook (feeds design 07 §05 live re-ranking).
6. Passport → Recommendations handoff.
