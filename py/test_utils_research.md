# Testing Utils Research

## Objective

The `FakeLlamaCloudServer` proposal aims to intercept raw HTTP traffic for extract, parse, classify, and files APIs so local tests behave like SaaS without per-test stubbing. The mock must respect base URLs, support context-manager or long-lived install modes, and deterministically synthesize payloads from file + schema hashes while still allowing targeted overrides.

```1:67:py/testing_utils_spec.md
## Local Testing Utilities 2.0 (Spec Draft)

- **Everything mocked by default** …
- **Context manager optional** …
- **Pydantic-first ergonomics** …
- **API-only contract** …
```

## Python Hand-Written SDK Surfaces

These modules sit on top of the generated `llama_cloud` client and are what most application tests exercise. `FakeLlamaCloudServer` must satisfy the HTTP contracts they rely on.

### Extract flow (`py/llama_cloud_services/extract/extract.py`)

- The class imports resource types from `llama_cloud` and owns an `AsyncLlamaCloud` client shared across both stateless and agent-backed flows.

```17:37:py/llama_cloud_services/extract/extract.py
from llama_cloud import (
    ExtractAgent as CloudExtractAgent,
    ExtractConfig,
    …
)
from llama_cloud.client import AsyncLlamaCloud
```

- Schema validation always calls `POST /api/v1/extraction/extraction-agents/schema/validation` through `client.llama_extract.validate_extraction_schema`, so the fake must mimic that endpoint.

```65:82:py/llama_cloud_services/extract/extract.py
async def _validate_schema(...):
    …
    validated_schema = await client.llama_extract.validate_extraction_schema(
        data_schema=processed_schema
    )
```

- Agent creation, listing, and run management use the `llama_extract` namespace. These calls surface the same request/response bodies as the SaaS API, so tests that interact through agents expect consistent metadata (IDs, status enums, etc.).

```636:738:py/llama_cloud_services/extract/extract.py
def create_agent(...):
    agent = self._run_in_thread(
        self._async_client.llama_extract.create_extraction_agent(
            project_id=self._project_id,
            …
        )
    )
    return ExtractionAgent(...)
```

- Stateless extraction queues work by converting file inputs into either `file_id`, inline text, or base64 payloads and forwarding them to `POST /api/v1/extraction/run`. Deterministic responses from the fake should be keyed off `processed_schema` + whichever file representation the SDK sent.

```921:1018:py/llama_cloud_services/extract/extract.py
async def queue_extraction(...):
    processed_schema = await _validate_schema(...)
    …
    job = await self._async_client.llama_extract.extract_stateless(
        project_id=self._project_id,
        organization_id=self._organization_id,
        data_schema=processed_schema,
        config=config,
        **file_args,
    )
```

### File uploads (`py/llama_cloud_services/files/client.py`)

- All higher-level services route file uploads/downloads through `FileClient`. When `use_presigned_url` is enabled, the client first calls `POST /api/v1/files` (generate URL), then performs the PUT upload directly, then fetches metadata via `GET /api/v1/files/{id}`. The fake must intercept both the API calls and the presigned PUT hops to return consistent `file_id`s and stored bytes.

```63:140:py/llama_cloud_services/files/client.py
presigned_url = await self.client.files.generate_presigned_url(...)
upload_response = await httpx_client.put(presigned_url.url, data=buffer.read())
…
return await self.client.files.get_file(presigned_url.file_id, …)
```

### Parse reader (`py/llama_cloud_services/parse/base.py`)

- `LlamaParse` is a bespoke reader that talks straight to HTTP routes defined in the module (e.g., `/api/parsing/upload`, `/api/parsing/job/{id}`). Unlike `LlamaExtract`, it does not go through the generated client; instead it builds URLs manually and uses `httpx`/`make_api_request`. A fake server must therefore implement these exact paths.

```49:66:py/llama_cloud_services/parse/base.py
JOB_RESULT_URL = "/api/parsing/job/{job_id}/result/{result_type}"
JOB_STATUS_ROUTE = "/api/parsing/job/{job_id}"
JOB_UPLOAD_ROUTE = "/api/parsing/upload"
```

```1056:1070:py/llama_cloud_services/parse/base.py
url = build_url(JOB_UPLOAD_ROUTE, self.organization_id, self.project_id)
resp = await make_api_request(self.aclient, "POST", url, …, files=files, data=data)
```

### Classifier beta client (`py/llama_cloud_services/beta/classifier/client.py`)

- Classification flows reuse `FileClient` for uploads and then call `AsyncLlamaCloud.classifier` endpoints (`create_classify_job`, `get_classify_job`, `get_classification_job_results`). Long-running tests poll until status becomes terminal, so mocking needs to cover both the enqueue POST and the follow-up GETs.

```75:151:py/llama_cloud_services/beta/classifier/client.py
return await self.client.classifier.create_classify_job(...)
…
results = await self.client.classifier.get_classification_job_results(
    classify_job_with_status.id,
    project_id=self.project_id,
)
```

