# Buildship — Build Plan *(priority-ordered)*

**Priorities (your call):** 1) win the hackathon · 2) paper-shaped result · 3) shippable harness.

**The key insight:** these don't compete. If you make ~5 decisions before writing code, the hackathon build *is* the paper's substrate *is* the product's core. Each stage is **additive**, not a rewrite — that's how a priority *ordering* pays off instead of splitting your effort three ways.

---

## Stage 0 — Lock these before you write code (~1 hr, Day 1 morning)

Five cheap decisions that keep the paper and product paths open without slowing the demo:

1. **Hero task — the single most important call.** One capability the starter kit lacks, small enough to generate reliably, visually obviously correct. Recommended: *"analyze this data → chart it"* with no charting tool in the kit (it writes a matplotlib tool, debugs it, renders the chart). Pick a task whose *category* will also appear in your eval set later, so the demo is a member of the benchmark family.
2. **State-externalize the harness from hour one.** Even in the MVP: a thin tool **registry** (name → callable + schema + test), a **verification record** per tool (last test result + status), and a **build-budget** counter (attempts, tokens). ~2 hours of structure, and it's literally the substrate for both the eval (Stage 2) and the product (Stage 3). Skip it and you rewrite the loop later.
3. **Structured trajectory log.** Every run writes one JSON: task, gap, search query + result, generated code, test outcome, each retry, final action. *One artifact, three uses* — demo trace, eval data, paper raw material.
4. **Fix the tool contract.** Typed signature + docstring + a self-test, every time. Constrained codegen is far more reliable than freeform, and it gives Stage 2's "tool-authoring skill" a clear object to optimize.
5. **Confirm the stack.** Nebius coder model (DeepSeek-V3 or a large Qwen), low temperature; Composio remote workbench as the sandbox + `@action` for registration; Tavily for the API-research step.

> **Guardrail:** anything in Stage 0 that threatens the Day-1 demo gets cut. Priority 1 is sacred.

---

## Stage 1 — Win the hackathon (Day 1) — **[PRIORITY 1]**

Two people, ~8 productive hours.

**H0–1 · Setup + lock hero task.** Nebius client + coder model; Composio session with one real action (Slack/Notion) + workbench sandbox; Tavily key live. Stub the harness state (registry, verification records, budget) and the state machine. Freeze the hero task and write its expected outcome.

**H1–3 · Happy path, end to end.** gap → research → codegen → run in sandbox → register → use → fire the Composio action — for the hero task only. No retries, no UI yet. Goal: one clean successful run.

**H3–5 · The reliability core (this is what wins).** Add: self-correction retry (feed the traceback back, make *minimal targeted fixes*, cap 3) · rejected-edit buffer (don't repeat a failed approach) · the validation gate (a tool is admitted only if its test passes) · the Tavily research step. This is the SkillOpt discipline and the single biggest reliability upgrade for a live demo.

**H5–6 · Trace UI.** Show plan → gap → search → generated code → a failure-and-fix → registration → action result. Judges reward what they can watch. The same UI emits the trajectory log from Stage 0.

**H6–7 · Harden.** Run the hero task 15–20×; fix flaky spots; lower temperature; freeze the template; pre-cache the Tavily snippet so a flaky search can't sink the demo. **Record a clean run as the fallback video.** Optional: wire a second "surprise" task as an encore to prove generality.

**H7–8 · Rehearse.** Run the 3-min demo twice on the real rig; time it; assign driver vs narrator; prep the two Q&A answers.

**Division of labor:**
- **Builder A** — agent loop: codegen prompts, retry logic, sandbox, the gate.
- **Builder B** — integrations (Composio + Tavily), trace UI, demo staging + fallback recording.

**3-min demo:** "Every agent is capped by the tools we give it — ours writes its own when it hits a wall," show the tiny kit (0:00) → give the task, it hits the gap (0:30) → it searches the docs on screen (0:50) → code streams as it writes the tool (1:05) → **test fails, it reads the traceback and fixes itself and passes — let this beat breathe** (1:25) → registers and uses it, real action fires (1:50) → "it couldn't do that two minutes ago; now the tool's permanent," optional encore (2:15) → close (2:45).

**Judge Q&A (have these ready):**
- *"What stops it running malicious code?"* → sandboxed execution + consequential actions are gated.
- *"How reliable is the codegen?"* → tests must pass before a tool is admitted; failures feed back as negative signal.

**Definition of done (Priority 1):** live self-debug lands cleanly · all four tools visibly load-bearing · 3-min demo rehearsed · fallback recorded.

---

## Stage 2 — Paper-shaped result (Days 2–5) — **[PRIORITY 2]**

The pivot: from *"it built a tool live"* to *"we measured that disciplined self-extension works, under a pre-registered protocol."*

**Build the eval benchmark.** 15–40 held-out tasks, each requiring a tool the agent lacks, each with an automatic verifier. Span 2–3 categories (compute/data tools, API-fetch tools, format/transform tools). This is the gating object the whole method needs.

**Metrics.** Build-success rate · attempts-to-success · tool reuse rate · end-to-end task success · cost/tokens per solved task — and how they move over the run.

**Pre-register the central claim.** *Gated, bounded, rejected-buffer self-extension beats ungated self-editing* on held-out build success and end-to-end task success. Pre-register hypotheses, metrics, conditions, sample sizes, and the analysis plan before running. Ablation arms mirror SkillOpt's own structure: **full** vs **no-gate** vs **no-rejected-buffer** vs **no-bounded-edits**. Clean, credible, hard to wave away.

**Optional headline contribution.** Implement SkillOpt's offline loop to optimize the *tool-authoring skill* (the prose policy for *how* it writes tools) and show the optimized skill lifts held-out build success — SkillOpt extended to a code-tool-building domain. More ambitious swing: optimize the *library itself* as external state (which tools to keep / how to document them), the open thread from their Outlook.

**Write-up framing.** Procedures-as-text (SkillOpt) and search-state-as-external (Harness-1) → *capabilities-as-code* (Buildship): same state-externalizing philosophy, new axis. Position against both.

**Reuse, don't rebuild.** If Stage 0 held, this stage is *additive*: the harness, registry, verification records, and trajectory logs are already your experimental apparatus.

---

## Stage 3 — Shippable harness (Days 6–7+) — **[PRIORITY 3]**

Directional, lowest priority:
- **Governance** — promote the demo's approval beat into a real policy engine: sandbox resource limits, static checks on generated code (block exfil/destructive ops), capability gating, a full provenance log.
- **Library curation** — dedupe, versioning, retire flaky tools; the architect/worker split for reliability.
- **Make it usable** — clean UI/CLI, docs, demo video, open-source repo.

This is where Buildship becomes something others can run. Touch it only after 1 and 2 are solid.

---

*Companion to `buildship-product-plan.md` (the what / why / who). This is the how / when.*
