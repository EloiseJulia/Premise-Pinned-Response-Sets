# Upstream SummEval Discretization Evidence

**Retrieved:** 2026-08-06 (+08:00)
**Status:** Evidence established; owner decision recorded; ChaosNLI planning
unblocked and SummEval retained as a parallel specification-curve branch.

## Binding Project Requirement

The proposal requires PPRS to use the SummEval discretization from
`lguerdan/indeterminacy` rather than inventing a new option space. It also
requires an exact commit pin, no copying of unlicensed upstream code, and a stop
for owner confirmation when a locked requirement cannot be implemented
unambiguously.

External sources below verify upstream behavior; they do not replace or amend
the proposal.

The local secondary analysis
`A——Validating LLM-as-a-Judge Systems under Rating Indeterminacy论文解读.md`
was also reviewed in full after it became available on 2026-08-06. It confirms
that the paper treats SummEval as a discrete/ordinal task and flags a general
risk that historical dataset annotations may not be distributed like ratings
elicited by the paper's constructed prompts. It does not state the SummEval
1--5 binning threshold or resolve the option-polarity conflict below. Because it
is an interpretation rather than the primary paper or executable artifact, it
is supporting context only.

## 1. Pinned Upstream Commit

| Evidence | Value |
|---|---|
| Repository | <https://github.com/lguerdan/indeterminacy> |
| Pinned commit | [`efdb3a2792369e2f98b86dd1d25c2f9c477c115a`](https://github.com/lguerdan/indeterminacy/commit/efdb3a2792369e2f98b86dd1d25c2f9c477c115a) |
| Commit timestamp | 2025-11-11T04:03:30Z |
| Message | `update with camera ready edits` |
| Parent | `0859863ce9701e3ae38ce3f3f9dd3b5b3b202476` |
| Tree | `441f32e81700006d98c834ca3bc3735561ca64f5` |
| `config/tasks.py` | [blob `818b0aed...`](https://github.com/lguerdan/indeterminacy/blob/efdb3a2792369e2f98b86dd1d25c2f9c477c115a/config/tasks.py) |
| `config/prompts.py` | [blob `ec419937...`](https://github.com/lguerdan/indeterminacy/blob/efdb3a2792369e2f98b86dd1d25c2f9c477c115a/config/prompts.py) |

At retrieval, `refs/heads/main` resolved to this commit. The two target config
files were introduced in the initial commit and were not changed by the later
camera-ready commit; pinning the camera-ready commit therefore preserves their
verified blobs while identifying the released repository state.

**Caveat:** `main` is mutable. Future code and documentation must use the full
commit SHA and verify the blob SHAs, not rely on the current branch head.

## 2. Judge-Facing SummEval-Relevance Discretization

The pinned task configuration (`config/tasks.py`, lines 53--63) defines:

| Field | Upstream value |
|---|---|
| Task | `summ_eval_relevance` |
| Source path | `SummEval/summ_eval_processed.csv` |
| Property | `Relevance` |
| Number of options | 2 |
| Allowed forced-choice tokens | `A`, `B` |
| Allowed response-set tokens | `A`, `B`, `AB` |
| Human ratings per item | 8 |

The pinned prompt (`config/prompts.py`, lines 242--304) defines:

- `A`: **Relevant** -- captures the main points effectively with minimal
  redundancy;
- `B`: **Not Relevant** -- misses key points or contains excessive irrelevant
  information;
- forced-choice elicitation selects one token;
- response-set elicitation selects all reasonably applicable tokens.

**Conclusion:** the upstream judge-facing discretization is binary, not the
original five-point Likert scale. The comparable PPRS option vocabulary is
therefore semantically `{Relevant, Not Relevant}`, with response sets
`{Relevant}`, `{Not Relevant}`, and `{Relevant, Not Relevant}`.

## 3. Human-Rating Transformation

### Sources

1. Official SummEval annotations:
   <https://storage.googleapis.com/sfr-summarization-repo-research/model_annotations.aligned.jsonl>
2. Upstream processed data at immutable Hugging Face revision
   `37b8d7863430ec3433d6a73da08408b064643b8b`:
   <https://huggingface.co/datasets/lguerdan/indeterminacy-datasets/blob/37b8d7863430ec3433d6a73da08408b064643b8b/SummEval/summ_eval_processed.csv>
3. Upstream task code:
   [`config/tasks.py`](https://github.com/lguerdan/indeterminacy/blob/efdb3a2792369e2f98b86dd1d25c2f9c477c115a/config/tasks.py)

### Reproduction method

- Read all 1,600 processed rows.
- Match each row to the official annotation record by article ID and exact
  summary text, retaining duplicate candidates rather than collapsing them.
- Combine three expert and five crowd annotations.
- Compare the published `_0`/`_1` counts with both candidate partitions:
  `1--2` versus `3--5`, and `1--3` versus `4--5`.
- Require every processed row to be compatible with the claimed partition.

### Result

| Dimension | Rows compatible with `1--3` / `4--5` | Rows compatible with `1--2` / `3--5` |
|---|---:|---:|
| Coherence | 1,600 / 1,600 | 311 / 1,600 |
| Consistency | 1,600 / 1,600 | 709 / 1,600 |
| Fluency | 1,600 / 1,600 | 629 / 1,600 |
| Relevance | 1,600 / 1,600 | 409 / 1,600 |

For relevance, the published columns therefore mean:

| Processed column | Verified source ratings |
|---|---|
| `relevance_0` | count of ratings 1, 2, or 3 |
| `relevance_1` | count of ratings 4 or 5 |

Local verification hashes:

- official annotation file SHA-256:
  `f0d4166e0cdeb439b387c4449634b067b7e9f721b9ef4c2b722f6b7550d3d6ab`;
- processed CSV SHA-256:
  `bfbfe70ae8703fcab94748364ab5e644f499cad13fbb8dbd911ad868a6761d04`;
- Hugging Face file object ID:
  `5f3c386bf230cfa0d53fec293cfb56bf7ac76637`.

**Caveat:** the processed file does not include the preprocessing script, so the
transformation is established by complete data reproduction rather than by an
author-provided transformation implementation.

## 4. Upstream Inconsistency and Published-Run Reproduction

The evidence does not yield one internally consistent end-to-end mapping.

| Surface | Option/index 0 | Option/index 1 |
|---|---|---|
| Prompt | `A = Relevant` | `B = Not Relevant` |
| Published human data | `relevance_0 = ratings 1--3` | `relevance_1 = ratings 4--5` |
| `tasks.py` comment | ratings 1--2 | ratings 3--5 |
| Human-distribution code | reads `relevance_0` | reads `relevance_1` |
| Positive-class config | index 0 is positive | index 1 is not |

Assuming the original 1--5 scale increases with quality, the processed data put
low ratings in index 0 while the prompt and positive-class configuration put
the positive semantic label in index 0. The code comment also states a threshold
that the published data do not use.

This is not a minor documentation ambiguity: it can invert human-versus-judge
comparisons and directly threaten H3.

The newly available local analysis of paper A supplies a decisive qualitative
anchor for SummEval-Relevance at beta 0 and tau 0.5: KL-D(j,h) selects
GPT-3.5-Turbo, while Claude-3.5-Sonnet has the lowest absolute downstream bias.

### Zero-API reproduction

Sources:

- upstream code at
  `efdb3a2792369e2f98b86dd1d25c2f9c477c115a`;
- public experiment revision
  `d009e71909eb242952bea8bd5475d6c27d22a1ff`;
- `runs/main-run/summ_eval_relevance/` judge logs and ratings;
- the upstream notebook's beta 0, tau 0.5 ranking setup.

No provider was called. The immutable logs were scored twice:

| Convention | KL-D(j,h) selected judge | Lowest-bias judge | Full-data absolute bias regret |
|---|---|---|---:|
| Published columns unchanged | GPT-3.5-Turbo | Claude-3.5-Sonnet | 0.255 |
| Human `_0`/`_1` columns swapped | DeepSeek Chat | Llama-3.3-70B-Instruct | 0.010 |

Using the notebook's ten 100-item subsamples, the unchanged-column arm retained
the reported qualitative ranking and had mean per-sample regret 0.300; the
swapped arm selected DeepSeek Chat for both KL-D(j,h) and mean absolute bias,
with mean per-sample regret 0.022.

**Conclusion:** no hidden loader remapping was found. The paper's published
qualitative result follows the unchanged-column convention, in which the human
low-score column occupies the prompt's positive option index. The semantic
polarity mismatch is therefore part of the effective published analysis
convention.

## 5. Provenance and License Evidence

### `lguerdan/indeterminacy`

- GitHub API license detection: `null`.
- The pinned root tree has no `LICENSE` file.
- The README shows an MIT badge linking to `LICENSE`, but that target is absent.

**Conclusion:** under the proposal's binding rule, treat the repository as
unlicensed. Cite and pin it; do not copy its code.

### Upstream Hugging Face dataset mirror

- Repository: <https://huggingface.co/datasets/lguerdan/indeterminacy-datasets>
- Pinned revision: `37b8d7863430ec3433d6a73da08408b064643b8b`
- The dataset card declares `license: mit`.

**Caveat:** this is a blanket card-level declaration over a collection of
third-party datasets. It does not document dataset-by-dataset relicensing
authority and must not be treated as superseding official source terms.

### Official SummEval

- Repository: <https://github.com/Yale-LILY/SummEval>
- Repository commit observed:
  `81b59ad53d63cb6009764240853c91235a44e238`
- License file: MIT.
- README: 1,600 summaries, each annotated by five crowdworkers and three
  experts on coherence, consistency, fluency, and relevance; source articles
  are not distributed; model outputs were shared with author consent.

**Caveat:** the repository license and consent statement do not eliminate
separate obligations for CNN/DailyMail source material or every incorporated
model output. Public redistribution needs a dedicated review.

### Official ChaosNLI

- Repository: <https://github.com/easonnie/ChaosNLI>
- README: 100 annotations per example; 4,645 examples total, including the
  proposal-relevant SNLI and MNLI portions.
- License: CC BY-NC 4.0.

**Caveat:** non-commercial and attribution conditions apply, and underlying
SNLI/MNLI terms remain relevant. The Hugging Face mirror's MIT metadata does
not replace these source terms.

## 6. Conclusions

1. Pin `lguerdan/indeterminacy` at
   `efdb3a2792369e2f98b86dd1d25c2f9c477c115a`.
2. The judge-facing SummEval-Relevance task is binary:
   `Relevant` / `Not Relevant`, with `A`, `B`, and `AB` response tokens.
3. The published human data actually bin original ratings as `1--3` versus
   `4--5`, not the `1--2` versus `3--5` split claimed by the source comment.
4. The published human column polarity conflicts with the prompt and
   positive-class polarity.
5. The unchanged-column convention reproduces the paper's reported qualitative
   SummEval-Relevance ranking; the semantic-polarity convention does not.
6. Both conventions must be reported as a specification curve.
7. This issue does not block the proposal-locked ChaosNLI SNLI and MNLI arms,
   whose E/N/C option spaces have no positive/negative polarity ambiguity.

## 7. Owner Decision

On 2026-08-06, the owner decided:

1. retain the verified `1--3` versus `4--5` binary data transformation;
2. do not wait for author correspondence when the public logs can establish the
   effective paper convention;
3. report both unchanged and semantically aligned polarities as a
   specification curve;
4. allow ChaosNLI planning to proceed while SummEval remains a parallel branch.

This is not recorded as a deviation from a locked experimental value: the
underlying data are unchanged, and the second polarity is a robustness analysis
over a coding convention. The proposal-locked downstream threshold scans remain
unchanged. No model calls or full experiments are authorized by this decision.
