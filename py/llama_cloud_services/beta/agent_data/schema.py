"""
Agent Data API Schema Definitions

This module provides typed wrappers around the raw LlamaCloud agent data API,
enabling type-safe interactions with agent-generated structured data.

The agent data API serves as a persistent storage system for structured data
produced by LlamaCloud agents (particularly extraction agents). It provides
CRUD operations, search capabilities, filtering, and aggregation functionality
for managing agent-generated data at scale.

Key Concepts:
- Agent Slug: Unique identifier for an agent instance
- Collection: Named grouping of data within an agent (defaults to "default"). Data within a collection should be of the same type.
- Agent Data: Individual structured data records with metadata and timestamps

Example Usage:
    ```python
    from pydantic import BaseModel

    class Person(BaseModel):
        name: str
        age: int

    client = AsyncAgentDataClient(
        client=async_llama_cloud,
        type=Person,
        collection="people",
        agent_url_id="my-extraction-agent-xyz"
    )

    # Create typed data
    person = Person(name="John", age=30)
    result = await client.create_agent_data(person)
    print(result.data.name)  # Type-safe access
    ```
"""

from datetime import datetime
from llama_cloud.types.agent_data import AgentData
from llama_cloud.types.aggregate_group import AggregateGroup
from pydantic import BaseModel, Field
from typing import (
    Generic,
    List,
    Literal,
    Optional,
    Dict,
    Type,
    TypeVar,
    Union,
    Any,
)


# Type variable for user-defined data models
AgentDataT = TypeVar("AgentDataT", bound=BaseModel)

# Type variable for extracted data (can be dict or Pydantic model)
ExtractedT = TypeVar("ExtractedT", bound=Union[BaseModel, dict])

# Status types for extracted data workflow
StatusType = Union[Literal["error", "accepted", "rejected", "pending_review"], str]

ComparisonOperator = Dict[
    str, Dict[Literal["gt", "gte", "lt", "lte", "eq", "includes"], Any]
]


class TypedAgentData(BaseModel, Generic[AgentDataT]):
    """
    Type-safe wrapper for agent data records.

    This class represents a single data record stored in the agent data API,
    combining the structured data payload with metadata about when and where
    it was created.

    Attributes:
        id: Unique identifier for this data record
        agent_url_id: Identifier of the agent that created this data
        collection: Named collection within the agent (used for organization)
        data: The actual structured data payload (typed as AgentDataT)
        created_at: Timestamp when the record was first created
        updated_at: Timestamp when the record was last modified

    Example:
        ```python
        # Access typed data
        person_data: TypedAgentData[Person] = await client.get_agent_data(id)
        print(person_data.data.name)  # Type-safe access to Person fields
        print(person_data.created_at)  # Access metadata
        ```
    """

    id: Optional[str] = Field(description="Unique identifier for this data record")
    agent_url_id: str = Field(
        description="Identifier of the agent that created this data"
    )
    collection: Optional[str] = Field(
        description="Named collection within the agent for data organization"
    )
    data: AgentDataT = Field(description="The structured data payload")
    created_at: Optional[datetime] = Field(description="When this record was created")
    updated_at: Optional[datetime] = Field(
        description="When this record was last modified"
    )

    @classmethod
    def from_raw(
        cls, raw_data: AgentData, validator: Type[AgentDataT]
    ) -> "TypedAgentData[AgentDataT]":
        """
        Convert raw API response to typed agent data.

        Args:
            raw_data: Raw agent data from the API
            validator: Pydantic model class to validate the data field

        Returns:
            TypedAgentData instance with validated data
        """
        data: AgentDataT = validator.model_validate(raw_data.data)

        return cls(
            id=raw_data.id,
            agent_url_id=raw_data.agent_slug,
            collection=raw_data.collection,
            data=data,
            created_at=raw_data.created_at,
            updated_at=raw_data.updated_at,
        )


class TypedAgentDataItems(BaseModel, Generic[AgentDataT]):
    """
    Paginated collection of agent data records.

    This class represents a page of search results from the agent data API,
    providing both the data records and pagination metadata.

    Attributes:
        items: List of agent data records in this page
        total: Total number of records matching the query (only present if requested)
        has_more: Whether there are more records available beyond this page

    Example:
        ```python
        # Search with pagination
        results = await client.search(
            page_size=10,
            include_total=True
        )

        for item in results.items:
            print(item.data.name)

        if results.has_more:
            # Load next page
            next_page = await client.search(
                page_size=10,
                offset=10
            )
        ```
    """

    items: List[TypedAgentData[AgentDataT]] = Field(
        description="List of agent data records in this page"
    )
    total: Optional[int] = Field(
        description="Total number of records matching the query (only present if requested)"
    )
    has_more: bool = Field(
        description="Whether there are more records available beyond this page"
    )


