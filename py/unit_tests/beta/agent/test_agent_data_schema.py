from datetime import datetime
from typing import Any, Dict

import pytest
from llama_cloud import ExtractRun, File
from llama_cloud.types.agent_data import AgentData
from llama_cloud.types.aggregate_group import AggregateGroup
from pydantic import BaseModel, ValidationError

from llama_cloud_services.beta.agent_data.schema import (
    ExtractedData,
    ExtractedFieldMetadata,
    InvalidExtractionData,
    TypedAgentData,
    TypedAggregateGroup,
    calculate_overall_confidence,
    parse_extracted_field_metadata,
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
    assert extracted.field_metadata == {}
    assert extracted.overall_confidence is None

    # Test with custom values using ExtractedFieldMetadata
    field_metadata = {
        "name": ExtractedFieldMetadata(confidence=0.99, page_number=1),
        "age": ExtractedFieldMetadata(confidence=0.85, page_number=1),
    }
    extracted_custom = ExtractedData.create(
        person, status="accepted", field_metadata=field_metadata
    )
    assert extracted_custom.status == "accepted"
    assert extracted_custom.field_metadata["name"].confidence == 0.99
    assert extracted_custom.field_metadata["age"].confidence == 0.85
    assert extracted_custom.overall_confidence == pytest.approx((0.99 + 0.85) / 2)


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


def test_calculate_overall_confidence_simple_flat():
    """Test calculate_overall_confidence with simple flat dictionary of ExtractedFieldMetadata."""
    field_metadata = {
        "name": ExtractedFieldMetadata(confidence=0.9),
        "age": ExtractedFieldMetadata(confidence=0.8),
        "email": ExtractedFieldMetadata(confidence=0.95),
    }
    result = calculate_overall_confidence(field_metadata)
    expected = (0.9 + 0.8 + 0.95) / 3
    assert result == pytest.approx(expected, rel=1e-9)


def test_calculate_overall_confidence_nested():
    """Test calculate_overall_confidence with nested dictionary structure."""
    field_metadata = {
        "person": {
            "name": ExtractedFieldMetadata(confidence=0.9),
            "age": ExtractedFieldMetadata(confidence=0.8),
        },
        "contact": {
            "email": ExtractedFieldMetadata(confidence=0.95),
            "phone": ExtractedFieldMetadata(confidence=0.85),
        },
        "score": ExtractedFieldMetadata(confidence=0.7),
    }
    result = calculate_overall_confidence(field_metadata)
    # Should average all leaf values: (0.9 + 0.8 + 0.95 + 0.85 + 0.7) / 5
    expected = (0.9 + 0.8 + 0.95 + 0.85 + 0.7) / 5
    assert result == pytest.approx(expected, rel=1e-9)


def test_calculate_overall_confidence_with_lists():
    """Test calculate_overall_confidence with lists of ExtractedFieldMetadata and nested structures."""
    field_metadata = {
        "scores": [
            ExtractedFieldMetadata(confidence=0.9),
            ExtractedFieldMetadata(confidence=0.8),
            ExtractedFieldMetadata(confidence=0.95),
        ],
        "nested_data": [
            {
                "field1": ExtractedFieldMetadata(confidence=0.7),
                "field2": ExtractedFieldMetadata(confidence=0.6),
            },
            {
                "field1": ExtractedFieldMetadata(confidence=0.8),
                "field2": ExtractedFieldMetadata(confidence=0.9),
            },
        ],
        "single_value": ExtractedFieldMetadata(confidence=0.85),
    }
    result = calculate_overall_confidence(field_metadata)
    # Should count: [0.9, 0.8, 0.95] + [0.7, 0.6, 0.8, 0.9] + [0.85] = 8 values
    expected = (0.9 + 0.8 + 0.95 + 0.7 + 0.6 + 0.8 + 0.9 + 0.85) / 8
    assert result == pytest.approx(expected, rel=1e-9)


def test_calculate_overall_confidence_invalid_types():
    """Test calculate_overall_confidence with invalid/mixed types alongside valid ExtractedFieldMetadata."""
    field_metadata = {
        "valid_metadata": ExtractedFieldMetadata(confidence=0.8),
        "valid_metadata_no_confidence": ExtractedFieldMetadata(),  # No confidence
        "valid_list": [
            ExtractedFieldMetadata(confidence=0.5),
            ExtractedFieldMetadata(confidence=0.6),
        ],
        "invalid_string": "not_a_number",
        "invalid_list_mixed": [
            ExtractedFieldMetadata(confidence=0.7),
            "invalid",
            ExtractedFieldMetadata(confidence=0.8),
        ],
        "invalid_none": None,
        "random_dict": {"a": 1, "b": 2},
    }
    result = calculate_overall_confidence(field_metadata)
    expected = (0.8 + 0.5 + 0.6 + 0.7 + 0.8) / 5
    assert result == pytest.approx(expected, rel=1e-9)


def test_calculate_overall_confidence_empty():
    """Test calculate_overall_confidence with empty inputs."""
    # Empty dict
    assert calculate_overall_confidence({}) is None

    # Empty list
    assert calculate_overall_confidence([]) is None

    # Dict with only invalid values
    field_metadata_invalid = {"invalid": "not_a_number", "also_invalid": None}
    assert calculate_overall_confidence(field_metadata_invalid) is None

    # List with only invalid values
    field_metadata_invalid_list = ["invalid", None, {}]
    assert calculate_overall_confidence(field_metadata_invalid_list) is None

    # Dict with ExtractedFieldMetadata but no confidence values
    field_metadata_no_confidence = {
        "field1": ExtractedFieldMetadata(),
        "field2": ExtractedFieldMetadata(),
    }
    assert calculate_overall_confidence(field_metadata_no_confidence) is None


def test_parse_extracted_field_metadata():
    """Test parse_extracted_field_metadata with legacy citation format."""
    raw_metadata = {
        "name": {
            "confidence": 0.95,
            "citation": [{"page": 1, "matching_text": "John Smith"}],
        },
        "age": {
            "confidence": 0.87,
            "citation": [
                {
                    "page": 2.0,  # Float page number
                    "matching_text": "25 years old",
                }
            ],
        },
        "email": {
            "confidence": 0.92,
            "citation": [],  # Empty citations
        },
    }

    result = parse_extracted_field_metadata(raw_metadata)
    result2 = parse_extracted_field_metadata(result)
    assert result2 == result

    # name should have parsed citation data
    assert isinstance(result["name"], ExtractedFieldMetadata)
    assert result["name"].confidence == 0.95
    assert result["name"].page_number == 1
    assert result["name"].matching_text == "John Smith"

    # age should handle float page number
    assert isinstance(result["age"], ExtractedFieldMetadata)
    assert result["age"].confidence == 0.87
    assert result["age"].page_number == 2  # Should be converted to int
    assert result["age"].matching_text == "25 years old"

    # email should handle empty citations
    assert isinstance(result["email"], ExtractedFieldMetadata)
    assert result["email"].confidence == 0.92


def test_parse_extracted_field_metadata_complex():
    """Test parse_extracted_field_metadata with new citation format and reasoning field."""
    raw_metadata = {
        "title": {
            "reasoning": "Combined key parametrics and construction from the datasheet for a structured title.",
            "citation": [
                {
                    "page": 1,
                    "matching_text": "PHE844/F844, Film, Metallized Polypropylene, Safety, 0.47 uF",
                }
            ],
            "extraction_confidence": 0.9470628580889779,
            "confidence": 0.9470628580889779,
        },
        "manufacturer": {
            "reasoning": "VERBATIM EXTRACTION",
            "citation": [{"page": 1, "matching_text": "YAGEO KEMET"}],
            "extraction_confidence": 0.9997446550976602,
            "confidence": 0.9997446550976602,
        },
        "features": [
            {
                "reasoning": "VERBATIM EXTRACTION",
                "citation": [
                    {"page": 1, "matching_text": "Features</td><td>EMI Safety"}
                ],
                "extraction_confidence": 0.9999308195540074,
                "confidence": 0.9999308195540074,
            },
            {
                "reasoning": "VERBATIM EXTRACTION",
                "citation": [
                    {"page": 1, "matching_text": "THB Performance</td><td>Yes"}
                ],
                "extraction_confidence": 0.8642493886452225,
                "confidence": 0.8642493886452225,
            },
        ],
        "dimensions": {
            "length": {
                "citation": [{"page": 1, "matching_text": "L</td><td>41mm MAX"}],
                "extraction_confidence": 0.8986941382802304,
                "confidence": 0.8986941382802304,
            },
            "width": {
                "citation": [{"page": 1, "matching_text": "T</td><td>13mm MAX"}],
                "extraction_confidence": 0.9999377974447091,
                "confidence": 0.9999377974447091,
            },
            "reasoning": "VERBATIM EXTRACTION",
        },
    }

    result = parse_extracted_field_metadata(raw_metadata)
    assert result == {
        "title": ExtractedFieldMetadata(
            reasoning="Combined key parametrics and construction from the datasheet for a structured title.",
            confidence=0.9470628580889779,
            extraction_confidence=0.9470628580889779,
            page_number=1,
            matching_text="PHE844/F844, Film, Metallized Polypropylene, Safety, 0.47 uF",
        ),
        "manufacturer": ExtractedFieldMetadata(
            reasoning="VERBATIM EXTRACTION",
            confidence=0.9997446550976602,
            extraction_confidence=0.9997446550976602,
            page_number=1,
            matching_text="YAGEO KEMET",
        ),
        "features": [
            ExtractedFieldMetadata(
                reasoning="VERBATIM EXTRACTION",
                confidence=0.9999308195540074,
                extraction_confidence=0.9999308195540074,
                page_number=1,
                matching_text="Features</td><td>EMI Safety",
            ),
            ExtractedFieldMetadata(
                reasoning="VERBATIM EXTRACTION",
                confidence=0.8642493886452225,
                extraction_confidence=0.8642493886452225,
                page_number=1,
                matching_text="THB Performance</td><td>Yes",
            ),
        ],
        "dimensions": {
            "length": ExtractedFieldMetadata(
                reasoning="VERBATIM EXTRACTION",
                confidence=0.8986941382802304,
                extraction_confidence=0.8986941382802304,
                page_number=1,
                matching_text="L</td><td>41mm MAX",
            ),
            "width": ExtractedFieldMetadata(
                reasoning="VERBATIM EXTRACTION",
                confidence=0.9999377974447091,
                extraction_confidence=0.9999377974447091,
                page_number=1,
                matching_text="T</td><td>13mm MAX",
            ),
        },
    }


def create_file(
    id: str = "file-456",
    name: str = "resume.pdf",
    external_file_id: str = "external-file-id",
    project_id: str = "project-123",
) -> File:
    return File.parse_obj(
        {
            "id": id,
            "name": name,
            "external_file_id": external_file_id,
            "project_id": project_id,
        }
    )


def create_extract_run(
    id: str = "extract-123",
    data: Dict[str, Any] = {"name": "John Doe", "age": 30, "email": "john@example.com"},
    extraction_metadata: Dict[str, Any] = {
        "name": {
            "confidence": 0.95,
            "citation": [{"page": 1, "matching_text": "John Doe"}],
        },
        "age": {"confidence": 0.87},
        "email": {
            "confidence": 0.92,
            "citation": [{"page": 1, "matching_text": "john@example.com"}],
        },
    },
    data_schema: Dict[str, Any] = {},
    file: File = create_file(),
) -> ExtractRun:
    return ExtractRun.parse_obj(
        {
            "id": id,
            "data": data,
            "extraction_metadata": {
                "field_metadata": extraction_metadata,
            },
            "data_schema": data_schema,
            "file": file,
            "extraction_agent_id": "extraction-agent-123",
            "config": {},
            "status": "SUCCESS",
            "from_ui": False,
        }
    )


def test_extracted_data_from_extraction_result_success():
    """Test ExtractedData.from_extraction_result with valid data."""
    # Create mock ExtractRun with valid data
    extract_run = create_extract_run(
        file=create_file(id="file-456", name="resume.pdf"),
    )

    # Create with file object
    extracted: ExtractedData[Person] = ExtractedData.from_extraction_result(
        extract_run,
        Person,
        file_hash="abc123",
        status="accepted",
    )

    # Verify the extracted data
    assert isinstance(extracted.data, Person)
    assert extracted.data.name == "John Doe"
    assert extracted.data.age == 30
    assert extracted.data.email == "john@example.com"
    assert extracted.status == "accepted"
    assert extracted.file_id == "file-456"
    assert extracted.file_name == "resume.pdf"
    assert extracted.file_hash == "abc123"

    # Verify field metadata was parsed
    assert isinstance(extracted.field_metadata["name"], ExtractedFieldMetadata)
    assert extracted.field_metadata["name"].confidence == 0.95
    assert extracted.field_metadata["name"].page_number == 1
    assert extracted.field_metadata["name"].matching_text == "John Doe"

    # Verify overall confidence was calculated
    expected_confidence = (0.95 + 0.87 + 0.92) / 3
    assert extracted.overall_confidence == pytest.approx(expected_confidence)


def test_extracted_data_from_extraction_result_with_file_params():
    """Test ExtractedData.from_extraction_result with explicit file parameters."""
    extract_run = create_extract_run(
        file=create_file(id="original-file", name="original.pdf"),
    )

    # Override file parameters
    extracted: ExtractedData[Person] = ExtractedData.from_extraction_result(
        extract_run,
        Person,
        file_id="custom-file-id",  # Should override file.id
        file_name="custom-name.pdf",  # Should override file.name
        file_hash="custom-hash",
        metadata={"source": "api_test"},
    )

    assert extracted.file_id == "custom-file-id"  # Overridden
    assert extracted.file_name == "custom-name.pdf"  # Overridden
    assert extracted.file_hash == "custom-hash"
    assert extracted.metadata["source"] == "api_test"


def test_extracted_data_from_extraction_result_invalid_data():
    """Test ExtractedData.from_extraction_result with invalid data raises custom exception."""
    # Create ExtractRun with data that doesn't match Person schema
    extract_run = create_extract_run(
        data={
            "name": "Valid Name",
            "age": "not_a_number",
            "missing_email": True,
        },  # Invalid age, missing email
        extraction_metadata={
            "name": {"confidence": 0.9},
        },
        data_schema={},
        file=create_file(id="error-file", name="bad_data.pdf"),
    )

    # Should raise InvalidExtractionData with ExtractedData containing error info
    with pytest.raises(InvalidExtractionData) as exc_info:
        ExtractedData.from_extraction_result(
            extract_run, Person, metadata={"test": "metadata"}
        )

    # Verify the exception contains the invalid ExtractedData
    invalid_data = exc_info.value.invalid_item
    assert isinstance(invalid_data, ExtractedData)
    assert invalid_data.status == "error"
    assert invalid_data.data == {
        "name": "Valid Name",
        "age": "not_a_number",
        "missing_email": True,
    }
    assert invalid_data.file_id == "error-file"
    assert invalid_data.file_name == "bad_data.pdf"

    # Check error metadata was added
    assert "extraction_error" in invalid_data.metadata
    assert "test" in invalid_data.metadata  # Original metadata preserved
    assert "2 validation errors" in invalid_data.metadata["extraction_error"]

    # Verify field metadata was still parsed (before validation failed)
    assert isinstance(invalid_data.field_metadata["name"], ExtractedFieldMetadata)
    assert invalid_data.field_metadata["name"].confidence == 0.9
    assert invalid_data.overall_confidence == 0.9
