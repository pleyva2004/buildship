# buildship — web trace viewer

A phone-first **static** page that renders a buildship run trajectory as the styled TUI
(spotlighting the **self-debug** fail→fix→pass beat and the **reuse** / 0-new-builds beat),
revealed step by step. It bundles two recorded traces so it works standalone (reliable for a
live demo + a public URL); a fresh run can be loaded via the **"＋ trace.json"** picker
(point it at any `trajectories/<id>.json` from a real run).

## Deploy to Vercel (renders the TUI on your iPhone)

It's a static site — no build step.

**Push-to-deploy via GitHub (recommended):**
1. [vercel.com](https://vercel.com) → **New Project** → import `pleyva2004/buildship`.
2. Set **Root Directory = `web`**, **Framework Preset = Other**, leave Build Command empty.
3. **Deploy** → you get `https://<project>.vercel.app`. Open it on your iPhone.
   Every push to `main` redeploys automatically.

**Or the CLI:**
```bash
cd web
npx vercel          # preview URL
npx vercel --prod   # production URL
```

## Local preview
```bash
cd web && python3 -m http.server 8000   # open http://localhost:8000
```

## Notes
- **Static-recorded by design.** The harness (Nebius/Tavily/Composio + matplotlib) doesn't
  fit Vercel's short-lived serverless functions, and recorded traces are far more reliable
  for a live demo. To show a *fresh* run, do a real `buildship.eval` / `demo_chain.py` run
  on a networked machine and load its `trajectories/<id>.json` via the picker.
- The bundled traces mirror `demo_traces/*.json` (and `demo_trace.py`, the terminal version).
