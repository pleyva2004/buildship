# Buildship — Product Plan *(working name; swap freely)*

**Thesis:** An agent's capabilities should be external, recoverable, validated state — not baked into weights or hand-wired ahead of time. Buildship is a *state-externalizing harness* that lets a **frozen** model grow its own toolset under control: when it hits a task it can't do, it builds the tool, proves it works, keeps it, and reuses it.

---

## 1. Product definition — *what* we're building

**One-liner:** An agent that writes its own tools. When it lacks a capability, it researches the API, generates a Python tool, tests it, self-corrects until it passes, registers it, and uses it — and that tool persists into a validated, inspectable library.

**The loop:**
1. Plan the task against the current toolset.
2. Detect the gap — "no tool for X."
3. Research X (Tavily) and feed what it learns to the coder.
4. Generate a tool against a fixed contract — typed signature, docstring, self-test — via codegen on Nebius.
5. Run it in a sandbox; on failure, feed the traceback back and retry under a bounded edit budget.
6. Admit the tool to the library **only if its test passes** (validation gate).
7. Use it to finish the task, firing a real action via Composio.

**Architecture in one breath:** a state-externalizing harness. The model owns only semantic decisions (what to build, whether it's done). The harness owns durable state — the tool library, a verification record per tool, and a build budget. This is the SkillOpt → Harness-1 lineage applied to *capabilities* rather than procedures or evidence.

**What it is NOT:**
- Not a fixed-toolset agent — the toolset is the *output*, not the input.
- Not fine-tuning — the model stays frozen; nothing touches weights.
- Not a generic "do-my-tasks" assistant — the wedge is *self-extension under control*, not breadth.

**Build tiers:**
- **1-day (hackathon MVP):** the live loop on one rehearsed hero task + one real Composio action + a visible trace, with the self-debug moment as the centerpiece.
- **7-day (real artifact):** persistent, versioned tool library; SkillOpt-style offline optimization of the tool-authoring skill; a held-out eval benchmark with verifiers; and a governance layer (sandbox hardening, static checks, capability gating, provenance log).

---

## 2. Problem–product fit — *why* we're building

**The problem.** Every agent is capped by the tools a human wired for it in advance. In real deployments the agent constantly hits the long tail — a SaaS endpoint, a format, a calculation, an integration — that nobody pre-built, and a human has to stop and write it. Extending an agent is manual, slow, and doesn't compound: each new capability is a fresh ticket, and the agent is no smarter tomorrow than it is today.

**Why now.**
- Agents are everywhere in 2026, so the capability-ceiling problem is widespread, not theoretical.
- Tool/integration layers (Composio and peers) make real-world actions accessible as primitives.
- Frontier and open models now write small, correct tools *reliably enough* — **if** the loop gates them.

The missing piece isn't codegen; it's the disciplined loop that makes self-extension trustworthy and durable.

**How Buildship fits the problem.**
- Removes the human tool-authoring bottleneck for the long tail of capabilities.
- The **validation gate** turns "let the agent write code" (flaky, scary) into propose-and-verify (reliable, auditable) — the difference between a party trick and something you'd deploy. *SkillOpt's evidence: most proposed edits are rejected by the gate; only the ones that prove out survive.*
- **State-externalization** makes new capabilities persistent, inspectable, auditable, and transferable — they compound across sessions instead of evaporating.
- **Weight-free and model-agnostic** — works with closed/frozen models, no fine-tuning, portable across models and harnesses.

**The moat.** The discipline, not the codegen. Anyone can prompt "write a tool." The defensible value is the controlled loop — gate + rejected-edit memory + budget + provenance — that makes self-written tools *trustworthy*, plus the externalized library that makes them *compound*.

---

## 3. Product–market fit — *who* we're serving

**Primary user (beachhead): teams building agentic products who keep hitting "we need a tool we don't have."** AI engineers and agent-platform builders wiring agents to long-tail SaaS/APIs.
- **Job to be done:** "Let my agent handle tasks that need capabilities I haven't pre-built — without me stopping to hand-write each integration."
- Why them first: large tool long-tail, technical enough to deploy, and reliability/auditability is exactly what unblocks them.

**Secondary:**
- Internal automation / ops teams (RPA-adjacent) who want agents that absorb new tools and workflows without an eng ticket per change.
- Researchers studying self-improving agents — the 7-day eval-harness version is a clean research instrument.

**Tertiary / later:** end-users of a vertical agent that quietly extends itself behind the scenes.

**Anti-personas (where value does *not* concentrate):** one-shot consumer chat (no long tail to cover) and ultra-narrow fixed-scope agents (no need to self-extend). Naming these keeps us honest about scope.

**The hackathon "market" (immediate):** the judges and the four sponsors. PMF for *that* audience =
1. all four tools doing visibly necessary work — Tavily learns the API, Nebius writes the code, Composio sandboxes + executes, the harness runs the loop;
2. a forward-looking "agents that grow their own capabilities" story;
3. the self-debug moment that sticks.

Best-overall is won on necessity + narrative + a memorable beat — and this hits all three.

---

## KPIs / success metrics

**Build-loop (does it work?):** tool-build success rate · attempts-to-success · % of runs needing the self-correct retry · tool reuse rate (library hits vs new builds).

**Product (is it valuable?):** end-to-end task success vs a fixed-toolset baseline (the headline lift) · cost / tokens per solved task · % of consequential actions correctly gated for approval.

**Hackathon (do we win?):** live self-debug lands cleanly · all four tools visibly load-bearing · 3-min demo timed and rehearsed with a recorded fallback.

---

## Key risks & assumptions

- **Verification dependency.** Self-extension is only as trustworthy as the test/verifier behind the gate. Weak signal → weak gate. (True of SkillOpt too — an honest limitation, not a flaw to hide.)
- **Codegen ceiling.** Small, well-scoped tools are reliable; large or genuinely novel integrations are not yet. Scope the demo accordingly; treat hard tools as a roadmap item.
- **Safety of self-written code.** An agent running code it wrote is a real risk surface — which is why the governance layer (sandbox, static checks, capability gating, provenance) is a first-class part of the 7-day build, not an afterthought.

---

*Lineage: the "state-externalizing harness" frame and the validation-gate / rejected-edit / budget discipline draw on SkillOpt (text-space skill optimization) and Harness-1 (RL search agents with state-externalizing harnesses). Buildship points the same philosophy at a new axis — the agent's executable capabilities.*
