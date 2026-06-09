# Buildship — Stage 2 Findings

*Self-extension reliability is bounded by the verifier behind the gate — and an
LLM-written verifier (self-authored OR independent) is not a reliable gate.*

## TL;DR

We built a 18-task held-out benchmark (compute / transform / chart / adversarial),
each with an automatic ground-truth verifier, and ran the harness under 5 ablation
arms (3 seeds each, DeepSeek-V3.2, local sandbox). **The validation gate never beat the
ungated baseline.** Removing the gate (`no_gate`) tied for the best end-to-end success;
the disciplined `full` arm did slightly *worse*; and replacing the self-test with an
*independently* LLM-generated test (`independent_gate`) was **dramatically worse and 3×
the cost**. The pre-registered claim ("gated, bounded, feedback-driven self-extension
beats ungated") is **refuted on this benchmark** — and the refutation is the contribution.

## Results (mean over 3 runs)

| arm | gate | e2e success | build rate | attempts | tokens | e2e per run |
|---|---|---|---|---|---|---|
| **no_gate** | off | **0.944** | 1.000 | 1.00 | 33,277 | .944 / .944 / .944 |
| **no_feedback** | self-test | **0.944** | 1.000 | 1.06 | 39,198 | .944 / .944 / .944 |
| full | self-test | 0.907 | 0.944 | 1.04 | 41,640 | .889 / .889 / .944 |
| budget_1 (1 attempt) | self-test | 0.870 | 0.926 | 1.00 | 32,493 | — |
| independent_gate | independent LLM test | **0.537** | 0.593 | 1.20 | **102,825** | .556 / .556 / .5 |

## What drove the numbers

- **`no_gate` = 0.944 is the ceiling.** Ungated, the only task that fails end-to-end is
  `adv_round_half_up` (17/18). Every other tool the model writes is correct on the first try.
- **The gate's *false positive* (`adv_round_half_up`).** The model reliably writes the
  naive `round(x*10**d)/10**d` (wrong on `1.005 → 1.0`, want `1.01`) **together with a
  self-test that passes it**. So the self-test gate *admits a broken tool* — the gate
  can't catch it because the test and the code share the same blind spot. This is the one
  task every self-test arm misses.
- **The gate's *false negative* (`transform_snake`).** The model writes verifier-correct
  code but a self-inconsistent self-test (it asserts an unspecified edge case its own code
  fails). The gate *rejects a correct tool*; with a bounded budget it sometimes can't
  recover → `exhausted_budget`. This is why `full` (0.907) < `no_gate` (0.944): gating's
  false-negatives cost more than its false-positives save.
- **`budget_1` (0.870)** loses `transform_snake` outright (no retry to recover the flaky
  self-test) — the one place the retry budget demonstrably helps.
- **`independent_gate` (0.537) is the key result.** Gating on a test written by a
  *separate* model call (which never sees the implementation) does **not** fix the
  problem — it **moves** it. The independent test is itself an unreliable LLM artifact:
  it over-specifies and rejects ~40% of correct tools (`transform_snake`, `wordcount`,
  …) → `build` drops to 0.593, and the extra `write_test` call + extra retries triple the
  token cost. It trades false-positives for rampant false-negatives.

## Alignment metric (self-test vs verifier, n=18)

A `no_gate` run with both signals captured per task:

```
pass/pass (correct admit) : 17
pass/FAIL (FALSE POSITIVE): 1  [adv_round_half_up]   gate admits a dud
FAIL/pass (FALSE NEGATIVE): 0  []                    (transform_snake's self-test fix held this run)
agreement = 0.944
```

The metric makes both failure modes measurable: the self-test agreed with ground truth
94% of the time, but its one disagreement was a false positive the gate could not catch.

## Conclusion

1. **Self-test gating is, at best, neutral here** and can hurt: `full ≤ no_gate` across
   all three seeds. The benchmark exhibits the gate's *false-negative* mode (reject
   correct tools) more than a *true-positive* mode (catch wrong tools a good test would
   flag), because **when the model's code is wrong, its self-test tends to be wrong too**
   (correlated errors → the `round_half_up` false positive).
2. **An independent LLM verifier is worse, not better.** The bottleneck is not *who*
   authors the test (the code's author vs a separate model) — it is that **the test is
   LLM-generated at all**. Both directions are unreliable; the independent one fails
   loudly (false negatives) and expensively.
3. **This is the project's stated risk, quantified:** "self-extension is only as
   trustworthy as the verifier behind the gate." A trustworthy gate needs a verifier
   grounded *outside* model output — a **spec / property-based check, an execution
   oracle, golden I/O examples, or a human** — not another generation from the same
   (or a sibling) model.

## Caveats

Single model (DeepSeek-V3.2), single sandbox (local subprocess), n=18 tasks, 3 seeds —
small and noisy (some runs had transient API timeouts; the runner now retries those, and
one independent_gate run predated that fix). Results are directional, not definitive; the
mechanism (correlated code/test errors; LLM-test unreliability) is the durable takeaway.

## Implied next experiments

- **Non-LLM gate signals:** property-based checks (e.g. Hypothesis), an execution oracle,
  or spec-derived golden examples as the gate — the arm that *should* finally beat
  `no_gate`.
- **Ensemble verification:** require K independent tests to agree (reduce single-test
  variance) — does a majority vote tame the false-negative blow-up?
- **Harder benchmark:** tasks where the model's first attempt is wrong *and* a faithful
  test catches it (true-positive mode), to give gating a fair chance to win.
