# CLAUDE.md — Project VISTA (working codename)

> Personalized cinematic home tours. The AI knows the buyer; it finds a real listing and renders a tour of that home restyled to their taste.
> **Context: 24-hour hackathon build. Submission: Friday night. Two engineers. Demo > everything.**

---

## 1. One-paragraph product definition

VISTA is a buyer-side demo of a seller-side business. The user converses with an agent that already holds deep personal context (taste profile, life situation, mood boards). The agent surfaces real listings, and on request generates a cinematic video tour of the actual home **restyled to the user's aesthetic** — same rooms, same architecture, new decor. The demo wow is the personalized tour; the pitched business model is seller-side (agents/brokerages pay for tour generation; the embedded "see this home in your style" widget collects buyer taste profiles → future buyer-side agent).

## 2. Non-negotiable demo requirements

1. **The stage demo runs entirely on pre-generated, locally cached assets.** The app simulates live generation with an ~8s loading state. Final videos must exist as files on local disk, playable outside the app as a fallback.
2. **Two taste profiles, one house.** The same hero listing rendered in two divergent aesthetics (Profile 1: Pablo's real profile — warm mid-century; Profile 2: Jake's real profile — bright Scandinavian minimalist). Both personas are real people, which strengthens the proof. Back-to-back playback is the proof of personalization.
3. **Original-vs-restyled slider** on every room. This proves it is the same real house.
4. **Visible context panel** showing what the AI knows about the user (sourced from mem0). The memory layer is the story.

## 3. Architecture

```
User chat ──► Agent (Nebius Token Factory LLM: Llama 3.3 70B or Qwen 2.5 72B)
                │
                ├── mem0 ──────────── taste profile, life situation, conversation memory
                ├── Tavily ────────── listing discovery + page extraction (3 pre-indexed listings)
                ├── Composio ──────── taste-context import (Pinterest if supported, else Notion mood board)
                │
                ▼
        Style Spec Generator (LLM) ── taste profile → locked JSON style spec
                │
                ▼
        Restyle Engine ── instruction-based image editing, per room, style spec injected
                │            (Nebius-hosted Flux Kontext if available; else Gemini image editing free tier)
                ▼
        Image-to-Video ── Kling / Hailuo / Higgsfield / Luma free-tier credits (Option A)
                │            ALL PRE-GENERATED. Never live on stage.
                ▼
        ffmpeg ── stitch, crossfades, one music track ──► cached tour video
```

**Fallback (build FIRST, by H6):** ffmpeg Ken Burns — slow pan/zoom over restyled stills + crossfades + music. A complete demo must exist by hour 6 regardless of video-model success.

## 4. The Style Spec (integration contract between Engineer A and B)

The LLM converts a taste profile into ONE locked spec, injected verbatim into every room's edit prompt. This is what makes the tour feel like a single coherent taste rather than per-room filters.

```json
{
  "profile_id": "pablo_v1",
  "aesthetic_name": "warm mid-century modern",
  "palette_hex": ["#C8A27A", "#2F3E46", "#E9E4DB", "#7A5C3E"],
  "materials": ["walnut", "boucle", "brushed brass", "wool"],
  "furniture_vocabulary": ["low-profile sofa", "slatted credenza", "arc floor lamp"],
  "lighting_mood": "warm, golden hour, soft shadows",
  "hard_constraints": ["preserve architecture", "preserve windows/doors", "preserve room geometry", "no people"]
}
```

## 5. Explicitly MOCKED / OUT OF SCOPE — do not build

- ❌ Web scraper (listings found via Tavily once; photos may be manually downloaded if extraction is blocked)
- ❌ User onboarding / auth (context is pre-seeded into mem0)
- ❌ Live video generation in the demo path
- ❌ More than 3 listings; more than 1 fully-treated hero listing
- ❌ Payment, seller dashboard, widget embed (pitch slides only)
- ❌ Option B self-hosted video (Wan 2.2 / LTX on Nebius GPU) — documented as FUTURE WORK in the deck: "production self-hosts on Nebius GPU, ~10x cost reduction per tour, no third-party model dependency"

## 6. Sponsor tool usage (judges score this — keep each load-bearing)

| Sponsor | Role in build | Pitch line |
|---|---|---|
| mem0 | Holds the entire personalization layer | "The 'AI that knows you' IS mem0" |
| Nebius Token Factory | All agent + style-spec inference | "Every token of reasoning runs on Nebius" |
| Tavily | Real-time listing discovery/extraction | Legitimizes data access story |
| Composio | Taste-context import (Pinterest/Notion) | "Context flows in via Composio integrations" |
| Nebius AI Cloud (GPU) | Future-work slide (Option B) | Unit-economics roadmap answer |

## 7. Repo conventions

