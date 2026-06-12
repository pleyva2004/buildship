# Design 03 — Listing Discovery & Index (B2)

> **A-blocking deliverable.** Engineer A cannot restyle a single room until hero photos
> land in `/assets/listings/hero/raw/`. Do this before anything clever. Due H4.

## 1. What this delivers

- `agent/listings.py` + `make listings`
- `assets/listings/index.json` — the 3-listing inventory the agent recommends from
- Hero listing photos on disk: `assets/listings/hero/raw/hero__<room>.jpg`

## 2. Listing index schema (`assets/listings/index.json`)

The agent and the app both read this file. No DB.

```json
{
  "listings": [
    {
      "listing_id": "hero",
      "title": "Modern 4BR in Travis Heights",
      "price": "$865,000",
      "location": "Austin, TX",
      "beds": 4, "baths": 3, "sqft": 2410,
      "summary": "Bright corner lot, big windows, open plan...",
      "source_url": "https://...",
      "hero": true,
      "rooms": ["living", "kitchen", "primary_bed", "office", "dining", "exterior"],
      "card_photo": "assets/listings/hero/raw/hero__exterior.jpg",
      "match_notes": {
        "jake_v1": ["daylight office", "walkable", "fenced yard"],
        "pablo_v1": ["wood detailing", "warm afternoon light"]
      }
    },
    { "listing_id": "alt1", "...": "metadata only, no photo treatment" },
    { "listing_id": "alt2", "...": "metadata only" }
  ]
}
```

- Only `hero` gets the full treatment. `alt1`/`alt2` exist so the agent's recommendation
  moment shows genuine choice (2–3 cards), per ENGINEER_B.md §4. Card photos for alts can
  be a single still each.
- `rooms[]` is the canonical room list — it drives A's render queue AND the app's tour
  view. **Pick 5–6 rooms and freeze the names at H4** (they're baked into filenames).
- `match_notes` gives the agent honest per-profile reasoning material ("for you, Jake:
  the office gets morning light") without hallucinating.

## 3. Acquisition flow

```
Tavily search ("4 bedroom listing Austin bright open plan...")   [LIVE]
  └─► pick hero by photo quality criteria (below)
  └─► tavily extract on listing page → title/price/location/summary
  └─► photos: extract if possible, else MANUAL DOWNLOAD (sanctioned by CLAUDE.md §5)
        └─► save as hero__<room>.jpg, normalize: JPEG, max 2048px long edge, strip EXIF
```

Hero photo criteria (TIMELINE pre-clock): **bright, wide-angle, decluttered, 5–6 distinct
rooms**. Wide-angle matters because the restyle model must keep geometry recognizable for
the slider moment.

### MOCK backend
`tavily_client` MOCK returns a canned search/extract response from `agent/mocks/`. The
index.json it produces is byte-identical to what we'd hand-write — so the agent and app
are unblocked **today**, before the Tavily key exists. When the key lands, run live once,
keep whichever index is better, and freeze.

**Important**: Tavily is one-time tooling, not a runtime dependency. After H4 the agent
reads only `index.json`. The Tavily call is demoed/credited in the deck, not on the
critical path on stage.

## 4. Room-name freeze (mini-contract with A)

`living, kitchen, primary_bed, office, dining, exterior` (adjust to the actual hero house,
then freeze). These strings appear in: asset filenames, index.json `rooms[]`, app tour
view labels. One source of truth: `index.json`.

## 5. Acceptance (B2)

- [ ] `index.json` with 3 listings (1 hero, 2 alts) exists and parses.
- [ ] 5–6 raw hero photos on disk, named `hero__<room>.jpg`, normalized.
- [ ] Room names frozen and communicated to A (the H4 sync point).
- [ ] Works fully in MOCK mode (manual photos + canned metadata is a valid pass).
