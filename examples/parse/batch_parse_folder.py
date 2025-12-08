"""
Example: Batch Processing a Folder of PDFs with LlamaParse

This script demonstrates how to process multiple PDFs from a folder
using LlamaParse with controlled concurrency using asyncio and semaphores.

Usage:
    python batch_parse_folder.py --input-dir ./pdfs --max-concurrent 5
"""

import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
import os

from llama_cloud_services import LlamaParse

# Load environment variables from .env file
load_dotenv()


async def parse_single_file(
    parser: LlamaParse,
    file_path: Path,
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """
    Parse a single PDF file with concurrency control.

    Args:
        parser: LlamaParse instance
        file_path: Path to the PDF file
        semaphore: Semaphore to control concurrent requests

    Returns:
        Dictionary with file info and parse result
    """
    async with semaphore:
        try:
            print(f"Starting parse: {file_path.name}")

            result = await parser.aparse(str(file_path))

            print(f"✓ Completed: {file_path.name} ({len(result.pages)} pages)")

            return {
                "file": file_path.name,
                "status": "success",
                "result": result,
                "pages": len(result.pages) if result.pages else 0,
            }
        except Exception as e:
            print(f"✗ Error parsing {file_path.name}: {str(e)}")
            return {
                "file": file_path.name,
                "status": "error",
                "error": str(e),
            }


async def parse_folder(
    input_dir: Path,
    max_concurrent: int = 5,
    api_key: str = None,
) -> List[Dict[str, any]]:
    """
    Parse all PDFs in a folder with controlled concurrency.

    Args:
        input_dir: Directory containing PDF files
        max_concurrent: Maximum number of concurrent parse operations
        api_key: LlamaCloud API key (loaded from .env file)

    Returns:
        List of parse results for each file
    """
    # Find all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return []

    print(f"Found {len(pdf_files)} PDF files to parse")

    # Initialize parser
    parser = LlamaParse(
        api_key=api_key,
        num_workers=1,  # We control concurrency with semaphore
        show_progress=False,  # We'll show our own progress
    )

    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)

    # Create tasks for all files
    tasks = [parse_single_file(parser, pdf_file, semaphore) for pdf_file in pdf_files]

    # Run all tasks concurrently (but limited by semaphore)
    print(
        f"Processing {len(tasks)} files with max {max_concurrent} concurrent operations..."
    )
    start_time = datetime.now()

    results = await asyncio.gather(*tasks)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Process results
    successful = [
        r for r in results if isinstance(r, dict) and r.get("status") == "success"
    ]
    failed = [r for r in results if isinstance(r, dict) and r.get("status") == "error"]

    # Print summary
    print("PARSE SUMMARY \n")
    print(f"Total files: {len(pdf_files)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total time: {duration:.2f} seconds")
    print(f"Average time per file: {duration / len(pdf_files):.2f} seconds")

    if failed:
        print("\nFailed files:")
        for result in failed:
            print(f"  - {result['file']}: {result.get('error', 'Unknown error')}")

    return results


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Batch process PDFs in a folder with LlamaParse"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing PDF files to parse",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum number of concurrent parse operations (default: 5)",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)

    # Validate input directory
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return

    if not input_dir.is_dir():
        print(f"Error: Input path is not a directory: {input_dir}")
        return

    # Get API key from environment (loaded from .env file)
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        print("Error: LLAMA_CLOUD_API_KEY not found. Please set it in your .env file")
        return

    # Run async function
    asyncio.run(
        parse_folder(
            input_dir=input_dir,
            max_concurrent=args.max_concurrent,
            api_key=api_key,
        )
    )


if __name__ == "__main__":
    main()
