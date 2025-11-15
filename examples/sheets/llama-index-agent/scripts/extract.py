"""Helper script to extract spreadsheets using LlamaSheets."""

import asyncio
import json
import os
import dotenv
from pathlib import Path

from llama_cloud_services.beta.sheets import LlamaSheets
from llama_cloud_services.beta.sheets.types import (
    SpreadsheetParsingConfig,
    SpreadsheetResultType,
)

dotenv.load_dotenv()


async def extract_spreadsheet(
    file_path: str, output_dir: str = "data", generate_metadata: bool = True
) -> dict:
    """Extract a spreadsheet using LlamaSheets."""

    client = LlamaSheets(
        base_url="https://api.cloud.llamaindex.ai",
        api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
    )

    print(f"Extracting {file_path}...")

    # Extract regions
    config = SpreadsheetParsingConfig(
        sheet_names=None,  # Extract all sheets
        generate_additional_metadata=generate_metadata,
    )

    job_result = await client.aextract_regions(file_path, config=config)

    print(f"Extracted {len(job_result.regions)} region(s)")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get base name for files
    base_name = Path(file_path).stem

    # Save job metadata
    job_metadata_path = output_path / f"{base_name}_job_metadata.json"
    with open(job_metadata_path, "w") as f:
        json.dump(job_result.model_dump(mode="json"), f, indent=2)
    print(f"Saved job metadata to {job_metadata_path}")

    # Download each region
    for idx, region in enumerate(job_result.regions, 1):
        sheet_name = region.sheet_name.replace(" ", "_")

        # Download region data
        region_bytes = await client.adownload_region_result(
            job_id=job_result.id,
            region_id=region.region_id,
            result_type=region.region_type,
        )

        region_path = output_path / f"{base_name}_region_{idx}_{sheet_name}.parquet"
        with open(region_path, "wb") as f:
            f.write(region_bytes)
        print(f"  Table {idx}: {region_path}")

        # Download metadata
        metadata_bytes = await client.adownload_region_result(
            job_id=job_result.id,
            region_id=region.region_id,
            result_type=SpreadsheetResultType.CELL_METADATA,
        )

        metadata_path = output_path / f"{base_name}_metadata_{idx}_{sheet_name}.parquet"
        with open(metadata_path, "wb") as f:
            f.write(metadata_bytes)
        print(f"  Metadata {idx}: {metadata_path}")

    print(f"\nAll files saved to {output_path}/")

    return job_result.model_dump(mode="json")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/extract.py <spreadsheet_file>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    result = asyncio.run(extract_spreadsheet(file_path))
    print(f"\n✅ Extraction complete! Job ID: {result['id']}")
