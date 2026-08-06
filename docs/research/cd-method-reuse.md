# C/D Method Reuse Evidence

**Retrieved:** 2026-08-06 (+08:00)

## Authorized Private Sources

| Work | Repository | Pinned commit | License state |
|---|---|---|---|
| C: When Consensus Lies | `EloiseJulia/When-Consensus-Lies` | `a0cd776fcdf8d155222514cf3ee6b8f52be2ed9c` | Private; no detected license; owner explicitly authorized reuse |
| D: two ways a design fail | `EloiseJulia/two-ways-a-design-fail` | `e08e051d11712c2e5356616d6110dd608b1920f5` | Private; no detected license; owner explicitly authorized reuse |

The repositories were cloned outside the PPRS worktree and inspected read-only.
No model was called and no experiment output was imported.

## Reusable Structure from C

Primary evidence:

- `scripts/lps_method.py`;
- `paper/plans/2026-07-23-study2-latent-premise-sensitivity-design.md`;
- `paper/specs/phase3-detector-hypothesis-surfacing.md`.

Reusable method structure:

1. use a generic prompt that contains no gold axis;
2. ask for decision-relevant unstated premises and 2--3 candidate values;
3. distinguish answer-semantic premises from formatting, language, tooling, or
   output-encoding dimensions;
4. pin one premise dimension and one candidate value per call;
5. preserve surfaced and dropped premises for audit;
6. use a different model family for independent leakage/method audit;
7. keep the prompt pilot exploratory and freeze only after owner review.

PPRS adaptations:

- output uses the proposal schema (`premise_id`, `premise_type`, `statement`,
  `candidate_values`);
- task option labels are excluded from the premise-disclosure framing;
- pinned scoring uses task-specific randomized discrete options;
- C's executable-answer clustering is not copied because PPRS labels already
  provide deterministic equivalence classes.
- C and D both use a local OpenAI-compatible proxy, but their historical
  defaults disagree (`127.0.0.1:8313/v1` versus `127.0.0.1:8787/v1`). PPRS
  therefore has no hard-coded `ghc-api` endpoint and requires
  `GHC_API_BASE_URL` when real calls are later approved.
- Model snapshots known to reject a temperature field must be rejected before
  collection rather than silently omitting a proposal-locked temperature arm.

## Reusable Structure from D

Primary evidence:

- `src/twdf/calibration/thresholds.py`;
- `docs/plans/preregistration-axis1.md`;
- `scripts/analysis/measurement_audit.py`.

Reusable method structure:

1. separate calibration procedure from frozen threshold values;
2. scan candidate thresholds deterministically;
3. refuse to serialize an unfrozen threshold as a confirmatory artifact;
4. report per-threshold decision instability rather than one selected point;
5. abstain/escalate when a configuration is outside the calibrated support or
   when design decisions reverse across valid specifications;
6. report null and directionally adverse results.

PPRS adaptations:

- the proposal already locks full scans for `pi` and `tau`, so no threshold
  fitting code is imported;
- SummEval polarity is represented as a specification curve;
- D's simulated-user metrics and persona/backend logic are out of scope.

## Caveats

- These repositories are secondary implementation evidence, not the factual
  authority for PPRS.
- Their parameters, thresholds, model lists, prompts, and task semantics are not
  inherited.
- PPRS code must remain independently written and cite the pinned commits when a
  method pattern is materially reused.
