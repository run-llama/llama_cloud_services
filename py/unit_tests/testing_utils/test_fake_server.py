from __future__ import annotations

from pathlib import Path

import pytest
from llama_cloud import ExtractConfig
from llama_cloud.types import ExtractMode
from llama_cloud.core.api_error import ApiError
from llama_cloud_services.extract import LlamaExtract
from llama_cloud_services.parse import LlamaParse
from llama_cloud_services.beta.agent_data import AsyncAgentDataClient
from llama_cloud_services.testing_utils import FakeLlamaCloudServer
from llama_cloud_services.testing_utils._deterministic import hash_schema
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


def test_stateless_extract_is_deterministic(
    fake_server: FakeLlamaCloudServer, tmp_path: Path
) -> None:
    extractor = LlamaExtract(api_key="unit-test-key", verify=False)
    config = ExtractConfig(extraction_mode=ExtractMode.FAST)
    sample_path = _write_sample_file(
        tmp_path, "receipt.txt", "Merchant: Lunar Bistro\nTotal: 123.45"
    )

    first_run = extractor.extract(Receipt, config, sample_path)
    second_run = extractor.extract(Receipt, config, sample_path)

    assert first_run.status.value == "SUCCESS"
    assert second_run.data == first_run.data
    assert "merchant" in first_run.data
    assert fake_server.extract.stateless_run.called


def test_agent_flow_uploads_and_processes_files(
    fake_server: FakeLlamaCloudServer, tmp_path: Path
) -> None:
    extractor = LlamaExtract(api_key="unit-test-key", verify=False)
    config = ExtractConfig(extraction_mode=ExtractMode.FAST)
    agent = extractor.create_agent(
        name="unit-test-agent", data_schema=Receipt, config=config
    )

    sample_path = _write_sample_file(
        tmp_path, "contract.pdf", "Agreement between parties."
    )
    run = agent.extract(sample_path)

    assert run.status.value == "SUCCESS"
    assert "merchant" in run.data

    uploaded_bytes = fake_server.files.read(run.file.id)
    assert uploaded_bytes.startswith(b"Agreement")
    assert fake_server.extract.agent_job.called
    assert fake_server.extract.agent_run.called


def test_parse_load_data_returns_documents(
    fake_server: FakeLlamaCloudServer, tmp_path: Path
) -> None:
    parser = LlamaParse(
        api_key="unit-test-key", base_url=FakeLlamaCloudServer.DEFAULT_BASE_URL
    )
    sample_path = _write_sample_file(
        tmp_path, "report.pdf", "Executive summary of quarterly goals."
    )

    documents = parser.load_data(sample_path)

    assert documents
    assert "(page 1)" in documents[0].text


@pytest.mark.asyncio
async def test_agent_data_create(fake_server: FakeLlamaCloudServer):
    with fake_server as _:
        client = AsyncAgentDataClient(
            Receipt,
            collection="extracted_data",
            deployment_name="extraction_agent",
            token="fake-api-key",
        )
        data = Receipt(merchant="Test Inc", total=1000)
        item = await client.create_item(data)
        assert item.id == hash_schema(data)[:7]
        assert item.data.merchant == data.merchant and item.data.total == data.total
        assert item.collection == "extracted_data"
        assert item.deployment_name == "extraction_agent"


@pytest.mark.asyncio
async def test_agent_data_update(fake_server: FakeLlamaCloudServer):
    with fake_server as _:
        client = AsyncAgentDataClient(
            Receipt,
            collection="extracted_data",
            deployment_name="extraction_agent",
            token="fake-api-key",
        )
        data = Receipt(merchant="Test Inc", total=1000)
        item = await client.create_item(data)
        assert item.id is not None
        updated_data = Receipt(merchant="Testing Inc", total=1100)
        updated_item = await client.update_item(item_id=item.id, data=updated_data)
        # ensure that the data actually changed
        assert (
            updated_item.data.merchant == updated_data.merchant
            and updated_item.data.total == updated_data.total
        )
        # make sure nothing else changed
        assert updated_item.id == item.id
        assert updated_item.collection == item.collection
        assert updated_item.deployment_name == item.deployment_name


@pytest.mark.asyncio
async def test_agent_data_search(fake_server: FakeLlamaCloudServer):
    with fake_server as _:
        client = AsyncAgentDataClient(
            Receipt,
            collection="extracted_data",
            deployment_name="extraction_agent",
            token="fake-api-key",
        )
        data1 = Receipt(merchant="Test Inc", total=1000)
        data2 = Receipt(merchant="Test Inc", total=1300)
        data3 = Receipt(merchant="Testing Inc", total=1100)
        item1 = await client.create_item(data1)
        item2 = await client.create_item(data2)
        item3 = await client.create_item(data3)
        result = await client.search(filter={"merchant": {"eq": "Test Inc"}})
        assert result.total == 2
        assert any(item.id == item1.id for item in result.items) and any(
            item.id == item2.id for item in result.items
        )
        assert all(item.data.merchant == "Test Inc" for item in result.items)
        result1 = await client.search(filter={"total": {"lt": 1200}})
        assert result.total == 2
        assert any(item.id == item1.id for item in result1.items) and any(
            item.id == item3.id for item in result1.items
        )
        assert all(item.data.total < 1200 for item in result1.items)


