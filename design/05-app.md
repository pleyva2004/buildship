# Design 05 — React App (B4, B5)

> Four elements, nothing else: chat panel, context panel, listing cards, tour view
> (player + original-vs-restyled slider). The slider and context panel are SACRED
> (failure playbook: cut listing cards before touching either).

## 1. Stack & constraints

- Vite + React, plain CSS (or Tailwind if scaffolded in <10 min — no design-system yak-shaving).
- No router needed: one screen with view states (`chat` → `loading` → `tour`).
- No state library: `useState`/`useReducer` + one context for `profile_id`.
- Assets served statically: symlink or copy `/assets` into `app/public/assets` at dev start
  (`make app` handles it). The app reads files ONLY by the filename convention.
- Backend: the 3-endpoint API from design 04. Dev proxy in `vite.config.ts`.

## 2. Layout

```
┌────────────────────────────────────────────────────────────┐
│  VISTA            [profile switch: Jake ▾]                 │
├───────────────────────────────┬────────────────────────────┤
│                               │  WHAT VISTA KNOWS ABOUT ME │
│   chat thread                 │  ┌ life situation ───────┐ │
│   (bubbles, listing cards     │  │ • WFH 3 days/week     │ │
│    inline as they're          │  │ • relocating: Austin  │ │
│    recommended)               │  ├ taste ────────────────┤ │
│                               │  │ • bright & airy   ⚡   │ │
│                               │  │ • pale woods      ⚡   │ │
│   [input ........... send]    │  ├ mood boards ──────────┤ │
│                               │  │ • Scandinavian living │ │
│                               │  │   (via Composio)      │ │
└───────────────────────────────┴────────────────────────────┘
     ⚡ = memory recalled THIS turn (pulse animation)
```

Tour view replaces the chat column (context panel stays — it's the story):

```
┌───────────────────────────────┬────────────────────────────┐
│  ◄ back   YOUR TOUR — Jake's style                         │
│  ┌─────────────────────────┐  │  context panel persists    │
│  │  tour.mp4 player        │  │                            │
│  └─────────────────────────┘  │  + style spec chip strip:  │
│  ROOMS                        │  palette swatches •        │
│  [living][kitchen][office]…   │  materials • aesthetic name│
│  ┌─────────────────────────┐  │                            │
│  │ ORIGINAL ⇆ RESTYLED     │  │  [See Pablo's version →]   │
│  │ (drag slider per room)  │  │                            │
│  └─────────────────────────┘  │                            │
└───────────────────────────────┴────────────────────────────┘
```

## 3. Components (build in this order)

| Component | Notes | Tier |
|---|---|---|
| `ContextPanel` | `GET /context/:id`, grouped by category; pulse items in last `recalled` | sacred |
| `CompareSlider` | original vs restyled still, drag divider. ~40 lines: two absolutely-positioned `<img>`, `clip-path` on top one, pointer events. **No library** | sacred |
| `ChatThread` + `Composer` | bubbles, `POST /chat`, render action results inline | core |
| `ListingCards` | 2–3 cards from `/listings`; hero card has "Show me my version" CTA | cuttable→static |
| `FakeLiveLoading` | ~8s staged loading: "Reading your profile… → Applying your palette… → Rendering rooms…" with the profile's actual palette hexes animating. Sells "live generation" | core |
| `TourPlayer` | `<video controls autoplay>` of `assets/listings/hero/video/<profile>/tour.mp4` | core |
| `ProfileSwitch` | Jake ⇄ Pablo. Re-fetch context, swap all asset paths. THE reveal moment | core |

## 4. Asset resolution (the only A↔B runtime coupling)

```ts
const raw      = (room: string) => `/assets/listings/hero/raw/hero__${room}.jpg`
const restyled = (room: string, p: string) => `/assets/listings/hero/restyled/${p}/hero__${room}__${p}.png`
const tour     = (p: string) => `/assets/listings/hero/video/${p}/tour.mp4`
```

- Every `<img>`/`<video>` has an `onError` fallback → branded placeholder ("render landing
  soon") so the app is demoable at ANY point before A's assets arrive. B4 (H15) is accepted
  with placeholders; B5 (H18) swaps in real files with zero code change.
- Room list comes from `index.json` `rooms[]` — never hardcoded.

## 5. Demo-critical behaviors

1. **Fake-live loading**: triggered by GENERATE_TOUR action. Fixed 8s, then plays the
   cached mp4. Never actually calls anything — pure theater, by design (CLAUDE.md §2.1).
2. **Slider proof**: default position 50%, drag handle obvious. Original on the left.
   This is the "same real house" proof — it must feel tactile in rehearsal.
3. **Second-profile reveal**: one click swaps everything (context panel, palette chips,
   restyles, tour). Back-to-back contrast is the personalization proof.
4. **Recall pulse**: when `/chat` returns `recalled` facts, those context-panel rows pulse.
   Judges see memory being *used*, not just listed.

## 6. Acceptance

- **B4 (H15)**: chat → recommendation cards → "show my version" → loading → placeholder
  tour view, fully clickable on MOCK backend.
- **B5 (H18)**: real restyled stills in sliders, real tour.mp4 playing, both profiles
  switchable. Full demo path clicked end-to-end twice on the demo machine (H18 gate).
- Graceful when any asset file is missing (placeholder, no broken-image icons, no crashes).
