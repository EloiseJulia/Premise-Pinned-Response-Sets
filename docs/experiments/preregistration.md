# PPRS Confirmatory Preregistration

**Config:** `configs/runs/confirmatory-v1.json`
**Status:** Amendment 1 ready for freeze as `pprs-prereg-v2`.

## Research Questions

Primary: how much judge-rating uncertainty comes from unstated scoring premises
rather than sampling variation or prompt compliance?

Secondary: does a premise-pinned response set more closely track observed human
rating distributions than a directly self-reported response set?

## Hypotheses

### H1: Self-report and pinning measure different sensitivity

Across task-judge cells, Pearson correlation between `beta_self` and `beta_pin`
at temperature 0.7 is predicted to be below 0.4. Cells with a null beta are
excluded and counted. Report Pearson `r`, the 12-cell scatter, and a 95%
percentile confidence interval from 10,000 bootstrap resamples of task-judge
cells with seed 42. H1's directional prediction is met when point `r < 0.4`;
call it bootstrap-robust only when the upper confidence limit is below 0.4. A
correlation at or above 0.4 is reported as evidence for the upstream self-report
construct rather than treated as no result.

### H2: Nontrivial dangerous mass

More than 15% of item-judge cells are predicted to satisfy:

`H_seed <= 0.5 bit` and `H_ctx > 0`.

The direction is immutable. High `H_seed` is visible uncertainty and is never
called the dangerous quadrant. The denominator is every temperature-0.7
item-judge cell with non-null `H_seed` and `H_ctx`; report excluded cells and
reasons. The pooled point estimate is the primary test. A 95% percentile
interval uses 10,000 bootstrap resamples of items within task, retaining all
judges for each sampled item, seed 42. The prediction is met when the point
estimate is above 15%; call it bootstrap-robust only when the lower limit is
above 15%. Per-task proportions are reported without replacing the pooled test.

### H3: PPRS better matches observed human distributions

PPRS is predicted to outperform self-reported response sets against observed
human distributions, with the advantage increasing along the preregistered
rubric-ambiguity gradient:

ChaosNLI-SNLI < ChaosNLI-MNLI < SummEval-Relevance.

Evidence strength is reported separately because SummEval has only eight human
ratings per item.

For each item, judge, and `pi`, construct the binary human response-set vector.
The self vector is the per-option inclusion frequency across valid S repeats.
The pin vector is the binary PPRS union. Define item loss as the sum of squared
option-wise errors and define advantage
`Delta = MSE_self - MSE_pin` (positive favors PPRS). Average items equally,
then judges equally, within task. Report every `pi`; report both SummEval
polarities.

The preregistered H3 directional prediction is met when the median task
advantage over the five locked `pi` values is positive for all three tasks and
is ordered `SNLI <= MNLI <= SummEval` under both SummEval polarity arms.
Item-level 95% percentile intervals use 10,000 within-task bootstrap resamples,
seed 42. No polarity or `pi` point is selected after seeing results.

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
- `H_ctx`: for each disclosure round and surfaced premise, form a label
  distribution by weighting its valid candidate values equally. Average premise
  distributions equally within a round, then average valid rounds equally.
  Compute Shannon entropy in bits from the resulting label distribution.
- A premise contributes only when at least two distinct candidate values have
  valid pinned choices. A round contributes only when at least one premise
  contributes. If no round contributes, `H_ctx` is null, never zero-filled.
- PPRS: union of labels observed under valid one-dimension pins.
- Repeated premise IDs across disclosure rounds are retained as separate
  self-disclosure observations. Duplicate premise IDs within one response are a
  parse failure.
- `beta_self`: pooled over valid paired F/S samples within each task-judge-
  temperature cell, estimate `P(positive option is in S | F chose the upstream
  negative option)`. Pair by item and sample ID.
- `beta_pin`: over the same valid negative F samples, estimate
  `P(positive option is in the item PPRS | F chose the upstream negative
  option)`.
- Positive/negative mapping follows the pinned upstream task contract:
  Entailment/Contradiction for SNLI and MNLI; Relevant/Not Relevant for
  SummEval. Neutral does not enter the beta denominator.
