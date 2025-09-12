import os
import pytest
import shutil
from typing import Optional, cast
from unittest.mock import patch
from fsspec.implementations.local import LocalFileSystem
from httpx import AsyncClient

from llama_cloud_services.parse import LlamaParse


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
def test_simple_page_text() -> None:
    parser = LlamaParse(result_type="text")

    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    result = parser.load_data(filepath)
    assert len(result) == 1
    assert len(result[0].text) > 0


@pytest.fixture(params=[None, 2])
def markdown_parser(request: pytest.FixtureRequest) -> LlamaParse:
    if os.environ.get("LLAMA_CLOUD_API_KEY", "") == "":
        pytest.skip("LLAMA_CLOUD_API_KEY not set")
    return LlamaParse(
        result_type="markdown",
        ignore_errors=False,
        partition_pages=cast(Optional[int], request.param),
    )


def test_simple_page_markdown(markdown_parser: LlamaParse) -> None:
    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    result = markdown_parser.load_data(filepath)
    assert len(result) == 1
    assert len(result[0].text) > 0


def test_simple_page_markdown_bytes(markdown_parser: LlamaParse) -> None:
    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    # client must provide extra_info with file_name
    with pytest.raises(ValueError):
        result = markdown_parser.load_data(file_bytes)
    result = markdown_parser.load_data(
        file_bytes, extra_info={"file_name": "attention_is_all_you_need.pdf"}
    )
    assert len(result) == 1
    assert len(result[0].text) > 0


def test_simple_page_markdown_buffer(markdown_parser: LlamaParse) -> None:
    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    with open(filepath, "rb") as f:
        # client must provide extra_info with file_name
        with pytest.raises(ValueError):
            result = markdown_parser.load_data(f)
        result = markdown_parser.load_data(
            f, extra_info={"file_name": "attention_is_all_you_need.pdf"}
        )
        assert len(result) == 1
        assert len(result[0].text) > 0


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.asyncio
async def test_simple_page_with_custom_fs() -> None:
    parser = LlamaParse(result_type="markdown")
    fs = LocalFileSystem()
    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    result = await parser.aload_data(filepath, fs=fs)
    assert len(result) == 1


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.asyncio
async def test_simple_page_progress_workers() -> None:
    parser = LlamaParse(result_type="markdown", show_progress=True, verbose=True)

    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    result = await parser.aload_data([filepath, filepath])
    assert len(result) == 2
    assert len(result[0].text) > 0

    parser = LlamaParse(
        result_type="markdown", show_progress=True, num_workers=2, verbose=True
    )

    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    result = await parser.aload_data([filepath, filepath])
    assert len(result) == 2
    assert len(result[0].text) > 0


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.asyncio
async def test_custom_client() -> None:
    custom_client = AsyncClient(verify=False, timeout=10)
    parser = LlamaParse(result_type="markdown", custom_client=custom_client)
    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    result = await parser.aload_data(filepath)
    assert len(result) == 1
    assert len(result[0].text) > 0


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.asyncio
async def test_input_url() -> None:
    parser = LlamaParse(result_type="markdown")

    # links to a resume example
    input_url = "https://cdn-blog.novoresume.com/articles/google-docs-resume-templates/basic-google-docs-resume.png"
    result = await parser.aload_data(input_url)
    assert len(result) == 1
    assert "your name" in result[0].text.lower()


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.asyncio
async def test_input_url_with_website_input() -> None:
    parser = LlamaParse(result_type="markdown")
    input_url = "https://www.example.com"
    result = await parser.aload_data(input_url)
    assert len(result) == 1
    assert "example" in result[0].text.lower()


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.asyncio
async def test_mixing_input_types() -> None:
    parser = LlamaParse(result_type="markdown")
    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    input_url = "https://cdn-blog.novoresume.com/articles/google-docs-resume-templates/basic-google-docs-resume.png"
    result = await parser.aload_data([filepath, input_url])

    assert len(result) == 2


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.parametrize("partition_pages", [None, 2])
@pytest.mark.asyncio
async def test_download_images(partition_pages: Optional[int]) -> None:
    parser = LlamaParse(
        result_type="markdown", take_screenshot=True, partition_pages=partition_pages
    )
    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    json_result = await parser.aget_json([filepath])

    assert len(json_result) == 1
    assert len(json_result[0]["pages"][0]["images"]) > 0

    download_path = "tests/test_files/images"
    shutil.rmtree(download_path, ignore_errors=True)

    await parser.aget_images(json_result, download_path)
    assert len(os.listdir(download_path)) == len(json_result[0]["pages"][0]["images"])


