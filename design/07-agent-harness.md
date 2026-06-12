# Design 07 — Agent Harness (OpenAI Agents SDK) + Tavily

> Supersedes the orchestration half of design 04 (the `<action>` tag protocol and the
> single-call turn). Folds in the Tavily client from design 03. The API surface
> (`{reply, action, recalled}`), the app, and the mock-first guarantee do NOT change.

## 0. Why a real harness

Design 04's loop is one LLM call with a regex-parsed `<action>` tag — fine for two
actions, but it dead-ends where we're going:

- **Composio is next.** Its entire product is feeding tools to agent frameworks. With a
  real tool-calling loop, "pull everything we can about a person to get their vibe"
  becomes: register Composio toolkits (Pinterest, Notion, …) on the agent. With the tag
  protocol it becomes hand-rolled glue per integration.
- Tavily, mem0 deep-recall, and listing actions all want to be **tools the model chooses
  to call**, not prompt conventions.
- The judges' "is it actually agentic?" question gets a structural answer.

**Decision (locked):** OpenAI Agents SDK. Points at Nebius via a custom
`AsyncOpenAI(base_url=…)` client + `OpenAIChatCompletionsModel` — every token still runs
on Nebius Token Factory (Llama 3.3 70B supports function calling there). Composio ships
a native openai-agents toolkit for the next phase. Rejected: PydanticAI (more new API
surface, same payoff), LangGraph (boilerplate too heavy for 24h), hand-rolled tools loop
(not a harness; re-solves what the SDK gives us).

## 1. Architecture

```
            ┌─ MOCK path (default, zero keys) ───────────────────────────┐
turn(msg) ──┤   canned keyword turns (mocks/turns.json) + <action> parse │ ── {reply, action, recalled}
            └─ LIVE path ────────────────────────────────────────────────┘
                Agents SDK Runner ── Nebius (OpenAIChatCompletionsModel)
                   │ tools (agent/tools.py), state in RunContext:
                   ├── recall_memories(query)        → mem0 (live)
                   ├── search_web_listings(query)    → Tavily (live)
                   ├── recommend_listings(ids)       → records UI action
                   └── generate_tour(listing_id)     → records UI action
                any exception, any turn ──► degrade to the MOCK turn (never stall)
```

- **Mock mode does not run the SDK.** The deterministic keyword-turn path from design 04
  survives verbatim as the stage fallback — it needs no network, no deps beyond stdlib,
  and it IS the rehearsed script. The harness is the live path only.
- **Hybrid recall stays.** We still pre-fetch mem0 facts and inject them as turn context
  (deterministic memory-rail pulse, no extra round trip), AND expose `recall_memories`
  as a tool for deeper digs. The rail shows the union.
- **Actions become tools.** `recommend_listings` / `generate_tour` write into a per-turn
  `TurnState` (SDK run context); `turn()` returns the recorded action in the same shape
  the app already consumes. The regex `<action>` parser remains only for the mock path.
  The "show me / my version / my style" keyword backstop survives in both paths.

## 2. Files

| File | What |
|---|---|
| `agent/harness.py` | SDK wiring: Nebius model, agent definition, `run_turn(state, history, msg)` |
| `agent/tools.py` | `TurnState` + the four function tools |
| `agent/clients/tavily_client.py` | `search(query)` / `extract(url)` — MOCK \| LIVE, stdlib urllib, same backend-flag pattern as nebius/mem0 |
| `agent/mocks/tavily.json` | Canned search results + hero extract (deterministic) |
| `agent/listings.py` | One-time B2 discovery script (`make listings`) |
| `agent/core.py` | `AgentSession.turn()` dispatches mock \| live; mock logic unchanged |

New dependency: `openai-agents` (brings `openai`). Tracing disabled (no OpenAI key).

## 3. Tavily: one-time tooling AND a runtime tool

Design 03 stands: after H4 the agent's inventory is `index.json`, frozen. Two uses:

1. **`agent/listings.py` (B2, one-time):** search → extract → writes
   `assets/listings/index.draft.json` + prints candidate photo URLs for manual download.
   **Never overwrites the frozen `index.json`** — promoting the draft is a human edit.
2. **`search_web_listings` (runtime tool, live only):** the agent can genuinely search —
   this is the honest Tavily sponsor story ("the agent discovers listings in real time").
   The system prompt pins recommendations to the frozen inventory; the tool legitimizes
   discovery, it doesn't expand what can be recommended on stage.

## 4. What does not change

`server.py` routes and response shapes; `loop.py`; the app and its mock fallback;
`mem0_client.py`; the filename contract; `VISTA_BACKEND=mock` as the default and the
demo-day answer for anything flaky.

## 5. Acceptance

- [ ] `make agent` (zero keys) behaves exactly as before — canned turns, actions fire.
- [ ] `VISTA_BACKEND=live make agent`: replies come from Nebius through the SDK; asking
      for listings triggers the `recommend_listings` tool; "show me my version" triggers
      `generate_tour`; recall pre-fetch still populates `recalled`.
- [ ] Live failure mid-conversation degrades to a mock turn (pull the network, keep talking).
- [ ] `make listings` produces `index.draft.json` in mock mode with zero keys.
- [ ] `/api/chat` shape unchanged; app needs no edits.
