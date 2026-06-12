# Design 08 — Flow Optimizations & Active Learning (post-hackathon)

> **Implementation status (2026-06-12): frontend SHIPPED.** All 8 steps (3 new screens +
> 5 refinements) built mock-first and Playwright-verified end-to-end on the zero-network
> path. Remaining work is the §1 agent surface (§5 item 1): `next_question` /
> `record_answer` / `rerank` in `agent/core.py` + `/api/interview/*`, `/api/memory/*`
> routes in `server.py`. The app already calls those endpoints and falls back to its
> deterministic mock twin (`app/src/mock/interview.js`) on failure — server-log 404s for
> them are expected until the backend lands. Interview state (`answers`) is client-held,
> so the backend surface can stay stateless.
> (Authored externally as "Design 07"; renumbered 08 in-repo — 07 is the agent harness.)

> The hackathon build nailed the spine: welcome → chat+memory-rail → generating → tour+slider.
> This doc is the v0→v1 optimization plan. **One new non-negotiable: the agent actively LEARNS.**
> VISTA no longer only arrives pre-seeded — it asks, listens, remembers, and **dynamically
> re-ranks** listings as it learns. Everything here is measured against one job: does it make
> *being understood* feel real?
>
> Companion artifact: the annotated visual proposals + the VISTA design system (tokens,
> components, UI kit) live in the design-system project. This doc is the engineering spec.

---

## 0. What changed since design 05

