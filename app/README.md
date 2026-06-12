# /app — VISTA frontend (React + Vite, Engineer B)

One page, no router. The view spine is the demo script (design 08 — three new stages
in brackets are skippable / reachable from the chat, never gates):

```
WELCOME ──► [GETTING TO KNOW YOU] ──► CHAT (+ memory rail) ──► [TASTE PASSPORT]
        ──► recommendations inline ──► [LISTING DETAIL] ──► [GENERATING ~8s] ──► TOUR
```

The welcome input doesn't navigate to results — submitting **becomes the first chat
message**. "Things changed — let's catch up" enters the adaptive interview; "keep going"
skips straight to the conversation (returning-user recognition). Discovery happens
inside the conversation (listing cards render inline from a `recommend` action); the
tour is "generated" behind a theatrical 8-second overlay and served from pre-rendered
local assets.

## The active-learning loop (design 08 §1)

Every interview answer (and some chat messages) does three things at once:

1. extracted facts animate into the memory rail (with stated/inferred provenance),
2. the 5-listing candidate pool **re-ranks via a pure client-side scoring pass**
   (`mock/interview.js` — never a network call), and
3. the re-rank panel animates the reorder: motion + "↑ moved up" + met/unmet
   must-have chips. **No numeric match score anywhere** — story, not percentage.

`api.js` calls the agent surface first (`/api/interview/next`, `/api/interview/answer`,
`/api/memory/*`) and falls back to the deterministic mock twin on any failure. The
backend landed (design 09 step 1, `agent/interview.py`): in mock mode the server is an
exact parity port of the local twin; in live mode questions are generated adaptively on
Nebius and facts are written to real mem0 — with zero frontend changes, as designed.

## Resilience model (the stage insurance)

Two independent fallback layers — the app demos end-to-end with **zero backend and
zero asset files**:

1. **`api.js`** calls the FastAPI bridge (`/api/*`, proxied to :8001 by Vite). On ANY
   failure it transparently falls back to the local mock (`mock/brain.js` +
   `mock/data.js` + `mock/interview.js`), which returns byte-compatible shapes.
2. **`assets.js`** consumers degrade gracefully: missing images swap to a branded SVG
   placeholder (never a broken-image icon); a missing tour video collapses to a
   "landing soon" notice while the sliders keep working; the restyle "peek" on the
   hero card hides itself (tag included) if the restyled still doesn't exist.

## Source map

| File | What |
|---|---|
| `src/App.jsx` | The spine: view state (welcome \| interview \| chat \| taste \| detail \| tour), profile switcher, interview answers + rank order, memory hygiene handlers, generate overlay trigger |
| `src/api.js` | `chat / getContext / resetSession` + `nextQuestion / recordAnswer / rankListings` + `updateMemory / deleteMemory` — live API with baked-in mock fallback |
| `src/assets.js` | **The only A↔B runtime coupling** — asset path builders following the filename convention, plus `PLACEHOLDER` |
| `src/components/Welcome.jsx` | Act 1 — invitation input that becomes the chat; warm-start chips, returning-user row, ambient Ken Burns |
| `src/components/InterviewView.jsx` | 02 · Getting to Know You — the 08b experience: intro Talk/Type choice, phases (speaking/ask/listening/thinking/done), orb + waveform, hold-to-speak voice answers via mic button OR held spacebar (MediaRecorder → `/api/voice/transcribe`, auto-fallback to text), text thread + chips, the always-asked final catch-all question, and the "Your taste, taking shape" panel (palette, aesthetic, grouped facts incl. the open "Also worth knowing" lane) |
| `src/components/RerankPanel.jsx` | The learn→re-rank proof — animated pool reorder, met/unmet chips, "↑ moved up" |
| `src/components/ChatView.jsx` | Conversation column; agent bubbles may carry inline listing cards and "✓ Saved to memory" fact chips |
| `src/components/ListingCards.jsx` | Curated cards, why-you headline first (price demoted), one honest tradeoff chip, restyle peek, sorted by learned rank; click opens Listing Detail |
| `src/components/ListingDetailView.jsx` | 06 · gallery + specs + neighborhood + expanded "why this fits you"; the **"See this home in your style"** CTA on its own stage |
| `src/components/TasteProfileView.jsx` | 04 · the taste passport — spec rendered as a designed object with provenance + warmer/cooler · simpler/ornate · darker/lighter nudge controls (pure hex math, exports `applyNudges`). Accepts a `spec` override: after an interview, App passes the spec distilled from THAT conversation (`/api/interview/finish`), so the passport is personal, not seeded |
| `src/components/MemoryRail.jsx` | The "knows you" proof — taste card (opens the passport) + grouped memories with stated/inferred/imported marks, hover confirm/edit/remove, readiness indicator; recalled facts pulse, fresh facts slide in. `constraint` memories are intentionally not rendered |
| `src/components/GeneratingOverlay.jsx` | The ~8s loading moment — narrated with the spec's ACTUAL words while the real room photo blooms from dim to bright |
| `src/components/TourView.jsx` | Payoff, slider-first: sticky proof line, per-room slider + taste cue chips, Jake ⇄ Pablo split-screen compare, save/share, video demoted to "play the full tour" |
| `src/components/CompareSlider.jsx` | The proof component — ~40-line pointer-events wipe, no library |
| `src/mock/data.js` | `SPECS / MEMORIES / LISTINGS / ROOM_LABELS / ROOM_CUES` — mirrors the agent API and `assets/listings/index.json`; 5-listing pool with `traits` for scoring. Includes `guest_v1` — a cold-start profile with zero seeded memories for testing without persona data |
| `src/mock/brain.js` | Canned conversation turns mirroring `agent/mocks/turns.json`, generate-keyword backstop, naive fact extraction |
| `src/mock/interview.js` | Deterministic mock twin of the agent's `next_question / record_answer / rerank` surface; ties break price-ascending so the right home visibly climbs |

## Conventions

- Memory categories use the agent's canonical names
  (`life_situation | taste | mood_board | constraint`); the rail maps them to labels.
- `TourView` re-renders entirely off `profileId` — switching profiles in the top bar
  after a tour is the back-to-back personalization proof; the in-view split-screen
  compare is the deliberate version of the same beat.
- Asset paths come exclusively from `assets.js`; never hand-build a path in a component.
- Interview session state (`answers`) lives client-side and is passed to the agent on
  every call — the backend surface can stay stateless.

## Run

```bash
cd app && npm install   # once
make app                # from repo root — symlinks /assets into app/public, runs Vite on :5173
```

Vite proxies `/api` → `http://localhost:8001` (`vite.config.js`); run `make serve` (or
`serve-live`) alongside for the real agent, or run nothing and let the mock take over.

Design docs: [design/05-app.md](../design/05-app.md) ·
[design/08-flow-optimizations.md](../design/08-flow-optimizations.md).
