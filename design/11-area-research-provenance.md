# 11 · Area research provenance — two kinds of knowledge, never confused

> Source: `Area Research - Design Proposal.html` + live prototype
> `experiences/home-discovery/index.html` (tweak: Area intel = merged|separated).
> Status: **agreed — building the separated design.**

## The problem

The research agent's findings pour into the same memory stream as the
interview. The rail renders them under one header — *"What VISTA knows about
Jake"* — so facts about **Austin** wear the framing of facts about **Jake**.
The buyer reads VISTA claiming to "know" things about them they never said.

- It reads like something you said → erodes trust in the memory layer.
- It muddies the honest stated/inferred provenance work.
- Genuinely good intel is buried as a one-line memory chip.

## The principle

Sort knowledge by **where it came from**, not by topic. Two channels:

| | About **you** | About the **place** |
|---|---|---|
| Source | your interview | VISTA researched the world |
| Nature | subjective — drives ranking | objective — context, not preference |
| Voice | warm, sans, first-person | monospace "showing-its-work", compass glyph |
| Stamp | `from your interview` (clay wash) | `VISTA researched` (hollow mono outline) |

## The design

1. **The rail, split into two tabs** — `You` / `The area` (with count).
   *You* keeps priorities + taste card + readiness + "what you've told me",
   exactly as today, minus the smuggled-in city facts. *The area* is the
   research agent's home: one note card per neighborhood, stamped
   *researched*, the ones in the current set flagged "in your current set"
   and floated first.
2. **Area note on the card** — below the moss why-you chips, a visually
   distinct block (sunken surface, compass icon, researched stamp): the
   neighborhood name + intel. Full text on the lead card, first clause on
   alternates. Chips say how the home matches *you*; the note says what
   VISTA learned about *there*.
3. **One shared stamp component** — `Stamp kind="you"|"researched"` reused by
   rail, card, detail view, and any future narration beat.
4. **Narration seam** — the curated set carries a researched framing line
   ("These sit across N neighborhoods — I read up on each; that intel lives
   under The area tab"). The existing "Researching X…" bubbles already mark
   the act in the thread.

## How it wires (frontend only — no data-model change)

| Piece | Change |
|---|---|
| `agent/researcher.py` | **None.** Already writes `category: "area_research"`, `source: "researched"` — the source of truth is correct; only the UI conflates. |
| `app/src/mock/areas.js` | NEW — mock twin of `agent/mocks/areas.json` (canned intel keyed by neighborhood) + `areaShort()` + `parseAreaFact()` ("`{hood} — {note}`", tolerates "`(for you)`"). |
| `app/src/components/Stamp.jsx` | NEW — shared provenance stamp, two variants; exports the compass/user glyphs. |
| `MemoryRail.jsx` | Core edit: drop the `Area research` group from GROUPS; add the You/Area railtabs; Area panel renders per-hood note cards from `area_research` memories (live findings), canned intel filling not-yet-researched hoods (stage fallback). In-set flag from `inPlayHoods`. |
| `CuratedSet.jsx` | Additive: area note below the why-you chips (`AREA_INTEL[hood] ?? listing.neighborhood_note`), researched framing line above the set. Chip logic untouched. |
| `ListingDetailView.jsx` | "The neighborhood" section gets the researched stamp + intel text. |
| `App.jsx` | Pass `inPlayHoods` (distinct neighborhoods of the visible set) to the rail. |
| `styles.css` | railtabs, stamp, anote (rail), areanote (card), researched-line — on the app's sand/clay tokens, `--mono` stack added. |

Mock-first: the Area tab is never empty on stage — canned intel (the mock
twin) is the baseline "wider reading"; live research findings take over
per-hood as they land (fresh-animate in, same as You facts).

Risk: low · additive · strengthens the existing provenance work.
