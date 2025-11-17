This project uses LlamaSheets to extract data from spreadsheets for analysis.

## Current Project Structure

- `data/` - Contains extracted parquet files from LlamaSheets
  - `{name}_region_{N}.parquet` - Table data files
  - `{name}_metadata_{N}.parquet` - Cell metadata files
  - `{name}_job_metadata.json` - Extraction job information
- `scripts/` - Analysis and helper scripts
- `reports/` - Your generated reports and outputs

## Working with LlamaSheets Data

### Understanding the Files

When a spreadsheet is extracted, you'll find:

1. **Table parquet files** (`region_*.parquet`): The actual table data
   - Columns correspond to spreadsheet columns
   - Data types are preserved (dates, numbers, strings, booleans)

2. **Metadata parquet files** (`metadata_*.parquet`): Rich cell-level metadata
   - Formatting: `font_bold`, `font_italic`, `font_size`, `background_color_rgb`
   - Position: `row_number`, `column_number`, `coordinate` (e.g., "A1")
   - Type detection: `data_type`, `is_date_like`, `is_percentage`, `is_currency`
   - Layout: `is_in_first_row`, `is_merged_cell`, `horizontal_alignment`
   - Content: `cell_value`, `raw_cell_value`

3. **Job metadata JSON** (`job_metadata.json`): Overall extraction results
   - `regions[]`: List of extracted regions with IDs, locations, and titles/descriptions
   - `worksheet_metadata[]`: Generated titles and descriptions
   - `status`: Success/failure status

### Key Principles

1. **Use metadata to understand structure**: Bold cells often indicate headers, colors indicate groupings
2. **Validate before analysis**: Check data types, look for missing values
3. **Preserve formatting context**: The metadata tells you what the spreadsheet author emphasized
4. **Save intermediate results**: Store cleaned data as new parquet files

### Common Patterns

**Loading data:**
```python
import pandas as pd

df = pd.read_parquet("data/region_1_Sheet1.parquet")
meta_df = pd.read_parquet("data/metadata_1_Sheet1.parquet")
```

**Finding headers:**
```python
headers = meta_df[meta_df["font_bold"] == True]["cell_value"].tolist()
```

**Finding date columns:**
```python
date_cols = meta_df[meta_df["is_date_like"] == True]["column_number"].unique()
```

## Tools Available

- **Python 3.11+**: For data analysis
- **pandas**: DataFrame manipulation
- **pyarrow**: Parquet file reading
- **matplotlib**: Visualization (optional)

## Guidelines

- Always read the job_metadata.json first to understand what was extracted
- Check both table data and metadata before making assumptions
- Write reusable functions for common operations
- Document any data quality issues discovered
