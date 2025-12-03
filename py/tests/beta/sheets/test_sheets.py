import os
import tempfile
import pytest
import pandas as pd
from pydantic import ValidationError

from llama_cloud_services.beta.sheets import LlamaSheets
from llama_cloud_services.beta.sheets.types import SpreadsheetParsingConfig


class TestSpreadsheetParsingConfig:
    """Unit tests for SpreadsheetParsingConfig."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = SpreadsheetParsingConfig()
        assert config.flatten_hierarchical_tables is False
        assert config.table_merge_sensitivity == "strong"

    def test_custom_values(self):
        """Test setting custom values for new fields."""
        config = SpreadsheetParsingConfig(
            flatten_hierarchical_tables=True,
            table_merge_sensitivity="weak",
        )
        assert config.flatten_hierarchical_tables is True
        assert config.table_merge_sensitivity == "weak"

    def test_table_merge_sensitivity_validation(self):
        """Test that invalid table_merge_sensitivity values are rejected."""
        with pytest.raises(ValidationError):
            SpreadsheetParsingConfig(table_merge_sensitivity="invalid")

    def test_unknown_fields_ignored(self):
        """Test that unknown fields are silently ignored."""
        config = SpreadsheetParsingConfig(
            unknown_field="test",
            another_unknown=123,
        )
        assert not hasattr(config, "unknown_field")
        assert not hasattr(config, "another_unknown")


@pytest.fixture
def sheets_client():
    """Create a LlamaSheets client for testing."""
    api_key = os.getenv(
        "LLAMA_CLOUD_API_KEY", "llx-3AEorIw5v0lnJPzEOI9xSl0N8yFx3fguw0Zn8QJHzGWmwg5r"
    )
    base_url = os.getenv("LLAMA_CLOUD_BASE_URL", "https://api.staging.llamaindex.ai")

    client = LlamaSheets(
        api_key=api_key,
        base_url=base_url,
        max_timeout=300,
        poll_interval=2,
    )
    return client


@pytest.fixture
def sample_excel_file():
    """Create a temporary Excel file with sample data."""
    # Create a simple dataframe with various data types
    data = {
        "Name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "Age": [25, 30, 35, 40, 45],
        "City": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
        "Salary": [50000.50, 75000.75, 100000.00, 125000.25, 150000.50],
    }
    df = pd.DataFrame(data)

    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
        df.to_excel(tmp_path, index=False, sheet_name="TestSheet")

    yield tmp_path

    # Cleanup
    try:
        os.unlink(tmp_path)
    except Exception:
        pass


@pytest.mark.skipif(
    os.environ.get(
        "LLAMA_CLOUD_API_KEY", "llx-3AEorIw5v0lnJPzEOI9xSl0N8yFx3fguw0Zn8QJHzGWmwg5r"
    )
    == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.asyncio
async def test_spreadsheet_extraction_e2e(
    sheets_client: LlamaSheets, sample_excel_file: str
):
    """End-to-end test for spreadsheet extraction.

    This test:
    1. Creates a temporary Excel file with sample data
    2. Uploads and extracts tables from the file
    3. Downloads the extracted table as a DataFrame
    4. Verifies the extracted data matches the original data
    """
    # Extract tables from the spreadsheet
    result = await sheets_client.aextract_regions(sample_excel_file)

    # Verify job completed successfully
    assert result.status in ("SUCCESS", "PARTIAL_SUCCESS")
    assert result.success is True

    # Verify we extracted at least one table
    assert len(result.regions) > 0, "Expected at least one table to be extracted"

    # Get the first table
    first_table = result.regions[0]
    assert first_table.sheet_name == "TestSheet"

    # Download the table as a DataFrame
    extracted_df = await sheets_client.adownload_region_as_dataframe(
        job_id=result.id,
        region_id=first_table.region_id,
        result_type=first_table.region_type,
    )

    # Load the original dataframe for comparison
    original_df = pd.read_excel(sample_excel_file)

    # Verify the extracted DataFrame has the expected shape
    assert extracted_df.shape[0] == original_df.shape[0], (
        f"Row count mismatch: extracted {extracted_df.shape[0]}, "
        f"original {original_df.shape[0]}"
    )
    assert extracted_df.shape[1] == original_df.shape[1], (
        f"Column count mismatch: extracted {extracted_df.shape[1]}, "
        f"original {original_df.shape[1]}"
    )

    # Verify column names match
    assert list(extracted_df.columns) == list(original_df.columns), (
        f"Column names mismatch: extracted {list(extracted_df.columns)}, "
        f"original {list(original_df.columns)}"
    )

    # Verify data types are preserved (at least numerically)
    for col in original_df.columns:
        if original_df[col].dtype in ["int64", "float64"]:
            assert extracted_df[col].dtype in ["int64", "float64"], (
                f"Column {col} type mismatch: extracted {extracted_df[col].dtype}, "
                f"original {original_df[col].dtype}"
            )

    # Verify the data values match (allowing for minor type conversions)
    for col in original_df.columns:
        original_values = original_df[col].tolist()
        extracted_values = extracted_df[col].tolist()

        # Convert both to strings for comparison to handle type differences
        original_str = [str(v) for v in original_values]
        extracted_str = [str(v) for v in extracted_values]

        assert original_str == extracted_str, (
            f"Column {col} values mismatch:\n"
            f"Original: {original_str}\n"
            f"Extracted: {extracted_str}"
        )


@pytest.mark.skipif(
    os.environ.get(
        "LLAMA_CLOUD_API_KEY", "llx-3AEorIw5v0lnJPzEOI9xSl0N8yFx3fguw0Zn8QJHzGWmwg5r"
    )
    == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.asyncio
async def test_spreadsheet_extraction_with_config(
    sheets_client: LlamaSheets, sample_excel_file: str
):
    """Test spreadsheet extraction with custom configuration."""
    # Create a config with specific settings
    config = SpreadsheetParsingConfig(
        sheet_names=["TestSheet"],
        include_hidden_cells=True,
        generate_additional_metadata=True,
    )

    # Extract tables with the config
    result = await sheets_client.aextract_regions(sample_excel_file, config=config)

    # Verify job completed successfully
    assert result.status in ("SUCCESS", "PARTIAL_SUCCESS")
    assert result.success is True

    # Verify that additional metadata was generated
    assert len(result.worksheet_metadata) > 0
    assert result.worksheet_metadata[0].title is not None
    assert result.worksheet_metadata[0].description is not None

    # Verify we extracted at least one table
    assert len(result.regions) > 0

    # Verify the sheet name matches
    assert result.regions[0].sheet_name == "TestSheet"
