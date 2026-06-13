# VISTA — personalized cinematic home tours

The AI knows the buyer. It surfaces real listings and renders a tour of the actual home
**restyled to their taste** — same rooms, same architecture, new decor. Full product
definition in [CLAUDE.md](CLAUDE.md); design docs in [/design](design/00-overview.md).

## Architecture

```
app (React/Vite) ──/api──► agent/server.py (FastAPI :8001) ──► agent/core.py (AgentSession)
                               routes = pure translation             │
agent/loop.py (terminal REPL) ───────────────────────────────────────┤
            ┌────────────────────────────────────────────────────────┴──┐
            │ MOCK (default): canned turns + <action> parse              │
            │ LIVE: OpenAI Agents SDK tool loop on Nebius (harness.py)   │
            │   tools: recall_memories · save_memory · revise_memory     │
            │   search_web_listings (Tavily) · whats_nearby (Composio)   │
            │   research_area · recommend_listings · generate_tour       │
            └─ clients: nebius · mem0 · tavily · composio ← MOCK|LIVE    ┘
```

The live path is a real tool-calling harness (design 07): the model itself calls
`recommend_listings` / `generate_tour` and the UI action comes out of the run context.
Live failure on any turn degrades to the deterministic mock turn — the demo never stalls.

Every external client (Nebius LLM, mem0, Tavily, Composio) is mock-first behind one
interface, selected by `VISTA_BACKEND=mock|live` (per-client override: `NEBIUS_BACKEND`,
`MEM0_BACKEND`, …). **Mock is the default and the on-stage fallback** — the entire demo
runs with zero keys and zero network. The React app additionally falls back to its own
local mock (`app/src/mock/`) if the API is unreachable.

## Sponsors — one journey, every sponsor load-bearing

The whole product is demonstrable in a single live session, and each sponsor below sits on
the critical path: pull any one and the buyer loses something they can feel — not just a
logo on a slide.

**The trace (one session, all of them fire):** *"We're finally ready to look in Austin"* →
the agent reasons on **Nebius**, recalls taste from **mem0**, hits **Tavily** for live
market color, asks **Composio** what's walkable near the home, recommends real listings →
*"see this home in my style"* → **Nebius** distills the style spec → restyled cinematic tour.

| Sponsor | What it unlocks for the buyer | Why it matters |
|---|---|---|
| **Nebius Token Factory** | The agent that actually *thinks* — it carries the conversation, reads the buyer's taste, decides which homes to surface, and writes the style direction behind every tour. | Every word of reasoning the buyer feels runs on Nebius. |
| **Tavily** | Real, on-the-market listings instead of stock demos — the tour is of a house the buyer could actually walk into this weekend. | Proves the homes are real, not props — the credibility layer. |
| **Composio** | Turns a listing into a neighborhood — "what's a short walk from here?" answered around what *this* buyer cares about (a dog park for the dog, restaurants for the host). | The buyer's world flows in as context, via Composio. |
| **mem0** | The memory that makes it personal — every taste, life detail, and preference the AI knows, shown live in the memory rail beside the chat. | The "AI that knows you" *is* mem0. |

Every sponsor is on the critical path, and each ships with a built-in offline fallback — so
the same journey demos flawlessly on stage with nothing live to break. See it whole:
`make serve-live` + `make app`, then walk the trace above.

## Setup

```bash
# 1. Secrets (only needed for live mode)
cp .env.example .env            # then fill in keys

# 2. Backend deps — fastapi, uvicorn, openai-agents (clients stay stdlib urllib)
make deps

# 3. Frontend deps
cd app && npm install && cd ..
```

## Run

| Command | What |
|---|---|
| `make agent` | Terminal chat with the agent (all mock, zero keys) |
| `VISTA_BACKEND=live make agent` | Same, fully live (Nebius + mem0) |
| `PROFILE=pablo_v1 make agent` | Other persona |
| `make serve` | Agent API on **:8001** (mock) — docs at `localhost:8001/docs` |
| `make serve-live` | Agent API, everything live |
| `make app` | React app on **:5173** (symlinks `/assets`, proxies `/api` → :8001) |
| `make interview` / `interview-live` | Terminal run of the getting-to-know-you interview (REPL) |
| `make test` | Smoke tests (`tests/`) — twin parity, engine, scorer, all routes; mock, zero network |
| `PROFILE=guest_v1 make agent` | Cold start — zero seeded memories (also a "Guest" button in the app) |
| `make seed` | Flatten profiles → memories (mock, sanity check) |
| `make seed-live` | Wipe + re-seed real mem0 with both profiles (idempotent) |
| `make listings` / `listings-live` | B2 discovery → `index.draft.json` + photo URLs (never touches frozen `index.json`) |

**Full live demo:** `make serve-live` in one terminal, `make app` in another, open
http://localhost:5173. Script: type *"We're finally ready to look in Austin"* → *"what
did you find"* → click **See this home in your style** → 8s generate → tour + slider →
flip Jake ⇄ Pablo in the top bar.

> Port note: VISTA uses **8001** (8000 was taken on the dev machine). Proxy is set in
> `app/vite.config.js`; port in the `Makefile`.

## API (design 04 §5)

