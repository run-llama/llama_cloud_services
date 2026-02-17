import os
import shutil
import uuid
import pytest
from pathlib import Path
from pydantic import BaseModel

from llama_cloud_services.extract import LlamaExtract, ExtractionAgent, SourceText
from llama_cloud.types import ExtractConfig, ExtractMode, ExtractRun
from tests.extract.util import load_test_dotenv
from .conftest import create_agent_with_retry

load_test_dotenv()

# Get configuration from environment
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
LLAMA_CLOUD_BASE_URL = os.getenv("LLAMA_CLOUD_BASE_URL")
LLAMA_CLOUD_PROJECT_ID = os.getenv("LLAMA_CLOUD_PROJECT_ID")

# Skip all tests if API key is not set
pytestmark = pytest.mark.skipif(
    not LLAMA_CLOUD_API_KEY, reason="LLAMA_CLOUD_API_KEY not set"
)


# Test data
class ExampleSchema(BaseModel):
    title: str
    summary: str


# Test data paths
TEST_DIR = Path(__file__).parent / "data"
TEST_PDF = TEST_DIR / "api_test" / "noisebridge_receipt.pdf"


@pytest.fixture
def llama_extract():
    return LlamaExtract(
        api_key=LLAMA_CLOUD_API_KEY,
        base_url=LLAMA_CLOUD_BASE_URL,
        project_id=LLAMA_CLOUD_PROJECT_ID,
        verbose=True,
    )


@pytest.fixture
def test_agent_name():
    return "test-api-agent"


@pytest.fixture
def test_schema_dict():
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
        },
    }


@pytest.fixture
def unique_test_pdf(tmp_path):
    """Copy test PDF to a unique path to avoid file deduplication across parallel tests.

    Uses a UUID in the filename so that external_file_id is unique regardless of
    whether the full path or just the filename is sent to the backend.
    """
    unique_name = f"{TEST_PDF.stem}-{uuid.uuid4().hex[:8]}{TEST_PDF.suffix}"
    unique_pdf = tmp_path / unique_name
    shutil.copy2(TEST_PDF, unique_pdf)
    return unique_pdf


@pytest.fixture
def test_agent(llama_extract, test_agent_name, test_schema_dict, request):
    """Creates a test agent with a unique name and cleans it up after the test."""
    unique_id = uuid.uuid4().hex[:8]
    base_name = next(
        (marker.args[0] for marker in request.node.iter_markers("agent_name")),
        test_agent_name,
    )
    name = f"{base_name}_{unique_id}"

    schema = next(
        (
            marker.args[0][0] if isinstance(marker.args[0], tuple) else marker.args[0]
            for marker in request.node.iter_markers("agent_schema")
        ),
        test_schema_dict,
    )

    # Use config with cache invalidation to ensure fresh results in tests
    config = ExtractConfig(invalidate_cache=True)
    agent = create_agent_with_retry(
        llama_extract, name=name, data_schema=schema, config=config
    )

    yield agent

    # Inline cleanup -- each worker cleans up its own agents
    try:
        llama_extract.delete_agent(agent.id)
    except Exception as e:
        print(f"Warning: Failed to cleanup agent {agent.id}: {e}")


class TestLlamaExtract:
    def test_init_without_api_key(self):
        env_backup = os.getenv("LLAMA_CLOUD_API_KEY")
        del os.environ["LLAMA_CLOUD_API_KEY"]
        with pytest.raises(ValueError, match="The API key is required"):
            LlamaExtract(api_key=None, base_url=LLAMA_CLOUD_BASE_URL)
        os.environ["LLAMA_CLOUD_API_KEY"] = env_backup

    @pytest.mark.agent_name("test-dict-schema-agent")
    def test_create_agent_with_dict_schema(self, test_agent):
        assert isinstance(test_agent, ExtractionAgent)

    @pytest.mark.agent_name("test-pydantic-schema-agent")
    @pytest.mark.agent_schema((ExampleSchema,))
    def test_create_agent_with_pydantic_schema(self, test_agent):
        assert isinstance(test_agent, ExtractionAgent)

    def test_get_agent_by_name(self, llama_extract, test_agent):
        agent = llama_extract.get_agent(name=test_agent.name)
        assert isinstance(agent, ExtractionAgent)
        assert agent.name == test_agent.name
        assert agent.id == test_agent.id
        assert agent.data_schema == test_agent.data_schema

    def test_get_agent_by_id(self, llama_extract, test_agent):
        agent = llama_extract.get_agent(id=test_agent.id)
        assert isinstance(agent, ExtractionAgent)
        assert agent.id == test_agent.id
        assert agent.name == test_agent.name
        assert agent.data_schema == test_agent.data_schema

    def test_list_agents(self, llama_extract, test_agent):
        agents = llama_extract.list_agents()
        assert isinstance(agents, list)
        assert any(a.id == test_agent.id for a in agents)


