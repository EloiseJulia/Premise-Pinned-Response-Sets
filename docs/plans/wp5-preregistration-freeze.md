# WP5 Plan: Preregistration Freeze

## Preconditions

1. WP4 pilot parse/review gate passes.
2. One prompt template is selected.
3. Leakage audit plan is executable.
4. Four model identifiers have successful compatibility probes.

## Freeze Steps

1. Write `docs/experiments/preregistration.md`.
2. Write canonical run config and model/task/prompt hashes.
3. Record `pi=(0.05,...,0.25)` and `tau=(0.0,...,1.0 by 0.1)`.
4. Record both SummEval polarity arms.
5. Record F/S/P repetitions, temperatures, placebo, option randomization, and
   leakage-audit sample sizes.
6. Hash the preregistration and run config.
7. Commit and create a preregistration tag.
8. Run an independent hostile audit.
9. Only after PASS, start WP6 smoke.

## Stop Conditions

- prompt review is not mostly pin-able;
- any model cannot honor temperature or JSON requirements;
- model identity is not sufficiently reproducible;
- cache/manifest lacks an output-affecting field;
- sample manifests no longer match local Parquet.

## Independent Audit Prompt

```text
Audit the PPRS preregistration against the binding proposal. Verify every locked
sample count, path repetition, temperature, pi/tau grid, dangerous-quadrant
direction, prompt/model/task hash, SummEval polarity arm, placebo, option
randomization, leakage audit, and figure definition. Treat smoke/full execution
as forbidden until the freeze commit/tag is proven. Report PASS/FAIL.
```
