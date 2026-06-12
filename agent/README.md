# /agent — the VISTA agent backend (Python, Engineer B)

The transport-agnostic agent brain plus two thin shells over it: a terminal REPL
and a FastAPI bridge. One LLM call per turn. No databases — conversation history
lives in-process, memories live in mem0 (or its mock).

```
loop.py (REPL)  ─┐
                 ├─► core.py AgentSession ──► clients/nebius.py     (LLM, mock|live)
server.py (API) ─┘        │
                          └─────────────────► clients/mem0_client.py (memory, mock|live)
```

## Files

| File | What |
|---|---|
| `config.py` | Loads `.env` (tiny stdlib loader, never overrides real env), exposes keys/paths and the `backend(client)` mock\|live selector |
| `core.py` | `AgentSession` — the brain. Also `parse_action`, `build_turn_message`, `load_listings`. **No HTTP imports, ever** |
| `server.py` | FastAPI bridge on :8001. Routes are pure HTTP↔AgentSession translation; one shared `Mem0Client`, one session per profile |
| `loop.py` | Terminal REPL — same brain, prints `[recall]` and `[action]` lines for debugging |
| `seed.py` | Flattens `profiles/*.json` → atomic facts → mem0. Live mode wipes first (idempotent re-seed) |
| `clients/nebius.py` | `chat(messages) -> str`. Live = OpenAI-compatible chat completions; mock = canned turns. **A live failure degrades to mock for that turn** — the demo never stalls |
| `clients/mem0_client.py` | `Mem0Client`: `seed / search / all / add / delete_all`. Live = mem0 REST (stdlib urllib); mock = in-memory keyword scoring, self-seeded from profiles |
| `profiles/jake.json`, `profiles/pablo.json` | Seed profiles (life situation, taste, mood boards, constraints) |
| `mocks/turns.json` | The canned demo script for the mock LLM — keyword match on the last user message, file order, first full match wins. Keep in sync with the rehearsed lines in design 06 |

## A turn, end to end (`AgentSession.turn`)

1. **Recall** — `memory.search(profile_id, user_msg, k=6)`, drop `constraint`-category
   facts (those are render rules for the pipeline, not conversation material), keep 4.
2. **Inject** — recalled facts are prepended to the user message as a
   `[context — what you remember about this client]` block.
3. **Chat** — one `nebius.chat(history)` call. The system prompt embeds the full
   listing inventory from `assets/listings/index.json` so the LLM can never invent homes.
4. **Parse** — strip a trailing `<action>{...}</action>` tag (forgiving: bad JSON = no
   action). **Keyword backstop:** if the user said "show me / my version / my style"
   and no action came back, force `generate_tour` — the tour moment can never fail to fire.
5. Return `{reply, action, recalled}` — the exact shape the app consumes.

### Actions (the LLM appends at most one)

```json
{"type": "recommend", "listing_ids": ["hero", "alt1"]}   // present listings → cards in chat
{"type": "generate_tour", "listing_id": "hero"}          // → 8s overlay → tour view
```

## Memory model

Memories are atomic facts: `{id, text, category, score}` with category in
`life_situation | taste | mood_board | constraint`. The category drives the app's
memory-rail grouping; `constraint` is never recalled into conversation and never
rendered. `flatten_profile()` in `mem0_client.py` is the single source of the
profile → facts mapping (the app's mock mirrors its output).

## Backends

`VISTA_BACKEND=mock|live` selects all clients; per-client override via
`NEBIUS_BACKEND` / `MEM0_BACKEND`. **Mock is the default** — everything here runs
with zero keys and zero network. Mock behavior is deterministic by design: it
doubles as the on-stage fallback.

## API (served by `server.py`, proxied from the Vite app)

| Endpoint | Returns |
|---|---|
| `POST /api/chat` `{profile_id, message}` | `{reply, action, recalled}` |
| `GET /api/context/{profile_id}` | `{profile_id, memories}` — powers the memory rail |
| `GET /api/listings` | `assets/listings/index.json` passthrough |
| `POST /api/reset/{profile_id}` | Drops the session (rehearsals); memories untouched |
| `GET /api/health` | `{llm, memory, model}` — backend mode per layer |

## Run

```bash
make agent        # terminal REPL, all mock, zero keys
make agent-live   # REPL against live Nebius + mem0
make serve        # API on :8001 (docs at /docs)
make serve-live   # API, everything live
make seed         # sanity-check profile flattening (mock)
make seed-live    # wipe + re-seed real mem0 with both profiles
PROFILE=pablo_v1 make agent   # other persona
```

Design doc: [design/04-agent-loop.md](../design/04-agent-loop.md) (also 01 for
mem0/profiles, 02 for the style-spec generator — not yet built).
