# test_utils_rfc_scratchpad

Quick, informal notes gathered while surveying the Python SDK to plan the fake LlamaCloud services.

## Extract-first plan
- Feedback: ship extract-only faker first, but design the plumbing so parse/classify/index can plug in later without rewriting the server.
- `FakeLlamaCloudServer` must intercept **both** the default SaaS URL (`https://api.cloud.llamaindex.ai`) and any user-provided `LLAMA_CLOUD_BASE_URL`. Plan: accept `base_urls` list, always union with default, register every route for every alias.
- No dependencies on SDK classes—handlers talk HTTP only and return JSON dicts that match the public API. That keeps the faker compatible with future auto-generated clients.

## Extract service observations (still relevant)
- `py/llama_cloud_services/extract/extract.py` wraps the generated `llama_cloud.AsyncLlamaCloud` client. Calls of interest:
  - Agent lifecycle: `create_extraction_agent`, `get_extraction_agent`, `list_extraction_agents`, `delete_extraction_agent`, `update_extraction_agent`.
  - Job lifecycle: `run_job`, `extract_stateless`, `get_job`, `get_run_by_job_id`, `list_extract_runs`, `delete_extraction_run`.
  - Schema validation: `_validate_schema` calls `validate_extraction_schema`.
- `ExtractionAgent.queue_extraction` first uploads files via `FileClient.upload_content`, then invokes `run_job` for each file.
- Stateless paths go through `_convert_file_to_file_data` and call `extract_stateless` with either `{file: FileData}`, `{file_id}`, or `{text}`.

## File upload flow
- `py/llama_cloud_services/files/client.py` is the higher-level uploader used by extraction:
  1. Calls `POST /api/v1/files` or (default) `PUT /api/v1/files` to fetch a presigned URL.
  2. Performs an additional `PUT` to the returned URL (currently S3) using the same shared `httpx.AsyncClient`.
  3. Fetches `GET /api/v1/files/{file_id}` to materialize the `File` object.
- Fake server must short-circuit the presigned URL step; easiest approach is to return a presigned URL that also points back to the fake base URL so `respx` can intercept the subsequent `PUT`.

## Why respx fits
- Project already depends on `respx[tests]>=0.22.0` (see `py/pyproject.toml`), but there is no existing usage.
- `respx.MockRouter` can globally patch `httpx.AsyncClient` instances, so we can avoid modifying service constructors: tests will set `base_url` to the fake server and enter the router context.

## Constraints & opportunities
- Fake extraction responses must be deterministic: requirement is to inspect submitted JSON schema, derive a hash (probably combine schema + file fingerprint + request body), seed `random.Random`, and synthesize data shaped exactly like the schema.
- Tests also want explicit overrides: “for this file, return this response.” Need matcher objects (maybe dataclasses) that look at filename, mime type, schema hash, etc., before falling back to auto-generated data.
- Will need to expose fixtures/helpers so pytest suites can do:
  ```python
  @pytest.fixture
  def fake_extract():
      with FakeLlamaExtractService() as fake:
          fake.stub_file("noisebridge_receipt.pdf", response={...})
          yield fake
  ```

## Open questions to revisit
- What is the minimum subset of extraction endpoints we must emulate so that agent creation + job polling works entirely offline? (Probably the set enumerated above, but double-check once implementation starts.)
- Do we need to hook `check_for_updates` (Parse uses it on first call) to avoid unexpected outbound calls, or can we leave it?
- Should fake services live under `src/testing_utils/llama_cloud/` or `py/src/...` so both python package builds and tests can import them cleanly?
- How should we serialize generated runs/jobs so they match the shapes of `llama_cloud` pydantic models without importing private internals? (Maybe leverage the public DTOs from `llama_cloud` directly.)
- Need a pattern for globally registered matchers so future namespaces (parse/index/etc.) can share overrides without duplicating logic.
