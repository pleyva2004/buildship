# Design 04 — Agent Conversation Loop (B3)

> Thin orchestration that must FEEL fully agentic. ~50–100 lines of real logic. Terminal
> first (B3, H10), then the same loop drives the app via a tiny HTTP layer (B4/B5).

## 1. Conversation arc (the demo script IS the state machine)

The demo conversation is semi-scripted (failure playbook), so model the arc explicitly as
stages rather than free chat. Free input still works; stages make rehearsal deterministic.

```
S0 GREET      agent opens, references known context ("welcome back, Jake — still set on Austin?")
S1 SITUATE    user states situation → agent recalls mem0 facts → reflects them back VISIBLY
S2 RECOMMEND  agent surfaces 2–3 listings from index.json with per-profile reasoning
S3 THE ASK    user: "show me my version" → triggers tour generation moment
S4 GENERATE   emit generate_tour event → app shows ~8s fake-live loading → cached tour plays
S5 REVEAL     after tour: offer the second profile ("want to see how Pablo would live here?")
```

## 2. Architecture

```
loop.py (orchestrator)
  ├── mem0_client.search(profile, user_msg)      # recall step — top-k facts
  ├── nebius.chat(system, history, context_block) # one LLM call per turn
  └── actions parsed from LLM output:
        RECOMMEND(listing_ids)   → render cards (terminal: text; app: event)
        GENERATE_TOUR(listing_id, profile_id) → app loading state → cached mp4
        NONE                     → plain reply
```

- **One LLM call per turn.** No multi-step tool-calling loop — too flaky for stage. The
  agent's "tools" are pre-fetched context injected into the prompt: top-k mem0 facts +
  the full 3-listing index (it's tiny). The LLM only converses and emits an action tag.
- **Action tagging**: the system prompt asks the model to end responses with
  `<action>{"type": "recommend", "listing_ids": [...]}</action>` when appropriate. Parser
  is forgiving (regex; missing tag → NONE). On stage, S3's GENERATE_TOUR also has a
  hard keyword trigger ("show me", "my version") so the moment can never fail to fire.
- **Memory visibility**: each turn returns `{reply, action, recalled: [facts]}` —
  `recalled` feeds the app's context panel highlight ("the AI just used these 3 memories").
  This is the mem0 story made visible; don't drop it.

## 3. Nebius client

`agent/clients/nebius.py` — OpenAI-compatible chat completions against Token Factory.

```python
def chat(messages: list[dict], temperature: float = 0.2, model: str = settings.NEBIUS_MODEL) -> str
```

- Model: `meta-llama/Llama-3.3-70B-Instruct` default; Qwen 2.5 72B as fallback flag.
- Low temperature + pinned seed where supported — rehearsal determinism.
- Timeout 20s, one retry, then **fall back to MOCK for that turn** (canned reply for the
  current stage). The demo never stalls on a network blip.

### MOCK backend
`agent/mocks/turns.json`: canned reply per (stage, profile). Keyword-matches the user
message to a stage. The full demo arc plays end-to-end with zero keys — this doubles as
the stage fallback.

## 4. Terminal UX (B3 acceptance form)

```
$ make agent PROFILE=jake_v1
[context] 12 memories loaded for Jake          ← proof of mem0 layer
you> we're finally ready to look in Austin
[recall] • prefers bright and airy • WFH 3 days • dog needs yard
agent> Welcome back Jake — since you work from home three days a week, I focused on...
       [recommend: hero, alt1]
you> show me my version of the first one
agent> Generating your tour of Travis Heights... (in the app this plays tour.mp4)
```

`[recall]` lines print the actual mem0 hits — same data the app's context panel will get.

## 5. App-facing surface (forward-design for B4/B5, build at H12+)

Tiny FastAPI (or even Flask) app, three endpoints, JSON only:

- `POST /chat {profile_id, message}` → `{reply, action, recalled}`
- `GET  /context/{profile_id}` → grouped memories (context panel)
- `GET  /listings` → index.json passthrough

No streaming, no websockets, no sessions (single-user demo; history kept in process).

## 6. Acceptance (B3)

- [ ] Full S0→S5 arc runs in terminal on MOCK with zero keys.
- [ ] Same arc on LIVE Nebius+mem0 when keys land (same code path, flag flip).
- [ ] `recalled` facts surface on every turn.
- [ ] GENERATE_TOUR always fires on the scripted S3 line (keyword backstop tested).
- [ ] A network-killed LIVE run degrades to canned turn, doesn't crash or stall.
