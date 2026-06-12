# /agent — the VISTA agent backend (Python, Engineer B)

The transport-agnostic agent brain plus two thin shells over it: a terminal REPL
and a FastAPI bridge. No databases — conversation history lives in-process,
memories live in mem0 (or its mock).

```
loop.py (REPL)  ─┐            ┌─ MOCK: canned turns (clients/nebius.py) + <action> parse
                 ├─► core.py ─┤
server.py (API) ─┘            └─ LIVE: harness.py (OpenAI Agents SDK on Nebius)
                                   └─ tools.py: recall_memories │ search_web_listings
                                                recommend_listings │ generate_tour
                 clients/: nebius │ mem0_client │ tavily_client   ← each MOCK | LIVE
```

The live path is a real tool-calling loop (design 07): the model itself calls
`recommend_listings` / `generate_tour`, which record the UI action into a per-turn
`TurnState` — no more relying on `<action>` tags in live mode. Any live failure on
any turn degrades to the deterministic mock turn; the demo never stalls.

## Files

| File | What |
|---|---|
| `config.py` | Loads `.env` (tiny stdlib loader, never overrides real env), exposes keys/paths and the `backend(client)` mock\|live selector |
| `core.py` | `AgentSession` — the brain; dispatches mock \| live per turn. Also `parse_action`, `build_turn_message`, `load_listings`. **No HTTP imports, ever** |
| `harness.py` | Agents SDK wiring (live path): Nebius via custom `AsyncOpenAI` + `OpenAIChatCompletionsModel`, tracing disabled. Imported lazily — the mock path never needs `openai-agents` |
| `tools.py` | `TurnState` + six function tools: `recall_memories`, `search_web_listings`, `recommend_listings`, `generate_tour`, and the dynamic-memory pair `save_memory` / `revise_memory` (design 09 §3.8 — trait-level tidbits, revisions supersede; both feed `new_facts`) |
| `listings.py` | One-time B2 discovery (`make listings[-live]`): Tavily search/extract → `assets/listings/index.draft.json` + photo URLs. **Never auto-writes the frozen `index.json`** |
| `interview.py` | The getting-to-know-you engine (designs 08b/09): mock = exact port of `app/src/mock/interview.js` (parity-tested); live = one structured Nebius completion per answer → distilled fact tidbits (mem0, with provenance, open `other` lane) + trait weights + next adaptive question. Always ends on the open catch-all question (backstopped in code). Ranking is always the deterministic scorer. REPL via `make interview[-live]` |
| `server.py` | FastAPI bridge on :8001. Routes are pure HTTP↔AgentSession translation; one shared `Mem0Client`, one session per profile |
| `loop.py` | Terminal REPL — same brain, prints `[recall]` and `[action]` lines for debugging |
| `seed.py` | Flattens `profiles/*.json` → atomic facts → mem0. Live mode wipes first (idempotent re-seed) |
| `clients/nebius.py` | `chat(messages) -> str`. Live = OpenAI-compatible chat completions; mock = canned turns. **A live failure degrades to mock for that turn** — the demo never stalls |
| `clients/mem0_client.py` | `Mem0Client`: `seed / search / all / add / delete_all`. Live = mem0 REST (stdlib urllib); mock = in-memory keyword scoring, self-seeded from profiles |
| `clients/tavily_client.py` | `search(query)` / `extract(url)`. Live = Tavily REST (stdlib urllib); mock = canned results from `mocks/tavily.json`. Extract failures are expected (portals block it) — callers degrade to manual photos |
| `profiles/jake.json`, `profiles/pablo.json` | Seed profiles (life situation, taste, mood boards, constraints) |
| `mocks/turns.json` | The canned demo script for the mock LLM — keyword match on the last user message, file order, first full match wins. Keep in sync with the rehearsed lines in design 06 |

## A turn, end to end (`AgentSession.turn`)

1. **Recall (both paths)** — `memory.search(profile_id, user_msg, k=6)`, drop
   `constraint`-category facts (render rules for the pipeline, not conversation
   material), keep 4. Injected into the user message as a `[context — what you
   remember about this client]` block. The instructions embed the full listing
   inventory from `assets/listings/index.json` so the LLM can never invent homes.
2. **LIVE** — `Runner.run_sync` drives the tool loop (max 6 hops). The model may call
   `recall_memories` for deeper digs (results union into the rail) and
   `search_web_listings` (Tavily) for market color; `recommend_listings` /
   `generate_tour` record the UI action into `TurnState`.
   **MOCK** — canned keyword turn from `mocks/turns.json` (matched against the client
   message only, not the injected context), `<action>` tag parsed off the reply.
3. **Keyword backstop (both paths):** if the user said "show me / my version / my
   style" and no action was recorded, force `generate_tour` — the tour moment can
   never fail to fire.
4. Return `{reply, action, recalled}` — the exact shape the app consumes.

### Actions (at most one per turn)

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
| `POST /api/chat` `{profile_id, message}` | `{reply, action, recalled, new_facts}` |
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
make listings     # B2 discovery → index.draft.json (mock tavily)
make listings-live# same, real Tavily search + extract
make test         # smoke tests (tests/) — parity, engine, scorer, routes
PROFILE=pablo_v1 make agent    # other persona
PROFILE=guest_v1 make interview  # cold start — no seeded memories
```

Design docs: [design/07-agent-harness.md](../design/07-agent-harness.md) (the tool-loop
architecture, supersedes the orchestration half of 04), [design/04-agent-loop.md](../design/04-agent-loop.md),
01 for mem0/profiles, 03 for listings, 02 for the style-spec generator — not yet built.
