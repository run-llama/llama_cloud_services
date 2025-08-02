import os
import pytest
from llama_cloud.client import AsyncLlamaCloud
from llama_cloud.types import Project, ClassifierRule, ClassifyJobResults, File
from llama_index.core.constants import DEFAULT_BASE_URL
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from llama_cloud_services.beta.classifier.client import ClassifyClient
from llama_cloud_services.files.client import FileClient
from llama_cloud.errors.unprocessable_entity_error import UnprocessableEntityError

class TestSettings(BaseSettings):
    LLAMA_CLOUD_BASE_URL: str = Field(description="The base URL of the LlamaCloud API", default=DEFAULT_BASE_URL)
    LLAMA_CLOUD_API_KEY: SecretStr = Field(description="The API key for the LlamaCloud API")
    LLAMA_CLOUD_ORGANIZATION_ID: str = Field(description="The organization ID for the LlamaCloud API")
    LLAMA_CLOUD_PROJECT_NAME: str = Field(description="The project name for the LlamaCloud API", default="framework_integration_test")


# Skip all tests if API key is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("LLAMA_CLOUD_API_KEY"), reason="LLAMA_CLOUD_API_KEY not set"
)


@pytest.fixture
def settings() -> TestSettings:
    return TestSettings()


@pytest.fixture
def async_llama_cloud_client(settings: TestSettings) -> AsyncLlamaCloud:
    return AsyncLlamaCloud(
        token=settings.LLAMA_CLOUD_API_KEY.get_secret_value(),
        base_url=settings.LLAMA_CLOUD_BASE_URL,
    )


@pytest.fixture
async def project(async_llama_cloud_client: AsyncLlamaCloud, settings: TestSettings) -> Project:
    projects = await async_llama_cloud_client.projects.list_projects(
        project_name=settings.LLAMA_CLOUD_PROJECT_NAME,
        organization_id=settings.LLAMA_CLOUD_ORGANIZATION_ID,
    )
    assert len(projects) == 1
    return projects[0]


@pytest.fixture
def classify_client(async_llama_cloud_client: AsyncLlamaCloud, project: Project) -> ClassifyClient:
    return ClassifyClient(
        async_llama_cloud_client,
        project_id=project.id,
        organization_id=project.organization_id,
        polling_interval=1
    )


@pytest.fixture
def file_client(async_llama_cloud_client: AsyncLlamaCloud, project: Project) -> FileClient:
    return FileClient(
        async_llama_cloud_client,
        project_id=project.id,
        organization_id=project.organization_id,
        use_presigned_url=False
    )

@pytest.fixture
def simple_pdf_file_path() -> str:
    return "tests/test_files/index/Simple PDF Slides.pdf"

@pytest.fixture
def resume_file_path() -> str:
    return "tests/test_files/resume/software_architect_resume.html"

@pytest.fixture
def classification_rules() -> list[ClassifierRule]:
    return [
        ClassifierRule(
            type="Number Document",
            description="Documents with numbers",
            classification="number"
        ),
        ClassifierRule(
            type="Resume Document",
            description="Resume or CV documents",
            classification="resume"
        ),
    ]


@pytest.mark.asyncio
async def test_classify_file_ids(
    classify_client: ClassifyClient,
    file_client: FileClient,
    simple_pdf_file_path: str,
    resume_file_path: str,
    classification_rules: list[ClassifierRule]
):
    """Test classifying files by their IDs"""
    # Upload test files first to get their IDs
    pdf_file = await file_client.upload_file(simple_pdf_file_path)
    resume_file = await file_client.upload_file(resume_file_path)

    # Classify the uploaded files
    results = await classify_client.classify_file_ids(
        rules=classification_rules,
        file_ids=[pdf_file.id, resume_file.id]
    )

    assert isinstance(results, ClassifyJobResults)
    assert len(results.items) == 2

    file_id_to_expected_type = {pdf_file.id: "pdf", resume_file.id: "resume"}
    # Verify each file got classified
    for item in results.items:
        expected_type = file_id_to_expected_type[item.file_id]
        assert item.result.type == expected_type


@pytest.mark.asyncio
async def test_classify_file_path(classify_client: ClassifyClient, simple_pdf_file_path: str, classification_rules: list[ClassifierRule]):
    """Test classifying a single file by path"""
    # Classify the file
    results = await classify_client.classify_file_path(
        rules=classification_rules,
        file_input_path=simple_pdf_file_path
    )

    assert isinstance(results, ClassifyJobResults)
    assert len(results.items) == 1

    # Verify the file got classified
    item = results.items[0]
    assert item.result.type == "number"


@pytest.mark.asyncio
async def test_classify_file_paths(classify_client: ClassifyClient, simple_pdf_file_path: str, resume_file_path: str, classification_rules: list[ClassifierRule]):
    """Test classifying multiple files by paths"""
    # Classify all test files
    results = await classify_client.classify_file_paths(
        rules=classification_rules,
        file_input_paths=[simple_pdf_file_path, resume_file_path]
    )

    assert isinstance(results, ClassifyJobResults)
    assert len(results.items) == 2

    file_id_to_expected_type = {simple_pdf_file_path: "number", resume_file_path: "resume"}
    # Verify each file got classified
    for item in results.items:
        expected_type = file_id_to_expected_type[item.file_id]
        assert item.result.type == expected_type


@pytest.mark.asyncio
async def test_classify_empty_file_list(classify_client: ClassifyClient, classification_rules: list[ClassifierRule]):
    """Test classifying an empty list of files"""
    # This should throw an error
    with pytest.raises(UnprocessableEntityError):
        await classify_client.classify_file_ids(
            rules=classification_rules,
            file_ids=[]
        )