class TestExtractionAgent:
    @pytest.mark.asyncio
    async def test_extract_single_file(self, test_agent, unique_test_pdf):
        result = await test_agent.aextract(unique_test_pdf)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_sync_extract_single_file(self, test_agent, unique_test_pdf):
        result = test_agent.extract(unique_test_pdf)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_file_from_buffered_io(self, test_agent, unique_test_pdf):
        result = test_agent.extract(
            SourceText(file=open(unique_test_pdf, "rb"), filename=unique_test_pdf.name)
        )
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_file_from_bytes(self, test_agent, unique_test_pdf):
        with open(unique_test_pdf, "rb") as f:
            file_bytes = f.read()
        result = test_agent.extract(
            SourceText(file=file_bytes, filename=unique_test_pdf.name)
        )
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_from_text_content(self, test_agent):
        TEST_TEXT = """
        # Llamas
        Llamas are social animals and live with others as a herd. Their wool is soft and
        contains only a small amount of lanolin.[2] Llamas can learn simple tasks after a
        few repetitions. When using a pack, they can carry about 25 to 30% of their body
        weight for 8 to 13 km (5–8 miles).[3] The name llama (also historically spelled
        "glama") was adopted by European settlers from native Peruvians.
        """
        unique_name = f"text-{uuid.uuid4().hex[:8]}.txt"
        result = test_agent.extract(
            SourceText(text_content=TEST_TEXT, filename=unique_name)
        )
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    @pytest.mark.asyncio
    async def test_extract_multiple_files(self, test_agent, unique_test_pdf):
        files = [unique_test_pdf, unique_test_pdf]  # Using same file twice for testing
        response = await test_agent.aextract(files)

        assert len(response) == 2
        for result in response:
            assert result.status == "SUCCESS"
            assert result.data is not None
            assert isinstance(result.data, dict)
            assert "title" in result.data
            assert "summary" in result.data

    def test_save_agent_updates(
        self, test_agent: ExtractionAgent, llama_extract: LlamaExtract
    ):
        new_schema = {
            "type": "object",
            "properties": {
                "new_field": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
            },
        }
        test_agent.data_schema = new_schema
        test_agent.save()

        # Verify the update by getting a fresh instance
        updated_agent = llama_extract.get_agent(name=test_agent.name)
        assert "new_field" in updated_agent.data_schema["properties"]

    def test_list_extraction_runs(self, test_agent: ExtractionAgent, unique_test_pdf):
        assert test_agent.list_extraction_runs().total == 0
        test_agent.extract(unique_test_pdf)
        runs = test_agent.list_extraction_runs()
        assert runs.total > 0

    def test_delete_extraction_run(self, test_agent: ExtractionAgent, unique_test_pdf):
        assert test_agent.list_extraction_runs().total == 0
        run: ExtractRun = test_agent.extract(unique_test_pdf)
        test_agent.delete_extraction_run(run.id)
        runs = test_agent.list_extraction_runs()
        assert runs.total == 0


