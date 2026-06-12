# /app — VISTA frontend (React + Vite, Engineer B)

One page, no router. The view spine is the demo script:

```
WELCOME ──► CHAT (+ memory rail) ──► [GENERATING ~8s overlay] ──► TOUR (+ rail)
```

The welcome input doesn't navigate to results — submitting **becomes the first chat
message**. Discovery happens inside the conversation (listing cards render inline from
a `recommend` action); the tour is "generated" behind a theatrical 8-second overlay and
served from pre-rendered local assets.

## Resilience model (the stage insurance)

Two independent fallback layers — the app demos end-to-end with **zero backend and
zero asset files**:

1. **`api.js`** calls the FastAPI bridge (`/api/*`, proxied to :8001 by Vite). On ANY
   failure it transparently falls back to the local mock (`mock/brain.js` +
   `mock/data.js`), which returns byte-compatible shapes.
2. **`assets.js`** consumers degrade gracefully: missing images swap to a branded SVG
   placeholder (never a broken-image icon); a missing tour video collapses to a
   "stills below are live" notice while the sliders keep working.

## Source map

| File | What |
|---|---|
| `src/App.jsx` | The spine: view state, profile switcher (Jake ⇄ Pablo in the top bar), message/recall state, generate overlay trigger |
| `src/api.js` | `chat / getContext / resetSession` — live API with baked-in mock fallback |
| `src/assets.js` | **The only A↔B runtime coupling** — asset path builders following the filename convention, plus `PLACEHOLDER` |
| `src/components/Welcome.jsx` | Act 1 — invitation input that becomes the chat |
| `src/components/ChatView.jsx` | Conversation column; agent bubbles may carry inline listing cards |
| `src/components/ListingCards.jsx` | Curated cards with per-profile match-reasoning chips; hero card carries the **"See this home in your style"** CTA |
| `src/components/MemoryRail.jsx` | The "knows you" proof — taste card (palette, materials) + grouped memories (Life / Taste / Inspiration / Must-haves); facts recalled this turn pulse. `constraint` memories are intentionally not rendered |
| `src/components/GeneratingOverlay.jsx` | The ~8s loading moment — pure theater by design: narrated stages + the profile's actual palette animating |
| `src/components/TourView.jsx` | Payoff: tour video player (per profile) + per-room original ⇄ restyled sliders |
| `src/components/CompareSlider.jsx` | The proof component — ~40-line pointer-events wipe, no library |
| `src/mock/data.js` | `SPECS / MEMORIES / LISTINGS / ROOM_LABELS` — mirrors the agent API and `assets/listings/index.json` |
| `src/mock/brain.js` | Canned conversation turns mirroring `agent/mocks/turns.json`, including the generate-keyword backstop |

## Conventions

- Memory categories use the agent's canonical names
  (`life_situation | taste | mood_board | constraint`); the rail maps them to labels.
- `TourView` re-renders entirely off `profileId` — switching profiles in the top bar
  after a tour is the back-to-back personalization proof.
- Asset paths come exclusively from `assets.js`; never hand-build a path in a component.

## Run

```bash
cd app && npm install   # once
make app                # from repo root — symlinks /assets into app/public, runs Vite on :5173
```

Vite proxies `/api` → `http://localhost:8001` (`vite.config.js`); run `make serve` (or
`serve-live`) alongside for the real agent, or run nothing and let the mock take over.

Design doc: [design/05-app.md](../design/05-app.md).
