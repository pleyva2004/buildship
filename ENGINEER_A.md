# ENGINEER A — Generation Pipeline Owner

**Mission:** Every pixel the judges see. You own photos-in → cinematic-tour-out. If your pipeline slips, the demo degrades gracefully (Ken Burns); it never dies.

---

## Role

Owner of `/pipeline` and `/assets`. You consume style specs from `/specs` (produced by Engineer B's agent) and produce restyled stills and final tour videos at the agreed asset paths. The filename convention IS the integration contract — honor it and you and B never block each other.

## Responsibilities

1. **Restyle engine.** Instruction-based image editing per room with the locked style spec injected verbatim. The hard problem is **cross-room taste consistency** — same palette, same furniture vocabulary in every shot. If outputs drift, tighten the spec injection (palette hexes + named materials in every prompt) before trying a different model.
2. **Architecture preservation.** Restyled rooms must keep geometry, windows, doors. A render that moves a wall destroys the "same real house" claim and the slider moment. Reject and regenerate any output that violates this.
3. **Ken Burns fallback.** ffmpeg pan/zoom over restyled stills, crossfades, one music track. This is built FIRST and ships by H6. It is a complete, submittable demo on its own.
4. **Option A video generation.** Queue image-to-video jobs on stacked free-tier credits (Kling / Hailuo / Higgsfield / Luma). Slow camera pushes and gentle pans only — aggressive motion reads as AI soup. Queue early; render time is dead time you spend elsewhere.
5. **Stitch + score.** ffmpeg assembly: clip order follows a natural walkthrough (entry → living → kitchen → bedroom → bath/outdoor), crossfades, ONE music track. Music carries more of the wow than you expect — pick something cinematic, not royalty-trap.
6. **Asset caching.** Final `tour.mp4` files for both profiles exist on local disk AND play in a bare video player outside the app. Verify on the actual demo machine.
7. **(Stretch, only if ahead at H15+) Option B side quest.** Spin up Wan 2.2 or LTX-Video on Nebius GPU credits for the "best use of Nebius" flex. Abort instantly if it threatens the critical path.

## Hard deliverables (acceptance criteria)

| # | Deliverable | Done means | Due |
|---|---|---|---|
| A1 | Restyle model chosen + one room restyled end-to-end | Spec-conditioned edit preserves architecture, looks intentional | **H6** |
| A2 | Ken Burns fallback tour (Profile 1, full house) | Watchable 60–90s mp4 with music, on disk | **H6** |
| A3 | All rooms restyled, BOTH profiles | 5–6 rooms × 2 profiles, visibly consistent within each profile, divergent across profiles | **H12** |
| A4 | All Option A video clips queued | Every room/profile job submitted to a video model | **H12** |
| A5 | Both final stitched tours | `tour.mp4` for profile 1 and 2, cached locally, plays standalone | **H18** |
| A6 | Asset freeze | `/assets` complete, paths verified against app, no further generation | **H21** |

## Failure playbook

- Restyle model inconsistent by H8 → simplify to one bolder, reliable style transfer per profile. Coherence beats sophistication.
- Video credits exhausted / queue stalled by H15 → ship Ken Burns as the primary tour. It was always good enough to win on.
- Extraction blocked → photos are manually downloaded from the hero listing tonight anyway; you never depend on Tavily.

## What you do NOT do

No frontend. No agent work. No live-generation endpoint. No scraper. No Option B before A5 is done.
