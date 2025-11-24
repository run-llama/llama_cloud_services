[![PyPI - Downloads](https://img.shields.io/pypi/dm/llama-cloud-services)](https://pypi.org/project/llama-cloud-services/)
[![GitHub contributors](https://img.shields.io/github/contributors/run-llama/llama_cloud_services)](https://github.com/run-llama/llama_cloud_services/graphs/contributors)
[![Discord](https://img.shields.io/discord/1059199217496772688)](https://discord.gg/dGcwcsnxhU)

# Llama Cloud Services

This repository contains the code for hand-written SDKs and clients for interacting with LlamaCloud.

This includes:

- [LlamaParse](../parse.md) - A GenAI-native document parser that can parse complex document data for any downstream LLM use case (Agents, RAG, data processing, etc.).
- [LlamaExtract](../extract.md) - A prebuilt agentic data extractor that can be used to transform data into a structured JSON representation.
- [LlamaCloud Index](../index.md) - A widely customizable and fully automated document ingestion pipeline that also serves retrieval purposes.

## Getting Started

Install the package:

```bash
pip install llama-cloud-services
```

Then, get your API key from [LlamaCloud](https://cloud.llamaindex.ai/).

Then, you can use the services in your code:

```python
from llama_cloud_services import (
    LlamaParse,
    LlamaExtract,
    LlamaCloudIndex,
)
from llama_cloud_services import LlamaParse, LlamaExtract

parser = LlamaParse(api_key="YOUR_API_KEY")
extract = LlamaExtract(api_key="YOUR_API_KEY")
index = LlamaCloudIndex(
    "my_first_index", project_name="default", api_key="YOUR_API_KEY"
)
```

See the quickstart guides for each service for more information:

- [LlamaParse](../parse.md)
- [LlamaExtract](../extract.md)
- [LlamaCloud Index](../index.md)

## Switch to EU SaaS 🇪🇺

If you are interested in using LlamaCloud services in the EU, you can adjust your base URL to `https://api.cloud.eu.llamaindex.ai`.

You can also create your API key in the EU region [here](https://cloud.eu.llamaindex.ai).

```python
from llama_cloud_services import (
    LlamaParse,
    LlamaExtract,
    EU_BASE_URL,
)

parser = LlamaParse(api_key="YOUR_API_KEY", base_url=EU_BASE_URL)
extract = LlamaExtract(api_key="YOUR_API_KEY", base_url=EU_BASE_URL)
index = LlamaCloudIndex(
    "my_first_index",
    project_name="default",
    api_key="YOUR_API_KEY",
    base_url=EU_BASE_URL,
)
```

## Documentation

You can see complete SDK and API documentation for each service on [our official docs](https://docs.cloud.llamaindex.ai/).

## Local Testing Utilities

The Python package now ships a lightweight fake LlamaCloud server that lets you run
offline tests without touching the real SaaS environment. The utilities live under
`llama_cloud_services.testing_utils` and are powered by [`respx`](https://respx.dev)
so any `httpx` client constructed by the SDK is seamlessly intercepted.

### Quick start

```python
import os
from pathlib import Path
from llama_cloud_services.extract import LlamaExtract, ExtractConfig, ExtractTarget
from llama_cloud_services.testing_utils import FakeLlamaCloudServer, attach_extract_api

schema = {
    "type": "object",
    "properties": {"title": {"type": "string"}, "total": {"type": "number"}},
}
config = ExtractConfig(extraction_target=ExtractTarget.PER_DOC)
pdf_path = Path("tests/fixtures/receipt.pdf")

with FakeLlamaCloudServer(base_urls=[os.environ.get("LLAMA_CLOUD_BASE_URL", "")]) as fake:
    attach_extract_api(fake)  # registers the extract routes, more namespaces coming soon
    extractor = LlamaExtract(api_key="test-key", base_url=fake.primary_base_url, verify=False)
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
    extractor = LlamaExtract(api_key="test", base_url=fake.primary_base_url, verify=False)
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

## Terms of Service

See the [Terms of Service Here](../TOS.pdf).

## Get in Touch (LlamaCloud)

You can get in touch with us by following our [contact link](https://www.llamaindex.ai/contact).
