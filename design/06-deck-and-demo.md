# Design 06 — Deck & Demo Choreography (B6, B7)

> 2 minutes. Demo > everything. The deck exists to frame the demo, not compete with it.

## 1. The 2-minute script (target 1:50, hard cap 2:30)

| t | Beat | On screen | Line |
|---|---|---|---|
| 0:00 | Setup | App, Jake profile, context panel visible | "This is VISTA. It already knows me — not my clicks, my *taste*. That panel is live from mem0." |
| 0:15 | Conversation | Type scripted S1 line | "Watch the right panel — it's recalling what it knows as it answers." (recall pulse) |
| 0:35 | Recommendation | 2–3 listing cards appear | "Real listings, found via Tavily. It explains *why* each fits me." |
| 0:50 | THE ASK | "Show me my version" | "Now the moment. I ask to see *my* version of this home." |
| 0:55 | Generation | Fake-live 8s loading, palette animating | "It's applying my style spec — derived from my memory layer — to every room." |
| 1:05 | Tour | tour.mp4 plays (Jake / Scandinavian) | Let it breathe. ~15s. No talking over the first 5s. |
| 1:20 | Slider | Drag original⇆restyled on living room | "Same room. Same windows, same walls. **That's the real house** — restyled to me." |
| 1:35 | Reveal | Switch to Pablo → his tour/stills | "My cofounder Pablo asked for the same house. Different person, different home. One listing, every buyer." |
| 1:50 | GTM | Deck: trojan-horse slide | "Sellers pay for tours; every tour collects buyer taste. That's the wedge." |

## 2. Deck (≤7 slides, in /deck)

1. **Title** — VISTA: every buyer sees their own version of your listing.
2. **Problem** — listings are styled for nobody; buyers can't see themselves in them.
3. **Live demo** — (placeholder slide; switch to app).
4. **How it works** — the CLAUDE.md architecture diagram, sponsor logos on their boxes.
5. **Trojan-horse GTM** — seller-side revenue (agents/brokerages pay per tour) → embedded
   "see it in your style" widget → buyer taste graph → buyer-side agent.
6. **Future work / unit economics** — Option B: self-host Wan/LTX on Nebius GPU, ~10x cost
   reduction per tour, model-agnostic spec architecture.
7. **Sponsor usage** — table from CLAUDE.md §6 (each load-bearing, one line each).

## 3. Q&A one-liners (rehearse verbatim)

- **Data rights**: "Production partners with brokerages who own the content — that's also who pays."
- **Conflict of interest**: "Seller money buys generation and distribution, never ranking."
- **Model pricing risk**: "The style spec is model-agnostic — we swapped restyle models mid-hackathon without touching the contract."
- **Why fake the live gen?**: "Generation takes minutes and credits; caching is what production does too — tours render once per buyer profile, then serve forever."

## 4. Rehearsal protocol (B7, H21–H23)

- Two full timed runs, both engineers present, on the demo machine, demo network OFF
  (everything MOCK/local — prove zero-network viability).
- Fallback drill: play both `tour.mp4` files from Finder/VLC outside the app.
- Same scripted inputs every run (S1/S3 lines pinned in `agent/mocks/turns.json`).
- After each run: one fix list, 15 minutes max, re-run. No new features (post-H18).

## 5. Acceptance

- [ ] Deck ≤7 slides in /deck, exports to PDF (backup on second device).
- [ ] Script above printed/visible at the podium.
- [ ] Two timed runs both under 2:30.
- [ ] Fallback playback verified standalone.
- [ ] Submission form fields drafted by H21 (per TIMELINE checklist).
