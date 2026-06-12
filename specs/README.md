# /specs — the A↔B integration contract

One locked JSON style spec per taste profile. **Engineer B generates these** (from mem0 profiles, via the LLM); **Engineer A consumes them** — injecting the spec *verbatim* into every room's restyle prompt. That verbatim injection is what makes a tour feel like one coherent taste instead of per-room filters.

## Rules (from CLAUDE.md §4)

- **Freeze the schema by H4. Never change it after H8.** A builds against these field names.
- Every `palette_hex` value goes into every prompt — this is the lever for cross-room palette consistency. If restyles drift, tighten injection (hexes + named materials) before swapping models.
- `hard_constraints` always preserves architecture / windows / doors / geometry, and `no people`. A render that moves a wall breaks the "same real house" claim and the slider moment.

## Files


| File            | Profile      | Aesthetic                                  |
| --------------- | ------------ | ------------------------------------------ |
| `pablo_v1.json` | Pablo (real) | warm mid-century modern                    |
| `jake_v1.json`  | Jake (real)  | bright Scandinavian minimalist             |
| `schema.json`   | —            | JSON Schema the two specs validate against |


Regenerate from seeded profiles: `make spec` (or `python -m agent.style_spec --all`).
Validate by eye against `schema.json` before freezing.