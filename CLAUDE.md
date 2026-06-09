# CLAUDE.md

Guidance for agents (and humans) working in this repo. Read this first, then read the planning docs it points to.

## What this project is

**buildship** (working name) is a *state-externalizing agent harness*: a **frozen** model that writes its own tools. When it hits a task it lacks a tool for, it researches the API, generates a Python tool against a fixed contract, runs it in a sandbox, self-corrects on failure under a bounded budget, admits the tool to a persistent library **only if its self-test passes**, then uses it to finish the task.

The model owns only *semantic* decisions (what to build, whether it's done). The harness owns *durable* state: the tool **registry**, a **verification record** per tool, a **build budget**, and a **trajectory log**.

## Source-of-truth docs — read and follow these

These define scope and sequencing. Treat them as canonical; this file defers to them.

- **[`buildship-product-plan.md`](./buildship-product-plan.md)** — the *what / why / who* (product definition, thesis, users, KPIs, risks).
- **[`stages.md`](./stages.md)** — the *how / when*, **priority-ordered**: **(1)** win the hackathon → **(2)** paper-shaped result → **(3)** shippable harness. Each stage is additive. Start at Stage 0 / Stage 1.
- [`README.md`](./README.md) — public-facing summary and quickstart.

When in doubt about scope or priority, follow `stages.md`. Priority 1 (a clean live demo) is sacred — anything that threatens it gets cut.

## Environment — Apple-managed machine (important, non-obvious)

This machine has constraints that break the usual workflows:

- **Proxy** at `http://localhost:5084`; **PyPI is mirrored** at `https://pypi.apple.com/simple` (set as the default index in `pyproject.toml`). Public pypi.org is not used.
- **uv CANNOT download a managed Python** — the proxy blocks GitHub's `python-build-standalone` host (`tunnel error`), and disabling the sandbox does not help. Use the **brew-installed** interpreter at `/opt/homebrew/opt/python@3.12/bin/python3.12` and pass it explicitly to uv.
- **Env-var modification is blocked** by a security hook — `export VAR=…` and inline `VAR=val cmd` are both rejected. Use CLI flags instead of env vars.
- **`gh` CLI keyring is broken** (tokens read back invalid). Git uses **SSH** (`git@github.com:pleyva2004/buildship.git`), which works. Don't rely on `gh` for auth.

## How to run

Always run from the repo root. Pass the brew interpreter to uv (see above).

```bash
# Install / sync dependencies into .venv
uv sync --python /opt/homebrew/opt/python@3.12/bin/python3.12

# Add a dependency
uv add --python /opt/homebrew/opt/python@3.12/bin/python3.12 <package>

# Run the entrypoint (config check — verifies your keys are loaded)
uv run --python /opt/homebrew/opt/python@3.12/bin/python3.12 main.py
```

Secrets: `cp .env.example .env` and fill in `NEBIUS_API_KEY`, `TAVILY_API_KEY`, `COMPOSIO_API_KEY`. `.env` is gitignored — never commit keys.

## Coding standards

- **Python 3.12**, PEP 8. Type-hint public functions; write module- and function-level docstrings. Match the style of surrounding code; keep changes minimal and focused.
- **The tool contract is fixed** (core to the product): every agent-generated tool has a **typed signature + docstring + self-test**, and is admitted to the library **only if its self-test passes** (the validation gate). Don't loosen this — it's the reliability mechanism, not boilerplate.
- **Codegen is constrained, not freeform**: low temperature (`BUILDSHIP_CODEGEN_TEMPERATURE`, default 0.1) and a bounded retry budget (`BUILDSHIP_MAX_BUILD_ATTEMPTS`, default 3). On failure, feed the traceback back and make minimal targeted fixes; keep a rejected-edit buffer so a failed approach isn't repeated.
- **State-externalization**: durable state (tool registry, verification records, build budget, trajectory logs) lives in the harness as inspectable artifacts (persist as JSON), not in prompts or weights. Every run writes one structured trajectory JSON: task, gap, search query+result, generated code, test outcome, each retry, final action.
- **Config via env**: read settings with `os.getenv` after `load_dotenv()`. No hardcoded secrets or endpoints.
- **Safety**: generated code runs sandboxed (Composio workbench); consequential actions are gated for approval.

## Git & collaboration conventions

- **Do NOT add a `Co-Authored-By: Claude` trailer** (or any Claude attribution) to commits — the user does not want Claude credited. Commit as `pleyva2004 <pleyva2004@gmail.com>`.
- Remote is **SSH**; pushes are plain `git push`. **Never force-push without explicit user approval** (history rewrites require it).

## Repository layout

```
buildship/
├── CLAUDE.md                  # this file
├── README.md                  # public overview + quickstart
├── buildship-product-plan.md  # what / why / who  (canonical product spec)
├── stages.md                  # how / when  (priority-ordered build plan)
├── main.py                    # entrypoint: config check
├── pyproject.toml             # uv project + deps (default index = pypi.apple.com)
├── uv.lock
├── .python-version            # 3.12
├── .env.example               # copy to .env, fill in keys
└── .gitignore
```

---

## Project log & status

> Keep this current. New sessions: read this section first for immediate context, and update it as work lands.

### 2026-06-09 — Oracle-gate arm (trustworthy-verifier ceiling) + chain-reaction demo

**Done (offline-verified — 65 tests green; built two-in-parallel via subagents):**
- **`oracle_gate` ablation arm** — added `Harness.gate_check`, a non-LLM gate that REPLACES the self-test (precedence: `gate_check` > `independent_verifier` > self-test). The eval's `oracle_gate` arm gates on the task's ground-truth verifier — the **trustworthy-verifier upper bound**. Honest caveat: it reuses the eval verifier, so it's a *ceiling*, not a deployable gate. Expectation: it catches the `round_half_up` false positive and retries to a correct tool → should beat `no_gate`. `ABLATION_ARMS` now has 6 arms.
- **`demo_chain.py`** — standalone chain-reaction demo: builds `aggregate_by_key`, then `make_bar_chart`, then re-runs the same steps showing all `[reused]` (zero new builds) → the library compounds. Signature-agnostic `PrintAction` (non-chart tools work), fresh `demo_library.json` per run.

**Next (live, user's terminal):** `uv run -m buildship.eval ablation 3` now includes the `oracle_gate` row — the ceiling that completes the FINDINGS story (LLM-gate floor 0.54 → ungated 0.94 → trustworthy-oracle ceiling, expected ~1.0). And `uv run --python … demo_chain.py` for the compounding-library demo.

### 2026-06-09 — Independent-verifier gate arm + transient-error hardening

**Done (offline-verified — 64 tests green):**
- **Independent-verifier gate** (the decisive experiment from the alignment finding): `Harness(independent_verifier=...)` runs the tool's code against a test written by a SEPARATE model call (`NebiusLLMClient.write_test`, which never sees the implementation) instead of the author's own self-test. New ablation arm `independent_gate`. An offline test proves it **catches a false positive the self-test misses** (buggy `round_half_up` + weak self-test → admitted by the self-test gate, rejected by the independent gate).
- **Transient-error hardening**: the eval runner retries transient API failures (ConnectionError / APITimeoutError / RateLimit / 5xx; `BUILDSHIP_TRANSIENT_RETRIES`, default 2) so network blips aren't counted as failed builds (fixes the `full [2/3]` noise from the last live run).
- 4 new tests (`write_test` fence-strip, independent-gate wiring + false-positive catch).

**Why:** the live alignment run showed the gate's value is bounded because self-test errors correlate with code errors (false positive on `adv_round_half_up`). An author-independent verifier breaks that correlation; this arm measures whether it helps.

**Next (live, user's terminal):** `uv run -m buildship.eval ablation 3` now includes the `independent_gate` arm — expect it to beat `full`/`no_gate` on e2e by catching first-attempt duds the self-test admits. Cost: +1 LLM call per build on that arm. Also `uv run -m buildship.eval alignment 3` for averaged confusion-matrix rates.

**LIVE RESULT (5-arm × 3-seed, refuted the prediction — see [`FINDINGS.md`](./FINDINGS.md)):** e2e — `no_gate` 0.944 = `no_feedback` 0.944 > `full` 0.907 > `budget_1` 0.870 ≫ `independent_gate` **0.537** (at 3× tokens). **Gating never beat ungated.** The independent verifier was *worst*: an LLM-written test (self OR independent) is an unreliable gate — self-tests admit duds (`round_half_up` false positive), independent tests reject correct tools (false negatives). The honest Stage-2 result: self-extension reliability is bottlenecked by the verifier being LLM-generated; a trustworthy gate needs a non-model signal (property check / execution oracle / spec / human). Full writeup + caveats + next experiments in `FINDINGS.md`.

### 2026-06-08 — Eval rigor: gate-alignment metric + adversarial tasks (subagent build)

**Done (built via a subagent workflow; all offline-verified — 61 tests green, BENCHMARK now 18 tasks):**
- **Self-test ↔ verifier alignment metric** (`buildship/eval/runner.py`): `compute_alignment` / `run_alignment` + `AlignmentReport` — the 2×2 confusion matrix (false-negative = gate rejects a *correct* tool; false-positive = gate admits a *dud*) plus precision / recall / agreement. New CLI: `uv run -m buildship.eval alignment [N]` (runs the `no_gate` arm so both the gate signal and ground truth are captured per task). `TaskResult` gained `self_test_passed`.
- **6 adversarial tasks** (`buildship/eval/tasks.py`, category `adversarial`): `round_half_up`, `slugify`, `int_to_roman`, `dedupe_preserving_order`, `flatten_one_level`, `median` — spec-traps where a careless first attempt fails but a faithful self-test catches it. Vetted offline (reference passes all cases; a deterministic naive fails ≥1). Added `_expect_cases` multi-case verifier helper.
- Tests: reference + naive impls per adversarial task (parametrized accept/reject), category test updated, `test_compute_alignment`.

**Why:** the 3-seed ablation showed `no_gate ≥ full` because the benchmark only exhibited the gate's *false-negative* mode (correct code, flaky self-test). The alignment metric quantifies that; the adversarial tasks add the *true-positive* mode so gated+retry can legitimately beat `no_gate`.

**Next (live, user's terminal):** `uv run -m buildship.eval alignment` (expect a non-zero false-negative count, e.g. `transform_snake`) and `uv run -m buildship.eval ablation 3` (expect `full` to meet/beat `no_gate` on the expanded benchmark).

### 2026-06-08 — Reuse fix + test suite + Stage 2 eval harness

**Done:**
- **Core reuse fix** (`buildship_core.py`, approved edit): the registry keys off `needed_tool` (the capability), decoupled from the function's def name — `admit(..., key=)`, `callable()` resolves by the contract's def name with a sole-function fallback, and `Harness.run` admits/reuses/acts on `needed_tool`. Verified: build → reuse across runs (no rebuild).
- **Offline pytest suite** (`tests/`, 37 tests, ~1s, `uv run -m pytest`): harness loop (gate, reuse, self-correction feedback carries the traceback, bounded budget, admit refusal); adapter helpers (JSON parse, `ast` name-align, output coercion, pass/fail heuristics, `LocalSandbox` incl. a real matplotlib chart); and the eval verifiers + metrics math.
- **Codegen generalized** — task-driven signatures (no hardcoded chart convention); the hero task text now states its signature; `NebiusLLMClient` tracks cumulative token usage (cost KPI).
- **Stage 2 eval harness** (`buildship/eval/`): 12 held-out tasks across compute/transform/chart, each with an automatic verifier; the runner drives the Harness (no-op action) and reports build-success / end-to-end / reuse / attempts-to-success / tokens. Run live: `uv run -m buildship.eval`.

**Live result (2026-06-08, user's terminal · DeepSeek-V3.2 · local sandbox): 12/12 — build-success 1.0, end-to-end 1.0, mean attempts-to-success 1.17, ~26.5k tokens.** Notes: `transform_snake` reliably needs the full 3-attempt self-correction budget; `compute_is_prime` occasionally emits a bloated non-JSON reply that the codegen JSON-retry recovers. Two live-found fixes landed: canonical self-test guidance (`transform_csv`) and JSON-retry resilience (`compute_is_prime`).

**Open / next:**
- Live runs still need the user's own terminal (the proxy blocks vendor APIs in-session): `smoke_hero.py`, `uv run -m buildship.eval`, and `uv run -m buildship.eval ablation`.
- **Ablation arms built** (`buildship/eval/runner.py`): full / no_gate / budget_1 / no_feedback via Harness config hooks (`gate`, `max_attempts`, `feedback_mode`) — just run them live for the paper numbers.
- Feature/use-case backlog captured in `IDEAS.md` (recommended-next shortlist at top).

### 2026-06-07 — Stage 0/1: vendor adapters wired

**Phase:** Stage 0 item (5) done — the four core Protocols are implemented; ready for a live end-to-end run once keys are added. Core (`buildship_core.py`) untouched.

**Done:**
- `buildship/adapters.py` implements all four Protocols:
  - `NebiusLLMClient` — codegen → `ToolContract` (low-temp, JSON mode, forwards retry `feedback`).
  - `ComposioSandbox` — runs tool source in the Composio remote workbench (`execute_meta` / `COMPOSIO_REMOTE_WORKBENCH`); `LocalSandbox` subprocess fallback via `BUILDSHIP_SANDBOX=local`.
  - `TavilySearcher` — `search(... include_answer=True)` → answer + snippets.
  - `ComposioAction` — renders the chart in-process via the built tool, then fires a real `tools.execute` Slack action.
  - `make_sandbox()` / `build_harness()` wiring helpers.
- `buildship/__init__.py`; `smoke_hero.py` end-to-end driver (key check → runs chart hero task → prints trajectory).
- `.env.example` extended (Composio session/sandbox/action config); `.gitignore` adds `artifacts/` + `*_library.json`; `matplotlib` added.
- Verified: compiles + imports; signatures match the Protocols; every SDK call checked against installed source (openai 2.41, tavily 0.7.25, composio 0.13.1 / composio_client 1.39.0) via an adversarial audit — no blocker/major bugs.
- Hardening: `write_tool` aligns `ToolContract.name` to the actual top-level `def` (via `ast`), so `registry.callable()` can't `KeyError` after a passed self-test.

**Open / blockers:**
- Not yet run live (needs keys). Run: `cp .env.example .env`, add NEBIUS/TAVILY/COMPOSIO keys, then `uv run --python /opt/homebrew/opt/python@3.12/bin/python3.12 smoke_hero.py`.
- Two backend-defined unknowns, configurable + flagged inline: workbench argument key (`BUILDSHIP_WORKBENCH_ARG`, default `code`; try `source`) and the Slack action slug/channel/connection. First-run tip: `BUILDSHIP_SANDBOX=local` validates the loop before the Composio workbench.

**Next up:**
- Run `smoke_hero.py` with keys; tune the two flagged knobs from the first live trace.
- Stage 1 polish: trace UI, run the hero task 15–20× to harden, record a fallback video.

### 2026-06-07 — Bootstrap complete

**Phase:** project bootstrap done; **no application code yet**.

**Done:**
- Repo created & pushed: `github.com/pleyva2004/buildship` (private, SSH remote). HEAD on `main`.
- uv project initialized at repo root, Python **3.12.13** (brew). Deps: `openai` (Nebius is OpenAI-compatible), `tavily-python`, `composio`, `python-dotenv` — locked in `uv.lock`.
- `.env.example` created (Nebius / Tavily / Composio keys + harness config). `.env` gitignored.
- `main.py` config-check entrypoint — verified it runs and reports key presence.
- Working name swept from **Forge → buildship** across all files; `forge-product-plan.md` renamed to `buildship-product-plan.md`.
- Git history cleaned of the Claude co-author trailer.

**Blockers / risks:**
- API keys not set yet (`.env` not created).
- `composio 0.13.x` API surface not yet validated against the build plan's assumptions (workbench sandbox + `@action`).
- uv must be invoked with the explicit brew interpreter on this machine (see Environment).

**Next up (per `stages.md` Stage 0 → Stage 1):**
1. Create `.env` from the template and add real keys.
2. Scaffold the `buildship/` package with the **Stage 0 substrate**: tool **registry** (name → callable + schema + test), per-tool **verification record**, **build-budget** counter, and the **structured trajectory log** (one JSON per run).
3. Lock the **hero task** — recommended: *"analyze data → chart it"* with no charting tool in the kit (it writes a matplotlib tool, debugs it, renders the chart).
4. Wire the **happy-path loop**: gap → Tavily research → Nebius codegen → Composio sandbox run → register → use → fire a real action.
5. Add the **reliability core**: self-correction retry (cap 3), rejected-edit buffer, validation gate, Tavily research step.
