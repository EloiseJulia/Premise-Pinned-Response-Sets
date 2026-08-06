# PPRS Confirmatory Preregistration

**Config:** `configs/runs/confirmatory-v1.json`  
**Status:** Draft pending leakage-audit completion, independent audit, freeze
commit, and preregistration tag.

## Research Questions

Primary: how much judge-rating uncertainty comes from unstated scoring premises
rather than sampling variation or prompt compliance?

Secondary: does a premise-pinned response set more closely track observed human
rating distributions than a directly self-reported response set?

## Hypotheses

### H1: Self-report and pinning measure different sensitivity

Across task-judge cells, Pearson correlation between `beta_self` and `beta_pin`
is predicted to be below 0.4. Report the coefficient, cell-level scatter, and
confidence interval. A correlation at or above 0.4 is reported as evidence for
the upstream self-report construct rather than treated as no result.

### H2: Nontrivial dangerous mass

More than 15% of item-judge cells are predicted to satisfy:

`H_seed <= 0.5 bit` and `H_ctx > 0`.

The direction is immutable. High `H_seed` is visible uncertainty and is never
called the dangerous quadrant.

### H3: PPRS better matches observed human distributions

PPRS is predicted to outperform self-reported response sets against observed
human distributions, with the advantage increasing along the preregistered
rubric-ambiguity gradient:

ChaosNLI-SNLI < ChaosNLI-MNLI < SummEval-Relevance.

Evidence strength is reported separately because SummEval has only eight human
ratings per item.

## Data

Use only the three committed seed-42 sample manifests:

- ChaosNLI-SNLI: 150;
- ChaosNLI-MNLI matched: 150;
- SummEval-Relevance: 150.

Every result retains source revision, original ID, sample manifest, license/data
card, and ordered item identity.

## Judges

Exact service identifiers:

- `gpt-5.4`;
- `gpt-4o-mini-2024-07-18`;
- `gemini-3.1-pro-preview`;
- `gemini-3.5-flash`.

The Google identifiers lack date suffixes. Claims are limited to the observed
service snapshots and call dates. No silent model replacement is permitted.

## Elicitation Paths

- F: forced choice, 20 repetitions.
- S: direct response set, 20 repetitions.
- P disclosure: `premise-disclosure-inventory-v2`, three repetitions.
- P scoring: pin one surfaced premise dimension and one candidate value per
  call; never pin multiple dimensions in the primary pipeline.
- Placebo: one syntax- and length-matched irrelevant pin for every real pin.

The selected disclosure prompt requests at most four premises, each with two or
three values and one of ambiguity/vagueness/disagreement.

All paths run at temperatures 0 and 0.7 with `top_p=1`. Options are permuted
using a recorded coordinate-derived seed. Every call uses strict JSON and the
proposal cache identity.

## Metrics

- `H_seed`: Shannon entropy in bits over F choices.
- `H_ctx`: Shannon entropy in bits after marginalizing P pinned choices over
  candidate values.
- PPRS: union of labels observed under valid one-dimension pins.
- Human ChaosNLI response set: include an option iff its human share is at least
  `pi`.
- `pi`: full grid 0.05, 0.10, 0.15, 0.20, 0.25.
- `tau`: full upstream-comparable grid 0.0 through 1.0 by 0.1.
- SummEval: report both `upstream_behavior` and `semantic_aligned` polarity
  conventions as a specification curve.

No selected threshold replaces the complete scan surface.

## Primary Outputs

1. `beta_self` versus `beta_pin` scatter by task-judge cell, correlation and
   diagonal.
2. `H_seed` versus `H_ctx` item-judge distribution with the dangerous quadrant
   shaded and high-risk item list.
3. Regret of the judge selected by each candidate metric relative to the
   human-distribution optimum, reporting Hit Rate, both KL directions,
   Coverage, `MSE_self`, and `MSE_pin`.

## Ablations and Audits

- temperature 0 versus 0.7;
- length/syntax-matched placebo;
- option order randomization;
- simultaneous full-grid pinning on 20 items per task only;
- prompt leakage audit on 30 items per task using
  `mai-code-1-flash-picker`, outside the measured panel;
- both SummEval polarity conventions;
- all parse/provider failures reported, never imputed.

## Smoke Gate

After freeze, run 10 items x two pilot models across F/S/P:

- parse success at least 95%;
- second-run cache hit rate exactly 100%;
- 20 records inspected with no silent imputation.

Failure blocks the full run.

## Reporting Commitments

- Report all three hypotheses bidirectionally.
- Report null, adverse, placebo, leakage, and polarity-sensitive findings.
- Do not claim deployment prevalence.
- Separate NLI and SummEval human-reference strength.
- Preserve the WP4 human-review deviation and do not describe AI review as
  human review.
