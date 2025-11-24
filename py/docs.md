## Local Testing Utilities

The Python package now ships a lightweight fake LlamaCloud server that lets you run
offline tests without touching the real SaaS environment. The utilities live under
`llama_cloud_services.testing_utils` and are powered by [`respx`](https://respx.dev)
so any `httpx` client constructed by the SDK is seamlessly intercepted.

### Quick start

```python
import os
from pathlib import Path
from llama_cloud_services.extract import (
    LlamaExtract,
    ExtractConfig,
    ExtractTarget,
)
from llama_cloud_services.testing_utils import (
    FakeLlamaCloudServer,
    attach_extract_api,
)

schema = {
    "type": "object",
    "properties": {"title": {"type": "string"}, "total": {"type": "number"}},
}
config = ExtractConfig(extraction_target=ExtractTarget.PER_DOC)
pdf_path = Path("tests/fixtures/receipt.pdf")

with FakeLlamaCloudServer(
    base_urls=[os.environ.get("LLAMA_CLOUD_BASE_URL", "")]
) as fake:
    attach_extract_api(
        fake
    )  # registers the extract routes, more namespaces coming soon
    extractor = LlamaExtract(
        api_key="test-key", base_url=fake.primary_base_url, verify=False
    )
    run = extractor.extract(schema, config, pdf_path)
    assert run.status.value == "SUCCESS"
```

Use the same server for stateful agent tests:

```python
from llama_cloud_services.testing_utils import FileMatcher, RequestMatcher

with FakeLlamaCloudServer() as fake:
    extract_api = attach_extract_api(fake)
    extract_api.stub_run(
        matcher=RequestMatcher(file=FileMatcher(filename="noisebridge.pdf")),
        data={"title": "Noisebridge", "total": 42.0},
    )
    extractor = LlamaExtract(
        api_key="test", base_url=fake.primary_base_url, verify=False
    )
    agent = extractor.create_agent("unit-agent", schema)
    run = agent.extract(pdf_path)
    assert run.data["title"] == "Noisebridge"
```

### Reference

- `FakeLlamaCloudServer(base_urls: Iterable[str] | None = None)`
  - Context manager that installs a shared `respx.MockRouter`. The first non-empty
    base URL becomes `primary_base_url` for convenience.
  - Use `register_namespace(name, obj)` to store helpers on the server if needed.
  - `add_handler(method, path_template)` decorator registers HTTP handlers for all
    configured base URLs (e.g., both the SaaS default and a custom LLAMA_CLOUD_BASE_URL).

- `attach_extract_api(server: FakeLlamaCloudServer) -> ExtractTestingApi`
  - Registers the `/api/v1/files`, `/api/v1/extraction/*`, and stateless run routes.
  - Manages in-memory state for files, agents, jobs, and runs so the public SDK surface
    works exactly as it would against production.

- `ExtractTestingApi.stub_run(...)`
  - Allows fine-grained overrides of generated extraction results. Accepts an optional
    `RequestMatcher` plus either a dict payload or a callable that receives a
    `MatcherContext`.
  - You can also override the job/run statuses via the `run_status`/`job_status`
    keyword arguments to simulate failures.

- Matchers (`RequestMatcher`, `FileMatcher`, `SchemaMatcher`)
  - Compose match conditions across file metadata (filename, SHA256, MIME type),
    schema hash, or custom predicates to pin overrides to specific requests.

See `unit_tests/testing_utils/test_fake_extract.py` for more end-to-end examples that
cover deterministic stateless extraction, custom overrides, and agent-based flows.
