# Testing Utils Implementation Plan

## Goal
Build a `FakeLlamaCloudServer` that intercepts all SDK HTTP traffic (extract, parse, classify, files, etc.) and returns deterministic responses so offline tests behave like production, per `testing_utils_spec.md`.

## High-Level Phases
1. **Router + lifecycle scaffold**
   - Implement `FakeLlamaCloudServer` with `respx.Router` that can be used as a context manager or via explicit `install()` / `uninstall()`.
   - Support multiple base URLs and namespace filtering so only selected APIs are intercepted.
2. **State stores + deterministic generators**
   - Create in-memory stores for files, jobs, runs, parse results, and classification predictions.
   - Implement deterministic data generation seeded by (file hash, schema hash, namespace) as described in the spec.
3. **Namespace handlers**
   - Extract: stub `/api/v1/extraction/extraction-agents/*`, `/api/v1/extraction/run`, `/api/v1/extraction/jobs*`, `/api/v1/extraction/runs/by-job/{id}`.
   - Files: stub `/api/v1/files/**` plus presigned upload/download workflows.
   - Parse: stub `/api/parsing/upload`, `/api/parsing/job/{id}`, `/api/parsing/job/{id}/result/{result_type}`.
   - Classify: stub `/api/v1/classifier/*` (job creation, polling, results).
4. **Matcher + override system**
   - Implement `RequestMatcher`, `FileMatcher`, `SchemaMatcher`, etc., and expose helper APIs like `fake.extract.stub_run`.
5. **Ergonomic utilities**
   - Provide helper shortcuts (`fake.extract.stateless_run`) and spy APIs (call count assertions).
6. **Docs + tests**
   - Document usage in `testing_utils_spec.md`.
   - Add tests that demonstrate end-to-end flows using the fake.

## Detailed Steps & Considerations

### 1. Router & Lifecycle
- Create a single `FakeLlamaCloudServer` class that holds a `respx.Router` configured for each base URL.
- Provide `__enter__/__exit__` plus `install()/uninstall()` to attach/detach the router.
- Complexity: need to handle both sync and async clients since `LlamaParse` uses raw `httpx.AsyncClient` instances constructed on the fly. Ensure `respx.mock(assert_all_called=False)` works for both.

### 2. State Management & Determinism
- Implement a `FileStore` that tracks uploaded file bytes, metadata, generated IDs, and seeded RNG values.
- Implement `ExtractStore`, `ParseStore`, `ClassifyStore` to track job lifecycles and generated runs.
- Deterministic generator design:
  - Compute SHA256 of (file bytes + filename) and of normalized schema JSON.
  - Combine into a seed (e.g., `seed = sha256(file_hash + schema_hash)`).
  - Use that seed for namespace-specific RNG (extract uses schema walk, parse uses layout heuristics, classify uses label sets).
- Complexity: schema normalization requires Pydantic `model_json_schema()` ordering; ensure we match production ordering to avoid drift.

### 3. Namespace Handlers
#### Extract
- Stub endpoints listed under `LlamaExtract` usage (`create_extraction_agent`, `run_job`, stateless run, poll job/run).
- Mirror response bodies (`ExtractJob`, `ExtractRun`, `PaginatedExtractRunsResponse`) so the SDK’s type deserialization works.
- Manage transitions `PENDING → SUCCESS/FAILED` with realistic timestamps.
#### Files
- Implement both presigned workflow and direct upload fallback:
  - `POST /api/v1/files` (or equivalent) returns a fake presigned URL (e.g., `https://fake-upload.local/{file_id}`) that our router also intercepts.
  - The subsequent `PUT` should store the bytes and mark upload complete.
  - `GET /api/v1/files/{id}` returns stored metadata; `read_file_content` returns presigned download URLs or raw bytes.
- Complexity: need to intercept arbitrary presigned hostnames (e.g., AWS S3). Spec does not clarify if presigned URLs live on the same base; we may need to whitelist custom domains or provide a fake S3 host.
#### Parse
- Because `LlamaParse` manually constructs `/api/parsing/*` URLs, ensure the fake registers these exact routes against every provided base URL.
- Store job configs, return deterministic `JobResult` payloads (text, markdown, JSON), and support partitioned jobs.
#### Classify
- Stub job creation/polling/responses, ensuring statuses transition according to `StatusEnum`.
- Return deterministically chosen labels based on input payload + rules (seed derived from contents).

### 4. Matcher / Override System
- Provide dataclasses from the spec (`FileMatcher`, `SchemaMatcher`, `RequestMatcher`).
- Implement matcher evaluation order with `once=True` behavior to remove one-time overrides.
- Expose helper APIs:
  - `fake.extract.stub_run(...)`
  - `fake.parse.stub_parse(...)`
  - `fake.classify.stub_prediction(...)`
  - `fake.files.stub_upload(...)`, etc.
- Complexity: Need to ensure matcher evaluation can inspect raw `httpx.Request` bodies/headers for both sync and async flows without consuming the stream twice.

### 5. Assertions & Spies
- Expose convenience attributes pointing to `respx.Route` objects for frequently used paths (e.g., `fake.extract.stateless_run`).
- Provide helper methods for call counts, captured requests, etc.
- Ensure naming stays stable to avoid brittle tests.

### 6. Testing Strategy
- Add pytest fixtures to install the fake server globally for integration tests.
- Cover scenarios:
  - Stateless extract returns deterministic payload.
  - Agent-backed extract polls job/runs.
  - Files API handles presigned upload and retrieval.
  - Parse job lifecycle for both success and failure.
  - Classification job with deterministic label output.
  - Matcher overrides injection & once-only behavior.
  - Mixed namespace configurations (e.g., intercept extract only, let parse hit real network).

## Extra Complexity & Spec Concerns
- **Presigned URL scope**: Spec assumes presigned uploads can be intercepted the same way as SaaS APIs, but actual presigned URLs often point to AWS domains outside `base_urls`. Need a strategy (e.g., generate fake host names the SDK will call, or rewrite responses to use local URLs).
- **Async client coverage**: LlamaParse builds new `httpx.AsyncClient` objects; the spec’s install/uninstall story must ensure respx patches all clients, not just the global one.
- **Deterministic generators**: The spec outlines hashing inputs but doesn’t define exact algorithms. Without mirroring production generator logic, fixtures might diverge. We may need to document any intentional differences.
- **Job state timelines**: The spec expects transitions (`PENDING → SUCCESS`) with realistic timestamps. Need to ensure we schedule async updates or respond with multi-step polling; otherwise, tests relying on delays may behave differently.
- **Namespace toggling**: Clarify behavior when a namespace is disabled—should unmatched routes fall through automatically or raise? Current spec implies fall-through to real network, but that could be surprising in CI.
- **Schema handling**: `_validate_schema` currently calls production for dict schemas. The fake must emulate validation; otherwise tests will still hit SaaS. Spec doesn’t detail validation logic, so we must decide on a simplified validator or deterministic echo.
- **Parse partitioning**: `LlamaParse` can partition jobs and expects consistent pagination semantics. Need to ensure deterministic results respect `target_pages`, `partition_pages`, etc., or document limitations.

## Next Actions
1. Prototype router + lifecycle with namespace toggles.
2. Implement FileStore + presigned workflow since other namespaces depend on file IDs.
3. Build deterministic generators and stores for extract/parse/classify.
4. Layer matcher/override system on top of the stores.
5. Write initial tests per namespace and refine spec gaps (presigned host, validation behavior).
6. Update `testing_utils_spec.md` with any clarifications discovered above.
