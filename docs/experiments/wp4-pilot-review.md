# WP4 Prompt Pilot Review

**Date:** 2026-08-07
**Status:** Positive exploratory signal; owner line review deferred under the
recorded deviation.

## Design

- Items: 7 ChaosNLI-SNLI, 7 ChaosNLI-MNLI, 6 SummEval-Relevance.
- Models: `gpt-5.4`, `gemini-3.5-flash`.
- Original variants: five disclosure templates.
- Temperature: 0.
- Total original cells: 200.
- Data identity: committed seed-42 sample manifests.

## Infrastructure Attempt

The first 200-cell attempt produced 200 explicit `provider_error` records
because LiteLLM required a placeholder API key even though the local proxy
requires no authentication. Those failures were retained under
`artifacts/wp4-pilot/`; the adapter was fixed, tested, audited, and rerun using
a new run tag/cache.

## Original Five-Variant Pilot

| Result | Count |
|---|---:|
| Strict parser `ok` | 150 |
| Strict parser `malformed_json` | 50 |
| Provider failures | 0 |

All 50 malformed responses were Gemini outputs wrapped in Markdown JSON fences;
their interiors were complete schema-shaped JSON. The strict parser correctly
kept them as failures rather than silently stripping fences.

Independent exhaustive AI review of all 200 raw responses:

| Category | Count |
|---|---:|
| Contains at least one genuinely pin-able scoring premise | 171 |
| Unusable/restatement/generic/tooling/label-only | 29 |

By original template:

| Template | Pin-able / 40 | Strict parsed / 40 |
|---|---:|---:|
| `inventory-v1` | 36 | 33 |
| `boundary-v1` | 36 | 30 |
| `counterfactual-v1` | 35 | 29 |
| `rubric-v1` | 33 | 32 |
| `minimal-v1` | 31 | 26 |

## Focused JSON-Compliance Refinement

`premise-disclosure-inventory-v2` uses a new ID and adds only response-format
constraints: first character `{`, last character `}`, no Markdown/code fences.
It does not constrain premise content.

| Result | Count |
|---|---:|
| Strict parser `ok` | 39 / 40 |
| Provider error | 1 / 40 |
| Pin-able among parsed | 38 / 39 |

The sole provider failure was a transient HTTP 500/no-choices response. Among
provider-returned responses, JSON compliance was 39/39. Mean premise count
remained approximately three, so the formatting refinement did not collapse
the substantive output.

## Decision

Select `premise-disclosure-inventory-v2` for preregistration.

Rationale:

1. highest original-template substantive yield;
2. focused refinement eliminates the observed fence failure;
3. 38/39 parsed focused outputs contain a usable premise;
4. no static prompt option-label leakage was detected offline;
5. every raw response remains available for owner review.

The required 30-item/task out-of-panel leakage audit subsequently passed 90/90;
see `docs/experiments/wp4-leakage-audit.md`.

## Caveats

- Review was performed by the Manager plus independent AI reviewers, not by the
  human owner line-by-line.
- Some model outputs themselves mention likely rating labels. This is not static
  prompt leakage, but later pinned prompts must treat surfaced values as
  untrusted model text and preserve them verbatim for audit.
- The prompt is exploratory until the preregistration freeze commit/tag.
