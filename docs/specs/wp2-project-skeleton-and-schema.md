# WP2 Specification: Project Skeleton and Schema

## Objective

Create the smallest executable and auditable Python project that can represent
the proposal-locked SNLI, MNLI, and SummEval-Relevance tasks without invoking
any model provider.

The first executable slice is the ChaosNLI arm:

- SNLI: 150 items sampled only from ChaosNLI SNLI;
- MNLI: 150 items sampled only from ChaosNLI MNLI;
- 100 human labels retained per item;
- option order fixed as Entailment, Neutral, Contradiction;
- source IDs, split, provenance, license source, and sampling seed retained.

The skeleton must also define the raw-result and run-manifest contracts required
by later provider, parser, cache, and analysis work.

## Non-goals

- Do not call any model or provider.
- Do not run a smoke test or full experiment.
- Do not implement prompt iteration, premise elicitation, or analysis figures.
- Do not select the four judge snapshots.
- Do not sample the final 150 SNLI or 150 MNLI records until the sampling seed
  and exact source revision are represented in a reviewable config.
- Do not collapse parse failures into defaults.
- Do not choose one SummEval polarity. Its interface must support the
  owner-approved unchanged and semantic-polarity specification-curve arms.
- Do not change any proposal-locked sample count, path count, repetition count,
  temperature condition, threshold scan, or dangerous-quadrant direction.

## Interfaces

### Proposed repository surface

```text
configs/
  tasks/
  prompts/
  runs/
src/pprs/
  data/
  records/
  manifests/
tests/
  data/
  records/
  manifests/
pyproject.toml
<dependency-lock-file>
```

The exact environment and lock command must be selected and recorded before
files are generated; it may not be invented retroactively after code exists.

### Task contract

Each task definition must include:

| Field | Meaning |
|---|---|
| `task_id` | Stable local identifier |
| `source_dataset` | Official dataset name |
| `source_revision` | Immutable revision or checksum |
| `source_split` | Source subset/split |
| `sample_size` | Proposal-locked item count |
| `sampling_seed` | Identity-bearing seed |
| `input_fields` | Ordered source fields used by prompts |
| `options` | Ordered semantic labels and transport tokens |
| `analysis_conventions` | Source-count mapping for each analysis convention |
| `ratings_per_item` | Expected human-label count |
| `license_source` | Immutable official license URL, revision, and blob |
| `data_card_source` | Immutable official data-card URL, revision, and blob |
| `upstream_reference` | Pinned indeterminacy commit and file/blob |

`analysis_conventions` maps semantic option tokens to source columns. NLI has
one canonical convention; SummEval has both owner-approved polarity
conventions.

For both NLI tasks:

| Token | Semantic label | ChaosNLI counter |
|---|---|---|
| `A` | Entailment | `e` |
| `B` | Neutral | `n` |
| `C` | Contradiction | `c` |

Allowed response-set tokens are `A`, `B`, `C`, `AB`, `AC`, `BC`, and `ABC`.
This option order matches the pinned upstream commit.

### Dataset-record contract

Every sampled item must retain:

- `task`;
- `item_id` from the official source;
- `source_dataset`;
- `source_revision`;
- `source_split`;
- `source_original_id`;
- `sampling_seed`;
- prompt input fields;
- raw human label counts in option order;
- normalized human label distribution;
- `ratings_per_item`;
- license and data-card source.

No generated model content belongs in the dataset record.

### Raw-result contract

The Parquet-compatible raw-result schema must contain every proposal field:

- identity: `cache_key`, `run_tag`, `git_sha`, `prereg_tag`;
- experiment coordinates: `task`, `item_id`, `judge_id`, `path`,
  `sample_id`;
- premise coordinates: `premise_id`, `premise_type`, `premise_value`,
  `premise_round`;
- call parameters: `model_snapshot`, `provider`, `temperature`, `top_p`,
  `seed`, `prompt_template_id`, `prompt_hash`,
  `option_permutation_seed`;
- raw response: `raw_text`;
- parsed response: `parsed_choice_hard`, `parsed_choice_set`,
  `parsed_premises`;
- status: `parse_status`, `provider_error`, `http_status`, `retry_count`;
- measurements: `prompt_tokens`, `completion_tokens`, `wall_clock_ms`,
  `ts_utc`.

Derived fields such as `H_seed`, `H_ctx`, PPRS vectors, `beta_self`, and
`beta_pin` must not be stored in the raw table.

`parse_status` is restricted to `ok`, `malformed_json`, `missing_field`,
`refused`, `timeout`, and `provider_error`. All parsed fields must be null for
non-`ok` records.

### Run-manifest contract

The manifest must identify every output-affecting input, including:

- git SHA and preregistration tag;
- task-config and prompt hashes;
- dataset revision and sampled-item-list hash;
- an explicit model-snapshot-to-provider mapping;
- temperatures, `top_p`, seeds, and response format;
- a content hash of the complete rendered-prompt ledger;
- option-permutation policy and seeds;
- path repetition counts;
- output locations and content hashes.

## Data and License Constraints

- Use only official ChaosNLI SNLI and MNLI records; never substitute original
  SNLI/MNLI random samples.
- Record the official ChaosNLI CC BY-NC 4.0 source. Mirrored repository metadata
  must not override official source terms.
- Retain original IDs so every sample maps back to ChaosNLI and its underlying
  SNLI/MNLI item.
- Raw datasets and sampled content remain outside Git under ignored data paths.
  Git tracks only configs, manifests, schemas, checksums, and small synthetic
  test fixtures.
- Upstream unlicensed source code is not copied. Local implementations may use
  the pinned behavior as evidence but must be independently written.
- Public release remains subject to later permission and provenance review.

## Acceptance Criteria

- [ ] Python project metadata and one dependency lock file exist.
- [ ] The selected environment, build, test, and lock commands are documented.
- [ ] SNLI and MNLI task configs encode the exact E/N/C option order and
  proposal-locked sample sizes.
- [ ] SummEval-Relevance encodes A=Relevant/B=Not Relevant and both polarity
  conventions; its sample seed remains null until owner approval.
- [ ] Config validation rejects wrong sample sizes, missing revisions, duplicate
  option tokens, and human-label mappings that do not sum to 100.
- [ ] Dataset schema retains every provenance field and original label count.
- [ ] Raw-result schema contains every proposal field with explicit nullability.
- [ ] Non-`ok` records cannot contain parsed values.
- [ ] Run-manifest schema includes every output-affecting identity dimension.
- [ ] Each SummEval polarity is represented by a distinct analysis manifest and
  output location, joined by a specification-curve manifest.
- [ ] Tests use only synthetic fixtures and make no network or provider calls.

## Test and Audit Evidence

Required tests:

1. valid SNLI and MNLI fixtures pass schema validation;
2. label counts not totaling 100 fail;
3. option-order drift fails;
4. a non-`ok` result with parsed values fails;
5. changing any identity-bearing manifest field changes the manifest identity;
6. both SummEval polarity convention identifiers can coexist without collision.

Independent audit must attack provenance loss, task-option drift, cache/manifest
identity omissions, silent null filling, and accidental network access.

## Deviations

None. Tooling choices not fixed by the proposal remain pending confirmation in
the WP2 plan and must not alter experimental parameters.
