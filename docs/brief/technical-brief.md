# Premise-Pinned Response Sets

## Question

Can stable judge ratings conceal sensitivity to unstated scoring premises, and
does premise pinning recover response sets that better match observed human
rating distributions?

## Study

- Tasks: ChaosNLI-SNLI, ChaosNLI-MNLI, SummEval-Relevance.
- Judges: two vendors and two capability tiers.
- Paths: forced choice, self-reported response set, premise disclosure and
  one-dimension pinning, matched placebo.
- Primary diagnostic: low `H_seed`, positive `H_ctx`.
- Robustness: full `pi`/`tau` surfaces and both SummEval polarity conventions.

## Results

The frozen run produced 365,543 raw records; 350,505 parsed successfully and all
failures remain explicit.

1. **H1 was not supported.** `beta_self` and `beta_pin` had Pearson
   `r=0.439`, 95% bootstrap CI `[0.306, 0.871]`, above the predicted 0.4
   threshold. This is evidence that direct self-report and premise pinning share
   more structure than predicted, though the interval is wide.
2. **H2 was strongly supported.** The dangerous quadrant contained 80.69% of
   valid temperature-0.7 item-judge cells, 95% CI `[78.72%, 82.63%]`. Mean
   real-pin context entropy was 0.922 bits versus 0.190 for matched placebo.
3. **H3 was mixed and therefore not supported overall.** Median
   `MSE_self-MSE_pin` was −0.327 for SNLI, +0.104 for MNLI, +0.595 for
   SummEval under the upstream polarity, and +0.254 under the semantic polarity.
   PPRS helped on MNLI/SummEval but hurt on SNLI, violating the preregistered
   all-positive monotonic prediction.

The matched real-minus-placebo flip contrast was +0.2265, 95% CI
`[0.2160, 0.2368]`. Full-grid interactions were small: mean entropy difference
approximately +0.0024 bits and mean PPRS Jaccard approximately 0.955.

The report includes:

- H1 correlation and confidence interval, including high-correlation evidence
  favorable to the upstream self-report construct;
- H2 dangerous mass, including a null or sub-15% estimate;
- H3 task/polarity/`pi` surfaces, including adverse PPRS results;
- placebo contrasts even when they weaken the premise-sensitivity claim;
- all 90 leakage-audit outcomes and rationale-quality caveat;
- both SummEval polarity conventions without selecting the favorable one.

## What the result can establish

- Whether the failure mode exists in the frozen task/model panel.
- Whether it is measurable with black-box calls.
- Whether PPRS is closer than direct self-report to the available human
  references.

## What it cannot establish

- Real-world deployment prevalence.
- Construct validity of model-disclosed premises as human reasoning.
- Equal human-reference strength for SummEval and ChaosNLI.
- Exact numeric reproducibility after commercial service drift.

## Reproducibility

The release package must include the preregistration tag, raw run manifest,
raw-record inventory, prompt ledger, analysis manifests for both SummEval
polarities, figures, high-risk list, and `artifacts/wp8/reproducibility-manifest.json`.
