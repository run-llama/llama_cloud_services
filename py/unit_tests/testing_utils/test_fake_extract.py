from __future__ import annotations

import hashlib
from pathlib import Path

from llama_cloud import ExtractConfig, ExtractMode, ExtractTarget, StatusEnum

from llama_cloud_services.extract import LlamaExtract
from llama_cloud_services.testing_utils import (
    FakeLlamaCloudServer,
    FileMatcher,
    RequestMatcher,
    attach_extract_api,
)


def _write_pdf(tmp_path: Path, name: str, contents: bytes) -> Path:
    target = tmp_path / name
    target.write_bytes(contents)
    return target


def _schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "total": {"type": "number"},
            "paid": {"type": "boolean"},
        },
    }


def _config() -> ExtractConfig:
    return ExtractConfig(
        extraction_mode=ExtractMode.FAST,
        extraction_target=ExtractTarget.PER_DOC,
    )


def test_stateless_extract_is_deterministic(tmp_path: Path) -> None:
    pdf = _write_pdf(tmp_path, "receipt.pdf", b"fake pdf bytes")
    schema = _schema()
    config = _config()

    with FakeLlamaCloudServer() as server:
        attach_extract_api(server)
        extractor = LlamaExtract(api_key="test-key", base_url=server.primary_base_url, verify=False)

        run_one = extractor.extract(schema, config, pdf)
        run_two = extractor.extract(schema, config, pdf)

        assert run_one.data == run_two.data
        assert run_one.status == run_two.status == StatusEnum.SUCCESS


def test_stateless_extract_can_be_stubbed(tmp_path: Path) -> None:
    pdf = _write_pdf(tmp_path, "noisebridge.pdf", b"noisebridge receipt")
    schema = _schema()
    config = _config()
    expected_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()

    with FakeLlamaCloudServer() as server:
        extract_api = attach_extract_api(server)
        extract_api.stub_run(
            matcher=RequestMatcher(file=FileMatcher(sha256=expected_sha)),
            data={"title": "Noisebridge", "total": 42.0, "paid": True},
        )
        extractor = LlamaExtract(api_key="test-key", base_url=server.primary_base_url, verify=False)

        run = extractor.extract(schema, config, pdf)

        assert run.data["title"] == "Noisebridge"
        assert run.data["total"] == 42.0
        assert run.data["paid"] is True


def test_agent_based_flow_uses_fake_server(tmp_path: Path) -> None:
    pdf = _write_pdf(tmp_path, "invoice.pdf", b"agent file")
    schema = _schema()

    with FakeLlamaCloudServer() as server:
        attach_extract_api(server)
        extractor = LlamaExtract(api_key="test-key", base_url=server.primary_base_url, verify=False)

        agent = extractor.create_agent("unit-agent", schema)
        run = agent.extract(pdf)

        assert run.file.name.endswith("invoice.pdf")
        assert "title" in run.data and "total" in run.data
