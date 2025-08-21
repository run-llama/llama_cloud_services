import os
from types import SimpleNamespace

import pytest

from llama_cloud.types import File as CloudFile
from llama_cloud_services.extract import LlamaExtract, ExtractionAgent


@pytest.fixture(autouse=True)
def _set_dummy_env(monkeypatch):
    monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "test-api-key")
    monkeypatch.setenv("LLAMA_CLOUD_BASE_URL", "https://example.test")


@pytest.fixture
def llama_file() -> CloudFile:
    return CloudFile(
        id="file_123",
        name="sample.pdf",
        external_file_id="ext_123",
        project_id="proj_123",
    )


@pytest.fixture
def extractor() -> LlamaExtract:
    return LlamaExtract(
        api_key=os.environ["LLAMA_CLOUD_API_KEY"],
        base_url=os.environ["LLAMA_CLOUD_BASE_URL"],
        verify=False,
    )


@pytest.fixture
def no_external_validation(monkeypatch):
    import llama_cloud_services.extract.extract as extract_mod

    async def _noop_validate_schema(client, data_schema):
        return data_schema

    # Disable config warnings and external schema validation
    monkeypatch.setattr(
        extract_mod, "_extraction_config_warning", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(extract_mod, "_validate_schema", _noop_validate_schema)


def test_convert_fileinput_accepts_llama_file_directly(
    extractor: LlamaExtract, llama_file: CloudFile
):
    result = extractor._convert_file_to_file_data(llama_file)
    assert result is llama_file


@pytest.mark.asyncio
async def test_queue_extraction_with_llama_file_uses_file_id(
    extractor: LlamaExtract, llama_file: CloudFile, no_external_validation, monkeypatch
):
    calls = []

    async def fake_extract_stateless(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id="job_1")

    # Patch the client's method that would normally hit the network
    monkeypatch.setattr(
        extractor._async_client.llama_extract,
        "extract_stateless",
        fake_extract_stateless,
    )

    # Minimal schema and dummy config (warnings disabled by fixture)
    schema = {"type": "object", "properties": {}}
    dummy_config = SimpleNamespace()

    job = await extractor.queue_extraction(schema, dummy_config, llama_file)

    assert getattr(job, "id") == "job_1"
    assert len(calls) == 1
    kwargs = calls[0]
    assert "file_id" in kwargs and kwargs["file_id"] == llama_file.id
    assert "file" not in kwargs
    assert "text" not in kwargs


@pytest.mark.asyncio
async def test_extraction_agent_upload_file_accepts_llama_file_directly(
    llama_file: CloudFile,
):
    # Build a minimal agent without hitting external services
    dummy_async_client = SimpleNamespace()
    dummy_agent = SimpleNamespace(id="agent_1", name="dummy", data_schema={}, config={})

    agent = ExtractionAgent(
        client=dummy_async_client,
        agent=dummy_agent,
        project_id=None,
        organization_id=None,
        check_interval=0,
        max_timeout=0,
        num_workers=1,
        show_progress=False,
        verbose=False,
        verify=False,
        httpx_timeout=1,
    )

    result = await agent._upload_file(llama_file)
    assert result is llama_file


@pytest.mark.asyncio
async def test_extraction_agent_aextract_accepts_llama_file(
    monkeypatch, llama_file: CloudFile
):
    # Build a minimal agent without network
    dummy_llama_extract_iface = SimpleNamespace()

    async def fake_run_job(**kwargs):
        # Ensure we are receiving a request with the right file_id
        request = kwargs.get("request")
        assert hasattr(request, "file_id")
        assert request.file_id == llama_file.id
        return SimpleNamespace(id="job_42")

    dummy_llama_extract_iface.run_job = fake_run_job
    dummy_async_client = SimpleNamespace(llama_extract=dummy_llama_extract_iface)
    dummy_agent = SimpleNamespace(id="agent_1", name="dummy", data_schema={}, config={})

    agent = ExtractionAgent(
        client=dummy_async_client,
        agent=dummy_agent,
        project_id=None,
        organization_id=None,
        check_interval=0,
        max_timeout=0,
        num_workers=1,
        show_progress=False,
        verbose=False,
        verify=False,
        httpx_timeout=1,
    )

    # Ensure _upload_file returns the File directly and is called with our File
    calls = {}

    async def fake_upload_file(file_input):
        calls["upload_called_with"] = file_input
        assert file_input is llama_file
        return file_input

    monkeypatch.setattr(agent, "_upload_file", fake_upload_file)

    # Avoid polling logic by short-circuiting result wait
    async def fake_wait(job_id: str):
        assert job_id == "job_42"
        return SimpleNamespace(id="run_42", status="SUCCESS", data={})

    monkeypatch.setattr(agent, "_wait_for_job_result", fake_wait)

    result = await agent.aextract(llama_file)

    assert calls.get("upload_called_with") is llama_file
    assert getattr(result, "status") == "SUCCESS"
    assert getattr(result, "id") == "run_42"