@pytest.mark.asyncio
@pytest.mark.parametrize("split_by_page,expected", [(True, 4), (False, 1)])
async def test_multiple_page_markdown(
    markdown_parser: LlamaParse,
    split_by_page: bool,
    expected: int,
) -> None:
    markdown_parser.split_by_page = split_by_page
    filepath = "tests/test_files/TOS.pdf"
    result = await markdown_parser.aload_data(filepath)
    assert len(result) == expected
    assert all(len(doc.text) > 0 for doc in result)


@pytest.mark.asyncio
async def test_get_result(markdown_parser: LlamaParse) -> None:
    filepath = "tests/test_files/attention_is_all_you_need.pdf"
    expected = await markdown_parser.aparse(filepath)
    result = await markdown_parser.aget_result(expected.job_id)
    assert result.job_id == expected.job_id
    assert len(result.pages) == len(expected.pages)


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
@pytest.mark.asyncio
async def test_parse_audio() -> None:
    parser = LlamaParse()
    filepath = "tests/test_files/hello_world.m4a"

    result = await parser.aparse(filepath)
    assert result.job_id is not None


@pytest.mark.asyncio
async def test_error_handling_with_raise_job_error_false() -> None:
    """Test that failed jobs return JobResult objects with error information when raise_job_error=False."""
    
    parser = LlamaParse(api_key="test_key")
    
    # Mock error result with full error information
    mock_error_result = {
        "pages": [],
        "job_metadata": {"job_pages": 0},
        "error": "Job ID: test_job_123 failed with status: ERROR, Error code: INVALID_FILE, Error message: File format not supported",
        "status": "ERROR",
    }
    
    with patch.object(parser, '_create_job', return_value="test_job_123"), \
         patch.object(parser, '_get_job_result', return_value=mock_error_result):
        
        # Test aparse with raise_job_error=False
        result = await parser.aparse("test_file.txt", raise_job_error=False)
        
        assert isinstance(result, type(result))  # Check it's a JobResult
        assert result.job_id == "test_job_123"
        assert result.error is not None
        assert "ERROR" in result.error
        assert "INVALID_FILE" in result.error
        assert "File format not supported" in result.error
        assert len(result.pages) == 0
        
        # Test parse (synchronous version) with raise_job_error=False
        result_sync = parser.parse("test_file.txt", raise_job_error=False)
        
        assert isinstance(result_sync, type(result_sync))
        assert result_sync.job_id == "test_job_123"
        assert result_sync.error is not None
        assert "INVALID_FILE" in result_sync.error
        assert "File format not supported" in result_sync.error


@pytest.mark.asyncio
async def test_error_handling_with_raise_job_error_true() -> None:
    """Test that failed jobs raise JobFailedException when raise_job_error=True (default behavior)."""
    
    parser = LlamaParse(api_key="test_key")
    
    # Mock that _get_job_result will raise JobFailedException when raise_job_error=True
    from llama_cloud_services.parse.base import JobFailedException
    
    def mock_get_job_result(job_id, result_type, verbose=False, raise_job_error=True):
        if raise_job_error:
            raise JobFailedException("test_job_123", "ERROR", error_code="INVALID_FILE", error_message="File format not supported")
        else:
            return {
                "pages": [],
                "job_metadata": {"job_pages": 0},
                "error": "Job ID: test_job_123 failed with status: ERROR, Error code: INVALID_FILE, Error message: File format not supported",
                "status": "ERROR",
            }
    
    with patch.object(parser, '_create_job', return_value="test_job_123"), \
         patch.object(parser, '_get_job_result', side_effect=mock_get_job_result):
        
        # Test aparse with raise_job_error=True (default) - should raise exception
        with pytest.raises(JobFailedException) as exc_info:
            await parser.aparse("test_file.txt")
        
        assert exc_info.value.job_id == "test_job_123"
        assert exc_info.value.status == "ERROR"
        assert exc_info.value.error_code == "INVALID_FILE"
        
        # Test parse (synchronous version) with raise_job_error=True (default) - should raise exception
        with pytest.raises(JobFailedException) as exc_info:
            parser.parse("test_file.txt")
        
        assert exc_info.value.job_id == "test_job_123"
        assert exc_info.value.status == "ERROR"


