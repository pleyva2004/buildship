# /assets — the filename API (the A↔B contract)

**Asset filenames are the integration surface between the pipeline and the app.**
Engineer A writes files here by the convention below; Engineer B's app builds the same
paths in `app/src/assets.js` and reads them. No other coupling exists — no shared code,
no queue, no manifest beyond `listings/index.json`.

## Convention

```
<listing_id>__<room>.<ext>                      # raw original photo
<listing_id>__<room>__<profile_id>.{png,mp4}    # restyled still / room clip
tour.mp4                                        # final stitched tour, per profile
```

## Layout

```
assets/
  listings/
    index.json                  # listing inventory (see below)
    hero/                       # the one fully-treated listing
      raw/                      # original photos:        hero__living.jpg, hero__office.jpg, …
      restyled/<profile_id>/    # edited stills:          hero__living__jake_v1.png, …
      video/<profile_id>/       # clips + final tour:     tour.mp4
  music/                        # one track for the ffmpeg stitch
```

Profiles: `jake_v1`, `pablo_v1`. Hero rooms (from `index.json`):
`living, kitchen, primary_bed, office, dining, exterior`.

## index.json

The single listing inventory. Consumed in two places: injected verbatim into the
agent's system prompt (so the LLM can never invent a home) and served raw via
`GET /api/listings`. Per listing: `listing_id`, `title`, `price`, `location`,
`beds/baths/sqft`, `summary`, `hero` flag, `rooms`, `card_photo`, and
`match_notes` keyed by profile_id (the "why it fits YOU" chips on the listing cards).
Only `hero` gets rooms and renders; `alt1`/`alt2` exist to be recommended against.

## Rules

- Every consumer must degrade gracefully when a file is missing — the app swaps in a
  branded placeholder (stills) or a fallback notice (video). Missing assets are an
  expected state during the build, never an error.
- Final tour videos must be playable outside the app (`open assets/listings/hero/video/jake_v1/tour.mp4`)
  — that's the stage fallback of last resort.
- `make app` symlinks this tree into `app/public/assets` so Vite serves it at `/assets/*`.
