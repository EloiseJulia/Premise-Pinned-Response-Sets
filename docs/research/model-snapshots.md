# Model Snapshot Evidence

**Retrieved:** 2026-08-07 (+08:00)

## Service

- Local OpenAI-compatible `ghc-api`;
- endpoint used for metadata and compatibility probes:
  `http://127.0.0.1:8313/v1`;
- endpoint is runtime configuration and is not stored in experiment manifests;
- no API credential is committed or logged.

## Pilot Models

| Service model ID | Family/tier role | Probe |
|---|---|---|
| `gpt-5.4` | OpenAI, stronger/reasoning-tier pilot model | JSON completion succeeded at temperature 0 and 0.7 |
| `gemini-3.5-flash` | Google, weaker/fast-tier pilot model | JSON completion succeeded at temperature 0 and 0.7 |

Anthropic IDs were present in `/models` but returned “requested model is not
supported” on both observed local endpoints. They are excluded rather than
silently replaced.

## Full-Study Candidates

| Service model ID | Vendor | Capability role | Temperature 0.7 JSON probe |
|---|---|---|---|
| `gpt-5.4` | OpenAI | stronger/reasoning | pass |
| `gpt-4o-mini-2024-07-18` | OpenAI | weaker, dated snapshot | pass |
| `gemini-3.1-pro-preview` | Google | stronger | pass |
| `gemini-3.5-flash` | Google | weaker | pass |

## Caveat

The two Google IDs are exact service identifiers but do not contain date
suffixes. The preregistration must record the retrieval date, endpoint
implementation, exact IDs, and conclusion-scope caveat. If the service later
exposes immutable deployment IDs, those should replace the preview/stable slugs
before the confirmatory full run; otherwise the study may claim only
snapshot-at-call-time directionality, as required by the proposal’s model-drift
boundary.

The local service returned `system_fingerprint=null` in compatibility probes.
The canonical sorted `/models` metadata observed on 2026-08-07 has SHA-256:

`0f17e867c0fd3d36c30232982bd4e43a30d31bbb1dd65d64d72ad38839513ac0`.

This roster hash detects service-list changes but does not prove model-weight
immutability.
