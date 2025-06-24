import os
import pytest
from pathlib import Path
from pydantic import BaseModel

from llama_cloud_services.extract import LlamaExtract, ExtractionAgent, SourceText
from tests.extract.util import load_test_dotenv
from .conftest import register_agent_for_cleanup

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
class TestSchema(BaseModel):
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
def test_agent(llama_extract, test_agent_name, test_schema_dict, request):
    """Creates a test agent and collects it for cleanup at the end of all tests"""
    test_id = request.node.nodeid
    test_hash = hex(hash(test_id))[-8:]
    base_name = test_agent_name

    base_name = next(
        (marker.args[0] for marker in request.node.iter_markers("agent_name")),
        base_name,
    )
    name = f"{base_name}_{test_hash}"

    schema = next(
        (
            marker.args[0][0] if isinstance(marker.args[0], tuple) else marker.args[0]
            for marker in request.node.iter_markers("agent_schema")
        ),
        test_schema_dict,
    )

    # Cleanup existing agent
    try:
        for agent in llama_extract.list_agents():
            if agent.name == name:
                llama_extract.delete_agent(agent.id)
    except Exception as e:
        print(f"Warning: Failed to cleanup existing agent: {e}")

    agent = llama_extract.create_agent(name=name, data_schema=schema)

    # Add agent to cleanup list via conftest helper
    register_agent_for_cleanup(agent.id)

    yield agent


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
    @pytest.mark.agent_schema((TestSchema,))
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
    async def test_extract_single_file(self, test_agent):
        result = await test_agent.aextract(TEST_PDF)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_sync_extract_single_file(self, test_agent):
        result = test_agent.extract(TEST_PDF)
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_file_from_buffered_io(self, test_agent):
        result = test_agent.extract(SourceText(file=open(TEST_PDF, "rb")))
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    def test_extract_file_from_bytes(self, test_agent):
        with open(TEST_PDF, "rb") as f:
            file_bytes = f.read()
        result = test_agent.extract(SourceText(file=file_bytes, filename=TEST_PDF.name))
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
        result = test_agent.extract(SourceText(text_content=TEST_TEXT))
        assert result.status == "SUCCESS"
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "title" in result.data
        assert "summary" in result.data

    @pytest.mark.asyncio
    async def test_extract_multiple_files(self, test_agent):
        files = [TEST_PDF, TEST_PDF]  # Using same file twice for testing
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

    def test_list_extraction_runs(self, test_agent: ExtractionAgent):
        assert test_agent.list_extraction_runs().total == 0
        test_agent.extract(TEST_PDF)
        runs = test_agent.list_extraction_runs()
        assert runs.total > 0

    def test_delete_extraction_run(self, test_agent: ExtractionAgent):
        assert test_agent.list_extraction_runs().total == 0
        run = test_agent.extract(TEST_PDF)
        test_agent.delete_extraction_run(run.id)
        runs = test_agent.list_extraction_runs()
        assert runs.total == 0