```
/pipeline      # Engineer A: restyle, video queue mgmt, ffmpeg stitch, ken-burns fallback
/agent         # Engineer B: core.py (AgentSession brain), server.py (FastAPI :8001),
               #   loop.py (terminal REPL), clients/ (nebius, mem0 — each MOCK|LIVE),
               #   profiles/ (seed JSONs), mocks/ (canned turns = stage fallback), seed.py
/app           # Engineer B: React/Vite frontend — one page, view states
               #   (welcome → chat+memory-rail → generating overlay → tour+slider)
/assets
  /listings/index.json         # 3-listing inventory (agent + app read this)
  /listings/<id>/raw/          # original photos
  /listings/<id>/restyled/<profile_id>/   # edited stills
  /listings/<id>/video/<profile_id>/      # clips + final stitched tour.mp4
/specs         # style spec JSONs (the A↔B contract)
/design        # Engineer B design docs 00–08 (architecture decisions live here)
/deck          # pitch + future-work slides
```

- Python for /pipeline and /agent. React (Vite) for /app. No databases — JSON files on disk are fine for 24h.
- All secrets in `.env`, never committed. `.env.example` documents every key.
- Asset filenames are the API: `<listing_id>__<room>__<profile_id>.{png,mp4}`. Engineer B's app reads assets by this convention; no other coupling. The app degrades to placeholders for any missing asset.
- **Mock-first rule:** every external client (Nebius, mem0, Tavily, Composio) has a MOCK twin behind the same interface, selected by `VISTA_BACKEND=mock|live` (per-client: `NEBIUS_BACKEND`, `MEM0_BACKEND`, …). Mock is default and is the on-stage fallback. Never wire a live call without its mock twin.
- Agent logic lives in `core.py` (transport-agnostic) — `server.py` routes and `loop.py` REPL are thin shells over it. Don't put logic in routes.
- Run targets: see `Makefile` (`make agent`, `make serve`, `make app`, `make seed-live`). Setup + API reference: `README.md`.

## 8. Decision log

- Path: demo buyer-side experience, pitch seller-side business (trojan-horse GTM)
- Video generation: **Option A** (commercial free-tier credits, pre-generated). Option B = future work.
- Restyle model: decide by H2 — Nebius-hosted Kontext if it exists, else Gemini image editing.
- Conflict-of-interest rule for the pitch, if asked: seller money buys generation/distribution, never ranking.
- Profile 2 is **Jake's real profile** (`jake_v1`, bright Scandinavian minimalist) — both personas are real people, not a mock contrast.
- Backend architecture: mock-first behind `VISTA_BACKEND=mock|live`; mocks are deterministic and double as the stage fallback (zero-network demo viable).
- HTTP layer: **FastAPI on :8001** (8000 occupied on dev machine), thin routes over `agent/core.py:AgentSession`. Chosen over stdlib for streaming/typed-contract iteration post-hackathon.
- LLM: **Llama 3.3 70B confirmed live** on Nebius (`api.studio.nebius.com/v1`); emits `<action>` tags reliably. Keyword backstop guarantees `generate_tour` fires on "show me my version" regardless.
- mem0 live: both profiles seeded (14 atomic facts each, categorized). `make seed-live` is idempotent (wipe + re-seed). mem0's search API ignores `limit` — enforced client-side.
- Recall filtering: `constraint`-category memories (render rules like "no people") are excluded from conversational recall — the LLM over-interprets them as life preferences.
- **Design 08 (flow optimizations) frontend shipped.** New spine: welcome → [getting-to-know-you interview] → chat+rail → [taste passport] → recommendations → [listing detail] → generating → tour (slider-first). Active-learning loop: interview answers write facts to the rail AND re-rank a 5-listing candidate pool via a pure client-side scoring pass (no network, no numeric score in UI). Verified end-to-end with Playwright on the zero-network mock path.
- Agent surface for the loop (`next_question` / `record_answer` / `rerank` in `agent/core.py` + `/api/interview/*`, `/api/memory/*` routes) is **pending backend work** (design 08 §5 item 1). Until then the frontend's calls 404 against the live server and fall back to the deterministic mock twin (`app/src/mock/interview.js`) — those 404s in the agent log are expected, not bugs. Interview state is client-held so the backend surface can stay stateless.

## 9. Build status (end of backend bring-up)

| Layer | Mock | Live |
|---|---|---|
| Nebius LLM | ✅ | ✅ tested |
| mem0 (seeded) | ✅ | ✅ tested |
| Tavily | — | key in .env, client pending (B2) |
| Composio | — | key in .env, client pending |
| React app (design 08 spine: interview, taste passport, listing detail, slider-first tour) | ✅ clickable end-to-end, Playwright-verified | wired to API w/ mock fallback |
| Interview/rerank agent surface (`/api/interview/*`, `/api/memory/*`) | ✅ client-side mock twin | **pending — frontend already calls it** |
| Hero photos / restyles / tours | — | **pending (B2 blocks Engineer A)** |
