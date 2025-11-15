"""
LlamaSheets Agent with LlamaIndex

This example shows how to build an agent that can work with spreadsheet data
extracted by LlamaSheets using Python code execution.

The agent has minimal tools but maximum flexibility - it can execute arbitrary
pandas code against the extracted data, similar to a coding agent.

NOTE: Code execution should be handled safely in a sandboxed environment for security.
"""

import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import dotenv
import pandas as pd
from llama_index.core.agent import FunctionAgent, ToolCall, ToolCallResult, AgentStream
from llama_index.llms.openai import OpenAI
from workflows import Context

dotenv.load_dotenv()

# Global context for loaded dataframes
_dataframe_context: Dict[str, Any] = {}


# Helper function for initial agent context
def list_extracted_data(data_dir: str = "data") -> str:
    """
    List all regions and metadata files extracted by LlamaSheets.

    This helps discover what data is available to work with.

    Args:
        data_dir: Directory containing extracted parquet files (default: "data")

    Returns:
        JSON string with information about available files
    """
    data_path = Path(data_dir)

    if not data_path.exists():
        return json.dumps({"error": f"Data directory '{data_dir}' not found"})

    # Find all parquet and metadata files
    region_files = list(data_path.glob("*_region_*.parquet"))
    job_metadata_files = list(data_path.glob("*_job_metadata.json"))

    regions = []
    for region_file in region_files:
        # Quick peek at dimensions
        df = pd.read_parquet(region_file)

        # Find corresponding metadata file
        base_name = region_file.stem.replace("_region_", "_metadata_")
        metadata_path = region_file.parent / f"{base_name}.parquet"

        regions.append(
            {
                "region_file": str(region_file),
                "metadata_file": str(metadata_path) if metadata_path.exists() else None,
                "shape": {"rows": len(df), "columns": len(df.columns)},
                "columns": list(df.columns),
            }
        )

    result = {
        "data_directory": str(data_path.absolute()),
        "num_regions": len(regions),
        "regions": regions,
        "job_metadata_files": [str(f) for f in job_metadata_files],
    }

    return json.dumps(result, indent=2)


# Agent tool for code execution against dataframes
def execute_dataframe_code(
    code: str, load_files: Optional[Dict[str, str]] = None
) -> str:
    """
        Execute Python pandas code against LlamaSheets extracted data.

        This tool allows flexible data analysis by executing arbitrary pandas code.
        You can load parquet files, manipulate dataframes, and return results.

        The code executes in a context where:
        - pandas is available as 'pd'
        - json is available for formatting output
        - Previously loaded dataframes are accessible by their variable names

        Args:
            code: Python code to execute. Any print() statements or stdout/stderr
                  will be captured and returned. Optionally set a 'result' variable
                  for structured output.
            load_files: Optional dict mapping variable names to file paths to load
                       Example: {"df": "data/sales_region_1.parquet",
                                "meta": "data/sales_metadata_1.parquet"}

        Returns:
            String containing:
            - Any stdout/stderr output from the code execution
            - The 'result' variable if it was set (formatted appropriately)
            - Error message if execution failed

        Example usage:
            code = '''
    # Load and inspect data
    df = pd.read_parquet("data/sales_region_1.parquet")
    print(f"Loaded {len(df)} rows")

    result = {
        "shape": df.shape,
        "columns": list(df.columns),
        "sample": df.head(3).to_dict(orient="records")
    }
            '''
    """
    global _dataframe_context

    # Capture stdout and stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        # Redirect stdout/stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        # Create execution context with pandas, json, and previously loaded dfs
        exec_context = {
            "pd": pd,
            "json": json,
            "Path": Path,
            **_dataframe_context,  # Include previously loaded dataframes
        }

        # Load any requested files into context
        if load_files:
            for var_name, file_path in load_files.items():
                if file_path.endswith(".parquet"):
                    exec_context[var_name] = pd.read_parquet(file_path)
                    # Also save to global context for future calls
                    _dataframe_context[var_name] = exec_context[var_name]
                elif file_path.endswith(".json"):
                    with open(file_path, "r") as f:
                        exec_context[var_name] = json.load(f)
                        _dataframe_context[var_name] = exec_context[var_name]

        # Execute the code
        exec(code, exec_context)

        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        # Collect output
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        output_parts = []

        # Add stdout if any
        if stdout_output:
            output_parts.append(f"<stdout>{stdout_output}</stdout>")

        # Add stderr if any
        if stderr_output:
            output_parts.append(f"<stderr>{stderr_output}</stderr>")

        # Try to get a result (if code set a 'result' variable)
        if "result" in exec_context:
            result = exec_context["result"]
            result_str = None

            if isinstance(result, pd.DataFrame):
                # Convert DataFrame to readable format
                result_str = result.to_string()
            elif isinstance(result, (dict, list)):
                result_str = json.dumps(result, indent=2, default=str)
            else:
                result_str = str(result)

            if result_str:
                output_parts.append(f"<result_var>{result_str}</result_var>")

        # Return combined output or success message
        if output_parts:
            return "\n\n".join(output_parts)
        else:
            return "Code executed successfully (no output or result)"

    except Exception as e:
        # Restore stdout/stderr in case of error
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        # Get any partial output
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        error_parts = []
        if stdout_output:
            error_parts.append(f"=== STDOUT (before error) ===\n{stdout_output}")
        if stderr_output:
            error_parts.append(f"=== STDERR (before error) ===\n{stderr_output}")

        error_parts.append(f"=== ERROR ===\n{str(e)}")
        error_parts.append(f"\n=== CODE ===\n{code}")

        return "\n\n".join(error_parts)


