# Testing Utilities RFC (rev 2)

Goal: land a **single, unified fake HTTP server** (powered by `respx`) that mimics the public LlamaCloud REST API so Python tests can run offline while keeping the surface identical to production. Phase 1 concentrates on the **extract** routes, but the infrastructure must scale to every namespace (parse, classify, index, agent data, files, etc.).

## Key adjustments from feedback
- **Unified faker**: one `FakeLlamaCloudServer` that owns routing/state for every namespace; service-specific helpers only layer on syntactic sugar.
- **Base URL interception**: the server automatically intercepts both the default SaaS URL (`https://api.cloud.llamaindex.ai`) and whatever users pass via `LLAMA_CLOUD_BASE_URL` (or explicit kwargs). We register handlers for each alias so existing SDK code needs zero modifications.
- **Extract-only scope for first cut**: implementation order flips—deliver extract endpoints first (agents, jobs, runs, files), then grow into parse/classify/index.
- **Pure HTTP contract**: handlers must not depend on current client classes (`LlamaExtract`, `AsyncLlamaCloud`, etc.). The faker responds with raw JSON/payloads that mirror the public API so future SDK rewrites can still lean on it.
- **Handler sketches**: include concrete `respx` examples that show how requests are parsed and responses minted.

## High-level layout
```
src/testing_utils/
  __init__.py
  llama_cloud/
    __init__.py
    server.py          # FakeLlamaCloudServer + shared state
    extract.py         # Extract-specific helpers + data generation
    matchers.py        # Reusable request matcher definitions
```

### FakeLlamaCloudServer responsibilities
- Manage one `respx.MockRouter` configured with multiple base URLs:
  ```python
  DEFAULT_SAAS_URL = "https://api.cloud.llamaindex.ai"


  class FakeLlamaCloudServer:
      def __init__(self, base_urls: Iterable[str] | None = None):
          self.base_urls = {DEFAULT_SAAS_URL, *(base_urls or [])}
          self.router = respx.MockRouter(assert_all_called=False)

      def __enter__(self):
          self._register_common_routes()
          self.router.__enter__()
          return self

      def add_handler(self, method: str, path_template: str, handler: Handler):
          for base in self.base_urls:
              self.router.route(method, f"{base}{path_template}").mock(
                  side_effect=self._wrap(handler)
              )
  ```
- Maintain shared in-memory state (files, agents, jobs, runs, future namespaces) keyed by resource IDs.
- Expose a simple decorator API so phase-1 extract handlers can register themselves without caring about routing internals.
- Provide convenience utilities: ID generation, seeded RNG helpers, JSON serialization helpers, request parsing (query params, JSON body, form-data).

### Respx handler sketch
```python
@dataclass
class FakeRequest:
    method: str
    url: httpx.URL
    headers: dict[str, str]
    query: dict[str, str]
    json: dict[str, Any] | None
    body: bytes


def register_extract_routes(server: FakeLlamaCloudServer, state: ExtractState):
    @server.add_handler("POST", "/api/v1/extraction/extraction-agents")
    def create_agent(req: FakeRequest):
        payload = req.json or {}
        agent_id = state.next_id("agent")
        agent = {
            "id": agent_id,
            "name": payload["name"],
            "data_schema": payload["data_schema"],
            "config": payload.get("config", DEFAULT_CONFIG),
            "project_id": payload.get("project_id"),
        }
        state.agents[agent_id] = agent
        return 201, agent

    @server.add_handler("POST", "/api/v1/extraction/run")
    def run_stateless(req: FakeRequest):
        schema = payload["data_schema"]
        file_ref = _hydrate_file(state, payload)
        run = generate_run(schema=schema, file=file_ref)
        state.runs[run["id"]] = run
        job = state.create_job(run_id=run["id"])
        return 202, {"id": job.id, "status": "PENDING"}
```
The handler returns a `(status_code, obj_or_bytes)` tuple; `FakeLlamaCloudServer` converts it into an `httpx.Response` automatically.

### Request matcher / overrides
- Provide a unified matcher system so callers can override any response, regardless of namespace.
- Example:
  ```python
  matcher = RequestMatcher(
      file=FileMatcher(filename="noisebridge_receipt.pdf"),
      schema=SchemaMatcher(hash="deadbeef"),
  )
  server.stub(
      method="POST",
      path="/api/v1/extraction/run",
      matcher=matcher,
      response=lambda req: (200, custom_payload),
  )
  ```
- If no matcher fires, the default handler (which mirrors production behavior) executes.

### Deterministic extract data generation
- Seed derivation: `seed = sha256(json.dumps(sorted_schema) + file_fingerprint)`.
- Use `random.Random(int(seed[:16], 16))` to walk the schema and build `ExtractRun.data`.
- Include metadata fields (run IDs, timestamps, status transitions) matching the actual API.

### Usage example
```python
from testing_utils.llama_cloud.server import FakeLlamaCloudServer
from testing_utils.llama_cloud.extract import attach_extract_api, FileMatcher


def test_stateless_extract(tmp_path):
    pdf_path = tmp_path / "noisebridge_receipt.pdf"
    pdf_path.write_bytes(b"fake pdf")

    with FakeLlamaCloudServer(
        base_urls=[os.getenv("LLAMA_CLOUD_BASE_URL", "")]
    ) as fake:
        extract_api = attach_extract_api(fake)
        extract_api.stub_run(
            matcher=FileMatcher(filename="noisebridge_receipt.pdf"),
            data={"title": "Noisebridge", "summary": "Receipt"},
        )

        extractor = LlamaExtract(
            api_key="test-key", base_url=fake.primary_base_url
        )
        run = extractor.extract(schema, config, pdf_path)
        assert run.data["title"] == "Noisebridge"
```
`FakeLlamaCloudServer` intercepts both the default SaaS URL and the custom URL derived from `LLAMA_CLOUD_BASE_URL`, so tests only need to swap the base URL argument (or env var) to point at the faker.

## Implementation sequence
1. **Server core**: build `FakeLlamaCloudServer`, request/response adapters, state stores, matcher plumbing, and base URL alias handling.
2. **Extract namespace (phase 1)**:
   - Files: presigned URL generation + upload endpoint that stores bytes and metadata.
   - Agents: CRUD endpoints + schema validation stub that simply echoes or validates JSON shape.
   - Jobs/runs: stateless run endpoint, agent job queue endpoint, job polling, run fetching, pagination, deletion.
   - Deterministic data generator + override API.
3. **Tests & docs**: add fixtures for extract tests, document usage, ensure no dependency on existing SDK classes other than passing `base_url`.
4. **Future phases**: incrementally register parse, classify, index, agent data, etc., reusing the same server + matcher backbone.

## Future-ready hooks
- The server keeps a registry per namespace (`server.namespaces["parse"] = {...}`) so adding a new API is just registering routes and shape-specific generators.
- Since everything sits on raw HTTP, future codegen-based SDKs can reuse the same fake server by simply pointing their clients to its base URL.
