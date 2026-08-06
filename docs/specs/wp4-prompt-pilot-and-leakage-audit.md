# WP4 Specification: Prompt Pilot and Leakage Audit

## Objective

Prepare and pilot the three proposal paths on a small exploratory slice:

- F: forced choice;
- S: self-reported response set;
- P: premise disclosure followed by one-dimension-at-a-time pinning;
- placebo: syntax-matched irrelevant pinning.

This specification covers the offline prompt assets and the later
20-item x 2-model pilot gate. The current implementation phase stops before any
model call.

## Non-goals

- Do not select the final premise-disclosure wording without human review.
- Do not change F=20 samples, S=20 samples, P disclosure=3 rounds, temperature
  conditions 0/0.7, or any proposal threshold.
- Do not run the pilot, smoke test, or full experiment yet.
- Do not include task option labels or gold hints in premise-disclosure
  instructions.
- Do not use C/D task-specific prompts, gold axes, or thresholds.

## Interfaces

### Prompt registry

Each prompt has:

- immutable template ID;
- path and stage;
- version;
- static framing;
- task-specific label-free criterion;
- rendered hash;
- option permutation seed when options are present.

### Premise-disclosure candidates

Maintain 4--5 candidate wordings. Every candidate must:

- ask only for decision-relevant scoring premises;
- exclude task option labels;
- request 2--3 concrete candidate values;
- classify each premise as ambiguity, vagueness, or disagreement;
- request strict JSON only;
- avoid asking for an answer or predicted label;
- state that formatting/tooling/output-encoding considerations are not scoring
  premises.

### Pinned scoring

Pinned prompts:

- pin exactly one premise and one value;
- use the same item/rubric/options as the forced-choice path;
- randomize option order deterministically;
- require one JSON choice;
- retain premise coordinates and permutation seed.

### Placebo

The placebo uses the same pinning syntax and forced-choice prompt, but pins an
irrelevant interface metadata dimension. The rendered record stores prompt
length and the difference from its matched real pin.

### Leakage audit

Two layers:

1. offline lexical guard verifies that the static disclosure framing and
   label-free task criterion contain no task option labels/tokens;
2. later out-of-panel model audit reviews 30 items per task.

Natural occurrences inside the source article/context are reported separately
and are not silently removed.

## Data and License Constraints

- C/D patterns are used under the owner's explicit authorization and pinned in
  `docs/research/cd-method-reuse.md`.
- No private repository content is copied verbatim as a wholesale module.
- Prompt candidates and audit records are PPRS-owned artifacts.
- Pilot outputs remain outside Git except for redacted review decisions,
  manifests, and hashes.

## Acceptance Criteria

- [ ] Five disclosure candidates exist with stable IDs.
- [ ] Offline leakage tests pass for all three task framings.
- [ ] Option permutation is deterministic, complete, and seed-sensitive.
- [ ] F/S/P/placebo renderers emit response-format-compatible prompts.
- [ ] Pinned prompts contain exactly one premise/value resolution.
- [ ] Placebo and real pin use the same syntactic template.
- [ ] No provider call occurs in offline tests.
- [ ] Before preregistration, 20 items x 2 models x 4--5 variants are manually
  reviewed and a single wording decision is recorded.
- [ ] Later leakage audit uses 30 items per task and an out-of-panel model.

## Test and Audit Evidence

Hostile audit attempts:

- inject option labels through criteria;
- reorder or drop an option during permutation;
- reuse one permutation seed for a different ordering;
- render multiple premise dimensions in one pinned prompt;
- make placebo syntax differ from the real pin;
- request an answer in the disclosure stage;
- allow unknown prompt IDs or response formats.

## Deviations

None. Prompt candidates are exploratory assets, not a change to locked
experimental parameters.