@pytest.mark.skipif(
    "CI" in os.environ, reason="Test locally; functionality is mostly duplicated."
)
class TestStatelessExtraction:
    """Tests for stateless extraction methods that don't require creating an agent."""

    @pytest.fixture
    def test_config(self):
        return ExtractConfig(extraction_mode=ExtractMode.FAST, invalidate_cache=True)

    @pytest.fixture
    def test_schema_dict(self):
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
            },
        }

    @pytest.mark.asyncio
    async def test_aextract_single_file(
        self, llama_extract, test_schema_dict, test_config
    ):
        """Test async stateless extraction with a single file."""
        result = await llama_extract.aextract(test_schema_dict, test_config, TEST_PDF)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_single_file(self, llama_extract, test_schema_dict, test_config):
        """Test synchronous stateless extraction with a single file."""
        result = llama_extract.extract(test_schema_dict, test_config, TEST_PDF)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_from_bytes_with_source_text(
        self, llama_extract, test_schema_dict, test_config
    ):
        """Test stateless extraction from bytes using SourceText with filename."""
        with open(TEST_PDF, "rb") as f:
            file_bytes = f.read()
        source_text = SourceText(file=file_bytes, filename=TEST_PDF.name)
        result = llama_extract.extract(test_schema_dict, test_config, source_text)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_from_source_text_with_file(
        self, llama_extract, test_schema_dict, test_config
    ):
        """Test stateless extraction from SourceText with file."""
        source_text = SourceText(file=TEST_PDF, filename=TEST_PDF.name)
        result = llama_extract.extract(test_schema_dict, test_config, source_text)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_from_buffered_io(
        self, llama_extract, test_schema_dict, test_config
    ):
        """Test stateless extraction from BufferedIO file handle."""
        with open(TEST_PDF, "rb") as file_handle:
            result = llama_extract.extract(test_schema_dict, test_config, file_handle)
            assert result.status == "SUCCESS"
            assert result.data is not None
            assert isinstance(result.data, dict)
            assert "title" in result.data
            assert "summary" in result.data

    def test_extract_from_source_text_with_text_content(
        self, llama_extract, test_schema_dict, test_config
    ):
        """Test stateless extraction from SourceText with text content."""
        TEST_TEXT = """
        # Llamas
        Llamas are social animals and live with others as a herd. Their wool is soft and
        contains only a small amount of lanolin. Llamas can learn simple tasks after a
        few repetitions. When using a pack, they can carry about 25 to 30% of their body
        weight for 8 to 13 km (5–8 miles). The name llama was adopted by European settlers
        from native Peruvians.
        """
        source_text = SourceText(text_content=TEST_TEXT)
        result = llama_extract.extract(test_schema_dict, test_config, source_text)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    @pytest.mark.asyncio
    async def test_queue_extraction_single_file(
        self, llama_extract, test_schema_dict, test_config
    ):
        """Test queuing extraction job without waiting for completion."""
        job = await llama_extract.queue_extraction(
            test_schema_dict, test_config, TEST_PDF
        )
        assert hasattr(job, "id")
        assert hasattr(job, "status")

    @pytest.mark.asyncio
    async def test_extract_multiple_files(
        self, llama_extract, test_schema_dict, test_config
    ):
        """Test stateless extraction with multiple files."""
        files = [TEST_PDF, TEST_PDF]  # Using same file twice for testing
        results = await llama_extract.aextract(test_schema_dict, test_config, files)

        assert isinstance(results, list)
        assert len(results) == 2

        for result in results:
            assert result.status == "SUCCESS"
            assert result.data is not None
            assert isinstance(result.data, dict)
            assert "title" in result.data
            assert "summary" in result.data

    def test_extract_with_pydantic_schema(self, llama_extract, test_config):
        """Test stateless extraction with Pydantic schema."""
        result = llama_extract.extract(ExampleSchema, test_config, TEST_PDF)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_from_raw_bytes_raises_error(
        self, llama_extract, test_schema_dict, test_config
    ):
        """Test that raw bytes without filename raises an error."""
        with open(TEST_PDF, "rb") as f:
            file_bytes = f.read()

        with pytest.raises(
            ValueError, match="Cannot determine file type from raw bytes"
        ):
            llama_extract.extract(test_schema_dict, test_config, file_bytes)

    def test_mime_type_detection(self, llama_extract):
        """Test that MIME types are correctly detected for various file types."""
        # Test PDF
        assert llama_extract._get_mime_type(filename="test.pdf") == "application/pdf"

        # Test DOCX
        assert (
            llama_extract._get_mime_type(filename="test.docx")
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # Test text files
        assert llama_extract._get_mime_type(filename="test.txt") == "text/plain"
        assert llama_extract._get_mime_type(filename="test.csv") == "text/csv"
        assert llama_extract._get_mime_type(filename="test.json") == "application/json"

        # Test image files
        assert llama_extract._get_mime_type(filename="test.png") == "image/png"
        assert llama_extract._get_mime_type(filename="test.jpg") == "image/jpeg"

        # Test file path
        from pathlib import Path

        assert (
            llama_extract._get_mime_type(file_path=Path("test.pdf"))
            == "application/pdf"
        )

        # Test unsupported file type
        with pytest.raises(ValueError, match="Unsupported file type: 'xyz'"):
            llama_extract._get_mime_type(filename="test.xyz")