Design 05 assumed the profile is **pre-seeded into mem0** (CLAUDE.md §5: "no onboarding —
context is pre-seeded"). That was the right hackathon cut. For v1 the product thesis shifts:

- **The agent is responsible for learning about you, not only knowing you up front.** There is
  now an explicit stage where it asks questions to build a sense of who you are and where you
  might want to live.
- **Learning re-ranks results in real time.** Every answer writes to mem0 *and* visibly
  re-orders the candidate listings. The learn→re-rank loop is the new proof of intelligence.
- **Two implied steps get real screens:** a Taste Profile and a Listing Detail.

Net spine (8 steps; 3 new):

```
01 Welcome
02 Getting to Know You   ← NEW (active learning + live re-rank)
03 Conversation + Memory Rail
04 Taste Profile          ← NEW (promote the style spec to a screen)
05 Recommendations
06 Listing Detail         ← NEW
07 Generating
08 Tour + Slider          (the hero)
```

---

## 1. The active-learning loop (the headline change)

```
┌─ user answers a question ──────────────────────────────────┐
│                                                            │
│   answer ──► extract facts ──► mem0.add (categorized)      │
│                   │                                         │
│                   ├──► memory rail: fact animates in       │
│                   │                                         │
│                   └──► re-rank candidate listings ─────────┤
│                            │                                │
│                            └──► cards visibly re-order  ◄───┘
└────────────────────────────────────────────────────────────┘
```

- **Re-rank is a pure scoring pass over the already-fetched candidate set** — not a new
  Tavily call per answer. Keep a small candidate pool (5–8 listings) in session state; each
  answer adjusts a per-listing score and the UI animates the reorder. This stays demo-safe
  (zero network on stage) and reads as "live."
- **Scoring inputs:** stated must-haves (hard filters), taste cues (soft weights), life
  situation (soft weights). Reuse the mem0 categories already in `agent/profiles/` seeds.
- **No numeric match score in the UI** (data slop). Re-rank shows as motion + "↑ moved up"
  affordances + met/unmet must-have chips. The *story*, not a percentage.

### New agent surface

`agent/core.py:AgentSession` already owns transport-agnostic logic (CLAUDE.md §7). Add:

| Method | Returns | Notes |
|---|---|---|
| `next_question(session)` | `{ id, prompt, chips[], optional }` | adaptive; branches on prior answers; finite (track asked-count) |
| `record_answer(session, answer)` | `{ new_facts[], reranked_listing_ids[] }` | writes mem0, returns reorder so the app can animate |
| `rerank(session)` | `listing_id[]` ordered | pure function over candidate pool + current profile |

Keep MOCK twins (CLAUDE.md §7 mock-first rule): `next_question`/`rerank` must be deterministic
under `VISTA_BACKEND=mock` so the loop is demoable with zero network.

---

## 2. Per-step optimizations

Tier legend: **refine** = additive to existing component · **new** = net-new screen/stage.

### 01 · Welcome — *refine*
- **Warm-start prompt chips** under the input ("Great morning light", "A place to host",
  "Walkable") — kills blank-input anxiety, teaches what to say.
- **Returning-user recognition:** if mem0 has the user, greet by name and offer
  "keep going" vs "things changed" — skips the interview for repeat visits.
- **Ambient golden-hour motion** behind the headline (slow Ken-Burns interior) to set the
  cinematic tone the tour pays off.

### 02 · Getting to Know You — *new stage*
- **Short adaptive interview** — one question at a time, never a form. ~5 questions: who's
  moving, what a great Saturday looks like, bright vs cozy, deal-breakers, where life centers.
- **Chips + free text** per question; questions **branch** on answers (mention a dog → ask
  about yard/walks).
- **Live re-rank panel** under the question: candidate homes reorder as you answer (§1).
- **Skippable & resumable** — never gates the experience; deepens the profile over time.
- Progress count ("2 of 5") keeps it finite and short.
- *Open decision:* distinct gated stage vs woven into the chat. Recommend **distinct but
  skippable** for v1 (clearer "it's learning about me" beat), revisit after testing.

### 03 · Conversation + Memory Rail — *refine* (rail stays SACRED, per design 05)
- **"Saved to memory" in motion:** extracted fact animates from the bubble into the rail.
- **Confirmable / editable memories:** tap to confirm, edit, remove (also cleans mem0 data).
- **Readiness indicator:** what VISTA still needs (budget · area · a must-have · a taste cue)
  so the chat has a finish line.
- **Stated vs inferred** mark on each memory — honest provenance for the memory layer.

### 04 · Taste Profile — *new screen* (promote the style spec; biggest UX gap)
- Render the locked `style_spec` (CLAUDE.md §4 / `/specs/*.json`) as a designed
  **"taste passport"**: aesthetic name, palette, materials, furniture vocabulary, lighting mood.
- **Nudge controls:** warmer/cooler, more/less ornate, lighter/darker — user co-authors the
  spec before homes are found (creates investment; the spec is already the A↔B contract).
- **Provenance:** "built from your conversation + N mood boards."

### 05 · Recommendations — *refine*
- **Lead with the "why you," not the price** — match reasoning is the headline.
- **Curated, honest & LIVE:** "Three homes that fit everything"; one-line tradeoff each;
  the set re-ranks and re-explains as the conversation reveals more (carries §1 through discovery).
- **Story over score:** ticked met / loose unmet must-have chips tied back to the rail. No %.
- **Tease the restyle early:** tiny before/after peek on the card.

### 06 · Listing Detail — *new screen*
- Gallery + specs + neighborhood + expanded "why this fits you." Gives the home weight so the
  transformation feels meaningful.
- **One hero CTA — "See this home in your style"** (the single most important button in the
  product) gets a dedicated stage, not a card footer.
- *Tradeoff:* design 05 skipped this for demo speed. Can ship as lightweight expand-in-place
  if velocity matters more than depth.

### 07 · Generating — *refine* (`FakeLiveLoading`, design 05)
- **Narrate with the user's ACTUAL taste:** swap generic "applying your palette" for the
  spec's real words — "Bringing in walnut and brushed brass… warming the light to golden hour."
- **Bloom the real room:** start from the dim original photo, let warmth + palette bloom over
  it as stages progress. Loading becomes a preview of the payoff.

### 08 · Tour + Slider — *refine* (the hero; slider stays SACRED)
- **Slider-first, video second:** lead each room with the draggable before/after (the
  credibility proof + most tactile moment); offer the video as "play the full tour."
- **Per-room taste chips:** surface which of *your* cues shaped each room (ties magic → rail).
- **Elevate "compare aesthetics":** make the Jake⇄Pablo swap a deliberate split-screen /
  one-tap morph, not a hidden topbar toggle. One house, two souls = the personalization proof.
- **Save & share the tour:** turn the one-time wow into retention/virality.
- **Sticky proof line:** keep "Same windows. Same walls. Your decor." visible during the slide.

---

## 3. Three whole-experience directions

Different answers to "what is VISTA fundamentally?" — pick the bet you believe.

| Dir | Thesis | Best for | Tradeoff |
|---|---|---|---|
| **A · The Concierge** | the chat IS the app; everything unfurls in one continuous conversation, rail always present | personal, human, continuous relationship; lowest risk, most coherent with what's built | chat-first can feel slow; wow lives deep in the thread |
| **B · The Taste Studio** | the taste passport is a living hub you return to; listings/tours generate *from* it | making personalization the explicit product; return visits; seller-side taste-graph story | more app-like, less magical-conversation; bigger build |
| **C · The Cinema** | restyle-first; minimal chat seeds taste, then full-bleed cinematic tour; slider/compare are the centerpiece | demo impact, emotional pull, shareability | risks under-selling the "knows you" intelligence |

**Recommended hybrid:** Concierge *way in* (A) → Taste Studio *hub* (B, also unlocks the
seller-side taste-graph business) → Cinema *payoff* (C) for the hero tour. Concretely: the
current flow **plus** the up-front interview that learns & re-ranks, a real Taste Profile
screen, a Listing Detail moment, and a rebuilt slider-first Tour.

---

## 4. Adopting the VISTA design system (incremental)

The design-system project formalizes the app's theme into tokens + components. The app's
current flat tokens (`app/src/styles.css`) map 1:1 onto the systematized scale — adopt
gradually, no rewrite required:

| app/src/styles.css | design-system token | note |
|---|---|---|
| `--sand` `#f3eee7` | `--bg-page` / `--sand-100` | page background |
| `--sand-deep` `#e8e1d5` | `--surface-deep` / `--sand-200` | sunken surfaces |
| `--card` `#fffdf9` | `--surface-card` / `--paper` | raised card |
| `--ink` `#2b2722` | `--text-primary` / `--ink-900` | body text |
| `--ink-soft` `#6f6557` | `--text-secondary` / `--ink-600` | secondary text |
| `--clay` `#a9714b` | `--accent` / `--clay-500` | primary action |
| `--clay-deep` `#8c5a39` | `--accent-hover` / `--clay-700` | hover/pressed |
| `--moss` `#a7b5a0` | `--match` / `--moss-300` | "why this fits you" |
| `--line` `#ddd4c6` | `--border-hairline` / `--sand-300` | hairlines |
| `--radius` `14px` | `--radius-md` | the brand radius |
| `--shadow` | `--shadow-sm` | the signature soft warm shadow |
| `--serif` Fraunces | `--font-serif` | brand voice |
| `--sans` system stack | `--font-sans` | intentional system UI |

New components introduced by this doc and available in the design system:
`InterviewQuestion` (02), `TastePalette` / Taste Profile screen (04), `MemoryRail` (sacred),
`CompareSlider` (sacred), `ListingCard`, `GeneratingDots`, plus core primitives
(`Button`, `Input`, `Chip`, `Badge`, `Card`, `Avatar`, `SegmentedControl`).

---

## 5. Build order (suggested)

1. **§1 active-learning loop** in `agent/core.py` (+ mock twins) — the thesis change; everything
   else renders its output.
2. **02 Getting to Know You** screen wired to `next_question`/`record_answer`, with the live
   re-rank panel.
3. **04 Taste Profile** screen (reads `style_spec`; nudge controls write back).
4. **05 Recommendations** live re-rank + honest framing (small delta over existing `ListingCards`).
5. **08 Tour** slider-first rebuild + elevated compare-aesthetics.
6. **06 Listing Detail** + **01/03/07 refinements** as polish.

Acceptance mirrors design 05 §6: every step demoable on MOCK backend first, graceful asset
fallback throughout, full path clicked end-to-end before any live wiring.
