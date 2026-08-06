# WP4 Leakage Audit

**Date:** 2026-08-07
**Template:** `premise-disclosure-inventory-v2`
**Auditor:** `mai-code-1-flash-picker` (Microsoft family; outside measured panel)

## Design

- 30 committed sample-manifest items per task;
- 90 total;
- auditor receives static disclosure prompt and source item in explicitly
  separated sections;
- every decision must quote a static-prompt phrase and a source-item phrase (or
  explicitly state no label-like source phrase);
- no measured judge output is shown to the auditor.

## Iterations

Earlier audit attempts are retained:

- v1: completion budget too small;
- v2: valid but rationale evidence too generic;
- v3: auditor instructions themselves listed forbidden labels, causing one
  self-induced false positive;
- v4: exact substring validation failed on line wrapping;
- v5: normalized evidence matching, no injected option list, five deterministic
  retries.

## Final Result

| Task | Valid | Leakage false | Leakage true |
|---|---:|---:|---:|
| ChaosNLI-SNLI | 30 | 30 | 0 |
| ChaosNLI-MNLI | 30 | 30 | 0 |
| SummEval-Relevance | 30 | 30 | 0 |
| **Total** | **90** | **90** | **0** |

Independent AI reconstruction confirmed:

- 90/90 static evidence phrases occur in the static prompt;
- 90/90 source evidence fields are valid source quotes or valid no-label
  statements;
- all 90 no-leakage conclusions are substantively supported.

## Caveat

59 rationales use a generic checklist rather than item-specific prose. This does
not invalidate the static-prompt leakage conclusion because the static prompt is
shared within task and the evidence fields are independently checked, but it
limits what the rationale text itself demonstrates.

Raw results and all failed earlier audit versions remain under
`artifacts/wp4-leakage-audit-*`.
