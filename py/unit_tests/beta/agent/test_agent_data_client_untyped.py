import pytest
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

from llama_cloud.types.agent_data import AgentData
from llama_cloud.types.aggregate_group import AggregateGroup

from llama_cloud_services.beta.agent_data.client import AsyncAgentDataClient


class Person(BaseModel):
    name: str
    age: int


class FakeBeta:
    def __init__(self) -> None:
        self._get_item_response: Optional[AgentData] = None
        self._search_items: List[AgentData] = []
        self._aggregate_items: List[AggregateGroup] = []
        self._total_size: Optional[int] = None
        self._next_page_token: Optional[str] = None

    # Single get
    async def get_agent_data(self, item_id: str) -> AgentData:
        assert self._get_item_response is not None, "_get_item_response not set"
        return self._get_item_response

    # Search
    async def search_agent_data_api_v_1_beta_agent_data_search_post(
        self,
        *,
        deployment_name: str,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        page_size: Optional[int] = None,
        include_total: bool = False,
    ) -> Any:
        class Resp:
            def __init__(
                self,
                items: List[AgentData],
                total_size: Optional[int],
                next_page_token: Optional[str],
            ) -> None:
                self.items = items
                self.total_size = total_size
                self.next_page_token = next_page_token

        return Resp(self._search_items, self._total_size, self._next_page_token)

    # Aggregate
    async def aggregate_agent_data_api_v_1_beta_agent_data_aggregate_post(
        self,
        *,
        deployment_name: str,
        collection: str,
        page_size: Optional[int] = None,
        filter: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        group_by: Optional[List[str]] = None,
        count: Optional[bool] = None,
        first: Optional[bool] = None,
        offset: Optional[int] = None,
    ) -> Any:
        class Resp:
            def __init__(
                self,
                items: List[AggregateGroup],
                total_size: Optional[int],
                next_page_token: Optional[str],
            ) -> None:
                self.items = items
                self.total_size = total_size
                self.next_page_token = next_page_token

        return Resp(self._aggregate_items, self._total_size, self._next_page_token)


class FakeClient:
    def __init__(self) -> None:
        self.beta = FakeBeta()


def make_agent_data(data: Dict[str, Any]) -> AgentData:
    return AgentData(
        id="id-1",
        deployment_name="dep",
        collection="col",
        data=data,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_group(
    group_key: Dict[str, Any],
    first_item: Optional[Dict[str, Any]],
    count: Optional[int] = None,
) -> AggregateGroup:
    return AggregateGroup(group_key=group_key, count=count, first_item=first_item)


@pytest.mark.asyncio
async def test_untyped_get_item_valid_to_dict() -> None:
    client = FakeClient()
    client.beta._get_item_response = make_agent_data({"name": "Alice", "age": 30})

    adc = AsyncAgentDataClient(type=Person, client=client, deployment_name="dep")
    item = await adc.untyped_get_item("id-1")
    assert item.data == {"name": "Alice", "age": 30}


@pytest.mark.asyncio
async def test_untyped_get_item_invalid_retains_dict() -> None:
    client = FakeClient()
    # age wrong type; will fail validation and should be returned as dict
    client.beta._get_item_response = make_agent_data({"name": "Bob", "age": "x"})

    adc = AsyncAgentDataClient(type=Person, client=client, deployment_name="dep")
    item = await adc.untyped_get_item("id-1")
    assert item.data == {"name": "Bob", "age": "x"}


@pytest.mark.asyncio
async def test_untyped_search_mixed_items() -> None:
    client = FakeClient()
    client.beta._search_items = [
        make_agent_data({"name": "Carol", "age": 22}),
        make_agent_data({"name": "Dave", "age": "bad"}),
    ]
    client.beta._total_size = 2

    adc = AsyncAgentDataClient(type=Person, client=client, deployment_name="dep")
    results = await adc.untyped_search(include_total=True)
    assert len(results.items) == 2
    assert results.items[0].data == {"name": "Carol", "age": 22}
    assert results.items[1].data == {"name": "Dave", "age": "bad"}
    assert results.total_size == 2


@pytest.mark.asyncio
async def test_untyped_aggregate_first_item_dict() -> None:
    client = FakeClient()
    client.beta._aggregate_items = [
        make_group({"k": 1}, {"name": "Eve", "age": 40}),
        make_group({"k": 2}, {"name": "Frank", "age": "bad"}),
    ]
    client.beta._total_size = 2

    adc = AsyncAgentDataClient(type=Person, client=client, deployment_name="dep")
    results = await adc.untyped_aggregate(group_by=["k"], first=True)
    assert len(results.items) == 2
    assert results.items[0].first_item == {"name": "Eve", "age": 40}
    assert results.items[1].first_item == {"name": "Frank", "age": "bad"}
