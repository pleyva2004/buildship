# ENGINEER B — Agent, Memory & App Owner

**Mission:** Everything the judges touch and every word the agent says. You own the story layer: the AI that "already knows me," the conversation, and the UI moments (context panel, slider, two-profile reveal) that convert renders into a winning demo.

---

## Role

Owner of `/agent` and `/app`. You produce the style specs (`/specs/*.json`) that Engineer A consumes, and your app reads A's assets strictly by the filename convention. You also own the pitch deck and demo choreography.

## Responsibilities

1. **mem0 personalization layer.** Define the profile schema (taste descriptors, life situation, mood-board references, constraints) and seed BOTH profiles: Pablo-real and the contrasting persona. mem0 is the architectural embodiment of the pitch — when judges ask "where does personalization live," the answer is this layer.
2. **Composio context import.** Pinterest if supported; otherwise a Notion mood-board pull. One real import path, demoed once, feeding mem0. Semi-mocked is fine; the connection must be real.
3. **Agent layer (Nebius Token Factory).** Llama 3.3 70B or Qwen 2.5 72B. Conversational flow: user states situation → agent recalls context from mem0 → surfaces 2–3 listings with reasoning → handles "show me my version." Thin is fine (~50 lines of orchestration); it must FEEL fully agentic.
4. **Tavily listing discovery.** One-time: find and extract the 3 demo listings, index title/price/location/photos into a local JSON. If photo extraction is blocked, metadata via Tavily + photos manual.
5. **Style Spec Generator.** LLM prompt that converts a mem0 profile into the locked JSON spec (schema in CLAUDE.md §4). This is the A↔B contract — freeze the schema by H4 and never change it after H8.
6. **React app.** Four elements, nothing else: chat panel; visible context panel ("what the AI knows about me," live from mem0); listing cards; tour view with video player + **original-vs-restyled slider** per room. Simulated-live loading state (~8s) before cached video plays.
7. **Deck + demo choreography.** 2-minute script (setup → conversation → the moment → slider reveal → second profile → trojan-horse GTM slide). Future-work slide: Option B on Nebius GPU, ~10x cost reduction, model-agnostic architecture. Q&A one-liners: data rights ("production partners with brokerages who own the content — that's also who pays"), conflict of interest ("seller money buys generation, never ranking").

## Hard deliverables (acceptance criteria)

| # | Deliverable | Done means | Due |
|---|---|---|---|
| B1 | mem0 seeded, both profiles + style spec schema frozen | Specs generate deterministically from profiles; A unblocked | **H4** |
| B2 | 3 listings indexed (Tavily) + hero listing photos in `/assets/raw` | A has inputs; agent has inventory | **H4** |
| B3 | Agent conversation loop working in terminal | Context recall + listing recommendation + reasoning, on Nebius | **H10** |
| B4 | App shell: chat + context panel + listing cards | Clickable end-to-end with placeholder video | **H15** |
| B5 | Tour view: slider + player + fake-live loading, wired to A's cached assets | Full demo path clickable | **H18** |
| B6 | Deck final + demo script written | GTM, future-work, Q&A answers done | **H20** |
| B7 | Two timed rehearsals run | Under 2:30, fallback video tested standalone | **H23** |

## Failure playbook

- Composio lacks Pinterest and Notion path is fighting you by H8 → drop to a pre-loaded JSON mood board, keep the context-panel narrative, mention Composio for the import roadmap.
- Agent flakiness on stage → demo conversation is semi-scripted: same prompts every rehearsal, deterministic temperature, listing choice pinned.
- App polish slipping at H20 → cut listing cards to static images before touching the slider or context panel. Slider and context panel are sacred.

## What you do NOT do

No generation work. No model debugging for A. No auth, no DB, no >3 listings, no live generation endpoint. No new features after H18 — only polish and rehearsal.
