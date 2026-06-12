# TIMELINE.md — 24-Hour Clock to Friday Night Submission

Wall-clock column assumes **Thursday 8:00 PM start → Friday 8:00 PM submission**. If the official clock differs, shift every row by the same offset; relative hours (H#) are the source of truth. Sync points are mandatory, 5 minutes max, standing up.

---

## Pre-clock (tonight, before H0)

- [ ] Both engineers stack free-tier signups: Kling, Hailuo, Higgsfield, Luma (Option A credits in hand)
- [ ] Activate all five sponsor codes: Composio `SHIP_BUILDERS`, Nebius Token Factory `BUILDER-SHIP-HACK`, Nebius GPU challenge, Tavily `TVLY-7CCN692Z`, mem0 `SHIPBUILDERS`
- [ ] Confirm whether Nebius hosts an instruction-based image-editing model (Kontext) — A's H2 decision input
- [ ] Pick hero listing: bright, wide-angle, decluttered photos, 5–6 distinct rooms; manually download photos as insurance

## The clock

| Hours | Wall clock | Engineer A (pipeline) | Engineer B (agent/app) | Sync point |
|---|---|---|---|---|
| H0–H2 | Thu 8–10 PM | Repo scaffold `/pipeline`; restyle model bake-off; **decide model by H2** | Repo scaffold `/agent` `/app`; mem0 + Nebius keys live; draft profile schema | **H2: model decision locked. No deliberation past it.** |
| H2–H4 | Thu 10 PM–12 AM | First room restyled with hand-written spec | **B1, B2 due:** specs frozen, listings indexed, raw photos in `/assets` | **H4: schema freeze. A switches to generated specs.** |
| H4–H6 | Fri 12–2 AM | **A1, A2 due:** one room end-to-end + full Ken Burns fallback tour on disk | Agent loop v0: mem0 recall + listing recommendation | **H6: GO/NO-GO #1 — a complete submittable demo exists (fallback). If A1 failing, invoke simplified-style playbook now.** |
| H6–H10 | Fri 2–6 AM | Restyle remaining rooms, Profile 1; start Profile 2 | **B3 due:** agent conversation working in terminal | — |
| H10–H12 | Fri 6–8 AM | **A3, A4 due:** all rooms × both profiles restyled; ALL video clips queued | App shell begun | **H12: GO/NO-GO #2 — clips queued? If credit problems, decide now: Ken Burns becomes primary.** |
| H12–H15 | Fri 8–11 AM | Monitor queues, regenerate rejects, begin stitching arrivals | **B4 due:** app shell clickable with placeholder video | — |
| H15–H18 | Fri 11 AM–2 PM | **A5 due:** both `tour.mp4` stitched, scored, cached | **B5 due:** tour view + slider + fake-live loading wired to real assets | **H18: FEATURE FREEZE. Integration test: full demo path clicked end-to-end on the demo machine.** |
| H18–H21 | Fri 2–5 PM | **A6 due:** asset freeze; verify standalone playback; (optional) Nebius GPU side quest | **B6 due:** deck final, demo script written | **H21: asset + code freeze. Only rehearsal artifacts change after this.** |
| H21–H23 | Fri 5–7 PM | Support rehearsals; fallback drill (play mp4 outside app) | **B7 due:** two timed rehearsals, both engineers present | **H23: submission package assembled.** |
| H23–H24 | Fri 7–8 PM | Buffer | Buffer | **Submit. Never submit at H24:00 — target H23:30.** |

## Synthesis dependencies (who blocks whom)

```
B1 (specs, H4) ──► A3 (both-profile restyles, H12) ──► A5 (tours, H18) ──► B5 (wired app, H18) ──► B7 (rehearsals, H23)
B2 (photos, H4) ─► A1 (first restyle, H6)
```
The only two cross-engineer handoffs are **H4 (B→A: specs + photos)** and **H15–H18 (A→B: cached assets)**. Everything else is parallel. Protect those two handoffs above all.

## Friday-night submission checklist

- [ ] Both `tour.mp4` files play standalone on the demo machine (fallback path tested)
- [ ] App demo path: chat → recommendation → "show my version" → loading → tour → slider → second profile, clicked end-to-end twice
- [ ] Deck: demo arc, trojan-horse GTM slide, future-work slide (Option B / Nebius GPU / ~10x cost), sponsor-usage slide
- [ ] Q&A one-liners rehearsed: data rights, conflict-of-interest rule, "what if the model provider changes pricing" (model-agnostic spec architecture)
- [ ] Repo: README, CLAUDE.md, `.env.example`, no secrets committed
- [ ] Submission form fields drafted at H21, not H23: project name, description, sponsor tools used, video/demo link
- [ ] Backup: tours + deck on a second device or drive

## Standing rules

1. Ken Burns fallback is sacred — it exists by H6 and is never deleted.
2. Decisions expire: any choice not made by its sync point goes to the default (simpler option).
3. No new features after H18. No regeneration after H21.
4. If a sync point slips by >1 hour, cut scope at the NEXT deliverable, not the current one — finish what's in flight.
