# Design 01 — Profiles & mem0 Memory Layer (B1)

> "The 'AI that knows you' IS mem0." This layer is the pitch made architecture. When a
> judge asks "where does personalization live," the answer is a live mem0 query on screen.

## 1. What this delivers

- A **profile seed schema** richer than the style spec — the human context the agent
  reasons over, from which the style spec is *derived*.
- Two seeded profiles: `pablo` (real) and `jake` (real).
- A `mem0_client` with MOCK and LIVE backends, exposing the minimal surface the agent and
  the app's context panel need.

## 2. Profile seed schema (`agent/profiles/<person>.json`)

This is NOT the style spec. It is the upstream human context. The style-spec generator
(`02`) consumes this; the agent recalls from it; the app's context panel renders it.

```json
{
  "profile_id": "jake_v1",
  "name": "Jake",
  "life_situation": {
    "summary": "First-time buyer, relocating to Austin, works from home 3 days/week",
    "household": "couple, no kids, one dog",
    "budget_band": "750k-900k",
    "must_haves": ["home office with daylight", "walkable neighborhood", "outdoor space for the dog"]
  },
  "taste_descriptors": [
    "bright and airy over cozy and dark",
    "uncluttered, few but intentional objects",
    "natural light is non-negotiable",
    "pale woods, no heavy ornamentation"
  ],
  "mood_board_refs": [
    {"source": "pinterest", "label": "Scandinavian living rooms", "imported_via": "composio"},
    {"source": "pinterest", "label": "minimalist oak kitchens", "imported_via": "composio"}
  ],
  "aesthetic_summary": "bright Scandinavian minimalist",
  "hard_constraints": ["preserve architecture", "no people"]
}
```

`pablo.json` mirrors this shape with warm-mid-century descriptors (cozy over bright, walnut/
brass, golden-hour lighting, a contrasting life situation — e.g. trading up, design-led).

### Why two layers (seed → spec)
The seed is *human and fuzzy* ("natural light is non-negotiable"); the spec is *machine and
locked* (`palette_hex`, `materials`). The generator's job (doc `02`) is the fuzzy→locked
transform, and showing that transform on stage is part of the wow ("it turned what it knows
about me into a rendering instruction"). Keep them separate files.

## 3. mem0 client interface

`agent/clients/mem0_client.py` — one class, two backends, selected by `VISTA_BACKEND`.

```python
class Mem0Client:
    def seed(self, profile_id: str, facts: list[dict]) -> None: ...
    def search(self, profile_id: str, query: str, k: int = 5) -> list[Memory]: ...
    def all(self, profile_id: str) -> list[Memory]: ...   # for the context panel
    def add(self, profile_id: str, text: str, meta: dict | None = None) -> None: ...

# Memory = {id, text, category, score}
```

- **Seeding**: flatten each profile JSON into atomic memory strings (one fact per memory),
  e.g. `"Jake works from home 3 days a week"`, `"Jake prefers bright and airy over cozy and
  dark"`, tagged with `category` in {life_situation, taste, mood_board, constraint}. The
  category drives the context-panel grouping in the app.
- **search()** powers the agent's recall step ("what do I know relevant to this listing?").
- **all()** powers the context panel — render grouped by category, this is the on-screen proof.

### MOCK backend
In-memory dict keyed by profile_id, seeded from the profile JSON at startup. `search()`
does naive keyword/substring scoring — deterministic, good enough for a scripted demo, and
identical shape to live so the swap is invisible. Canned data in `agent/mocks/`.

### LIVE backend
mem0 SDK. `seed()` → `client.add()` per fact with metadata; `search()` → `client.search()`;
`all()` → `client.get_all()`. Sponsor code `SHIPBUILDERS`. Key: `MEM0_API_KEY`.

## 4. Composio import (one real path, semi-mocked)

Goal: demo *once* that a mood board flows in via Composio → becomes mem0 memories. Real
connection, narrow scope. See `01`-level detail here; full agent flow in `04`.

- **Preferred**: Composio Pinterest connector → pull board titles/pins → write as
  `category=mood_board` memories.
- **Fallback (playbook, default if fighting by H8)**: pre-loaded `agent/mocks/moodboard.json`
  representing "what Composio returned," still written into mem0 the same way. The narrative
  ("context flows in via Composio") survives; only the live socket is stubbed.
- Interface: `composio_client.import_moodboard(profile_id) -> list[MoodRef]`, MOCK reads the
  JSON, LIVE hits Composio. Either way the result lands in mem0 via `Mem0Client.add`.

## 5. Acceptance (B1)

- [ ] `pablo.json` and `jake.json` seeds exist and are internally consistent with the frozen specs.
- [ ] `make seed` populates mem0 (mock or live) and `mem0_client.all("jake_v1")` returns
      grouped facts the context panel can render.
- [ ] `composio_client.import_moodboard` returns mood refs (mock acceptable) that land in mem0.
- [ ] Deterministic: same seed in → same memories out (required for scripted rehearsal).