def create_llamasheets_agent(
    llm_model: str = "gpt-4.1", api_key: Optional[str] = None
) -> FunctionAgent:
    # Initialize LLM
    llm = OpenAI(model=llm_model, api_key=api_key)

    # Create tools - just 4 simple but powerful tools
    tools = [execute_dataframe_code]

    # System prompt to guide the agent
    available_regions = list_extracted_data()
    system_prompt = f"""You are an AI assistant that helps analyze spreadsheet data extracted by LlamaSheets.

LlamaSheets extracts messy spreadsheets into clean parquet files with two types of outputs:
1. Region files (*_region_*.parquet) - The actual data with columns and rows
2. Metadata files (*_metadata_*.parquet) - Rich cell-level metadata including:
   - Formatting: font_bold, font_italic, font_size, background_color_rgb
   - Position: row_number, column_number, coordinate
   - Type detection: data_type, is_date_like, is_percentage, is_currency
   - Layout: is_in_first_row, is_merged_cell, horizontal_alignment

Your approach:
1. Use list_extracted_data() to discover available files
2. Use execute_dataframe_code() to load and analyze data with pandas
3. Use metadata to understand structure (bold = headers, colors = groups)
4. Use save_dataframe() to export results

Key tips:
- Bold cells in metadata often indicate headers
- Background colors often indicate groupings or departments
- Load both region and metadata files for complete analysis
- Write clear pandas code - you have full pandas functionality available
- Store results in variables for reuse across multiple code executions

Existing Processed Regions:
{available_regions}
"""

    # Configure agent
    return FunctionAgent(tools=tools, llm=llm, system_prompt=system_prompt)


async def main():
    """Example of using the LlamaSheets agent."""

    # Create the agent
    agent = create_llamasheets_agent()
    ctx = Context(agent)

    # Example queries the agent can handle:
    queries = [
        # Discovery
        "What spreadsheet data is available?",
        # Simple analysis
        "Load the sales data and show me the first few rows with column info",
        # Using metadata
        "Find all bold cells in the metadata - these are likely headers",
    ]

    # Example: Run a query
    for query in queries:
        print(f"\n=== Query: {query} ===")
        handler = agent.run(query, ctx=ctx)
        async for ev in handler.stream_events():
            if isinstance(ev, ToolCall):
                tool_kwargs_str = (
                    str(ev.tool_kwargs)[:500] + " ..."
                    if len(str(ev.tool_kwargs)) > 500
                    else str(ev.tool_kwargs)
                )
                print(f"\n[Tool Call] {ev.tool_name} with args:\n{tool_kwargs_str}\n\n")
            elif isinstance(ev, ToolCallResult):
                result_str = (
                    str(ev.tool_output)[:500] + " ..."
                    if len(str(ev.tool_output)) > 500
                    else str(ev.tool_output)
                )
                print(f"\n[Tool Result] {ev.tool_name}:\n{result_str}\n\n")
            elif isinstance(ev, AgentStream):
                print(ev.delta, end="", flush=True)

        _ = await handler
        print("=== End Query ===\n")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
