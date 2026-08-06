# WP5 Specification: Preregistration Freeze

## Objective

After WP4 prompt review passes, freeze the confirmatory study before smoke or
full collection:

- hypotheses H1--H3;
- task samples and hashes;
- exact model IDs and service evidence;
- prompt IDs and hashes;
- path repetitions and temperature arms;
- `pi` and `tau` scan grids;
- dangerous-quadrant direction;
- SummEval polarity specification curve;
- three primary figures and reporting rules.

## Non-goals

- Do not tune thresholds from smoke/full results.
- Do not replace a failed model after freeze without a deviation entry.
- Do not change prompt wording after freeze.
- Do not call the full grid before smoke passes.
- Do not hide null, adverse, polarity-sensitive, or placebo results.

## Locked Inputs from the Proposal

- tasks: ChaosNLI SNLI 150, ChaosNLI MNLI 150, SummEval-Relevance 150;
- seed 42 and committed sample manifests;
- F resamples: 20;
- S resamples: 20;
- P disclosure rounds: 3;
- P pinning: one premise dimension at a time;
- full-grid pinning: only 20-item/task subset ablation;
- temperature arms: 0 and 0.7;
- dangerous quadrant: `H_seed <= 0.5` bit and `H_ctx > 0`;
- `pi`: 0.05--0.25 by 0.05;
- option order randomized with recorded seed;
- placebo and leakage audits required.

## Upstream-Comparable `tau` Grid

Unless the pilot exposes an implementation impossibility, freeze the pinned
indeterminacy analysis grid observed in its camera-ready notebook:

`tau = 0.0, 0.1, ..., 1.0`.

This is a full surface, not a selected operating point.

## Acceptance Criteria

- [ ] WP4 review record states most outputs are pin-able.
- [ ] One disclosure template ID is selected with rationale.
- [ ] Model IDs and service probe evidence are recorded.
- [ ] All config and prompt hashes are in one canonical manifest.
- [ ] Preregistration contains H1--H3 and all robustness surfaces.
- [ ] Deviation log remains empty or contains explicit owner-approved entries.
- [ ] Freeze commit is signed by hash and tagged before smoke.

## Deviations

None at draft time.
