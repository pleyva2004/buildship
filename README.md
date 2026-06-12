# VISTA — personalized cinematic home tours

The AI knows the buyer. It surfaces real listings and renders a tour of the actual home
**restyled to their taste** — same rooms, same architecture, new decor. Full product
definition in [CLAUDE.md](CLAUDE.md); design docs in [/design](design/00-overview.md).

## Architecture

```
app (React/Vite) ──/api──► agent/server.py (FastAPI :8001) ──► agent/core.py (AgentSession)
                               routes = pure translation           recall → prompt → LLM → action parse
agent/loop.py (terminal REPL) ─────────────────────────────────────┤
                                                       mem0_client │ nebius     ← each MOCK | LIVE
```

Every external client (Nebius LLM, mem0, Tavily, Composio) is mock-first behind one
interface, selected by `VISTA_BACKEND=mock|live` (per-client override: `NEBIUS_BACKEND`,
`MEM0_BACKEND`, …). **Mock is the default and the on-stage fallback** — the entire demo
runs with zero keys and zero network. The React app additionally falls back to its own
local mock (`app/src/mock/`) if the API is unreachable.

## Setup

```bash
# 1. Secrets (only needed for live mode)
cp .env.example .env            # then fill in keys

# 2. Backend deps — fastapi + uvicorn, that's all (clients are stdlib urllib)
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
| `make seed` | Flatten profiles → memories (mock, sanity check) |
| `make seed-live` | Wipe + re-seed real mem0 with both profiles (idempotent) |

**Full live demo:** `make serve-live` in one terminal, `make app` in another, open
http://localhost:5173. Script: type *"We're finally ready to look in Austin"* → *"what
did you find"* → click **See this home in your style** → 8s generate → tour + slider →
flip Jake ⇄ Pablo in the top bar.

> Port note: VISTA uses **8001** (8000 was taken on the dev machine). Proxy is set in
> `app/vite.config.js`; port in the `Makefile`.

## API (design 04 §5)

| Endpoint | Returns |
|---|---|
| `POST /api/chat` `{profile_id, message}` | `{reply, action, recalled}` — action drives the UI (recommend / generate_tour) |
| `GET /api/context/{profile_id}` | All memories (powers the memory rail) |
| `GET /api/listings` | `assets/listings/index.json` passthrough |
| `POST /api/reset/{profile_id}` | Fresh conversation (rehearsals); memories untouched |
| `GET /api/health` | Backend mode per layer |

## Repo layout

```
agent/            # Python: core.py (brain), server.py (FastAPI), loop.py (REPL),
                  #   clients/ (nebius, mem0 — mock|live), profiles/, mocks/, seed.py
app/              # React/Vite: one page, view states (welcome → chat → tour)
assets/listings/  # index.json + hero/{raw,restyled,video} per the filename convention
pipeline/         # Engineer A: restyle + video + ffmpeg stitch (not yet built)
specs/            # the frozen A↔B style-spec contract
design/           # design docs 00–06 (read 00-overview first)
```

Each module has its own README: [agent/](agent/README.md) · [app/](app/README.md) ·
[assets/](assets/README.md) · [pipeline/](pipeline/README.md) · [specs/](specs/README.md).

**The A↔B contract** (only coupling with the pipeline): the app reads assets strictly by
`<listing_id>__<room>__<profile_id>.{png,mp4}` under `assets/listings/…` and degrades to
placeholders when files are missing. Specs in `/specs` are frozen — see `specs/README.md`.

## Status

| Layer | Mock | Live |
|---|---|---|
| Nebius LLM (Llama 3.3 70B) | ✅ | ✅ tested |
| mem0 (both profiles seeded) | ✅ | ✅ tested |
| Tavily (listing discovery) | — | key in .env, client pending |
| Composio (mood-board import) | — | key in .env, client pending |