- If a beta denominator is zero, the cell is null and excluded from correlation;
  it is never imputed.
- Human ChaosNLI response set: include an option iff its human share is at least
  `pi`.
- `pi`: full grid 0.05, 0.10, 0.15, 0.20, 0.25.
- `tau`: full upstream-comparable grid 0.0 through 1.0 by 0.1.
- SummEval: report both `upstream_behavior` and `semantic_aligned` polarity
  conventions as a specification curve.

No selected threshold replaces the complete scan surface.

The primary H1/H2/H3 tests use temperature 0.7. Temperature 0 is a
preregistered greedy-decoding ablation and is reported with the same metrics.
This avoids mechanically defining every temperature-0 cell as low seed entropy.

For `H_seed`, require at least two valid F samples. For all metrics, report valid
sample counts and failure rates alongside estimates.

## Primary Outputs

1. `beta_self` versus `beta_pin` scatter by task-judge cell, correlation and
   diagonal.
2. `H_seed` versus `H_ctx` item-judge distribution with the dangerous quadrant
   shaded and high-risk item list.
3. Regret of the judge selected by each candidate metric relative to the
   human-distribution optimum, reporting Hit Rate, both KL directions,
   Coverage, `MSE_self`, and `MSE_pin`.

For each task, threshold, polarity arm where applicable, and downstream metric,
each candidate metric selects its optimizing judge using its preregistered
direction. Exact ties are broken by lexicographically ascending model ID.
Consistency regret is `max_j consistency_j - consistency_selected`; bias regret
is `bias_mae_selected - min_j bias_mae_j`. Report the complete threshold
surface; any aggregate gives equal weight to tasks and grid cells.

## Ablations and Audits

- temperature 0 versus 0.7;
- length/syntax-matched placebo;
- option order randomization;
- simultaneous full-grid pinning on 20 items per task only;
- prompt leakage audit on 30 items per task using
  `mai-code-1-flash-picker`, outside the measured panel;
- both SummEval polarity conventions;
- all parse/provider failures reported, never imputed.

### Placebo estimand

For each valid real-pin/placebo matched pair, compare each choice with the
item-model-temperature forced-choice modal label (ties broken by task option
order). Define real and placebo flip indicators. Primary placebo contrast is
the mean matched difference `real_flip - placebo_flip`, with 10,000
item-cluster bootstrap resamples, seed 42. Also report real-pin and placebo
entropies using the same hierarchical weighting. Report adverse or null
contrasts.

### Full-grid estimand

On the committed 20-item/task subset, within each disclosure round enumerate
the Cartesian product containing one value from every valid surfaced premise
(maximum four premises, two or three values each). Each combination receives
one forced-choice call. Weight combinations equally within round and valid
rounds equally. Report full-grid entropy, full-grid label union, the difference
from one-dimensional `H_ctx`, and Jaccard similarity with the one-dimensional
PPRS. A round needs at least two valid grid combinations; otherwise its entropy
is null. This is an ablation, not a confirmatory hypothesis.

## Generation Controls

- forced-choice/pinned/placebo max completion tokens: 1024;
- response-set max completion tokens: 1024;
- premise-disclosure max completion tokens: 8192;
- request timeout: 120 seconds;
- provider retry count: 0 (each failure remains an explicit record);
- no fallback model or success-shaped retry.

## Amendment 1: Smoke generation budget repair

The frozen v1 smoke failed at 62.7% parse success. `gpt-5.4` parsed normally;
`gemini-3.5-flash` produced 1,094 malformed responses, overwhelmingly
empty/truncated completions under the v1 token budgets. Six provider errors were
also explicit. No confirmatory full run began.

Amendment 1 changes only generation budgets and the JSON-format suffix:

- new IDs `forced-choice-v2`, `response-set-v2`, `premise-pinned-v2`,
  `placebo-pinned-v2`, `premise-full-grid-v2`;
- require first character `{`, last character `}`, and no Markdown fences;
- increase completion budgets to 1024/1024/8192 as listed above.

All datasets, models, temperatures, repetitions, estimators, thresholds,
subsets, hypotheses, and reporting rules remain unchanged. The v1 smoke cache
is retained under `artifacts/wp6-smoke/`.

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
