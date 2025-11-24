## Local Testing Utilities 2.0 (Spec Draft)

Offline testing should feel identical to calling the public LlamaCloud API. The new utilities center a single `FakeLlamaCloudServer` that intercepts HTTP traffic at the API boundary, deterministically generates responses from real files + schemas, and only requires overrides when a test needs to exercise edge cases.

### Design goals
- **Everything mocked by default**: instantiating `FakeLlamaCloudServer()` wires up every public LlamaCloud namespace (extract, parse, classify, files, etc.) so the SDK behaves as if it were talking to production. Deterministic responses are returned without any additional wiring.
- **Context manager optional**: `FakeLlamaCloudServer` still supports `with ...` for pytest isolation, but you can call `install()` / `uninstall()` to keep the mock server active inside a long-running process (e.g., a FastAPI dev server that proxies to the fake).
- **Pydantic-first ergonomics**: all documentation and helpers assume schemas are declared as `BaseModel` subclasses. JSON Schema dictionaries are still accepted for compatibility.
- **API-only contract**: handlers talk raw HTTP (request dicts, status codes, JSON payloads) so we can reuse the mock in future SDKs or other languages without depending on `LlamaExtract`.

### Quick start (pytest-friendly, deterministic by default)

```python
from pathlib import Path
from pydantic import BaseModel, Field
from llama_cloud import ExtractConfig, ExtractMode
from llama_cloud_services.extract import LlamaExtract
from llama_cloud_services.testing_utils import FakeLlamaCloudServer


class Receipt(BaseModel):
    merchant: str = Field(description="Vendor name")
    total: float = Field(description="Grand total in USD")


config = ExtractConfig(extraction_mode=ExtractMode.FAST)
pdf_path = Path("tests/fixtures/receipt.pdf")


with FakeLlamaCloudServer() as fake:
    extractor = LlamaExtract(
        api_key="test-key",
        verify=False,
    )
    run = extractor.extract(Receipt, config, pdf_path)
    assert run.status.value == "SUCCESS"
    assert run.data["total"] > 0  # generated entirely from file + schema
```

Key points:
- No manual stubbing required. The fake server hashes the uploaded file bytes + schema JSON to derive a deterministic seed and walks the schema to produce stable mock data.
- `FakeLlamaCloudServer` automatically intercepts the default SaaS URL (`https://api.cloud.llamaindex.ai`). If your tests point at another host (e.g., BYOC), pass it via `FakeLlamaCloudServer(base_urls=["https://byoc.dev/api"])`; otherwise, keep using your normal SDK base URL.

### Works across extract, parse, classify

```python
from llama_cloud_services.testing_utils import FakeLlamaCloudServer
from llama_cloud_services.extract import LlamaExtract
from llama_cloud_services.parse import LlamaParse
from llama_cloud_services.classify import LlamaClassify


with FakeLlamaCloudServer() as fake:
    extractor = LlamaExtract(api_key="test-key")
    parser = LlamaParse(api_key="test-key")
    classifier = LlamaClassify(api_key="test-key")

    run = extractor.extract(
        Receipt, config, "noisebridge.pdf"
    )  # reuse quick-start schema/config
    parse_result = parser.parse("noisebridge.pdf")
    classification = classifier.classify({"text": "foo"})

    assert run.status.value == "SUCCESS"
    assert parse_result.documents[0].text  # deterministically generated
    assert classification.prediction in {
        "A",
        "B",
    }  # stable RNG driven by payload
```

Every namespace uses its own deterministic generator (schema-driven for extract, layout-driven for parse, label-driven for classify) but shares the same matcher/override system described below.

### Limiting intercepted APIs

If you only need a subset of APIs (e.g., extract + files during early bring-up), pass `namespaces` explicitly. Anything omitted will fall through to the real network, which is handy for hybrid tests.

```python
fake = FakeLlamaCloudServer(
    namespaces=["extract", "files"],
    base_urls=["https://api.cloud.llamaindex.ai"],  # optionally point at BYOC
)

with fake:
    extractor = LlamaExtract(api_key="test-key")
    extractor.extract(Receipt, config, "noisebridge.pdf")
```

### Long-lived install for iterative development

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

fake = FakeLlamaCloudServer(
    namespaces=["extract"],
    base_urls=[
        os.environ.get(
            "LLAMA_CLOUD_BASE_URL", "https://api.cloud.llamaindex.ai"
        )
    ],
)