class ExtractedData(BaseModel, Generic[ExtractedT]):
    """
    Wrapper for extracted data with workflow status tracking.

    This class is designed for extraction workflows where data goes through
    review and approval stages. It maintains both the original extracted data
    and the current state after any modifications.

    Attributes:
        original_data: The data as originally extracted from the source
        data: The current state of the data (may differ from original after edits)
        status: Current workflow status (in_review, accepted, rejected, error)
        confidence: Confidence scores for individual fields (if available)
        file_id: The llamacloud file ID of the file that was used to extract the data
        file_name: The name of the file that was used to extract the data
        file_hash: A content hash of the file that was used to extract the data, for de-duplication

    Status Workflow:
        - "pending_review": Initial state, awaiting human review
        - "accepted": Data approved and ready for use
        - "rejected": Data rejected, needs re-extraction or manual fix
        - "error": Processing error occurred

    Example:
        ```python
        # Create extracted data for review
        extracted = ExtractedData.create(
            data=person_data,
            status="pending_review",
            confidence={"name": 0.95, "age": 0.87}
        )

        # Later, after review
        if extracted.status == "accepted":
            # Use the data
            process_person(extracted.data)
        ```
    """

    original_data: ExtractedT = Field(
        description="The original data that was extracted from the document"
    )
    data: ExtractedT = Field(
        description="The latest state of the data. Will differ if data has been updated"
    )
    status: StatusType = Field(description="The status of the extracted data")
    confidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Confidence scores, if any, for each primitive field in the original_data data",
    )
    file_id: Optional[str] = Field(
        None, description="The ID of the file that was used to extract the data"
    )
    file_name: Optional[str] = Field(
        None, description="The name of the file that was used to extract the data"
    )
    file_hash: Optional[str] = Field(
        None, description="The hash of the file that was used to extract the data"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata about the extracted data, such as errors, tokens, etc.",
    )

    @classmethod
    def create(
        cls,
        data: ExtractedT,
        status: StatusType = "pending_review",
        confidence: Optional[Dict[str, Any]] = None,
        file_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ExtractedData[ExtractedT]":
        """
        Create a new ExtractedData instance with sensible defaults.

        Args:
            extracted_data: The extracted data payload
            status: Initial workflow status
            confidence: Optional confidence scores for fields
            file_id: The llamacloud file ID of the file that was used to extract the data
            file_name: The name of the file that was used to extract the data
            file_hash: A content hash of the file that was used to extract the data, for de-duplication

        Returns:
            New ExtractedData instance ready for storage
        """
        return cls(
            original_data=data,
            data=data,
            status=status,
            confidence=confidence or {},
            file_id=file_id,
            file_name=file_name,
            file_hash=file_hash,
            metadata=metadata or {},
        )


class TypedAggregateGroup(BaseModel, Generic[AgentDataT]):
    """
    Represents a group of agent data records aggregated by common field values.

    This class is used for grouping and analyzing agent data based on shared
    characteristics. It's particularly useful for generating summaries and
    statistics across large datasets.

    Attributes:
        group_key: The field values that define this group
        count: Number of records in this group (if count aggregation was requested)
        first_item: Representative data record from this group (if requested)

    Example:
        ```python
        # Group by age range
        groups = await client.aggregate_agent_data(
            group_by=["age_range"],
            count=True,
            first=True
        )

        for group in groups.items:
            print(f"Age range {group.group_key['age_range']}: {group.count} people")
            if group.first_item:
                print(f"Example: {group.first_item.name}")
        ```
    """

    group_key: Dict[str, Any] = Field(
        description="The field values that define this group"
    )
    count: Optional[int] = Field(
        description="Number of records in this group (if count aggregation was requested)"
    )
    first_item: Optional[AgentDataT] = Field(
        description="Representative data record from this group (if requested)"
    )

    @classmethod
    def from_raw(
        cls, raw_data: AggregateGroup, validator: Type[AgentDataT]
    ) -> "TypedAggregateGroup[AgentDataT]":
        """
        Convert raw API response to typed aggregate group.

        Args:
            raw_data: Raw aggregate group from the API
            validator: Pydantic model class to validate the first_item field

        Returns:
            TypedAggregateGroup instance with validated first_item
        """
        first_item: Optional[AgentDataT] = raw_data.first_item
        if first_item is not None:
            first_item = validator.model_validate(first_item)

        return cls(
            group_key=raw_data.group_key,
            count=raw_data.count,
            first_item=first_item,
        )


class TypedAggregateGroupItems(BaseModel, Generic[AgentDataT]):
    """
    Paginated collection of aggregate groups.

    This class represents a page of aggregation results from the agent data API,
    providing both the grouped data and pagination metadata.

    Attributes:
        items: List of aggregate groups in this page
        total: Total number of groups matching the query (only present if requested)
        has_more: Whether there are more groups available beyond this page

    Example:
        ```python
        # Get first page of groups
        results = await client.aggregate_agent_data(
            group_by=["department"],
            count=True,
            page_size=20
        )

        for group in results.items:
            dept = group.group_key["department"]
            print(f"{dept}: {group.count} employees")

        # Load more if needed
        if results.has_more:
            next_page = await client.aggregate_agent_data(
                group_by=["department"],
                count=True,
                page_size=20,
                offset=20
            )
        ```
    """

    items: List[TypedAggregateGroup[AgentDataT]] = Field(
        description="List of aggregate groups in this page"
    )
    total: Optional[int] = Field(
        description="Total number of groups matching the query (only present if requested)"
    )
    has_more: bool = Field(
        description="Whether there are more groups available beyond this page"
    )
