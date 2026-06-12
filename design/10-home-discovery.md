# Design 09 — Home Discovery (the chat that finds homes)

> The discovery surface: VISTA shows a small curated set of homes inside the conversation,
> explains why each fits *you*, and re-ranks live as you react. Output: the user opens a
> listing → "See it in your style" → tour (design 07 §08).
>
> **Core principle:** a portal's product is the *grid* (infinite supply, user filters). VISTA's
> product is the *conversation*, and curation is the value. The cards are VISTA **showing you a
> few things it chose and telling you why** — not search results. Every answer below follows.
>
> **Visual source of truth:** the working prototype at `experiences/home-discovery/index.html`
> (design-system project), which runs the real weighted-scoring model described in §4. This doc
> is the integration spec; prototype wins on look/feel, this doc wins on contracts.

---

## 1. The four decisions

| Question | Decision |
|---|---|
| **How many at once?** | **3** — one **lead pick + two alternates**. Not a grid. "See a few more" reveals ~2 more on demand. Never infinite scroll. |
| **How ranked?** | By **fit to the profile** (hard must-haves filter; taste/life signals weight). Expressed as **story, never a score** — no "94% match". |
| **How styled?** | Inline in the thread as VISTA's *response*. Lead = large (photo + body), alternates = compact rows. Each leads with **"why you"** chips + an honest **tradeoff**; price/specs secondary; restyle teaser present. |
| **How do responses change it?** | Reactions + natural language → **re-rank in place** (taste nudges) or **re-fetch/widen** (constraint changes), **always narrated**. The memory/weight rail reflects every signal. |

