# CLAUDE.md — Project VISTA (working codename)

> Personalized cinematic home tours. The AI knows the buyer; it finds a real listing and renders a tour of that home restyled to their taste.
> **Context: 24-hour hackathon build. Submission: Friday night. Two engineers. Demo > everything.**

---

## 1. One-paragraph product definition

VISTA is a buyer-side demo of a seller-side business. The user converses with an agent that already holds deep personal context (taste profile, life situation, mood boards). The agent surfaces real listings, and on request generates a cinematic video tour of the actual home **restyled to the user's aesthetic** — same rooms, same architecture, new decor. The demo wow is the personalized tour; the pitched business model is seller-side (agents/brokerages pay for tour generation; the embedded "see this home in your style" widget collects buyer taste profiles → future buyer-side agent).

## 2. Non-negotiable demo requirements

1. **The stage demo runs entirely on pre-generated, locally cached assets.** The app simulates live generation with an ~8s loading state. Final videos must exist as files on local disk, playable outside the app as a fallback.
2. **Two taste profiles, one house.** The same hero listing rendered in two divergent aesthetics (Profile 1: Pablo's real profile; Profile 2: deliberately contrasting persona). Back-to-back playback is the proof of personalization.
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
/agent         # Engineer B: LLM agent, mem0 client, tavily client, style-spec generator
/app           # Engineer B: React frontend (chat, context panel, listing cards, slider, player)
/assets
  /listings/<id>/raw/          # original photos
  /listings/<id>/restyled/<profile_id>/   # edited stills
  /listings/<id>/video/<profile_id>/      # clips + final stitched tour.mp4
/specs         # style spec JSONs (the A↔B contract)
/deck          # pitch + future-work slides
```

- Python for /pipeline and /agent. React (Vite) for /app. No databases — JSON files on disk are fine for 24h.
- All secrets in `.env`, never committed.
- Asset filenames are the API: `<listing_id>__<room>__<profile_id>.{png,mp4}`. Engineer B's app reads assets by this convention; no other coupling.

## 8. Decision log

- Path: demo buyer-side experience, pitch seller-side business (trojan-horse GTM)
- Video generation: **Option A** (commercial free-tier credits, pre-generated). Option B = future work.
- Restyle model: decide by H2 — Nebius-hosted Kontext if it exists, else Gemini image editing.
- Conflict-of-interest rule for the pitch, if asked: seller money buys generation/distribution, never ranking.
