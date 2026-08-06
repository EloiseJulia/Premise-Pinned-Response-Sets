# WP1 Specification: Upstream and Data Evidence

## Objective

Establish the immutable upstream reference and the exact evidence needed to
define the PPRS task interfaces lawfully and comparably:

- pin `lguerdan/indeterminacy` to a full commit SHA;
- verify the SummEval-Relevance option space and the transformation of the
  original 1--5 human ratings;
- record source, retrieval date, license status, and unresolved caveats;
- stop before WP2 if the upstream behavior is internally inconsistent.

The proposal remains the sole authority for research facts and locked
experimental parameters.

## Non-goals

- Do not copy upstream source code into this repository.
- Do not add the upstream submodule yet.
- Do not create local task configuration or choose a corrected label mapping.
- Do not change any locked sample count, threshold, task, model, prompt, or
  analysis parameter.
- Do not invoke models, run a smoke test, or run a full experiment.
- Do not commit, open a PR, mark a PR ready, or merge to `main` as part of this
  evidence gate.

## Interfaces

### Upstream code identity

| Field | Locked value |
|---|---|
| Repository | `https://github.com/lguerdan/indeterminacy` |
| Commit | `efdb3a2792369e2f98b86dd1d25c2f9c477c115a` |
| Commit date | 2025-11-11T04:03:30Z |
| Commit message | `update with camera ready edits` |
| `config/tasks.py` blob | `818b0aedb2281323f8440d8e0ddd8cbe0af50163` |
| `config/prompts.py` blob | `ec4199372aa80355e249d39cd061af2eaa5d09fd` |

The full SHA, not `main`, is the only acceptable future reference.

### SummEval-Relevance evidence interface

The pinned upstream exposes a binary judge interface:

- forced choice: `A = Relevant`, `B = Not Relevant`;
- response sets: `A`, `B`, or `AB`;
- inputs: article and summary;
- human ratings per item: 8.

The public processed human table contains:

- `relevance_0`: count of original ratings in `{1, 2, 3}`;
- `relevance_1`: count of original ratings in `{4, 5}`.

This data transformation was independently reproduced for all 1,600 processed
rows from the official SummEval file containing three expert and five crowd
ratings per summary.

### Resolved upstream inconsistency

The pinned upstream does not establish one semantically consistent mapping:

1. the prompt defines option index 0 (`A`) as **Relevant**;
2. `get_task_forced_choice_distribution` assigns option index 0 from
   `relevance_0`, whose published data are the **low** scores 1--3;
3. the nearby source comment instead claims `relevance_0` means scores 1--2
   and `relevance_1` means scores 3--5, which the published data contradict;
4. `positive_categorization_options` is `[0]`, again treating option index 0
   as the positive class.

The owner resolved this by requiring a specification curve with both
conventions:

- **upstream-behavior arm:** preserve the published human columns exactly;
- **semantic-polarity arm:** swap the human columns so ratings 4--5 align with
  `A = Relevant` and ratings 1--3 align with `B = Not Relevant`.

A zero-API reproduction using the immutable `main-run` logs established that
the upstream-behavior arm reproduces the paper's reported qualitative ranking:
KL-D(j,h) selects GPT-3.5-Turbo while Claude-3.5-Sonnet minimizes absolute
downstream bias. Swapping the human columns changes that ranking. The
specification curve is therefore required evidence, not an optional cleanup.

This conflict no longer blocks the ChaosNLI work. SummEval remains a parallel
analysis branch until both conventions are reported.

## Data and License Constraints

- Treat `lguerdan/indeterminacy` as unlicensed. GitHub reports no detected
  license and the pinned tree has no `LICENSE` file. Its README displays an MIT
  badge pointing to a missing file; that badge is not a license grant.
- Refer to upstream code only by repository, commit, file, line range, and blob
  SHA. Do not reproduce substantial code.
- The `lguerdan/indeterminacy-datasets` Hugging Face card declares MIT, but it
  aggregates third-party datasets and does not itemize how that declaration
  interacts with each source dataset's terms. It cannot override source terms.
- The official SummEval repository has an MIT `LICENSE`, but its README states
  that model outputs were shared with author consent, source articles are not
  included, and reconstruction requires CNN/DailyMail material. Dataset and
  underlying-content rights therefore require a separate release review.
- The official ChaosNLI repository states 100 annotations per example and uses
  CC BY-NC 4.0. The PPRS sampling frame remains the proposal-locked SNLI and
  MNLI portions of ChaosNLI; the mirrored Hugging Face metadata does not replace
  the official source license.
- Public release or publication remains blocked pending a dedicated permission
  and provenance review, as required by the proposal.

## Acceptance Criteria

- [x] A full immutable upstream commit SHA is recorded and resolves.
- [x] The target task and prompt blobs are recorded.
- [x] The SummEval judge option space is established.
- [x] The actual 1--5 to binary transformation is reproduced against all 1,600
  published processed rows.
- [x] Retrieval dates, source URLs, hashes, and license caveats are recorded in
  `docs/research/upstream-discretization.md`.
- [x] No upstream code is copied into this repository.
- [x] The owner resolves the upstream polarity inconsistency.
- [x] The published run logs are recomputed under both polarity conventions
  without model calls.
- [x] ChaosNLI planning may begin while the SummEval specification curve remains
  a parallel evidence branch.

## Test and Audit Evidence

- GitHub API commit, ref, tree, contents, file-history, and license checks.
- Hugging Face immutable dataset revisions and file object IDs.
- Row-level recomputation from official SummEval annotations to the upstream
  processed CSV.
- Exact upstream analysis at beta 0 and tau 0.5 using the immutable public
  `main-run` logs under unchanged and swapped human columns.
- Independent audit must attempt to falsify the commit identity, threshold
  mapping, prompt polarity, and license conclusions from the cited immutable
  sources.

## Deviations

None. No locked experimental parameter was changed. Both polarity conventions
are reported as a robustness surface; neither silently replaces the other.
