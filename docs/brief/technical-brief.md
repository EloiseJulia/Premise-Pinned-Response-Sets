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

Pending completion of the frozen full run. Insert:

1. beta_self versus beta_pin figure and correlation;
2. seed/context entropy figure and dangerous-mass estimate;
3. judge-selection regret figure and complete threshold-surface summary.

Regardless of direction, the completed brief will report:

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
