# Design 00 — Engineer B Overview & Architecture

> Scope: `/agent` (Python) + `/app` (React/Vite) + `/deck`. This doc is the index; each
> component has its own design file. Read this first.

## 0. Guiding principle for a 24h build

**Mock-first behind interfaces.** No API keys are live yet. Every external dependency
(Nebius LLM, mem0, Tavily, Composio) is reached through one thin client module with a
single swappable backend. Each client ships a `MOCK` implementation that returns
deterministic canned data and a `LIVE` implementation that calls the real API. A single
env flag (`VISTA_BACKEND=mock|live`) or per-client flag selects which. This means:

- The whole demo path is clickable from hour 1, before any key exists.
- Switching to live is a one-line change per client, not a refactor.
- On stage we can run `mock` for anything flaky and still tell the real story.

The mock is not throwaway — it **is** the on-stage fallback (see ENGINEER_B.md failure
playbook: "demo conversation is semi-scripted… listing choice pinned").

## 1. The two contracts that must not move

1. **Style Spec** (`/specs/schema.json`) — B generates, A consumes verbatim. Frozen at H4.
   Already exists: `pablo_v1.json`, `jake_v1.json`. See `02-style-spec-generator.md`.
2. **Asset filename convention** — A writes, the app reads. **This is the only coupling
   between the app and the pipeline.** Format (from CLAUDE.md §7):
   ```
   <listing_id>__<room>__<profile_id>.{png,mp4}
   ```
   - Restyled still:  `assets/listings/hero/restyled/<profile_id>/hero__<room>__<profile_id>.png`
   - Tour video:      `assets/listings/hero/video/<profile_id>/tour.mp4`
   - Original (raw):  `assets/listings/hero/raw/hero__<room>.jpg`
   The app must degrade gracefully when a file is missing (show placeholder), so B's UI
   work never blocks on A's renders landing.

## 2. Component map (each has a design doc)

| Doc | Component | Owns | Deliverable |
|---|---|---|---|
| `01-mem0-and-profiles.md` | Profiles + memory layer | profile schema, both personas, mem0 client | B1 |
| `02-style-spec-generator.md` | Profile → locked spec | `agent/style_spec.py`, `make spec` | B1 |
| `03-listings-tavily.md` | Listing discovery + index | `agent/listings.py`, `listings.json` | B2 |
| `04-agent-loop.md` | Conversation orchestration | `agent/loop.py`, Nebius client | B3 |
| `05-app.md` | React frontend | chat, context panel, cards, slider, player | B4, B5 |
| `06-deck-and-demo.md` | Pitch + choreography | `/deck`, 2-min script | B6, B7 |

## 3. Repo layout B will create

```
/agent
  config.py            # env loading, VISTA_BACKEND flag, paths
  clients/
    nebius.py          # LLM chat completion — MOCK | LIVE
    mem0_client.py     # memory read/write/search — MOCK | LIVE
    tavily_client.py   # listing search/extract — MOCK | LIVE
    composio_client.py # mood-board import — MOCK | LIVE
  profiles/
    pablo.json         # mem0 seed: taste, life situation, mood refs, constraints
    jake.json          # mem0 seed (real persona — Jake)
  style_spec.py        # profile JSON -> /specs/<id>.json (validates vs schema)
  listings.py          # Tavily discovery -> assets/listings/index.json
  loop.py              # terminal agent: recall -> recommend -> "show my version"
  mocks/               # canned LLM turns, canned mem0 facts, canned listings
/app                   # Vite + React (see 05-app.md)
/design                # these docs
Makefile               # `make spec`, `make seed`, `make agent`, `make app`
.env.example           # every key, documented, no values
```

## 4. The personas (both real)

CLAUDE.md framed Profile 2 as a "deliberately contrasting persona." It is in fact **Jake's
real profile** (`jake_v1`). We keep the contrast (warm mid-century vs. bright Scandinavian
minimalist) but both are real people — which strengthens the "two real humans, one house"
proof. Profile seeds live in `agent/profiles/`; specs already frozen in `/specs/`.

| profile_id | Person | Aesthetic |
|---|---|---|
| `pablo_v1` | Pablo (real) | warm mid-century modern |
| `jake_v1` | Jake (real) | bright Scandinavian minimalist |

## 5. Build order (maps to TIMELINE.md)

1. `config.py` + all four clients as **MOCK** + `.env.example` (foundation; ~H0–H2).
2. `style_spec.py` + `make spec` → regenerate the two frozen specs from profile seeds (B1).
3. `listings.py` → `index.json` + hero photos to `/assets/raw` (B2 — **A-blocking, do early**).
4. `loop.py` terminal agent on mock Nebius/mem0 (B3).
5. Swap clients MOCK→LIVE as keys arrive (no structural change).
6. App shell → tour view (B4, B5).
7. Deck + rehearsals (B6, B7).

## 6. Open decisions (resolve at the noted gate)

- Nebius model: Llama 3.3 70B vs Qwen 2.5 72B — pick whichever responds cleaner on the
  recommendation prompt; default Llama 3.3 70B. Decide when key is live, latest by H8.
- Composio path: Pinterest vs Notion vs pre-loaded JSON mood board — see `01`. Default to
  pre-loaded JSON if either fights us by H8 (playbook).
- mem0 live vs mock on stage: decide at H21 rehearsal based on latency/flakiness.
