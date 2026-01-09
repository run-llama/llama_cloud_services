"""
Agent Data API Schema Definitions

This module provides typed wrappers around the raw LlamaCloud agent data API,
enabling type-safe interactions with agent-generated structured data.

The agent data API serves as a persistent storage system for structured data
produced by LlamaCloud agents (particularly extraction agents). It provides
CRUD operations, search capabilities, filtering, and aggregation functionality
for managing agent-generated data at scale.

Key Concepts:
- Deployment Name: Unique identifier for an agent deployment
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
        deployment_name="my-extraction-agent-xyz"
    )

    # Create typed data
    person = Person(name="John", age=30)
    result = await client.create_agent_data(person)
    print(result.data.name)  # Type-safe access
    ```
"""

from datetime import datetime
from llama_cloud import ExtractRun
from llama_cloud.types.agent_data import AgentData
from llama_cloud.types.aggregate_group import AggregateGroup
from pydantic import BaseModel, Field, ValidationError, model_validator, ConfigDict
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
        deployment_name: Identifier of the agent deployment that created this data
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
    deployment_name: str = Field(
        description="Identifier of the agent deployment that created this data"
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
            deployment_name=raw_data.deployment_name,
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


class BoundingBox(BaseModel):
    """Bounding box coordinates for a citation location on a page."""

    x: float = Field(description="X coordinate of the bounding box origin")
    y: float = Field(description="Y coordinate of the bounding box origin")
    w: float = Field(description="Width of the bounding box")
    h: float = Field(description="Height of the bounding box")


class PageDimensions(BaseModel):
    """Dimensions of a page in the source document."""

    width: float = Field(description="Width of the page")
    height: float = Field(description="Height of the page")


class FieldCitation(BaseModel):
    page: Optional[int] = Field(
        None, description="The page number that the field occurred on"
    )
    matching_text: Optional[str] = Field(
        None,
        description="The original text this field's value was derived from",
    )
    bounding_boxes: Optional[List[BoundingBox]] = Field(
        None,
        description="Bounding boxes indicating where the citation appears on the page",
    )
    page_dimensions: Optional[PageDimensions] = Field(
        None,
        description="Dimensions of the page containing the citation",
    )


class ExtractedFieldMetadata(BaseModel):
    """
    Metadata for an extracted data field, such as confidence, and citation information.
    """

    reasoning: Optional[str] = Field(
        None,
        description="symbol for how the citation/confidence was derived: 'INFERRED FROM TEXT', 'VERBATIM EXTRACTION'",
    )
    confidence: Optional[float] = Field(
        None,
        description="The confidence score for the field, combined with parsing confidence if applicable",
    )
    extraction_confidence: Optional[float] = Field(
        None,
        description="The confidence score for the field based on the extracted text only",
    )
    parsing_confidence: Optional[float] = Field(
        None,
        description="The confidence score for the field based on the parsing/OCR quality",
    )
    citation: Optional[List[FieldCitation]] = Field(
        None,
        description="The citation for the field, including page number and matching text",
    )

    # Forbid unknown keys to avoid swallowing nested dicts
    model_config = ConfigDict(extra="forbid")


ExtractedFieldMetaDataDict = Dict[
    str, Union[ExtractedFieldMetadata, Dict[str, Any], list[Any]]
]


def parse_extracted_field_metadata(
    field_metadata: dict[str, Any],
) -> ExtractedFieldMetaDataDict:
    return {
        k: _parse_extracted_field_metadata_recursive(v)
        for k, v in field_metadata.items()
        if not _is_reasoning_field(k, v) and k not in _ADDITIONAL_ROOT_METADATA_FIELDS
    }


def _is_reasoning_field(field_name: str, field_value: Any) -> bool:
    # There can either be a user specified reasoning field (from the schema), or a reasoning metadata field for the
    # dict of values
    return field_name == "reasoning" and isinstance(field_value, str)


_ADDITIONAL_ROOT_METADATA_FIELDS = {"error"}


def _parse_extracted_field_metadata_recursive(
    field_value: Any,
    additional_fields: dict[str, Any] = {},
) -> Union[ExtractedFieldMetadata, Dict[str, Any], list[Any]]:
    """
    Parse the extracted field metadata into a dictionary of field names to field metadata.
    """

    if isinstance(field_value, ExtractedFieldMetadata):
        # support running this multiple times
        return field_value
    elif isinstance(field_value, dict):
        # reasoning explicitly excluded, as it is included next to subfields, for example
        # "dimensions.width" is a leaf, but there will still potentially be a "dimensions.reasoning"
        indicator_fields = {"confidence", "extraction_confidence", "citation"}
        if len(indicator_fields.intersection(field_value.keys())) > 0:
            try:
                merged = {**field_value, **additional_fields}
                allowed_fields = ExtractedFieldMetadata.model_fields.keys()
                merged = {k: v for k, v in merged.items() if k in allowed_fields}
                validated = ExtractedFieldMetadata.model_validate(merged)

                return validated
            except ValidationError:
                pass
        additional_fields = {
            k: v for k, v in field_value.items() if _is_reasoning_field(k, v)
        }
        return {
            k: _parse_extracted_field_metadata_recursive(v, additional_fields)
            for k, v in field_value.items()
            if not _is_reasoning_field(k, v)
        }
    elif isinstance(field_value, list):
        return [_parse_extracted_field_metadata_recursive(item) for item in field_value]
    else:
        raise ValueError(
            f"Invalid field value: {field_value}. Expected ExtractedFieldMetadata, dict, or list"
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
    overall_confidence: Optional[float] = Field(
        None,
        description="The overall confidence score for the extracted data",
    )
    field_metadata: ExtractedFieldMetaDataDict = Field(
        default_factory=dict,
        description="Page links, and perhaps eventually bounding boxes, for individual fields in the extracted data. Structure is expected to have a ",
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

    @model_validator(mode="before")
    @classmethod
    def _normalize_field_metadata_on_input(cls, value: Any) -> Any:
        # Ensure any inbound representation (including JSON round-trips)
        # gets normalized so nested dicts become ExtractedFieldMetadata where appropriate.
        if (
            isinstance(value, dict)
            and "field_metadata" in value
            and isinstance(value["field_metadata"], dict)
        ):
            try:
                value = {
                    **value,
                    "field_metadata": parse_extracted_field_metadata(
                        value["field_metadata"]
                    ),
                }
            except Exception:
                # Let pydantic surface detailed errors later rather than swallowing completely
                pass
        return value

    @classmethod
    def create(
        cls,
        data: ExtractedT,
        status: StatusType = "pending_review",
        field_metadata: ExtractedFieldMetaDataDict = {},
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
            field_metadata: Optional confidence scores, citations, and other metadata for fields
            file_id: The llamacloud file ID of the file that was used to extract the data
            file_name: The name of the file that was used to extract the data
            file_hash: A content hash of the file that was used to extract the data, for de-duplication
            metadata: Arbitrary additional application-specific data about the extracted data

        Returns:
            New ExtractedData instance ready for storage
        """
        normalized_field_metadata = parse_extracted_field_metadata(field_metadata)
        return cls(
            original_data=data,
            data=data,
            status=status,
            field_metadata=normalized_field_metadata,
            overall_confidence=calculate_overall_confidence(normalized_field_metadata),
            file_id=file_id,
            file_name=file_name,
            file_hash=file_hash,
            metadata=metadata or {},
        )

    @classmethod
    def from_extraction_result(
        cls,
        result: ExtractRun,
        schema: Type[ExtractedT],
        file_hash: Optional[str] = None,
        file_name: Optional[str] = None,
        file_id: Optional[str] = None,
        status: StatusType = "pending_review",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ExtractedData[ExtractedT]":
        """
        Create an ExtractedData instance from an extraction result.
        """
        file_id = file_id or result.file.id
        file_name = file_name or result.file.name
        job_id = result.job_id
        job_field_metadata = result.extraction_metadata.get("field_metadata", {})
        errors = job_field_metadata.get("error", None)
        if not isinstance(errors, str):
            errors = None

        try:
            field_metadata = parse_extracted_field_metadata(job_field_metadata)
        except ValidationError:
            field_metadata = {}

        try:
            data = schema.model_validate(result.data)  # type: ignore
            return cls.create(
                data=data,
                status=status,
                field_metadata=job_field_metadata,
                file_id=file_id,
                file_name=file_name,
                file_hash=file_hash,
                metadata={
                    **({"field_errors": errors} if errors else {}),
                    "job_id": job_id,
                    **(metadata or {}),
                },
            )
        except ValidationError as e:
            invalid_item = ExtractedData[Dict[str, Any]].create(
                data=result.data or {},
                status="error",
                field_metadata=field_metadata,
                metadata={"extraction_error": str(e), **(metadata or {})},
                file_id=file_id,
                file_name=file_name,
                file_hash=file_hash,
            )
            raise InvalidExtractionData(invalid_item) from e


class InvalidExtractionData(Exception):
    """
    Exception raised when the extracted data does not conform to the schema.
    """

    def __init__(self, invalid_item: ExtractedData[Dict[str, Any]]):
        self.invalid_item = invalid_item
        super().__init__("Not able to parse the extracted data, parsed invalid format")


def calculate_overall_confidence(
    metadata: ExtractedFieldMetaDataDict,
) -> Optional[float]:
    """
    Calculate the overall confidence score for the extracted data.
    """
    numerator, denominator = _calculate_overall_confidence_recursive(metadata)
    if denominator == 0:
        return None
    return numerator / denominator


def _calculate_overall_confidence_recursive(
    confidence: Union[ExtractedFieldMetadata, Dict[str, Any], list[Any]],
) -> tuple[float, int]:
    """
    Calculate the overall confidence score for the extracted data.
    """
    if isinstance(confidence, ExtractedFieldMetadata):
        if confidence.confidence is not None:
            return confidence.confidence, 1
        else:
            return 0, 0
    if isinstance(confidence, dict):
        numerator: float = 0
        denominator: int = 0
        for value in confidence.values():
            num, den = _calculate_overall_confidence_recursive(value)
            numerator += num
            denominator += den
        return numerator, denominator
    elif isinstance(confidence, list):
        numerator = 0
        denominator = 0
        for value in confidence:
            num, den = _calculate_overall_confidence_recursive(value)
            numerator += num
            denominator += den
        return numerator, denominator
    else:
        return 0, 0


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
