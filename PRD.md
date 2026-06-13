# Diffusion Pipeline — Product Requirements Document

> **Branch:** `pablo/diffusion-pipeline` · **Owner:** Engineer A (Pablo) · **Domain:** `/pipeline` + `/assets`
> **Scope of this PRD:** *only* the diffusion pipeline — the component that turns raw listing photos + a locked taste spec into a **personalized cinematic walkthrough video** of the real home. The agent, memory, conversation, and app are **out of scope here** (Engineer B). For whole-product context, see [`CLAUDE.md`](./CLAUDE.md) and [`README.md`](./README.md).

---

## 1. What this component is

**Input a real home's photos and a buyer's taste spec → output a cinematic walkthrough video of that exact home, restyled to the buyer's aesthetic.**

Same rooms, same architecture, new decor. The pipeline is the *generation* half of VISTA: a diffusion restyle of every room, assembled into one scored walkthrough tour — with a guaranteed fallback so a watchable tour always exists.

It does not talk to the user, hold memory, pick listings, or render UI. It is a batch generator: **photos + spec in, cached `tour.mp4` out.**

## 2. Role in the product (one paragraph)

VISTA shows a buyer a real for-sale home restyled to their taste. The buyer-facing experience (chat, memory, listing recommendation, slider UI) is Engineer B's. **This pipeline produces the thing the buyer actually watches.** It consumes a locked **style spec** (`/specs/<profile>.json`) and emits cached assets named by a strict convention; those two interfaces are the *only* coupling to the rest of the system.

## 3. Goals & non-goals

**Goals**
- Produce a personalized walkthrough video of the hero home for **two divergent taste profiles**, each visibly coherent and clearly different from the other.
- Keep every restyled room recognizably the **same real house** (architecture preserved).
- Guarantee a complete, submittable tour exists **regardless of any model's success** (the fallback).
- Deliver everything **pre-generated and cached** — nothing in this pipeline runs live during the demo.

**Non-goals (explicitly not this component)**
- ❌ Conversation, memory (mem0), taste import, listing discovery — Engineer B.
- ❌ The app, the original-vs-restyled slider UI, the context panel — Engineer B (this pipeline *supplies the assets* the slider compares).
- ❌ Live, on-stage generation of any kind.
- ❌ Web scraping (photos are provided as raw inputs).
- ❌ Self-hosted video models on owned GPUs (future-work roadmap, not built).

## 4. Inputs & outputs (the contracts)

**Inputs**
| Input | Source | Detail |
|---|---|---|
| Raw room photos | `/assets/listings/<id>/raw/` | One per room, named `<id>__<room>.png` (+ `_alt` angles) |
| Locked style spec | `/specs/<profile_id>.json` | Aesthetic name · `palette_hex` · `materials` · `furniture_vocabulary` · `lighting_mood` · `hard_constraints`. Frozen by H4; **injected verbatim** into every room edit. |
| Listing metadata | `/assets/listings/<id>/listing.json` | Address, rooms available, etc. (used for ordering/labeling only) |

**Outputs** (the filename **is** the API — Engineer B reads assets by it, nothing else)
```
/assets/listings/<id>/restyled/<profile>/   diffusion-edited stills   <id>__<room>.png
/assets/listings/<id>/video/<profile>/      per-room clips            <id>__<room>.mp4
/assets/listings/<id>/video/<profile>/      final walkthrough         tour.mp4   ◄── the deliverable
```

## 5. Core use cases (pipeline operations)

- **UC1 — Restyle one room.** Given a raw room photo + a locked spec, produce a restyled still that preserves architecture and applies the aesthetic. *(The atomic unit; everything builds on this.)*
- **UC2 — Restyle a full home for a profile.** Run UC1 across all target rooms, enforcing **cross-room consistency** (same palette + materials everywhere) so the set reads as one taste.
- **UC3 — Assemble a walkthrough tour.** Order the restyled rooms into a natural walkthrough (entry → living → kitchen → bedroom → bath/outdoor), add motion, crossfades, and one music track → `tour.mp4`.
- **UC4 — Build the Ken Burns fallback.** Produce a complete pan/zoom-over-stills tour with ffmpeg only — no video model — as the guaranteed floor. *Built first.*
- **UC5 — Generate motion clips (Option A).** Queue restyled stills to a free-tier image-to-video model (slow cinematic push/pan), then retrieve finished clips to the asset path. All offline.
- **UC6 — QA & regenerate.** Reject any restyle that moves a wall, drops a window, or drifts off-palette; regenerate that single room. Architecture and consistency gate every output.

## 6. Functional requirements

- **FR1 — Spec-conditioned restyle.** Every room edit injects the spec's palette hexes + named materials verbatim. Aesthetic is determined by the spec, not hardcoded per room.
- **FR2 — Architecture preservation.** Windows, doors, and room geometry are unchanged across the restyle. A render that alters structure is rejected.
- **FR3 — Cross-room consistency.** Within a profile, palette and furniture vocabulary are consistent room-to-room.
- **FR4 — Two profiles, one house.** The full hero home is generated for both `pablo_v1` and `jake_v1`, visibly divergent.
- **FR5 — Deterministic assembly.** Tour stitching is reproducible: fixed room order, fixed transitions, one music track.
- **FR6 — Cached & standalone.** Final `tour.mp4`s exist on disk and play in a bare video player outside the app.
- **FR7 — Guaranteed fallback.** A Ken Burns tour exists by H6 and is never deleted (it is itself a complete deliverable).
- **FR8 — Contract compliance.** All outputs land at the exact convention paths; nothing else is required of Engineer B.