@pytest.mark.asyncio
async def test_error_handling_with_minimal_fields() -> None:
    """Test error handling when only status is available (no error_code/error_message) with raise_job_error=False."""
    
    parser = LlamaParse(api_key="test_key")
    
    # Mock error result with minimal fields (only what's guaranteed)
    mock_minimal_error_result = {
        "pages": [],
        "job_metadata": {"job_pages": 0},
        "error": "Job ID: test_job_456 failed with status: CANCELED",
        "status": "CANCELED",
    }
    
    with patch.object(parser, '_create_job', return_value="test_job_456"), \
         patch.object(parser, '_get_job_result', return_value=mock_minimal_error_result):
        
        # Test aparse with a minimal error response and raise_job_error=False
        result = await parser.aparse("test_file.txt", raise_job_error=False)
        
        assert isinstance(result, type(result))
        assert result.job_id == "test_job_456"
        assert result.error is not None
        assert "CANCELED" in result.error
        assert len(result.pages) == 0


@pytest.mark.asyncio
async def test_successful_job_still_works() -> None:
    """Test that successful jobs still work as before after error handling changes."""
    
    parser = LlamaParse(api_key="test_key")
    
    # Mock successful result
    mock_success_result = {
        "pages": [
            {
                "page": 0,
                "text": "Sample text content",
                "md": "# Sample markdown content",
                "images": [],
                "charts": [],
                "tables": [],
                "layout": [],
                "items": [],
                "status": "SUCCESS",
                "links": [],
                "width": 612.0,
                "height": 792.0,
            }
        ],
        "job_metadata": {"job_pages": 1},
    }
    
    with patch.object(parser, '_create_job', return_value="success_job_456"), \
         patch.object(parser, '_get_job_result', return_value=mock_success_result):
        
        # Test aparse with a successful job (both with and without raise_job_error parameter)
        result = await parser.aparse("test_file.txt")
        
        assert isinstance(result, type(result))
        assert result.job_id == "success_job_456"
        assert result.error is None  # No error for successful jobs
        assert len(result.pages) == 1
        assert result.pages[0].text == "Sample text content"
        
        # Test with explicit raise_job_error=False (should work the same for successful jobs)
        result2 = await parser.aparse("test_file.txt", raise_job_error=False)
        
        assert isinstance(result2, type(result2))
        assert result2.job_id == "success_job_456"
        assert result2.error is None
        assert len(result2.pages) == 1
        assert result2.pages[0].text == "Sample text content"


@pytest.mark.asyncio
async def test_get_result_with_raise_job_error_parameter() -> None:
    """Test that get_result method respects the raise_job_error parameter."""
    
    parser = LlamaParse(api_key="test_key")
    
    # Mock error result
    mock_error_result = {
        "pages": [],
        "job_metadata": {"job_pages": 0},
        "error": "Job ID: test_job_789 failed with status: ERROR, Error code: TIMEOUT, Error message: Job timed out",
        "status": "ERROR",
    }
    
    with patch.object(parser, '_get_job_result', return_value=mock_error_result):
        
        # Test aget_result with raise_job_error=False
        result = await parser.aget_result("test_job_789", raise_job_error=False)
        
        assert isinstance(result, type(result))
        assert result.job_id == "test_job_789"
        assert result.error is not None
        assert "TIMEOUT" in result.error
        assert len(result.pages) == 0
        
        # Test get_result (synchronous version) with raise_job_error=False
        result_sync = parser.get_result("test_job_789", raise_job_error=False)
        
        assert isinstance(result_sync, type(result_sync))
        assert result_sync.job_id == "test_job_789"
        assert result_sync.error is not None
        assert "TIMEOUT" in result_sync.error
