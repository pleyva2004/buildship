# VISTA — Diffusion Pipeline

> **Branch:** `pablo/diffusion-pipeline` · **Owner:** Engineer A (Pablo) · **Domain:** `/pipeline` + `/assets`
>
> Raw listing photos in → a cinematic, personalized home tour out. This branch is the *generation* half of VISTA: the diffusion restyle, the video assembly, and the fallback that guarantees a demo exists no matter what.

---

## The use case

**VISTA shows you a real home for sale — restyled to *your* taste — as a cinematic video tour.**

A buyer talks to an agent that already knows them (their aesthetic, life situation, mood boards). The agent surfaces a real listing and, on request, generates a tour of *that actual house* with **the same rooms, same architecture, new decor** in the buyer's style. Two people see the same listing rendered two completely different ways — that back-to-back reveal is the proof of personalization.

It's a buyer-side demo of a seller-side business: brokerages pay to generate these tours and embed a "see this home in your style" widget that collects buyer taste profiles. (Full product context: [`CLAUDE.md`](./CLAUDE.md).)

This branch doesn't do conversation, memory, or UI — that's Engineer B (`jake/*`). **This branch makes every pixel the judges see.**

---

## What this branch does

The heart of the branch is the **diffusion restyle**: an instruction-based image-editing model (Nebius-hosted Flux Kontext, with Gemini image editing as the backup) edits each room *in place* — keeping the walls, windows, and geometry, swapping only the decor — conditioned on a locked style spec.

```
  raw room photo
        │
        ▼
  ┌─────────────────────────┐   style spec injected verbatim
  │  DIFFUSION RESTYLE       │◄── (palette hexes · materials · furniture
  │  edit decor, keep walls  │     vocabulary · lighting · hard constraints)
  └─────────────────────────┘
        │  restyled still (per room, per profile)
        ▼
  ┌─────────────────────────┐
  │  IMAGE-TO-VIDEO          │   slow cinematic push-in / gentle pan
  │  (Option A, pre-gen)     │   Kling · Hailuo · Higgsfield · Luma
  └─────────────────────────┘
        │  per-room clips
        ▼
  ┌─────────────────────────┐
  │  ffmpeg STITCH + SCORE   │   walkthrough order · crossfades · one track
  └─────────────────────────┘
        │
        ▼
   cached tour.mp4   ──►  Engineer B's app plays it behind a simulated ~8s "live" loader

  FLOOR (built first, never deleted):
   KEN BURNS FALLBACK — ffmpeg pan/zoom over the restyled stills + crossfades + music.
   A complete, submittable tour on its own, even if every video model falls over.
```

**Why "diffusion"?** The restyle is the only place a generative image model touches the pipeline, and it's where the whole illusion lives. Get the diffusion edit right — same house, coherent taste — and the slider and the two-profile reveal both land. Everything downstream is deterministic ffmpeg.

---

## Three rules that protect the demo

1. **Architecture preservation — it's the *same real house*.** Windows, doors, and room geometry are locked; only decor changes. A render that moves a wall kills the original-vs-restyled slider. Reject and regenerate anything that violates it.
2. **Cross-room taste consistency.** The style spec's palette hexes and named materials are injected into *every* room's edit prompt, so the tour reads as one coherent taste — not per-room filters. If outputs drift, tighten the injection before swapping models.
3. **Pre-generated, never live.** All generation happens offline; the demo plays cached files. The "generating your tour…" loader is theater. Final `tour.mp4`s must play standalone outside the app.

---

## The integration contract (with Engineer B)

Two handoffs, and only two — protect them above all.

| Direction | Artifact | Detail |
|---|---|---|
| **B → A** (in) | `/specs/<profile_id>.json` | Locked style spec: aesthetic name, `palette_hex`, `materials`, `furniture_vocabulary`, `lighting_mood`, `hard_constraints`. Frozen by H4. |
| **A → B** (out) | `/assets/.../<listing_id>__<room>.png\|mp4` | The filename **is** the API. The app reads assets by this convention — no other coupling. |

**Asset tree:**
```
/assets/listings/<id>/raw/                  original room photos
/assets/listings/<id>/restyled/<profile>/   diffusion-edited stills
/assets/listings/<id>/video/<profile>/      per-room clips + final tour.mp4
```

**Profiles seeded today** (two deliberately divergent tastes — the contrast *is* the demo):

| Spec | Persona | Aesthetic |
|---|---|---|
| `specs/pablo_v1.json` | Pablo (real) | warm mid-century modern — walnut, boucle, brushed brass, golden hour |
| `specs/jake_v1.json` | Jake (real) | bright Scandinavian minimalist — pale oak, linen, matte black, cool daylight |

---

## Current status

**Hero listing locked → `austin_01`**
1724 Canon Yeomans Trl, Austin, TX 78748 · 3 bd / 2.5 ba / 1,422 sqft · $350,000 · [Zillow](https://www.zillow.com/homedetails/1724-Canon-Yeomans-Trl-Austin-TX-78748/29513162_zpid/)

- ✅ **16 raw photos** classified and organized into the filename convention — `living` / `kitchen` / `bedroom` / `bathroom` / `dining` / `office` / `exterior` / `outdoor` (plus `_alt` angles). All six target rooms present.
- ✅ **Style-spec contract** + JSON schema in `/specs`; two divergent profiles seeded.
- ✅ Repo + asset scaffold in place.
- ⏳ **Next:** lock the restyle backend (H2: Nebius Flux Kontext vs Gemini) → restyle the hero rooms for both profiles → build the Ken Burns fallback tour on disk → queue Option A image-to-video clips → stitch + score both final tours.

> ⚠️ The raw photos are Zillow *page screenshots* — they carry UI chrome (nav arrows, "X of 22" badge, agent watermark, side gutters). **Crop to the photo area before restyling**, or the diffusion model will try to restyle the arrows too.

---

## Layout (Engineer A's domain)

```
/pipeline    restyle · video-queue · ffmpeg stitch · ken-burns fallback   ← mine (code lands here)
/assets      raw photos in  ·  restyled stills + tour.mp4 out             ← mine
/specs       style-spec contract                                         ← consumed (B produces)
```

The hour-by-hour deliverable plan and failure playbook live in [`ENGINEER_A.md`](./ENGINEER_A.md); the shared clock is in [`TIMELINE.md`](./TIMELINE.md).
