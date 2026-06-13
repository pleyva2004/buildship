---
name: vista-restyle-tour
description: >
  Generate a personalized restyled walkthrough tour for a VISTA listing — the
  diffusion-pipeline half (Engineer A). Trigger whenever the user asks to restyle
  a listing, build/render/generate the walkthrough tour, "render austin_01",
  "generate the tour for pablo_v1" / "jake_v1", "restyle the rooms", "make the
  Ken Burns fallback", "stitch the tour", "build the cinematic home tour", or
  anything about turning raw listing photos + a style spec into a tour.mp4.
  Always use this skill for VISTA tour generation — don't hand-roll it.
---

# VISTA Restyle Tour Skill

You are driving VISTA's generation pipeline: **raw listing photos + a locked style spec → a cached, cinematic walkthrough `tour.mp4` of the same real home, restyled to the buyer's taste.** This is a batch generator, not a chatbot — most "intake" is reading files, and you only stop for the human at two gates: **after the restyle (before spending video credits)** and **after the tour renders**.

Be concise and direct. Work one listing × one profile at a time.

**Prime directives (these override everything below):**
1. **Architecture is sacred.** Windows, doors, room geometry never change. A render that moves a wall is rejected, no exceptions — it breaks the "same real house" promise and the slider.
2. **Inject the spec verbatim.** Every room edit carries the spec's `palette_hex` + `materials` literally. This is the only lever that keeps the whole tour one coherent taste.
3. **Fallback first, never deleted.** The Ken Burns tour is built before any video model is touched, and is itself a complete deliverable.
4. **Pre-generated only.** Nothing here runs live in the demo. Outputs land at the exact convention paths — the filename *is* the API.

---

## STEP 0 — Select the target

Lock two things before anything else:

- **`listing_id`** — default `austin_01` (1724 Canon Yeomans Trl, Austin). Confirm if the user named another.
- **`profile_id`** — `pablo_v1` (warm mid-century modern), `jake_v1` (bright Scandinavian minimalist), or **both** (the two-profile reveal *is* the demo).

The profile is the propagating choice — it selects the style spec that drives every restyle. If the user says "build the tour" without specifying, ask once:

> "Which profile — `pablo_v1`, `jake_v1`, or both? And which listing (default `austin_01`)?"

If both profiles: run the whole flow for one, then repeat for the other. Same house, divergent taste.

---

## STEP 1 — Load inputs (read files; don't ask what the files already say)

Load, don't interview:

- **Style spec** → `/specs/<profile_id>.json` — `aesthetic_name`, `palette_hex`, `materials`, `furniture_vocabulary`, `lighting_mood`, `hard_constraints`. This is frozen; never edit it here.
- **Listing metadata** → `/assets/listings/<listing_id>/listing.json` — derive target rooms from `rooms_available` and the walkthrough order.
- **Raw photos** → list `/assets/listings/<listing_id>/raw/` to confirm what rooms you actually have.

**Walkthrough order** (natural tour, drives clip/stitch sequence):
`exterior → living → kitchen → dining → bedroom → bathroom → office → outdoor`
(use only rooms present; `_alt` angles are extras, not part of the primary sequence.)

Only **ask the human** for what isn't in a file:
- **Video backend** for Step 4b — `kling` / `hailuo` / `higgsfield` / `luma` (whichever credits are stacked). Default to `higgsfield`.
- **Seconds per room** — default 5s. **Music track** — default `/assets/music/score.mp3`.

---

## STEP 2 — Asset prep

- **Verify** one raw photo exists per target room. If a target room is missing, tell the user explicitly which — don't invent it (the house is real and fixed; there is no "generate a base" path).
- **Crop the Zillow chrome.** The raw photos are page screenshots carrying UI (nav arrows, "X of 22" badge, agent watermark, side gutters). **Crop every photo to the bare image area before any restyle** — otherwise the diffusion model restyles the arrows too. Keep originals; write crops in place or to a working copy.
- Register/stage inputs for the chosen backend (e.g. `mcp__higgsfield__media_upload` if routing stills through Higgsfield later).

---

## STEP 3 — Restyle every room  ◀ creative core + APPROVAL GATE

For each target room, produce a restyled still that **keeps the architecture and applies the spec**.

