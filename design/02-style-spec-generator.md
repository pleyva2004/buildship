# Design 02 — Style Spec Generator (B1)

> The A↔B contract generator. Converts a fuzzy mem0/profile into ONE locked JSON spec that
> Engineer A injects verbatim into every room's restyle prompt. Schema frozen at H4.

## 1. What this delivers

`agent/style_spec.py` + a `make spec` target that regenerates `/specs/<profile_id>.json`
from the profile seed (`agent/profiles/<person>.json`), validated against
`/specs/schema.json` before writing.

The two specs already exist and are frozen. This generator must **reproduce them** (or
something schema-valid and equivalent in spirit) so the story "the AI derived this from what
it knows about me" is real and repeatable — not hand-authored once.

## 2. Pipeline

```
profile seed JSON ──► build prompt ──► Nebius LLM ──► raw JSON ──► validate(schema) ──► write /specs/<id>.json
                       (deterministic)   (temp=0)        │
                                                         └─ on invalid: repair-retry once, else fall back to mock spec
```

- **Deterministic**: `temperature=0`, fixed system prompt, fixed field order. Same profile
  in → same spec out. This is a hard requirement (rehearsal stability + A builds against it).
- **Validation gate**: use the JSON Schema. Reject and repair if `palette_hex` isn't 3–6
  valid hexes, or `hard_constraints` is missing the architecture-preservation rules. Never
  write an invalid spec — A reads these blind.
- **Mock backend**: returns the known-good frozen spec for that profile_id directly (no LLM).
  This is also the fallback if the live LLM emits junk on stage.

## 3. Interface

```python
def generate_spec(profile_id: str) -> dict          # profile seed -> validated spec dict
def write_spec(profile_id: str) -> Path             # generate + validate + write /specs/<id>.json
def validate_spec(spec: dict) -> list[str]          # [] if valid, else list of errors

# CLI:  python -m agent.style_spec --all      (regenerate both)
#       python -m agent.style_spec jake_v1    (one)
```

## 4. Prompt shape (LIVE backend)

System: "You convert a home-buyer taste profile into a locked interior-design style spec as
strict JSON. Output ONLY JSON matching this schema. Always include the four architecture-
preservation hard_constraints. palette_hex: 3–6 hexes capturing the aesthetic."
+ inject `schema.json` + the profile seed's `taste_descriptors`, `aesthetic_summary`,
`mood_board_refs`.

Pin `materials`/`furniture_vocabulary` to concrete nameable objects (A injects these as
literal prompt tokens — vague adjectives restyle inconsistently across rooms; see specs/README).

## 5. Critical rules (from specs/README + CLAUDE.md §4)

- **Every `palette_hex` is injected into every room prompt** — this is the cross-room
  consistency lever. Keep palettes tight (3–4 hexes), high-contrast between the two profiles.
- `hard_constraints` ALWAYS contains preserve architecture / windows-doors / geometry +
  no people. A render that moves a wall breaks the slider. Validator enforces presence.
- **Freeze schema H4, never change field names after H8.** This generator may change; the
  schema and field names may not.

## 6. Acceptance (B1)

- [ ] `make spec` regenerates both specs; output validates against `schema.json`.
- [ ] Regenerated specs are schema-equivalent to the frozen `pablo_v1.json` / `jake_v1.json`.
- [ ] Mock backend returns the frozen spec verbatim (zero-dependency fallback).
- [ ] Invalid LLM output is repaired or rejected — never written.