@pytest.mark.asyncio
async def test_agent_data_aggregate(fake_server: FakeLlamaCloudServer):
    with fake_server as _:
        client = AsyncAgentDataClient(
            Receipt,
            collection="extracted_data",
            deployment_name="extraction_agent",
            token="fake-api-key",
        )
        data1 = Receipt(merchant="Test Inc", total=1000)
        data2 = Receipt(merchant="Test Inc", total=1300)
        data3 = Receipt(merchant="Testing Inc", total=1100)
        await client.create_item(data1)
        await client.create_item(data2)
        await client.create_item(data3)
        result = await client.aggregate(
            filter={"merchant": {"eq": "Test Inc"}},
            group_by=["merchant"],
            count=True,
        )
        # filtering for 'Test Inc' on merchant means that only data with 'Test Inc' are left, meaning that there is only one group of data for merchant, i.e. the 'Test Inc' group
        assert len(result.items) == 1
        assert result.items[0].count == 2
        assert result.items[0].first_item is not None
        assert result.items[0].first_item.merchant == data1.merchant
        assert result.items[0].first_item.total == data1.total
        assert result.items[0].group_key == {"merchant": "Test Inc"}
        result = await client.aggregate(
            group_by=["merchant"],
            count=True,
        )
        assert len(result.items) == 2
        assert result.items[0].count == 2
        assert result.items[0].first_item is not None
        assert result.items[0].first_item.merchant == data1.merchant
        assert result.items[0].first_item.total == data1.total
        assert result.items[0].group_key == {"merchant": "Test Inc"}
        assert result.items[1].count == 1
        assert result.items[1].first_item is not None
        assert result.items[1].first_item.merchant == data3.merchant
        assert result.items[1].first_item.total == data3.total
        assert result.items[1].group_key == {"merchant": "Testing Inc"}


@pytest.mark.asyncio
async def test_agent_data_get(fake_server: FakeLlamaCloudServer):
    with fake_server as _:
        client = AsyncAgentDataClient(
            Receipt,
            collection="extracted_data",
            deployment_name="extraction_agent",
            token="fake-api-key",
        )
        data1 = Receipt(merchant="Test Inc", total=1000)
        data2 = Receipt(merchant="Test Inc", total=1300)
        item1 = await client.create_item(data1)
        assert item1.id is not None
        item2 = await client.create_item(data2)
        assert item2.id is not None
        item = await client.get_item(item1.id)
        assert item.collection == item1.collection
        assert item.deployment_name == item1.deployment_name
        assert item.data.merchant == data1.merchant
        assert item.data.total == data1.total
        # using this pattern instead of `with pytest.raise` for more granual control over the error itself
        try:
            notitem = await client.get_item(item2.id + "thisdoesnotexist")
            e = None
        except ApiError as err:
            e = err
            notitem = None
        assert notitem is None
        assert e is not None
        assert e.status_code == 404
        assert e.body == {"detail": f"No data with ID: {item2.id+'thisdoesnotexist'}"}


@pytest.mark.asyncio
async def test_agent_data_delete_by_id(fake_server: FakeLlamaCloudServer):
    with fake_server as _:
        client = AsyncAgentDataClient(
            Receipt,
            collection="extracted_data",
            deployment_name="extraction_agent",
            token="fake-api-key",
        )
        data = Receipt(merchant="Test Inc", total=1300)
        item = await client.create_item(data)
        assert item.id is not None
        await client.delete_item(item.id)
        # using this pattern instead of `with pytest.raise` for more granual control over the error itself
        try:
            notitem = await client.get_item(item.id)
            e = None
        except ApiError as err:
            e = err
            notitem = None
        assert notitem is None
        assert e is not None
        assert e.status_code == 404
        assert e.body == {"detail": f"No data with ID: {item.id}"}
        # using this pattern instead of `with pytest.raise` for more granual control over the error itself
        try:
            await client.delete_item(item.id)
            e = None
        except ApiError as err:
            e = err
        assert e is not None
        assert e.status_code == 404
        assert e.body == {"detail": f"No data with ID: {item.id}"}


@pytest.mark.asyncio
async def test_agent_data_delete_by_query(fake_server: FakeLlamaCloudServer):
    with fake_server as _:
        client = AsyncAgentDataClient(
            Receipt,
            collection="extracted_data",
            deployment_name="extraction_agent",
            token="fake-api-key",
        )
        data1 = Receipt(merchant="Test Inc", total=1000)
        data2 = Receipt(merchant="Test Inc", total=1300)
        data3 = Receipt(merchant="Testing Inc", total=1100)
        item1 = await client.create_item(data1)
        item2 = await client.create_item(data2)
        item3 = await client.create_item(data3)
        result = await client.delete(filter={"merchant": {"eq": "Test Inc"}})
        assert result == 2
        for item in (item1, item2):
            assert item.id is not None
            try:
                notitem = await client.get_item(item.id)
                e = None
            except ApiError as err:
                e = err
                notitem = None
            assert notitem is None
            assert e is not None
            assert e.status_code == 404
            assert e.body == {"detail": f"No data with ID: {item.id}"}
        assert item3.id is not None
        itemfound = await client.get_item(item3.id)
        assert itemfound.id == item3.id
