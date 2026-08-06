# WP3 Specification: Provider, Parser, and Cache

## Objective

Implement the offline-testable collection infrastructure required by the
proposal:

- an asynchronous provider interface with LiteLLM and deterministic mock
  implementations;
- strict structured parsers for forced choice, response sets, and premise
  disclosure;
- a cache key over every proposal-locked call identity field;
- an idempotent Parquet record cache;
- collection orchestration that always preserves raw text and explicit failure
  metadata.

No real provider call is part of WP3 validation.

## Non-goals

- Do not select or call judge models.
- Do not connect to `ghc-api` yet.
- Do not finalize prompt wording.
- Do not sample datasets or start smoke/full experiments.
- Do not compute entropy, PPRS, beta, or figures.
- Do not retry malformed outputs as if they were successful.
- Do not impute any parsed value after a failure.

## Interfaces

### Call identity

The cache key is the SHA-256 hash of canonical JSON containing exactly:

- rendered prompt;
- model snapshot;
- temperature;
- `top_p`;
- seed;
- response format.

Changing any one field must change the key. Non-identity metadata such as
wall-clock time, retry count, and token usage must not change the key.

### Provider contract

An async provider receives a complete immutable request and returns:

- raw response text;
- HTTP status when available;
- prompt/completion token counts when available;
- provider retry count.

Provider timeouts and provider errors are surfaced as typed exceptions and
converted by the collector into explicit raw records.

### Parser contract

The parser accepts raw text and one expected response format:

| Format | Required JSON payload |
|---|---|
| forced choice | `{"choice": "A"}` |
| response set | `{"choices": ["A", "B"]}` |
| premise disclosure | `{"premises": [...]}` |

The caller supplies the valid option tokens for the task. Parsers reject:

- invalid JSON;
- missing required fields;
- unknown or duplicate option tokens;
- extra payload fields;
- empty response sets;
- premise lists with blank/duplicate candidate values.

Parsing returns an explicit status and nullable parsed payload. It never returns
a default choice.

### Parquet cache contract

The cache stores one immutable raw-result record per `cache_key` under an
ignored cache directory. Writes use a temporary Parquet file and atomic replace
under a per-key async lock.

- first write creates the record;
- repeated identical writes are no-ops;
- a different record with the same key raises an identity-collision error;
- reads return the exact validated raw record;
- partial temporary files are never treated as cache hits.

### Collector contract

The collector:

1. computes the call identity;
2. returns a validated cache hit when present;
3. otherwise invokes the provider once;
4. parses the raw response;
5. writes one validated `RawResult` immediately;
6. converts typed timeout/provider failures into records with null parsed
   fields.

## Data and License Constraints

- Provider outputs and Parquet files remain outside Git.
- Raw text is preserved for every success and failure.
- No upstream implementation is copied.
- The local A/B/C/D repositories may be consulted later, but WP3 code is an
  independent implementation of the proposal contract.
- Real credentials and local service endpoints are not stored in source or
  manifests.

## Acceptance Criteria

- [ ] Cache key mutation tests cover all six identity fields.
- [ ] Repeating an identical collection produces a cache hit and no second
  provider invocation.
- [ ] Different payloads cannot occupy the same cache key.
- [ ] Malformed JSON, missing fields, timeout, and provider errors produce
  non-`ok` records with every parsed field null.
- [ ] Raw text is retained for parser failures.
- [ ] Forced choice, response set, and premise disclosure success records obey
  the WP2 stage/path schema.
- [ ] Concurrent identical requests converge to one cached record.
- [ ] All tests use the mock provider and temporary directories.

## Test and Audit Evidence

Required hostile probes:

- mutate each cache identity field independently;
- force duplicate/unknown response-set tokens;
- force an `ok` result with absent payload;
- race two identical requests;
- reuse a key with different raw content;
- leave a temporary file beside a valid cache path;
- verify provider exceptions cannot become success-shaped records.

## Deviations

None. The provider implementation is present but remains unused until later
model-call gates are approved.