## 7. Acceptance criteria (demo-critical)

| # | Done means |
|---|---|
| AC1 | One hero room restyled end-to-end: spec-conditioned, architecture preserved, looks intentional |
| AC2 | Ken Burns fallback tour for one full profile on disk, watchable (~60–90s) with music |
| AC3 | All target rooms restyled for **both** profiles — consistent within, divergent across |
| AC4 | Both final `tour.mp4`s stitched, scored, cached, and **playable standalone** |
| AC5 | Asset tree complete and verified against Engineer B's app paths |

## 8. Pipeline architecture

```
  raw room photo  +  /specs/<profile>.json
        │                    │  (palette · materials · furniture · lighting · constraints)
        ▼                    ▼
  ┌─────────────────────────────────┐
  │  DIFFUSION RESTYLE (per room)    │   instruction-based image edit; spec injected verbatim
  │  edit decor · keep architecture  │   backend: Nebius Flux Kontext  ·  fallback: Gemini image edit
  └─────────────────────────────────┘
        │  restyled still  (/restyled/<profile>/<id>__<room>.png)
        ▼
  ┌─────────────────────────────────┐
  │  IMAGE-TO-VIDEO (Option A)       │   slow cinematic push-in / gentle pan, pre-generated
  │  Kling · Hailuo · Higgsfield ·   │   (offline queue; never on stage)
  │  Luma                            │
  └─────────────────────────────────┘
        │  per-room clip  (/video/<profile>/<id>__<room>.mp4)
        ▼
  ┌─────────────────────────────────┐
  │  ffmpeg STITCH + SCORE           │   walkthrough order · crossfades · one music track
  └─────────────────────────────────┘
        │
        ▼
   tour.mp4   ───►   Engineer B's app plays it behind a simulated ~8s "live" loader

  GUARANTEED FLOOR (built first, never deleted):
   KEN BURNS FALLBACK — ffmpeg pan/zoom over the restyled stills + crossfades + music.
   A complete walkthrough tour with zero dependency on any video model.
```

## 9. Key decisions

- **Restyle backend (decide by H2):** Nebius-hosted **Flux Kontext** if available, else **Gemini** image editing. The diffusion edit is where the illusion lives — get it right before optimizing anything downstream.
- **Video = Option A only:** stacked commercial free-tier credits, **pre-generated**. Self-hosted video (Option B) is documented future work, not built.
- **Consistency lever:** if restyles drift room-to-room, *tighten spec injection* (hexes + materials in every prompt) before swapping models.
- **Motion is gentle:** slow pushes and pans only — aggressive motion reads as AI soup.

## 10. Concrete instance (loaded today)

- **Hero listing — `austin_01`:** 1724 Canon Yeomans Trl, Austin, TX 78748 · 3 bd / 2.5 ba / 1,422 sqft · $350,000. 16 raw photos organized into the convention (living, kitchen, bedroom, bathroom, dining, office, exterior, outdoor + `_alt`s). All six target rooms present.
- **Two divergent profiles** (the contrast is the demo):
  - `pablo_v1` — **warm mid-century modern** (walnut, boucle, brushed brass, golden-hour light)
  - `jake_v1` — **bright Scandinavian minimalist** (pale oak, linen, matte black, cool daylight)
- ⚠️ Raw photos are Zillow **page screenshots** carrying UI chrome (nav arrows, "X of 22" badge, agent watermark, gutters). **Crop to the photo area before restyling.**

## 11. Risks & fallback playbook

| Risk | Mitigation |
|---|---|
| Restyle drifts / inconsistent across rooms by H8 | Simplify to one bolder, reliable style transfer per profile — coherence beats sophistication |
| Restyle alters architecture | Reject + regenerate; tighten `hard_constraints`; never ship a wall that moved |
| Video credits exhausted / queue stalled by H15 | Ship the **Ken Burns fallback** as the primary tour — it was always good enough to win on |
| Screenshot chrome corrupts edits | Batch-crop raw photos to the image area before any restyle |

## 12. Glossary

- **Style Spec** — the locked JSON encoding one taste profile; consumed verbatim by the restyle.
- **Restyle** — diffusion image edit of a room photo: new decor, preserved architecture.
- **Walkthrough tour** — the final stitched, scored video of a listing's restyled rooms (`tour.mp4`).
- **Asset convention** — `<listing_id>__<room>.{png,mp4}`; the only interface Engineer B depends on.
- **Ken Burns fallback** — pan/zoom-over-stills tour built with ffmpeg; the guaranteed, model-independent floor.
- **Option A / B** — A = commercial free-tier video credits, pre-generated (shipped); B = self-hosted GPU video (future work).