@asynccontextmanager
async def lifespan(app):
    fake.install()
    app.state.extractor = LlamaExtract(
        api_key="dev",
        verify=False,
    )
    try:
        yield
    finally:
        fake.uninstall()


app = FastAPI(lifespan=lifespan)
```

`install()`/`uninstall()` simply wrap the respx router lifecycle so you can keep the mock server hot for REPLs, background workers, or manual QA sessions without relying on a context manager.

### Files API behavior

`FakeLlamaCloudServer` ships with a first-class fake for `/api/v1/files/*` because uploads sit on the critical path for both extract and downstream workflows that pre-stage files.

- Every call to `POST /files/generate-presigned-url`, the subsequent `PUT` upload, and the follow-up `GET /files/{file_id}` is intercepted and stored in-memory. The response objects mirror the real API so `FileClient` keeps working unchanged.
- `fake.files.preload(path="tests/fixtures/plan.pdf", filename="plan.pdf")` ingests local fixtures ahead of time and returns a reusable `file_id`, which is useful when tests pass `SourceText(file_id=...)`.
- `fake.files.stub_upload(...)` lets you simulate storage failures (e.g., 413 "file too large") using the same matcher system as extract.
- You can download what the SDK uploaded via `fake.files.read(file_id)` to assert on the bytes or to feed downstream mocks.

```python
from llama_cloud_services.extract import SourceText

with FakeLlamaCloudServer() as fake:
    file_id = fake.files.preload(path="tests/fixtures/noisebridge.pdf")
    extractor = LlamaExtract(api_key="test-key")
    run = extractor.extract(Receipt, config, SourceText(file_id=file_id))
    assert fake.files.read(file_id).startswith(b"%PDF")
```

### Deterministic response generation
1. Files uploaded via `/api/v1/files` (or inlined via `extract_stateless`) are fingerprinted using SHA256 (file content bytes + filename).
2. Schemas are normalized (Pydantic `model_json_schema()` plus sorted keys) and hashed.
3. A seed derived from `sha256(file_fingerprint + schema_digest)` feeds a tiny RNG that walks the schema to synthesize values (numbers, strings, arrays) while respecting field metadata (descriptions hint names, numeric ranges, etc.).
4. Runs transition through the same states as production (`PENDING` → `SUCCESS`) and return realistic timestamps, metadata, and config echoes.

Because the seed is stable, rerunning the same schema/file pair yields identical mock payloads without stubbing.

### Stubbing, spying, and assertions
Most tests only need the deterministic defaults, but the fake server provides a layered set of helpers for overriding responses, asserting call counts, and finally dropping down to raw `respx` when necessary.

#### Matcher API

```python
from dataclasses import dataclass
from typing import Callable, Optional
from httpx import Request


@dataclass
class FileMatcher:
    filename: str | None = None
    sha256: str | None = None
    file_id: str | None = None


@dataclass
class SchemaMatcher:
    model: type[BaseModel] | None = None
    schema_hash: str | None = None


@dataclass
class RequestMatcher:
    file: FileMatcher | Callable[[Request], bool] | None = None
    schema: SchemaMatcher | None = None
    agent_id: str | None = None
    project_id: str | None = None
    organization_id: str | None = None
    predicate: Callable[[Request], bool] | None = None
```

Every callable matcher receives the raw `httpx.Request` object that respx captured, so you can inspect headers, cookies, bodies, etc., without learning another wrapper type. The helper dataclasses (`FileMatcher`, `SchemaMatcher`) just cover the common cases; mix and match as needed. Stubs are evaluated in registration order, and `once=True` removes the stub after the first match.

#### Stateless extraction example

```python
fake.extract.stub_run(
    matcher=RequestMatcher(file=FileMatcher(filename="noisebridge.pdf")),
    data={"merchant": "Noisebridge", "total": 42.0},
    status="SUCCESS",  # defaults to deterministic timeline when omitted
    metadata={"source": "unit-test"},
    once=True,
)

run = extractor.extract(Receipt, config, "noisebridge.pdf")
assert run.data["merchant"] == "Noisebridge"
```

`data` accepts dictionaries, Pydantic models, or callables (`Callable[[Request], dict]`). If you omit `status`, the stub only replaces the payload while preserving the deterministic job/run lifecycle.

#### Agent extraction example

```python
agent = extractor.create_agent(
    name="tests", data_schema=Receipt, config=config
)

fake.extract.stub_agent_run(
    agent_id=agent.id,
    matcher=RequestMatcher(file=FileMatcher(filename="bad.pdf")),
    job_status="FAILED",  # overrides POST /extraction/jobs
    run_status="FAILED",  # overrides GET /runs/by-job
    error={"message": "Schema mismatch"},
)

with pytest.raises(ApiError):
    agent.extract("bad.pdf")
```

`stub_agent_run` targets the stateful job pipeline (`/extraction/jobs`, `/extraction/jobs/{id}`, `/extraction/runs/by-job/{id}`) so you can mimic long-running failures, retries, or partial completions without hand-writing multiple HTTP handlers.

#### Parse, classify, and files stubs

- `fake.parse.stub_parse(...)` lets you override document splits, token counts, or even return structured HTML for specific file IDs.
- `fake.classify.stub_prediction(...)` accepts label sets and score distributions so you can test downstream logic that inspects confidences.
- `fake.files.stub_upload(...)` / `fake.files.stub_download(...)` simulate storage edge cases such as timeouts or corrupted content.

Because every namespace uses the same matcher primitives, you can coordinate multi-API scenarios (e.g., stub the file upload and the subsequent extract run) without duplicating predicates.

#### Assertions without extra abstractions

Since everything runs through the same `respx.MockRouter` you already use elsewhere, assertions stay lightweight:

```python
with FakeLlamaCloudServer() as fake:
    route = fake.router["POST", "/api/v1/extraction/run"]
    extractor = LlamaExtract(api_key="test-key")
    extractor.extract(Receipt, config, "noisebridge.pdf")

assert route.called
assert route.call_count == 1
req = route.calls[0].request  # this is httpx.Request
assert req.headers["authorization"].startswith("Bearer ")
```

For friendlier names, every frequently used route is also pinned to a stable attribute:

- `fake.extract.stateless_run` (alias: `fake.extract_run`) → `POST /api/v1/extraction/run`
- `fake.extract.agent_job` → `POST /api/v1/extraction/jobs`
- `fake.extract.agent_run` → `GET /api/v1/extraction/runs/by-job/{job_id}`
- `fake.files.upload` → `POST /api/v1/files/upload` (or the presigned PUT hop, depending on mode)
- `fake.files.get` → `GET /api/v1/files/{file_id}`

Each attribute is the underlying `respx.Route`, so assertions feel natural:

```python
assert fake.extract.stateless_run.called
fake.extract.stateless_run.assert_called_once()
assert fake.files.upload.call_count == 1
assert fake.extract_run.called  # global alias for the same route
```

If you ever need the full mapping, `fake.extract.routes["stateless_run"] is fake.extract.stateless_run`.

#### Advanced (respx-level) overrides

When you need total control, drop straight into respx:

```python
route = fake.router["POST", "/api/v1/extraction/run"]
route.mock(side_effect=lambda request: (418, {"detail": "I'm a teapot"}))
```

Or use the attribute shortcuts:

```python
fake.extract.stateless_run.mock(
    side_effect=lambda request: (500, {"detail": "boom"})
)
```

Either way you're dealing with the canonical respx objects, so regex paths, call assertions, and other ecosystem tools keep working. The only convention is that handlers should return `(status_code, json_body | bytes)` so logging and deterministic fallbacks remain consistent.

### API-layer implementation hints
- Route decorators such as `server.add_handler("POST", "/api/v1/extraction/run")` install handlers for **every** registered base URL declared in the constructor, keeping the mock independent of SDK client classes.
- Request objects passed to handlers expose method, URL, headers, query params, JSON body, and raw bytes—everything needed to mirror production without importing internal models.
- Namespaces self-register via the constructor (e.g., `namespaces=["extract"]`) so no additional attach helpers are required; future SDKs can opt into the same HTTP contracts by toggling the namespaces they care about.

## Research: Extract SDK surface map

The current Python SDK (`py/llama_cloud_services/extract/extract.py`) is a thin wrapper over the HTTP API exposed in `ts/llama_cloud_services/openapi.json`. Understanding this mapping helps ensure the fake server mirrors the real contract.

### Core classes
- `LlamaExtract`: factory that owns an `AsyncLlamaCloud` client, manages thread pools, and exposes both stateless extraction (`extract`, `aextract`, `queue_extraction`) and agent CRUD helpers.
- `ExtractionAgent`: wraps an existing agent returned by the API and provides methods for queuing files, polling jobs, listing runs, updating schemas/configs, and deleting runs.
- `FileClient`: abstracts the `/api/v1/files` upload + download flow, including presigned URL handling for uploads.

### Stateless extraction flow
1. `LlamaExtract.queue_extraction(data_schema, config, files)` validates schemas via `POST /api/v1/extraction/extraction-agents/schema/validation`, converts input files into either `file_id`, `file` (base64 body), or inline `text`.
2. For each file the SDK calls `POST /api/v1/extraction/run` with the processed schema + config + file payload. The API responds with an `ExtractJob`.
3. `LlamaExtract.aextract` waits for completion by polling `_wait_for_job_result`, which hits `GET /api/v1/extraction/jobs/{job_id}` until the job is `SUCCESS`/`FAILED`, then fetches the run via `GET /api/v1/extraction/runs/by-job/{job_id}`. The synchronous `extract` just wraps this coroutine in a worker thread.

### Agent-backed flow
1. `create_agent` issues `POST /api/v1/extraction/extraction-agents` with name, schema, and config; responses seed `ExtractionAgent`.
2. `ExtractionAgent.queue_extraction` uploads files via `FileClient`, then enqueues jobs with `POST /api/v1/extraction/jobs` (or `/jobs/file` for multipart uploads). Returned job IDs are polled via `_wait_for_job_result` just like the stateless path.
3. `ExtractionAgent.list_extraction_runs` and `delete_extraction_run` map to `GET /api/v1/extraction/runs` (with pagination) and `DELETE /api/v1/extraction/runs/{run_id}` respectively.
4. Manual inspection helpers (`get_extraction_job`, `get_extraction_run_for_job`, `get_extraction_run`) call `GET /api/v1/extraction/jobs/{job_id}` and `GET /api/v1/extraction/runs/by-job/{job_id}` / `GET /api/v1/extraction/runs/{run_id}`.

### Files API touch points
- Uploads default to presigned URLs: the SDK first calls `POST /api/v1/files/generate-presigned-url`, then performs an HTTP PUT to the returned URL, and finally fetches the file metadata via `GET /api/v1/files/{file_id}`.
- When BYOC deployments disable presigned uploads, `FileClient` falls back to `POST /api/v1/files/upload`.

### Implications for the fake server
- **API-level parity**: mocking should happen at the HTTP layer (matching the endpoints listed above) so new SDKs can reuse the fake by simply pointing their base URL at it.
- **State surfaces**: to emulate production, the fake needs in-memory stores for files, jobs, and runs keyed by UUIDs, plus schema validation stubs that mimic the `/schema/validation` endpoint.
- **Deterministic generators**: since `ExtractRun.data` is derived from schema + file, implementing the generator once at the API layer ensures consistency across SDKs.
- **Error simulation hooks**: overrides should let us short-circuit any endpoint (jobs, runs, schema validation) without changing SDK code, mirroring how the real API might fail.

This map should serve as the checklist when we implement the mock: if an SDK method calls a certain path, our fake server must expose the same path with compatible request/response bodies so we can eventually lift these utilities into a standalone package.

## Implementation status

- `FakeLlamaCloudServer` now lives in `llama_cloud_services.testing_utils` and registers the files, extract, parse, and classify namespaces by default. It can be used as `with FakeLlamaCloudServer(): ...` or by calling `install()` / `uninstall()` explicitly.
- Deterministic payloads derive from file fingerprints plus schema hashes for extraction, seeded layout information for parse, and rule/file hashes for classification. The helper exposes matcher-driven overrides (`stub_run`, `stub_agent_run`, `files.stub_upload`) so tests can simulate errors.
- Common `respx.Route` handles are exposed via namespaces (`fake.extract.stateless_run`, `fake.extract.agent_job`, `fake.files.routes["upload"]`, etc.) for assertions that mirror the examples in this spec.
- End-to-end usage is covered in `py/unit_tests/testing_utils/test_fake_server.py`, which exercises stateless extraction, agent-backed uploads, and LlamaParse readers entirely against the fake server without external network calls.
