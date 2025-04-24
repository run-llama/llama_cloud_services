import tempfile
import os
import pytest
from llama_cloud_services import LlamaParse
from llama_cloud_services.parse.types import JobResult


@pytest.fixture
def file_path() -> str:
    return "tests/test_files/attention_is_all_you_need.pdf"


@pytest.fixture
def chart_file_path() -> str:
    return "tests/test_files/attention_is_all_you_need_chart.pdf"


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
async def test_basic_parse_result(file_path: str):
    parser = LlamaParse(
        take_screenshot=True,
        auto_mode=True,
        fast_mode=False,
    )
    result = await parser.aparse(file_path)

    assert isinstance(result, JobResult)
    assert result.job_id is not None
    assert result.file_name == file_path
    assert len(result.pages) > 0

    assert result.pages[0].text is not None
    assert len(result.pages[0].text) > 0

    assert result.pages[0].md is not None
    assert len(result.pages[0].md) > 0

    assert result.pages[0].md != result.pages[0].text

    assert len(result.pages[0].images) > 0
    assert result.pages[0].images[0].name is not None

    with tempfile.TemporaryDirectory() as temp_dir:
        file_names = await result.asave_all_images(temp_dir)
        assert len(file_names) > 0
        for file_name in file_names:
            assert os.path.exists(file_name)
            assert os.path.getsize(file_name) > 0

    assert result.job_metadata is not None

    text_documents = result.get_text_documents(
        split_by_page=True,
    )
    assert len(text_documents) > 0
    assert text_documents[0].text is not None
    assert len(text_documents[0].text) > 0

    markdown_documents = result.get_markdown_documents(
        split_by_page=True,
    )
    assert len(markdown_documents) > 0
    assert markdown_documents[0].text is not None
    assert len(markdown_documents[0].text) > 0

    image_documents = await result.aget_image_documents(
        include_screenshot_images=True,
        include_object_images=False,
    )
    assert len(image_documents) > 0
    assert image_documents[0].image is not None
    assert len(image_documents[0].resolve_image().getvalue()) > 0


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="TODO: I don't actually know how to trigger links in the output."
)
async def test_link_parse_result(file_path: str):
    parser = LlamaParse(
        annotate_links=True,
    )
    result = await parser.aparse(file_path)

    assert isinstance(result, JobResult)
    assert len(result.pages) > 0
    assert len(result.pages[0].links) > 0


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
async def test_parse_structured_output(file_path: str):
    parser = LlamaParse(
        structured_output=True,
        structured_output_json_schema_name="imFeelingLucky",
    )
    result = await parser.aparse(file_path)
    assert isinstance(result, JobResult)
    assert len(result.pages) > 0
    assert len(result.pages[0].structuredData) > 0


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
async def test_parse_charts(chart_file_path: str):
    parser = LlamaParse(
        extract_charts=True,
    )
    result = await parser.aparse(chart_file_path)
    assert isinstance(result, JobResult)
    assert len(result.pages) > 0
    assert len(result.pages[0].charts) > 0


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
async def test_parse_layout(file_path: str):
    parser = LlamaParse(
        extract_layout=True,
    )
    result = await parser.aparse(file_path)

    assert isinstance(result, JobResult)
    assert len(result.pages) > 0
    assert len(result.pages[0].layout) > 0


@pytest.mark.skipif(
    os.environ.get("LLAMA_CLOUD_API_KEY", "") == "",
    reason="LLAMA_CLOUD_API_KEY not set",
)
def test_parse_multiple_files(file_path: str, chart_file_path: str):
    parser = LlamaParse()
    result = parser.parse([file_path, chart_file_path])

    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], JobResult)
    assert isinstance(result[1], JobResult)
    assert result[0].file_name == file_path
    assert result[1].file_name == chart_file_path
