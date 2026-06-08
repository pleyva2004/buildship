# buildship — Ideas & Backlog

Synthesized from a 5-lens ideation pass (demo / paper / capability / governance / product),
deduped and ordered by the `stages.md` priorities (**1** win the hackathon → **2** paper-shaped
result → **3** shippable harness). Tags: **effort** S/M/L · **stage** · *demoable*.

> Status anchors (already built): core harness + reuse-by-capability, the four vendor
> adapters, the chart hero task + smoke test, the Stage-2 eval harness (12 tasks +
> verifiers + metrics), and the **ablation hooks** (gate / budget / rejected-buffer).

## Recommended next (highest leverage, given current state)

1. **Run the eval + ablation live** (S · stage 2) — the apparatus is built; one `uv run -m buildship.eval ablation` from a networked terminal produces the headline numbers (full vs no-gate vs budget-1 vs no-feedback). This is the paper's core result and needs no new code.
2. **Chain-reaction hero task** (M · stage 1) — one task that forces building *two* tools (CSV transform → chart), so the second run shows a real library **reuse** hit. Proves "capabilities compound" live; exercises all four vendors twice.
3. **Four-panel trace UI** (M · stage 1) — live view of gap → Tavily snippet → Nebius codegen JSON → sandbox pass/fail. `stages.md` H5–6: judges reward what they can watch; emits straight from the trajectory log.
4. **AST static-safety gate** (M · stage 3) — reject dangerous codegen (`os.system`, raw `subprocess`, exfil, file writes outside tmp) *before* the sandbox, feeding the violation back as negative signal. Turns "let it run code" into a real trust story; builds on the `ast` use already in the registry.
5. **SkillOpt on the codegen prompt** (L · stage 2) — optimize `_CODEGEN_SYSTEM` offline against the benchmark (score → rank → beam → converge); show lift in build-success. The novel "capabilities-as-code" contribution.

---

## Stage 1 — Win the hackathon (demo)

- **Recoverable self-debug beat** (S · *demo*) — script a *predictable* first-attempt failure (off-by-one / empty input) so the traceback→fix→pass loop reads as discipline, not luck.
- **Live judge-visible action** (S · *demo*) — the freshly-built tool posts its chart to a Slack channel projected in the room; undeniable "it couldn't do this 2 min ago." (Pre-stage workspace + fallback screenshot.)
- **Micro-benchmark flash** (M · *demo*) — after the hero task, blitz 3–5 eval tasks (compute / transform / second chart) to prove generality + reuse in seconds each.
- **Render the rejected-edit buffer** (S · *demo*) — show "attempt 1 failed → buffered → attempt 2 learned → passed"; makes the gating discipline a visible artifact.
- **Sponsor-role narration** (S) — call out each vendor's load-bearing moment (Tavily found docs · Nebius wrote it · Composio sandboxed it · gate+library locked it in).
- **Pre-registered demo script + Q&A** (S) — committed answers to the safety / reliability / generality questions + a recorded clean-run fallback.

## Stage 2 — Paper-shaped result (eval & analysis)

> The **ablation arms are now built** (`buildship/eval/runner.py`): full · no_gate · budget_1 · no_feedback. The items below are analyses to run/extend on top.

- **Gated vs ungated** (M · stage 2) — does the validation gate lift end-to-end success? Report gate precision (rejected-that-would-fail) and false-positives (passed-but-fails-verifier).
- **Bounded-retry Pareto** (S) — success vs attempts vs tokens across budgets {1, 3, ∞}; find the diminishing-returns inflection.
- **Rejected-buffer value** (M) — full vs traceback-only vs none: does negative feedback reduce repeated failure patterns (failure-pattern entropy, time-to-fix)?
- **Library compounding over time** (M) — warm vs cold start across a task sequence; reuse rate should rise, cost/task should fall; test order-sensitivity.
- **Verification-signal alignment** (S) — confusion matrix of self-test outcome vs benchmark verifier; quantify how well the self-test gate predicts real correctness.
- **Capability saturation** (M) — extend to 30–50 tasks; plot the tool-discovery curve (does the long tail plateau?).
- **SkillOpt on codegen prompt** (L) — see Recommended #5; the headline contribution.

## Capability & composition

- **Tool dependency graph + auto-composition** (M · stage 3) — when a single-shot tool fails, decompose into verified building blocks (`fetch` + `parse` + `chart`) and compose; compounds library value.
- **Semantic reuse** (M · stage 3) — embed tool docstrings/signatures; on a gap, find a near-match in the library (bar↔line, c→f↔f→c) and reuse/compose *before* codegen.
- **Architect/worker split** (L · stage 3) — a planning pass decomposes a task into micro-capabilities + budget, then the worker executes; fail gracefully with a clear reason.
- **Capability taxonomy + routing** (S · stage 2) — classify tools (compute/io/network/auth/...); route per-category codegen templates and surface capability clusters/root-causes.
- **Multi-model canary routing** (M · stage 3) — a Nebius model roster: cheap model first, escalate to frontier on failure; track cost-per-success per model.
- **Versioned library + rollback / A-B** (M · stage 3) — immutable tool versions, per-trajectory version tracking, auto-rollback when a new version degrades e2e.

## Governance & safety (Stage 3 trust layer)

- **AST static-safety gate** (M) — see Recommended #4 (pre-sandbox static rejection + negative feedback).
- **Capability-gating policy engine** (M) — `capability_category` on the contract + JSON policy {risk, require_approval, sandbox_constraints}; forbid e.g. network tools without code changes.
- **Consequential-action approval** (L · *demo*) — serialize the trajectory as an approval request before `action.execute()`; human/policy decides; logged in the verification record. (Auto-approve in demo mode.)
- **Provenance manifest** (S) — per-tool genealogy (task, research query, model+params, test outcome, approver, timestamp, trajectory id) for audit/chain-of-custody.
- **Sandbox resource profiling** (M) — capture peak CPU/mem/time/network in the test output + verification record; reject tools that exceed limits (also feeds cost KPIs).
- **Tiered sandbox isolation** (M · *demo*) — new tools run network/compute-restricted; trust (and permissions) grow after N clean passes.
- **Risk score + shadow mode** (S/M) — score = complexity + deps + network/io surface; high-risk tools need approval; newly-admitted tools run "shadow" (results unused) for N runs before going live.

## Product use-cases (Stage 3 verticals)

- **Composio action auto-builder** (M · *demo*) — "API docs link → auto-built, tested action" contributed back to Composio's marketplace; natural co-brand with the sponsor.
- **No-code "auto-build tool" plugin** (L) — embed the harness in a Zapier/Make/n8n-style platform; users auto-extend agents without code (premium: governance + shared libraries).
- **RPA workflow auto-learner** (L · *demo*) — observe repeated SAP/Salesforce workflows, build+version tools for the steps, replay on demand; library compounds 10× over manual bots.
- **Finance reporting agent w/ audit provenance** (M · *demo*) — auto-build GL/accounting integrations with full provenance + approval trail; compliance asset, not liability.
- **Healthcare FHIR/HL7 harmonizer** (L · *demo*) — auto-build provider-format mappers, validated + versioned; safe self-extension for a notoriously one-off integration space.
- **Notion/Linear automator** (S · *demo*) — auto-build custom DB queries / bulk updates per workspace; reuse compounds across requests.
