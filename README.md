# Buildship

> **Working name.** An agent that writes its own tools.

**Thesis:** an agent's capabilities should be external, recoverable, validated state — not baked into weights or hand-wired ahead of time. Buildship is a *state-externalizing harness* that lets a **frozen** model grow its own toolset under control: when it hits a task it can't do, it builds the tool, proves it works, keeps it, and reuses it.

## The loop

1. **Plan** the task against the current toolset.
2. **Detect the gap** — "no tool for X."
3. **Research X** (Tavily) and feed what it learns to the coder.
4. **Generate** a tool against a fixed contract — typed signature, docstring, self-test — via codegen on Nebius.
5. **Run** it in a sandbox; on failure, feed the traceback back and retry under a bounded edit budget.
6. **Gate** — admit the tool to the library **only if its test passes**.
7. **Use** it to finish the task, firing a real action via Composio.

## Architecture in one breath

A state-externalizing harness. The model owns only *semantic* decisions (what to build, whether it's done). The harness owns *durable* state — the tool library, a verification record per tool, and a build budget.

## What it is **not**

- Not a fixed-toolset agent — the toolset is the *output*, not the input.
- Not fine-tuning — the model stays frozen; nothing touches weights.
- Not a generic "do-my-tasks" assistant — the wedge is *self-extension under control*, not breadth.

## Stack

- **Package manager:** [uv](https://docs.astral.sh/uv/) (Python 3.12).
- **Codegen:** Nebius coder model (DeepSeek-V3 or large Qwen), low temperature.
- **Sandbox + actions:** Composio remote workbench + `@action` registration.
- **Research:** Tavily for the API-research step.

## Getting started

```bash
cp .env.example .env   # then fill in your keys
uv sync                # install dependencies into .venv
uv run main.py         # config check — verifies your keys are loaded
```

Run everything from the repo root.

## Project docs

- [`forge-product-plan.md`](./forge-product-plan.md) — the *what / why / who*.
- [`stages.md`](./stages.md) — the *how / when* (priority-ordered build plan).

## Status

Early. See `stages.md` for the priority ordering: **1)** win the hackathon · **2)** paper-shaped result · **3)** shippable harness.
