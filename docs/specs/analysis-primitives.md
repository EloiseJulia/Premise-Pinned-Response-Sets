# Analysis Primitives Specification

## Objective

Implement proposal-locked measurement primitives before preregistration:

- Shannon entropy in bits;
- `H_seed` from forced-choice resamples;
- `H_ctx` from one-dimension-at-a-time pinned choices;
- dangerous quadrant: `H_seed <= 0.5` and `H_ctx > 0`;
- ChaosNLI human response-set scan over `pi = 0.05..0.25` by `0.05`;
- threshold-surface evaluation over an explicitly supplied `tau` grid;
- SummEval unchanged/semantic-aligned polarity mappings.

These functions do not constitute preregistration and do not choose an
otherwise unspecified `tau` grid.

## Non-goals

- Do not compute results from model outputs.
- Do not select a single `pi`, `tau`, or polarity.
- Do not implement beta estimation until its exact PPRS definition is frozen.
- Do not aggregate across tasks or judges.
- Do not generate publication figures.

## Acceptance Criteria

- Entropy is zero for a point mass and one bit for a balanced binary sample.
- Empty inputs fail rather than returning zero.
- `H_ctx` groups only within one item/judge/premise dimension supplied by the
  caller.
- Dangerous-quadrant direction cannot be inverted.
- `pi` values are exactly `(0.05, 0.10, 0.15, 0.20, 0.25)`.
- A human option enters the response set when its share is greater than or equal
  to `pi`.
- `tau` values must be explicit, unique, finite, and within `[0,1]`.
- Both SummEval polarity mappings are available and produce distinct semantic
  distributions when source columns differ.
- Input count/probability validation rejects NaN, negative, or unnormalized
  values.

## Deviations

None. The `tau` grid remains owner/preregistration-gated.
