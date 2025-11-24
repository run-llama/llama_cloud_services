from __future__ import annotations

from pathlib import Path

import pytest
from llama_cloud import ExtractConfig
from llama_cloud.types import ExtractMode
from llama_cloud_services.extract import LlamaExtract
from llama_cloud_services.parse import LlamaParse
from llama_cloud_services.testing_utils import FakeLlamaCloudServer
from pydantic import BaseModel, Field


class Receipt(BaseModel):
    merchant: str = Field(description="Vendor name")
    total: float = Field(description="Grand total")


@pytest.fixture(autouse=True)
def _fake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "unit-test-key")
    monkeypatch.setenv("LLAMA_CLOUD_BASE_URL", FakeLlamaCloudServer.DEFAULT_BASE_URL)


@pytest.fixture
def fake_server() -> FakeLlamaCloudServer:
    with FakeLlamaCloudServer() as server:
        yield server


def _write_sample_file(tmp_path: Path, name: str, content: str) -> Path:
    target = tmp_path / name
    target.write_text(content)
    return target


def test_stateless_extract_is_deterministic(fake_server: FakeLlamaCloudServer, tmp_path: Path) -> None:
    extractor = LlamaExtract(api_key="unit-test-key", verify=False)
    config = ExtractConfig(extraction_mode=ExtractMode.FAST)
    sample_path = _write_sample_file(tmp_path, "receipt.txt", "Merchant: Lunar Bistro\nTotal: 123.45")

    first_run = extractor.extract(Receipt, config, sample_path)
    second_run = extractor.extract(Receipt, config, sample_path)

    assert first_run.status.value == "SUCCESS"
    assert second_run.data == first_run.data
    assert "merchant" in first_run.data
    assert fake_server.extract.stateless_run.called


def test_agent_flow_uploads_and_processes_files(fake_server: FakeLlamaCloudServer, tmp_path: Path) -> None:
    extractor = LlamaExtract(api_key="unit-test-key", verify=False)
    config = ExtractConfig(extraction_mode=ExtractMode.FAST)
    agent = extractor.create_agent(name="unit-test-agent", data_schema=Receipt, config=config)

    sample_path = _write_sample_file(tmp_path, "contract.pdf", "Agreement between parties.")
    run = agent.extract(sample_path)

    assert run.status.value == "SUCCESS"
    assert "merchant" in run.data

    uploaded_bytes = fake_server.files.read(run.file.id)
    assert uploaded_bytes.startswith(b"Agreement")
    assert fake_server.extract.agent_job.called
    assert fake_server.extract.agent_run.called


def test_parse_load_data_returns_documents(fake_server: FakeLlamaCloudServer, tmp_path: Path) -> None:
    parser = LlamaParse(api_key="unit-test-key", base_url=FakeLlamaCloudServer.DEFAULT_BASE_URL)
    sample_path = _write_sample_file(tmp_path, "report.pdf", "Executive summary of quarterly goals.")

    documents = parser.load_data(sample_path)

    assert documents
    assert "(page 1)" in documents[0].text