**Anti-patterns (do not build):** infinite grid, match percentages, filter chrome (sliders/dropdowns — you *talk*, you don't filter), >3 cards per turn, silent re-ranking.

---

## 2. Layout

```
┌─────────────────────────────────────────────┬─────────────────────────┐
│ topbar: VISTA · "Finding your home" · 📍area                          │
├─────────────────────────────────────────────┼─────────────────────────┤
│  THREAD (conversation + curated card sets)   │  WHAT VISTA IS          │
│   • agent intro line                         │  WEIGHTING              │
│   • ▸ LEAD card (photo + why-you + actions)  │   yard ▓▓▓▓▓▓░ ↑raised   │
│   • ▸ alternate · ▸ alternate                │   light ▓▓▓▓▓░░          │
│   • "see a few more"                         │   walkable ▓▓▓▓░░        │
│   • user reaction → narrated re-rank → new set│  Saved ♥ …              │
├─────────────────────────────────────────────┤                         │
│ refine chips + composer ("tell VISTA…")      │                         │
└─────────────────────────────────────────────┴─────────────────────────┘
        flexible (minmax(0,1fr))                      312px
```

- Thread is the scroll container — **must** be `min-height:0` inside a `grid-template-rows: minmax(0,1fr)` split, or it grows instead of scrolling (learned in the prototype).
- `< 880px`: single column, rail hidden (mobile surfaces the rail as a slide-up).
- New card set auto-scrolls into view after each re-rank.

---

## 3. The card (anatomy)

**Lead** (`grid: photo 240px | body`) and **Alternate** (`grid: photo 120px | body`, denser) share parts:

- **Photo**: real listing hero. Lead carries the **"See it in your style"** restyle teaser + a status **badge** (`Top pick for you` / `Moved up` / `New find`). ♥ save control top-right.
- **Body**: name (serif) + price (serif, right), neighborhood · beds/baths/sqft (muted),
  then **why-you chips** (moss, ✓-prefixed, tied to weighted features), then **one tradeoff chip**
  (`~ smaller yard`), then **actions**.
- **Actions**: lead = `See it in your style` (primary) + `View home` + `Not for me`. Alternate = `View home` + `Not for me`.

Chip selection logic (from prototype, §4): why-you = the user's **top-weighted features this listing
scores high on**; tradeoff = the **most-weighted priority it's weakest on** (omit if none material).

---

## 4. Ranking model (the engine)

Each listing has a feature vector `f[k] ∈ [0,1]` over priorities `k` (light, walkable, yard, value,
character, open-kitchen, quiet, …). The user has a **weight vector** `w[k]`, seeded from the taste
profile (design 08) and nudged by reactions.

```
score(listing) = Σ_k f[k]·w[k]  /  Σ_k w[k]      // weighted, normalized
rank          = listings, hard-filters applied, sorted by score desc, minus dismissed
visible       = rank.slice(0, showMore ? 5 : 3)
```

- **Hard must-haves** (e.g. min beds, max price, required area) are **filters**, not weights —
  applied before scoring. Soft preferences are weights.
- **Reaction → weight delta**: a positive nudge bumps `w[k]` (prototype: `+0.55`, capped); `Not for me`
  down-weights the dismissed listing's salient features and removes it.
- **No score is ever shown.** The rail visualizes *weights* (priorities), not listing scores.

**Two impact modes**

| Trigger | Behavior | UI |
|---|---|---|
| Taste nudge (brighter, more character, react to a card) | **re-rank in place** — re-score current pool, reorder | cards animate, `Moved up`/`New find` badges, rail bars shift |
| Constraint change (new neighborhood, new budget, more beds) | **re-fetch / widen** — new candidate pool | a distinct "widening the search…" beat, then a fresh set |

> Open decision: prototype models only re-rank-in-place. Recommend adding the **re-fetch beat** for
> constraint changes so the user understands *new* homes appeared (vs. a reshuffle).

---

## 5. Agent contract

Extends design 08's `AgentSession`. All MOCK-first (CLAUDE.md §7) — the prototype's static model is the mock.

```ts
type Listing = {
  id: string; name: string; hood: string; price: string; spec: string;
  hero_photo: string;                 // asset path (see CLAUDE.md asset convention)
  features: Record<string, number>;   // f[k] ∈ [0,1]
};

type RankedSet = {
  intro: string;                      // VISTA's framing line for the set
  visible: string[];                  // ordered listing ids (lead first)
  badges: Record<string,'top'|'moved'|'fresh'>;
  weights: Record<string,number>;     // current priorities (for the rail)
};
```

| Method | Returns | Notes |
|---|---|---|
| `discover(session)` | `RankedSet` | initial curated set from the profile |
| `react(session, {listingId, kind})` | `{ narration, set: RankedSet }` | kind = `more_like_this`\|`not_for_me`\|`save` |
| `refine(session, utterance)` | `{ narration, mode:'rerank'\|'refetch', set: RankedSet }` | NL or chip; classifies taste-nudge vs constraint |

- **`narration` is required** on every change — name the shifted priority + what moved
  ("weighting outdoor space higher · Mueller moves to the top, Circle C comes into the mix").
- `refine` must classify the utterance: weight-nudge → `rerank`; constraint → `refetch`.
- Writes notable signals to mem0 (feeds the memory rail, design 07 §03).

---

## 6. Interaction inventory

| Action | Signal | Result |
|---|---|---|
| `See it in your style` (lead) | strong intent | → Listing Detail / Generating (design 07 §06–07) |
| `View home` | interest | → Listing Detail |
| ♥ Save | positive | adds to Saved (rail); mild up-weight |
| `Not for me` | negative | dismiss + down-weight; backfill next-best with `New find` |
| Refine chip | targeted nudge | re-rank, narrated |
| Free-text refine | nudge or constraint | re-rank or re-fetch, narrated |
| `See a few more` | wants range | reveal ranks 4–5 (still bounded) |

Disable inputs during the brief "thinking/widening" beat; keep reduced-motion safe (no infinite loops).

---

## 7. Copy & tone

- Set intros frame curation + honesty: *"3 homes that fit everything so far — my top pick first."*
- Narration is warm, first-person, names the change: *"Got it — weighting walkability higher. …"*
- Tradeoffs are stated plainly, never hidden: *"~ smaller kitchen", "~ busier street."*
- No scores, no emoji, sentence case (matches app voice; design 07 §ContentFundamentals).

---

## 8. Edge cases

- **Over-constrained / nothing fits everything** → show the closest + name what VISTA would relax
  ("Nothing hits all five. Closest is X — I'd loosen the yard or stretch budget ~$30k. Want me to?").
- **Pool exhausted** → "That's the strong matches in this area — widen the area or budget?"
- **Rapid reactions** → debounce; disable during re-rank beat.
- **All dismissed** → re-fetch / suggest a constraint change.
- **Returning user** → seed weights from saved profile; resume the prior set.

---

## 9. Design tokens

Built on `styles.css`. Key usage: `--accent` (lead actions, user bubbles, weight-bar fill, badges) ·
`--match`/`--match-text`/`--match-wash` (why-you ✓ chips) · `--surface-deep` (tradeoff chips) ·
`--surface-card` + `--shadow-sm`/`--shadow-md` (cards) · `--font-serif` (names, prices) ·
`--radius-md` (cards) / `--radius-pill` (chips, buttons) · `--ease-soft` + `--dur-*` (motion).

**Motion gotcha (shared with design 08):** entrance animations are **transform-only** with the
resting state fully visible — never `opacity:0→1` with `fill:both`, which traps elements invisible
under React re-renders. **Layout gotcha:** the scrolling thread needs `min-height:0` AND a grid row
of `minmax(0,1fr)`, or it expands to fit content instead of scrolling.

---

## 10. Acceptance

- **A (mock):** initial curated set of 3 (lead + 2); refine chips + reactions re-rank live with
  narration; weight rail updates; `Moved up`/`New find` badges; dismiss backfills; save works;
  "see a few more" bounded; no scores anywhere; thread scrolls.
- **B (live):** wired to `discover`/`react`/`refine` over the real candidate pool + mem0; `refine`
  correctly classifies rerank vs refetch with the widening beat; graceful over-constrained + empty states.

---

## 11. Build order

1. Static curated set on the mock scoring model — lead + alternates, why-you/tradeoff chips. ✅ (prototype)
2. `react` + `refine` (rerank mode) with narration + weight rail. ✅ (prototype)
3. `refine` constraint classification + **re-fetch/widen** beat.
4. Hard-filter layer (beds/price/area) distinct from soft weights.
5. Wire to real listings + mem0; over-constrained/empty states.
6. Handoff to Listing Detail / "See it in your style".