| Endpoint | Returns |
|---|---|
| `POST /api/chat` `{profile_id, message}` | `{reply, action, recalled, new_facts}` — action drives the UI; `new_facts` = memories the agent saved/revised this turn (`save_memory`/`revise_memory` tools) |
| `GET /api/context/{profile_id}` | All memories (powers the memory rail) |
| `GET /api/listings` | `assets/listings/index.json` passthrough |
| `POST /api/reset/{profile_id}` | Fresh conversation (rehearsals); memories untouched |
| `GET /api/health` | Backend mode per layer |

**Interview surface (designs 08b/09, live since step 1)** — adaptive engine in
`agent/interview.py`; the app still falls back to its local mock twin on failure:

| Endpoint | Returns |
|---|---|
| `POST /api/interview/next` `{profile_id, answers}` | `{id, prompt, chips, optional, asked, total}` — next interview question |
| `POST /api/interview/answer` `{profile_id, answers, question_id, answer}` | `{new_facts, ranked, next}` — facts (written to mem0 with provenance) + deterministic re-rank + next adaptive question |
| `POST /api/interview/finish` `{profile_id, answers}` | `{style_spec}` — distilled from THIS conversation (live: LLM over facts; mock: deterministic); never writes the frozen `/specs` |
| `POST /api/memory/{profile_id}/update` · `…/delete` | Memory hygiene (rail confirm/edit/remove → mem0) |
| `POST /api/voice/transcribe` (multipart audio) | `{text}` — local faster-whisper STT, offline; any failure → client falls back to text mode |

## Repo layout

```
agent/            # Python: core.py (brain), server.py (FastAPI), loop.py (REPL),
                  #   clients/ (nebius, mem0, tavily, composio — mock|live), profiles/, mocks/, seed.py
app/              # React/Vite: one page, view states (welcome → [interview] → chat →
                  #   [taste passport] → [listing detail] → tour) — design 08 spine
assets/listings/  # index.json + hero/{raw,restyled,video} per the filename convention
pipeline/         # Engineer A: diffusion restyle + video + ffmpeg stitch (see pipeline/README.md)
specs/            # the frozen A↔B style-spec contract
design/           # design docs 00–09 (read 00-overview first)
tests/            # smoke tests (`make test`) — all mock, zero network
```

Each module has its own README: [agent/](agent/README.md) · [app/](app/README.md) ·
[assets/](assets/README.md) · [pipeline/](pipeline/README.md) · [specs/](specs/README.md).

**The A↔B contract** (only coupling with the pipeline): the app reads assets strictly by
`<listing_id>__<room>__<profile_id>.{png,mp4}` under `assets/listings/…` and degrades to
placeholders when files are missing. Specs in `/specs` are frozen — see `specs/README.md`.

## Status

| Layer | Mock | Live |
|---|---|---|
| Nebius LLM via Agents SDK harness (**Qwen3.5-397B** default; Llama 3.3 70B / DeepSeek alt) | ✅ | ✅ tested — tools fire end-to-end |
| mem0 (both profiles seeded) | ✅ | ✅ tested |
| Tavily (listing discovery + `search_web_listings` tool) | ✅ | ✅ search tested; extract blocked by portals → manual photos (sanctioned) |
| Hero photos — **austin_01 locked** (1724 Canon Yeomans Trl; 16 raw rooms in `assets/listings/austin_01/raw/`) | n/a | ✅ merged from `pablo/diffusion-pipeline`; app's hero card/tour reads these pixels |
| Nebius Object Storage asset pipe (`make assets-pull` / `assets-push`) | n/a | ✅ authenticated, dry-runs green; `index.json` clobber-protected |
| Composio (Google Maps via `whats_nearby` tool) | ✅ canned POIs | ✅ live v3 toolkit — personalized nearby places, writes area facts to mem0 |
| Design 08b interview experience (phases, voice\|text modes, orb, taste panel, passport) | ✅ Playwright-verified end-to-end | ✅ same UI; live engine answers |
| Voice v1 — hold-to-speak → `/api/voice/transcribe` (local faster-whisper, offline) | n/a — needs the server | ✅ tested (synthesized speech word-perfect; warm transcribe ~0.4s; human-verified) |
| Interview engine (`agent/interview.py`: adaptive planner, mem0 writes, scorer, routes; always ends on the open catch-all question) | ✅ exact parity with `app/src/mock/interview.js` (tested) | ✅ tested end-to-end — adaptive questions, distilled fact tidbits → real mem0 with provenance |
| Chat memory tools (`save_memory`/`revise_memory` — learns + revises during property talk) | mock returns `new_facts: []` (app twin extracts locally) | ✅ live-tested: revision + new fact + re-recommendation in one turn |
| Guest profile (`guest_v1` — zero seeded memories, cold-start testing) | ✅ verified in browser | ✅ empty mem0 user |
| `finish` → style_spec → dynamic taste passport (design 09 step 4) | ✅ deterministic, parity-tested | ✅ tested — spec genuinely derived from the conversation |
| Home discovery (design 10): curated sets, narrated re-rank, weights rail, dismiss/save/see-more | ✅ Playwright-verified; 7-listing pool with feature vectors | local model for now — live `discover/react/refine` endpoints pending (10b) |
| Smoke tests (`make test`, 40 tests) | ✅ all passing | n/a — tests force mock |

> The interview topbar shows a **brain badge** (`live` / `scripted fallback` / `offline ·
> local mock`) from `/api/health` — if questions ever look canned, check the badge first.