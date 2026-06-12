# Design 10b — Home Discovery: integration spec

> Companion to [10-home-discovery.md](10-home-discovery.md) (Jake's doc — wins on
> look/feel and product decisions). This doc maps it onto the existing app/agent and
> records integration decisions. **The ranking engine question is PARKED** (unified
> scorer vs. RRF vs. retrieve→score→curate over a real catalog — discussion of
> June 12): everything below builds against the `RankedSet` contract, which insulates
> the UI from whichever engine lands behind it.

## 1. Where it lives

Discovery is the **chat view, evolved** — not a new spine stage. The thread IS the
conversation surface (design 10 §2); curated sets render inline as VISTA's responses,
exactly where `ListingCards` renders today. View states don't change:
`welcome → [interview] → CHAT/DISCOVERY → [detail] → [generating] → tour`.

## 2. Surface contract (engine-agnostic)

The UI consumes exactly design 10 §5's shapes (`Listing`, `RankedSet`,
`discover / react / refine`), served the same way as the interview surface:

| Route | Returns |
|---|---|
| `POST /api/discover` `{profile_id}` | `RankedSet` |
| `POST /api/discover/react` `{profile_id, listing_id, kind}` | `{narration, new_facts, set}` |
| `POST /api/discover/refine` `{profile_id, utterance}` | `{narration, mode, new_facts, set}` |

- Stateless-style like the interview (client passes its reaction history if needed);
  mock twin in `app/src/mock/discovery.js` is a port of the prototype's model; server
  mock mirrors it (twin parity test extends to discovery).
- **`new_facts` everywhere:** reactions and refines that reveal preferences flow
  through the SAME `save_memory`/`revise_memory` path as chat (design 09 §3.8) — a
  dismissal's *why* is stored at the trait level ("dismissed for price, not character"),
  and the rail's "✓ Saved to memory" chips fire here too.
- `narration` is mandatory on every change (10 §5). In live mode the agent writes it;
  mock uses the prototype's templates.

## 3. Components (new/changed)

| Component | What |
|---|---|
| `CuratedSet.jsx` (new) | One thread entry: intro line + LeadCard + two AltRows + "see a few more" |
| `LeadCard` / `AltRow` | Design 10 §3 anatomy: photo (badge, ♥, restyle teaser on lead), serif name/price, why-you chips, ONE tradeoff chip, actions |
| `ChatView.jsx` | Renders `CuratedSet` for `show_set` payloads; refine chips above the composer; disables input during the thinking/widening beat |
| `MemoryRail.jsx` | **Merged rail** (decision below): "What VISTA is weighting" bars + Saved ♥ block ABOVE the existing memory groups — one rail, one story |
| `ListingCards.jsx` | Retired in chat (superseded by CuratedSet); detail view unaffected |

Badges: `top` (first set) / `moved` (rerank) / `fresh` (backfill or widen). Dismiss →
card animates out, next-best backfills with `fresh`. All entrance motion transform-only
(10 §9); thread scroll container `min-height:0` + `minmax(0,1fr)` (10 §2 gotcha).

## 4. Decisions taken here

1. **One merged rail.** Weights + Saved sit atop memories in the existing MemoryRail
   rather than replacing it per-view. Rationale: the "knows you" continuity is the
   demo's spine; a reaction should visibly move a weight bar AND land a memory chip
   in one gesture. (10 §2's 312px rail = the same rail, new top blocks.)
2. **`Not for me` never down-weights blindly.** Live: the agent infers/asks the why
   and writes a trait-level fact; weights move only on the *named* reason. Mock: the
   prototype's salient-feature down-weight stands (deterministic). This guards the
   "dismissed the craftsman over price → penalized character" failure.
3. **Actions stay verbs the views already speak:** `View home` → ListingDetailView;
   `See it in your style` → GeneratingOverlay → Tour. No new navigation.
4. **Numbering:** Jake's doc = design 10 (his "09" collided with the interview
   engine doc); this spec = 10b.

## 5. Edge states (10 §8) — demo copy stubs

Over-constrained, pool-exhausted, and all-dismissed get the doc's copy verbatim as
mock narrations; live behavior follows the parked engine decision (a real retrieval
layer makes these genuine — see PARKED).

## 6. Build order (today)

1. `mock/discovery.js` — prototype model port (features, weights, react/refine-rerank,
   narration templates) + server mock twin + routes + parity test.
2. `CuratedSet`/`LeadCard`/`AltRow` + ChatView wiring + beats/badges/backfill.
3. Merged rail (weight bars + Saved).
4. Live narration + `new_facts` via the harness; refine classification (rerank vs
   refetch) — refetch lands with the engine decision.
5. Playwright pass + smoke tests + docs.

## PARKED (revisit after the UI lands)

Retrieve → score → curate over a real catalog; RRF fuses heterogeneous retrievers at
the *retrieval* layer only; weighted linear scoring stays at the *ranking* layer
(explainability — chips/narration derive from it); unify the interview's trait scorer
onto the same weight vector; expand `index.json` to a 12–15 listing catalog with
LLM-enriched feature vectors; inventory leaves the agent's system prompt in favor of
catalog-querying tools.
