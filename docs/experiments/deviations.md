# Deviations Log

Record a deviation before changing any locked proposal value. Each entry must include the date, affected lock, reason, alternatives considered, expected analysis impact, approval, and the commit or issue that implements it.

## 2026-08-07: Proceed after exhaustive AI review before owner line review

- **Affected gate:** WP4 requires human reading of all prompt-pilot outputs
  before selecting the final premise-disclosure wording.
- **Decision:** The Manager performed automated review and commissioned two
  independent exhaustive AI reviews of all pilot outputs. The owner’s overnight
  GO explicitly authorized progression to smoke/full work if the pilot was
  positive. Owner line-by-line review is deferred, not claimed complete.
- **Reason:** Avoid an overnight idle stop while preserving every raw response
  and a complete review packet for later owner inspection.
- **Alternatives considered:** stop after pilot until the owner wakes; proceed
  without recording the review limitation; treat parse success alone as the
  gate. The first wastes the authorized window; the latter two are rejected as
  methodologically dishonest.
- **Evidence:** Original pilot: 171/200 outputs independently judged to contain
  at least one pin-able premise; focused `inventory-v2`: 38/39 parsed outputs
  judged pin-able, with one transient provider error.
- **Expected impact:** Prompt selection may still change after owner review. No
  confirmatory result may conceal that change; a post-freeze wording change
  requires a new deviation and invalidates cached prompt identities.
- **Approval:** User input on 2026-08-07: “整包批准。甚至如果pilot有积极效果你可以smoke/full run/ghc-api选多个模型 GO”.
- **Implementation:** selected template
  `premise-disclosure-inventory-v2`; raw artifacts remain under
  `artifacts/wp4-pilot-*`.

## 2026-08-07: Exact service slugs without dated deployment IDs

- **Affected lock:** Model identities must be immutable snapshots rather than
  aliases that can drift.
- **Decision:** Use exact `ghc-api` service IDs
  `gemini-3.1-pro-preview` and `gemini-3.5-flash` because no date-qualified
  Google deployment IDs are exposed by the approved local service. Freeze the
  `/models` roster hash, exact slugs, and call timestamps. Record
  `system_fingerprint` when available and stop if a non-null value changes
  within a run.
- **Reason:** Two-vendor/two-tier coverage cannot be achieved from the currently
  callable service using only date-qualified IDs. Anthropic IDs are listed but
  return “requested model is not supported.”
- **Alternatives considered:** use only dated OpenAI models, violating the
  two-vendor design; use unsupported Anthropic IDs; stop all work pending a
  different service.
- **Expected impact:** The service currently returns
  `system_fingerprint=null`, so exact numeric reproduction may be weaker for the
  Google arms. The roster hash does not prove weight immutability. Claims remain
  limited to call-time service snapshots and directionality.
- **Approval:** The owner explicitly authorized `ghc-api` model selection and
  smoke/full progression in the overnight GO.
- **Implementation:** `configs/runs/confirmatory-v1.json`,
  `docs/research/model-snapshots.md`, and per-call `system_fingerprint`.

## 2026-08-07: Preregistration amendment after failed smoke

- **Affected lock:** Generation max-completion budgets and F/S/pin/placebo/full-
  grid prompt template IDs.
- **Observed failure:** Frozen v1 smoke parse success was 62.7%. All 1,094
  malformed responses came from `gemini-3.5-flash`; raw text showed empty or
  truncated JSON under 64/128/2048 completion budgets. Full run did not start.
- **Decision:** Increase budgets to 1024 for forced/response-set/pinned/placebo
  calls and 8192 for disclosure. Add explicit no-fence/first-and-last-character
  JSON instructions under new v2 template IDs.
- **Alternatives considered:** loosen the parser to strip fences; drop Gemini;
  impute failures; continue despite the smoke gate. All are rejected.
- **Expected impact:** Lower truncation/format failure. Prompt semantics and
  research constructs are unchanged.
- **Approval:** Owner's GO authorized repair and rerun after smoke failures.
- **Implementation:** preregistration amendment tag `pprs-prereg-v2`; v1 tag and
  raw failures remain immutable.

## 2026-08-07: Seed collision resolution amendment

- **Affected lock:** Deterministic call and option-permutation seed derivation.
- **Observed failure:** The v2 full plan found a 31-bit SHA-derived seed
  collision before any provider call and stopped.
- **Decision:** Preserve the original seed for all non-colliding coordinates;
  on collision, append a deterministic integer nonce and rehash until unique.
- **Expected impact:** Only colliding full-run coordinates change seed. The
  passed v2 smoke had no collision and remains valid.
- **Approval:** Covered by the owner's overnight GO to repair gates and proceed.
- **Implementation:** `pprs-prereg-v3`; accepted smoke remains bound to v2 Git
  SHA `280a6f46e4d3a66ca38e2747abfa7524642a5f4c`.