- **Backend:** `RESTYLE_BACKEND` — Nebius-hosted **Flux Kontext** if available, else **Gemini** image editing.
- **Prompt construction** (spec injected verbatim — palette hexes + named materials in *every* prompt):
  ```
  Restyle this <room> in a <aesthetic_name> aesthetic.
  Strict palette (use only): <palette_hex joined>.
  Materials: <materials>.  Furniture: <furniture_vocabulary>.
  Lighting: <lighting_mood>.
  HARD CONSTRAINTS: <hard_constraints>. Same room, same architecture — only decor changes.
  ```
- **Output path (exact):** `/assets/listings/<id>/restyled/<profile>/<id>__<room>.png`

**QA every output before moving on:**
- Architecture preserved? (windows/doors/geometry unchanged) — if not, **reject + regenerate** that room.
- On-palette and consistent with the other rooms? If it drifts, tighten the injection (hexes + materials) before swapping models.

**GATE — present the restyled set as a contact sheet and get approval:**
> "Restyled <N> rooms for <profile>. Architecture preserved, palette consistent? Approve to build the tour, or flag rooms to redo."

Do **not** spend video credits until the stills are approved. This is the natural cost checkpoint.

---

## STEP 4 — Assemble the tour

**4a — Ken Burns fallback (BUILD THIS FIRST, every time).**
ffmpeg pan/zoom over the approved restyled stills, in walkthrough order, with crossfades + one music track. Gentle motion only. This is a complete, submittable tour with zero model dependency.
→ writes `/assets/listings/<id>/video/<profile>/tour.mp4`
Verify it plays standalone before going further. If anything downstream fails, this *is* the demo.

**4b — Option-A motion video (the upside, all offline).**
- Per room: send the restyled still to the chosen video backend with a **slow cinematic push-in / gentle pan** prompt. Seed with `start_image` = the restyled still.
  - Higgsfield: `mcp__higgsfield__generate_video` (confirm model ID via `mcp__higgsfield__models_explore`; display with `mcp__higgsfield__job_display`; check `mcp__higgsfield__balance` if credits are a concern).
- Retrieve each clip → `/assets/listings/<id>/video/<profile>/<id>__<room>.mp4`
- **Stitch** clips in walkthrough order with ffmpeg: crossfades + one music track → overwrite `tour.mp4`.
- Aggressive motion reads as AI soup — keep it slow.

---

## STEP 5 — Review & iterate

Present the tour and verify:
> "Tour for <profile> is rendered. Plays clean?"

- **Standalone playback** — `tour.mp4` plays in a bare player outside the app. ✅ required.
- **Contract check** — every output is at its exact convention path; nothing else is required of Engineer B.
- **Regenerate rejects** — bad room → redo just that room's still (Step 3) or clip (Step 4b), re-stitch.
- **Second profile** — if doing both, repeat Steps 1–5 for the other profile.

---

## Notes & Rules

- **Architecture preservation is rule #1.** Reject any restyle that alters structure — tighten `hard_constraints`, never ship a moved wall.
- **Spec injected verbatim** into every room edit — palette hexes + materials, every prompt. It's the consistency lever; reach for it before changing models.
- **Restyle approved before video.** The Step 3 gate exists to protect video credits.
- **Fallback is sacred** — Ken Burns tour built first (Step 4a), never deleted, always playable standalone.
- **Pre-generated only** — no live generation in the demo path. The app fakes an ~8s "generating" loader over the cached file.
- **Filenames are the API** — exact paths: `raw/<id>__<room>.png`, `restyled/<profile>/<id>__<room>.png`, `video/<profile>/<id>__<room>.mp4`, `video/<profile>/tour.mp4`. No other coupling to Engineer B.
- **Crop screenshots first** — strip Zillow chrome before restyling.
- **Gentle motion only** — slow pushes/pans; logo/brand holds are Engineer B's app, not this pipeline.
- **One listing × one profile at a time.** For the two-profile reveal, run the flow twice.
- **Tools:** restyle via `RESTYLE_BACKEND` (Flux Kontext / Gemini); video via `VIDEO_BACKEND` (Kling / Hailuo / Higgsfield / Luma — Higgsfield MCP: `media_upload`, `generate_video`, `models_explore`, `job_display`, `balance`); ffmpeg via shell for fallback + stitch. Confirm exact MCP tool IDs with `tool_search` if unsure.
- **If generation fails** — explain briefly, fall back one tier (or to Ken Burns), and offer a retry with adjusted parameters.
- **Scope:** this skill is the generation pipeline only. Conversation, memory, listing discovery, the app, and the slider UI are Engineer B — out of scope here.
