from datetime import datetime
from typing import Any, Dict

import pytest
from llama_cloud.types.agent_data import AgentData
from llama_cloud.types.aggregate_group import AggregateGroup
from pydantic import BaseModel, ValidationError

from llama_cloud_services.beta.agent_data.schema import (
    ExtractedData,
    TypedAgentData,
    TypedAggregateGroup,
)


# Test data models
class Person(BaseModel):
    name: str
    age: int
    email: str


class Company(BaseModel):
    name: str
    industry: str
    employees: int


def test_typed_agent_data_from_raw():
    """Test TypedAgentData.from_raw class method."""
    raw_data = AgentData(
        id="456",
        agent_slug="extraction-agent",
        collection="employees",
        data={"name": "Jane Smith", "age": 25, "email": "jane@company.com"},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    typed_data = TypedAgentData.from_raw(raw_data, Person)

    assert typed_data.id == "456"
    assert typed_data.agent_url_id == "extraction-agent"
    assert typed_data.collection == "employees"
    assert typed_data.data.name == "Jane Smith"
    assert typed_data.data.age == 25
    assert typed_data.data.email == "jane@company.com"


def test_typed_agent_data_from_raw_validation_error():
    """Test TypedAgentData.from_raw with invalid data."""
    raw_data = AgentData(
        id="789",
        agent_slug="test-agent",
        collection="people",
        data={"name": "Invalid Person", "age": "not_a_number"},  # Invalid age
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    with pytest.raises(ValidationError):
        TypedAgentData.from_raw(raw_data, Person)


def test_extracted_data_create_method():
    """Test ExtractedData.create class method."""
    person = Person(name="Created Person", age=35, email="created@example.com")

    # Test with defaults
    extracted = ExtractedData.create(person)
    assert extracted.original_data == person
    assert extracted.data == person
    assert extracted.status == "pending_review"
    assert extracted.confidence == {}

    # Test with custom values
    extracted_custom = ExtractedData.create(
        person, status="accepted", confidence={"name": 0.99}
    )
    assert extracted_custom.status == "accepted"
    assert extracted_custom.confidence["name"] == 0.99


def test_extracted_data_with_dict():
    """Test ExtractedData with dict data instead of Pydantic model."""
    data_dict = {"name": "Dict Person", "age": 45, "email": "dict@example.com"}

    extracted = ExtractedData[Dict[str, Any]](
        original_data=data_dict, data=data_dict, status="accepted", confidence={}
    )

    assert extracted.original_data["name"] == "Dict Person"
    assert extracted.data["age"] == 45


def test_typed_aggregate_group_from_raw():
    """Test TypedAggregateGroup.from_raw class method."""
    raw_group = AggregateGroup(
        group_key={"industry": "Technology"},
        count=25,
        first_item={"name": "Tech Corp", "industry": "Technology", "employees": 500},
    )

    typed_group = TypedAggregateGroup.from_raw(raw_group, Company)

    assert typed_group.group_key["industry"] == "Technology"
    assert typed_group.count == 25
    assert typed_group.first_item.name == "Tech Corp"
    assert typed_group.first_item.employees == 500