## Generated Python Client

- The repo depends on the published `llama_cloud` package (currently 0.1.44) which is itself generated from the OpenAPI spec. All hand-written modules import types and service clients from this package, so the fake server may need to mirror whatever transport settings `AsyncLlamaCloud` expects (headers, pagination, etc.).

```1605:1608:py/uv.lock
sdist = { … "llama_cloud-0.1.44.tar.gz", … }
wheels = [{ … "llama_cloud-0.1.44-py3-none-any.whl", … }]
```

- Since `AsyncLlamaCloud` handles auth headers and base URLs, integrating the fake server typically means pointing `LLAMA_CLOUD_BASE_URL` at the mock and letting the generated client continue to build resource paths.

## TypeScript + OpenAPI Assets

- The canonical OpenAPI document lives in `ts/llama_cloud_services/openapi.json`. It defines every path/operation used by both the generated TypeScript SDK and the Python client. For example, the stateless extract endpoint is captured as `POST /api/v1/extraction/run`.

```13825:13872:ts/llama_cloud_services/openapi.json
"/api/v1/extraction/run": {
  "post": {
    "summary": "Extract Stateless",
    "description": "… Requires data_schema, config, and either file_id, text, or base64 encoded file data.",
    …
  }
}
```

- The OpenAPI document is downloaded from production via `scripts/download.mjs` and then fed into `@hey-api/openapi-ts` to regenerate the TypeScript client and schema wrappers. Keeping the fake server in sync with the spec means you can diff regenerated clients when the API evolves.

```3:21:ts/llama_cloud_services/scripts/download.mjs
const response = await fetch('https://api.cloud.llamaindex.ai/api/openapi.json');
…
fs.writeFileSync('openapi.json', JSON.stringify(data, null, 2));
```

```1:24:ts/llama_cloud_services/openapi-ts.config.ts
export default defineConfig({
  input: "./openapi.json",
  output: { path: "./src/client", format: "prettier", lint: "eslint" },
  plugins: [ … "@hey-api/sdk", "@hey-api/typescript" ],
});
```

- The public TypeScript surface (`src/LlamaClassify.ts`, etc.) already consumes the generated client by injecting auth headers and delegating to `classify(...)`. If Python tests eventually need to reuse the same fake server, TypeScript examples provide another reference for how SDK consumers expect responses to look.

```12:74:ts/llama_cloud_services/src/LlamaClassify.ts
export class LlamaClassify {
  constructor(apiKey?: string, baseUrl?: string, region?: string) {
    …
    this.client = createClient(createConfig({ baseUrl: url, headers: { Authorization: `Bearer ${key}` }}));
  }

  async classify(rules, configuration, { fileContents, filePaths, projectId, … }) {
    const result = await classify(rules, configuration, {
      fileContents,
      filePaths,
      projectId: projectId ?? undefined,
      client: this.client,
      …
    });
    return result;
  }
}
```

## Endpoint Map to Stub First

Cross-referencing the Python call-sites with the OpenAPI spec yields the minimum set of HTTP routes the fake server must implement:

1. `/api/v1/extraction/run` for stateless jobs, plus the agent CRUD endpoints under `/api/v1/extraction/extraction-agents`, `/api/v1/extraction/jobs`, and `/api/v1/extraction/runs/by-job/{id}` (see `LlamaExtract` usage above).
2. `/api/v1/files/**` for upload/generate-presigned/list/get/delete, plus any presigned `PUT` destinations (`FileClient`).
3. `/api/parsing/upload`, `/api/parsing/job/{job_id}`, `/api/parsing/job/{job_id}/result/{result_type}` (direct HTTPX calls in `LlamaParse`).
4. `/api/v1/classifier/**` for job creation, polling, and result retrieval (`LlamaClassify` and `ClassifyClient`).

Having deterministic handlers for these routes unlocks end-to-end coverage of extract/parse/classify flows without touching live SaaS.

## Implementation Reminders from the Spec

- Namespace toggles let tests intercept a subset of APIs while letting others fall through—mirror this by allowing `FakeLlamaCloudServer(namespaces=[...])` to selectively register respx routes.
- Deterministic payloads should derive from uploaded file bytes + schema hashes for extract, layout characteristics for parse, and label sets for classify so that rerunning the same test yields identical responses (reducing fixture churn).
- Keep the matcher system (`RequestMatcher`, `FileMatcher`, etc.) flexible so individual tests can stub failures (e.g., presigned upload errors, job timeouts) without reconfiguring the entire fake.

```44:210:py/testing_utils_spec.md
with FakeLlamaCloudServer() as fake:
    extractor = LlamaExtract(...)
    parser = LlamaParse(...)
    classifier = LlamaClassify(...)
…
fake.extract.stub_run(... RequestMatcher ...)
```

Armed with the file map above, a new developer can trace any SDK call from the hand-written layers down to the generated client and the authoritative OpenAPI route, making it clear where the fake server needs to hook in.
