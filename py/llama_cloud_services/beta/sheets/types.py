from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpreadsheetResultType(str, Enum):
    TABLE = "table"
    EXTRA = "extra"
    CELL_METADATA = "cell_metadata"

    def __str__(self) -> str:
        return self.value


class ExtractedRegionSummary(BaseModel):
    """A summary of a single extracted region from a spreadsheet"""

    region_id: str = Field(
        ...,
        description="Unique identifier for this region within the file",
    )
    sheet_name: str = Field(..., description="Worksheet name where region was found")
    location: str = Field(..., description="Location of the region in the spreadsheet")
    title: str | None = Field(None, description="Generated title for the region")
    description: str | None = Field(
        None, description="Generated description of the region"
    )
    region_type: SpreadsheetResultType = Field(
        ..., description="Type of the extracted region"
    )


class WorksheetMetadata(BaseModel):
    """Metadata about a worksheet in a spreadsheet"""

    sheet_name: str = Field(..., description="Name of the worksheet")
    title: str | None = Field(None, description="Generated title for the worksheet")
    description: str | None = Field(
        None, description="Generated description of the worksheet"
    )


class SpreadsheetParseResult(BaseModel):
    """Result of parsing a single spreadsheet file"""

    success: bool = Field(..., description="Whether parsing was successful")
    file_name: str = Field(..., description="Original filename")

    regions: list[ExtractedRegionSummary] = Field(
        default_factory=list, description="All successfully extracted regions"
    )
    worksheet_metadata: list[WorksheetMetadata] = Field(
        default_factory=list, description="Metadata for each processed worksheet"
    )

    # Error information
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered during parsing"
    )


class SpreadsheetParsingConfig(BaseModel):
    """Configuration for spreadsheet parsing and region extraction"""

    model_config = ConfigDict(extra="ignore")

    sheet_names: list[str] | None = Field(
        default=None,
        description="The names of the sheets to extract regions from. If empty, the default sheet is extracted.",
    )
    include_hidden_cells: bool = Field(
        default=True,
        description="Whether to include hidden cells when extracting regions from the spreadsheet.",
    )
    extraction_range: str | None = Field(
        default=None,
        description="A1 notation of the range to extract a single region from. If None, the entire sheet is used.",
    )
    generate_additional_metadata: bool = Field(
        default=True,
        description="Whether to generate additional metadata (title, description) for each extracted region.",
    )
    use_experimental_processing: bool = Field(
        default=False,
        description="Enables experimental processing. Accuracy may be impacted.",
    )

    flatten_hierarchical_tables: bool = Field(
        default=False,
        description="Return a flattened dataframe when a detected table is recognized as hierarchical.",
    )

    table_merge_sensitivity: Literal["strong", "weak"] = Field(
        default="strong",
        description="Influences how likely similar-looking regions are merged into a single table. Useful for spreadsheets that either have sparse tables (strong merging) or many distinct tables close together (weak merging).",
    )


class SpreadsheetJob(BaseModel):
    """A spreadsheet parsing job"""

    id: str = Field(..., description="The ID of the job")
    user_id: str = Field(..., description="The ID of the user")
    project_id: str = Field(..., description="The ID of the project")
    file: dict = Field(..., description="The file object being parsed")
    config: SpreadsheetParsingConfig = Field(
        ..., description="Configuration for the parsing job"
    )
    status: str = Field(..., description="The status of the parsing job")
    created_at: str = Field(..., description="When the job was created")
    updated_at: str = Field(..., description="When the job was last updated")

    @field_validator("created_at", "updated_at", mode="before")
    def validate_dates(cls, v: str) -> str:
        """Validate that the dates are in the correct format"""
        if isinstance(v, datetime):
            return v.isoformat()
        else:
            return v


class SpreadsheetJobResult(SpreadsheetJob):
    """A spreadsheet parsing job result."""

    # Results are included when the job is complete
    success: bool | None = Field(
        None, description="Whether the job completed successfully"
    )
    regions: list[ExtractedRegionSummary] = Field(
        default_factory=list,
        description="All extracted regions (populated when job is complete)",
    )
    worksheet_metadata: list[WorksheetMetadata] = Field(
        default_factory=list,
        description="Metadata for each processed worksheet (populated when job is complete)",
    )
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered"
    )


class JobStatus(str, Enum):
    """Status of a spreadsheet parsing job"""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    ERROR = "ERROR"
    FAILURE = "FAILURE"


class PresignedUrlResponse(BaseModel):
    """Response containing a presigned URL for downloading results"""

    url: str = Field(..., description="The presigned URL for downloading")


class FileUploadResponse(BaseModel):
    """Response from uploading a file"""

    id: str = Field(..., description="The ID of the uploaded file")
    name: str = Field(..., description="The name of the file")
    project_id: str = Field(..., description="The project ID")
    user_id: str = Field(..., description="The user ID")
