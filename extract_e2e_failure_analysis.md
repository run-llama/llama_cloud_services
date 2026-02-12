# Extract E2E Failure & Confidence Score Analysis

## Summary

The E2E test failures and the confidence scores issue reported by adtalem are both caused by
**a backend/staging parsing regression**, not an SDK code bug. The document parsing step in
PREMIUM extraction mode is producing severely degraded results on the staging environment.

## Evidence

### 1. Parsing produces abnormally low token counts

When extraction succeeds (doesn't timeout), the response shows:
```
num_document_tokens: 12
num_output_tokens: 9
```
For the Noisebridge receipt PDF, which should yield hundreds of tokens. This means the parsing
step is extracting almost no text from the document.

### 2. Incomplete extraction data

Because only 12 tokens are parsed, the LLM can only produce:
```json
{"title": "Receipt"}
```
instead of the expected `{"title": "...", "summary": "..."}`.

### 3. Empty field_metadata (no confidence scores)

The response returns `field_metadata: {}` — completely empty. No confidence scores are
generated because the parsing step produced insufficient content for the confidence pipeline.

### 4. Only PREMIUM mode is affected

- FAST, BALANCED, MULTIMODAL modes: **PASS consistently**
- PREMIUM mode (which uses a separate parse step): **FAILS consistently**

In the latest run (Feb 12 04:38), receipt tests for modes 0/1/2 all passed; only mode 3
(PREMIUM with `anthropic-sonnet-4.5` parse model) failed.

### 5. Timeline of failures

| Time (UTC) | Run ID | Result | Notes |
|---|---|---|---|
| Feb 10 22:31 | 21884943986 | SUCCESS | All 27 tests pass |
| Feb 10 23:31 | 21886493352 | FAILURE | `test_extract_single_file` timeout |
| Feb 11 00:58 | 21888521253 | FAILURE | Multiple timeouts |
| Feb 11 03:24 | 21891572523 | SUCCESS | Intermittent recovery |
| Feb 11 05:00+ | | FAILURE | Consistent failures |
| Feb 11 15:39 | 21911691852 | SUCCESS | Brief recovery |
| Feb 11 16:39+ | | FAILURE | Consistent failures through Feb 12 |

The failures started consistently around **Feb 10-11 night** and are ongoing.

### 6. No SDK code changes

The last meaningful change to `py/llama_cloud_services/extract/` was commit `dd83c1a`
("Add retries to all extract sdk functions uniformly") from before the failures began.
The `llama-cloud` API client dependency has been stable at `0.1.46`.

## Specific Failure Modes

### Timeout failures (most tests)
Tests `test_extract_single_file`, `test_extract_file_from_buffered_io`, and receipt
e2e tests in PREMIUM mode hang for >300s waiting for the extraction job to complete.
The backend appears to be hanging/stalled during the parse step.

### Assertion failures (`test_extract_file_from_bytes`)
When extraction completes, the LLM returns `{"title": "Receipt"}` without the `summary`
field. The test asserts `"summary" in result.data` which fails.

### Confidence scores not produced
`extraction_metadata.field_metadata` is `{}` even for successful extractions. This directly
explains adtalem's report that confidence scores stopped being produced.

## Root Cause

The **staging backend's PREMIUM mode parsing pipeline** is degraded. When a document is sent
for extraction in PREMIUM mode:
1. The parse step runs but produces only ~12 tokens (vs hundreds expected)
2. The LLM receives insufficient context to fill all schema fields
3. The confidence scoring pipeline has no meaningful data to score
4. Some parse jobs hang entirely, causing timeouts

## Recommendations

1. **Backend investigation needed**: The staging PREMIUM mode parsing service needs to be
   investigated. Something changed around Feb 10-11 that degraded the `anthropic-haiku-4.5`
   and `anthropic-sonnet-4.5` parse models.

2. **Check production**: adtalem's confidence score issue suggests this may also affect
   production. Verify the parse token counts in production PREMIUM mode extractions.

3. **SDK test improvement**: The `test_extract_api.py` tests create agents with
   `ExtractConfig(invalidate_cache=True)` without specifying `extraction_mode`. The server
   defaults to PREMIUM. Consider explicitly setting `extraction_mode=ExtractMode.MULTIMODAL`
   in test configs to avoid depending on the server's default extraction mode.
