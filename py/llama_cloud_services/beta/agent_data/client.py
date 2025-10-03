import os
from typing import Any, Dict, Generic, List, Optional, Type

from llama_cloud import (
    AgentData,
    PaginatedResponseAgentData,
    PaginatedResponseAggregateGroup,
)
from llama_cloud.client import AsyncLlamaCloud
from tenacity import (
    WrappedFn,
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

from .schema import (
    AgentDataT,
    ComparisonOperator,
    TypedAgentData,
    TypedAgentDataItems,
    TypedAggregateGroup,
    TypedAggregateGroupItems,
)


def agent_data_retry(func: WrappedFn) -> WrappedFn:
    """
    Decorator that adds automatic retry logic to agent data API calls.

    Applies exponential backoff retry strategy for common network-related exceptions:
    - Up to 3 retry attempts
    - Exponential wait time between 0.5s and 10s
    - Retries on timeout, connection, and HTTP status errors

    This ensures resilient API communication in distributed environments where
    temporary network issues or service unavailability may occur.
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.5, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)
        ),
    )(func)


def get_default_agent_id() -> str:
    """
    Retrieve the default agent ID from environment variables.

    Returns:
        The value of LLAMA_DEPLOY_DEPLOYMENT_NAME environment variable,
        or None if not set

    Note:
        This provides a convenient way to configure agent ID globally
        via environment variables instead of passing it explicitly
        to each client instance.
    """
    return os.getenv("LLAMA_DEPLOY_DEPLOYMENT_NAME") or "_public"


class AsyncAgentDataClient(Generic[AgentDataT]):
    """
    Async client for managing agent-generated structured data with type safety.

    This client provides a high-level interface for CRUD operations, searching, and
    aggregation of structured data created by agents. It enforces type safety by
    validating all data against a specified Pydantic model type.

    The client is generic over AgentDataT, which must be a Pydantic BaseModel that
    defines the structure of your agent's data output.

    Example:
        ```python
        from pydantic import BaseModel
        from llama_cloud.client import AsyncLlamaCloud
        from llama_cloud_services.beta.agent_data import AsyncAgentDataClient

        class ExtractedPerson(BaseModel):
            name: str
            age: int
            email: str

        # Initialize client
        llama_client = AsyncLlamaCloud(token="your-api-key")
        agent_client = AsyncAgentDataClient(
            client=llama_client,
            type=ExtractedPerson,
            collection="extracted_people",
            deployment_name="person-extraction-agent"
        )

        # Create data
        person = ExtractedPerson(name="John Doe", age=30, email="john@example.com")
        result = await agent_client.create_agent_data(person)

        # Search data
        results = await agent_client.search(
            filter={"age": {"gt": 25}},
            order_by="data.name",
            page_size=20
        )
        ```

    Type Parameters:
        AgentDataT: Pydantic BaseModel type that defines the structure of agent data
    """

    def __init__(
        self,
        type: Type[AgentDataT],
        collection: str = "default",
        deployment_name: Optional[str] = None,
        client: Optional[AsyncLlamaCloud] = None,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        # deprecated, use deployment_name instead
        agent_url_id: Optional[str] = None,
    ):
        """
        Initialize the AsyncAgentDataClient.

        Args:
            type: Pydantic BaseModel class that defines the data structure.
                All agent data will be validated against this type.
            collection: Named collection within the agent for organizing data.
                Defaults to "default". Collections allow logical separation of
                different data types or workflows within the same agent.
            deployment_name: Unique identifier for the agent deployment. This normally
                appears in the URL of an agent within the Llama Cloud platform. If not
                provided, will attempt to use the LLAMA_DEPLOY_DEPLOYMENT_NAME
                environment variable. Data can only be added to an already existing
                agent in the platform.
            client: AsyncLlamaCloud client instance for API communication. If not provided, will
                construct one from the provided api token and base url
            token: Llama Cloud API token. Reads from LLAMA_CLOUD_API_KEY if not provided
            base_url: Llama Cloud API token. Reads from LLAMA_CLOUD_BASE_URL if not provided, and
                defaults to https://api.cloud.llamaindex.ai

        Raises:
            ValueError: If deployment_name is not provided and the
                LLAMA_DEPLOY_DEPLOYMENT_NAME environment variable is not set

        Note:
            The client automatically applies retry logic to all API calls with
            exponential backoff for timeout, connection, and HTTP status errors.
        """
        self.deployment_name = deployment_name or agent_url_id or get_default_agent_id()

        self.collection = collection
        if not client:
            client = AsyncLlamaCloud(
                token=token or os.getenv("LLAMA_CLOUD_API_KEY"),
                base_url=base_url or os.getenv("LLAMA_CLOUD_BASE_URL"),
            )
        self.client = client
        self.type = type

    @agent_data_retry
    async def get_item(self, item_id: str) -> TypedAgentData[AgentDataT]:
        raw_data = await self.untyped_get_item(item_id)
        return TypedAgentData.from_raw(raw_data, self.type)

    @agent_data_retry
    async def untyped_get_item(self, item_id: str) -> AgentData:
        return await self.client.beta.get_agent_data(
            item_id=item_id,
        )

    @agent_data_retry
    async def create_item(self, data: AgentDataT) -> TypedAgentData[AgentDataT]:
        raw_data = await self.client.beta.create_agent_data(
            deployment_name=self.deployment_name,
            collection=self.collection,
            data=data.model_dump(),
        )
        return TypedAgentData.from_raw(raw_data, validator=self.type)

    @agent_data_retry
    async def update_item(
        self, item_id: str, data: AgentDataT
    ) -> TypedAgentData[AgentDataT]:
        raw_data = await self.client.beta.update_agent_data(
            item_id=item_id,
            data=data.model_dump(),
        )
        return TypedAgentData.from_raw(raw_data, validator=self.type)

    @agent_data_retry
    async def delete_item(self, item_id: str) -> None:
        await self.client.beta.delete_agent_data(item_id=item_id)

    @agent_data_retry
    async def delete(
        self, filter: Optional[Dict[str, Dict[ComparisonOperator, Any]]] = None
    ) -> int:
        """
        Delete agent data by query, similar to search.
        Returns the number of deleted items.
        """
        response = await self.client.beta.delete_agent_data_by_query_api_v_1_beta_agent_data_delete_post(
            deployment_name=self.deployment_name,
            collection=self.collection,
            filter=filter,
        )
        return response.deleted_count

    @agent_data_retry
    async def search(
        self,
        filter: Optional[Dict[str, Dict[ComparisonOperator, Any]]] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        page_size: Optional[int] = None,
        include_total: bool = False,
    ) -> TypedAgentDataItems[AgentDataT]:
        """
        Search agent data with filtering, sorting, and pagination.
        Args:
            filter: Filter conditions to apply to the search. Dict mapping field names to FilterOperation objects. Filters only by data fields
                Examples:
                - {"age": {"gt": 18}} - age greater than 18
                - {"status": {"eq": "active"}} - status equals "active"
                - {"tags": {"includes": ["python", "ml"]}} - tags include "python" or "ml"
                - {"created_at": {"gte": "2024-01-01"}} - created after date
                - {"score": {"lt": 100, "gte": 50}} - score between 50 and 100
            order_by: Comma delimited list of fields to sort results by. Can order by standard agent fields like created_at, or by data fields. Data fields must be prefixed with "data.". If ordering desceding, use a " desc" suffix.
                Examples:
                - "data.name desc, created_at" - sort by name in descending order, and then by creation date
            page_size: Maximum number of items to return per page. Defaults to 10.
            offset: Number of items to skip from the beginning. Defaults to 0.
            include_total: Whether to include the total count in the response. Defaults to False to improve performance. It's recommended to only request on the first page.
        """
        raw = await self.untyped_search(
            filter=filter,
            order_by=order_by,
            offset=offset,
            page_size=page_size,
            include_total=include_total,
        )
        return TypedAgentDataItems(
            items=[
                TypedAgentData.from_raw(item, validator=self.type) for item in raw.items
            ],
            has_more=raw.next_page_token is not None,
            total=raw.total_size,
        )

    @agent_data_retry
    async def untyped_search(
        self,
        filter: Optional[Dict[str, Dict[ComparisonOperator, Any]]] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        page_size: Optional[int] = None,
        include_total: bool = False,
    ) -> PaginatedResponseAgentData:
        return await self.client.beta.search_agent_data_api_v_1_beta_agent_data_search_post(
            deployment_name=self.deployment_name,
            collection=self.collection,
            filter=filter,
            order_by=order_by,
            offset=offset,
            page_size=page_size,
            include_total=include_total,
        )

    @agent_data_retry
    async def aggregate(
        self,
        filter: Optional[Dict[str, Dict[ComparisonOperator, Any]]] = None,
        group_by: Optional[List[str]] = None,
        count: Optional[bool] = None,
        first: Optional[bool] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> TypedAggregateGroupItems[AgentDataT]:
        """
        Aggregate agent data into groups according to the group_by fields.
        Args:
            filter: Filter conditions to apply to the search. Dict mapping field names to FilterOperation objects. Filters only by data fields
                See search for more details on filtering.
            group_by: List of fields to group by. Groups strictly by equality. Can only group by data fields.
                Examples:
                - ["name"] - group by name
                - ["name", "age"] - group by name and age
            count: Whether to include the count of items in each group.
            first: Whether to include the first item in each group.
            order_by: Comma delimited list of fields to sort results by. See search for more details on ordering.
            offset: Number of groups to skip from the beginning. Defaults to 0.
            page_size: Maximum number of groups to return per page.
        """
        raw = await self.untyped_aggregate(
            filter=filter,
            group_by=group_by,
            count=count,
            first=first,
            order_by=order_by,
            offset=offset,
            page_size=page_size,
        )

        return TypedAggregateGroupItems(
            items=[
                TypedAggregateGroup.from_raw(grp, validator=self.type)
                for grp in raw.items
            ],
            has_more=raw.next_page_token is not None,
            total=raw.total_size,
        )

    @agent_data_retry
    async def untyped_aggregate(
        self,
        filter: Optional[Dict[str, Dict[ComparisonOperator, Any]]] = None,
        group_by: Optional[List[str]] = None,
        count: Optional[bool] = None,
        first: Optional[bool] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> PaginatedResponseAggregateGroup:
        return await self.client.beta.aggregate_agent_data_api_v_1_beta_agent_data_aggregate_post(
            deployment_name=self.deployment_name,
            collection=self.collection,
            page_size=page_size,
            filter=filter,
            order_by=order_by,
            group_by=group_by,
            count=count,
            first=first,
            offset=offset,
        )
