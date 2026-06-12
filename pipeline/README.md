# /pipeline — restyle + video pipeline (Python, Engineer A)

**Not yet built.** This directory will hold Engineer A's side: per-room restyling,
video generation queue management, the ffmpeg stitch, and the Ken Burns fallback
(which per CLAUDE.md §3 must exist first, by H6).

## Contract with the rest of the repo (already frozen)

- **Input:** style specs in [/specs](../specs/README.md) — injected *verbatim* into
  every room's restyle prompt — plus raw photos from `assets/listings/<id>/raw/`.
- **Output:** files written under `assets/listings/…` by the filename convention in
  [assets/README.md](../assets/README.md). The app reads them by path; nothing else
  crosses the A↔B boundary.
- Everything is pre-generated offline. Nothing here runs in the live demo path.

See [ENGINEER_A.md](../ENGINEER_A.md) for the task breakdown and CLAUDE.md §3/§8 for
the model decisions (restyle: Nebius-hosted Kontext or Gemini image editing; video:
commercial free-tier credits, Option A).
