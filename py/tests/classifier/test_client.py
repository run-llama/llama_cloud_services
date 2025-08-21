import os
import pytest
from llama_cloud.client import AsyncLlamaCloud
from llama_cloud.types import Project, ClassifierRule, ClassifyJobResults
from llama_cloud_services.beta.classifier.client import ClassifyClient
from llama_cloud_services.files.client import FileClient
from llama_cloud.errors.unprocessable_entity_error import UnprocessableEntityError
from tests.conftest import EndToEndTestSettings
import nest_asyncio

# Skip all tests if API key is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("LLAMA_CLOUD_API_KEY"), reason="LLAMA_CLOUD_API_KEY not set"
)


@pytest.fixture
def async_llama_cloud_client(
    e2e_test_settings: EndToEndTestSettings,
) -> AsyncLlamaCloud:
    return AsyncLlamaCloud(
        token=e2e_test_settings.LLAMA_CLOUD_API_KEY.get_secret_value(),
        base_url=e2e_test_settings.LLAMA_CLOUD_BASE_URL,
    )


@pytest.fixture
async def project(
    async_llama_cloud_client: AsyncLlamaCloud, e2e_test_settings: EndToEndTestSettings
) -> Project:
    projects = await async_llama_cloud_client.projects.list_projects(
        project_name=e2e_test_settings.LLAMA_CLOUD_PROJECT_NAME,
        organization_id=e2e_test_settings.LLAMA_CLOUD_ORGANIZATION_ID,
    )
    assert len(projects) == 1
    return projects[0]


@pytest.fixture
def classify_client(
    async_llama_cloud_client: AsyncLlamaCloud, project: Project
) -> ClassifyClient:
    return ClassifyClient(
        async_llama_cloud_client,
        project_id=project.id,
        organization_id=project.organization_id,
        polling_interval=1,
    )


@pytest.fixture
def file_client(
    async_llama_cloud_client: AsyncLlamaCloud, project: Project
) -> FileClient:
    return FileClient(
        async_llama_cloud_client,
        project_id=project.id,
        organization_id=project.organization_id,
        use_presigned_url=False,
    )


@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio():
    nest_asyncio.apply()


@pytest.fixture
def simple_pdf_file_path() -> str:
    return "tests/test_files/index/Simple PDF Slides.pdf"


@pytest.fixture
def research_paper_path() -> str:
    return "tests/test_files/attention_is_all_you_need_chart.pdf"


@pytest.fixture
def classification_rules() -> list[ClassifierRule]:
    return [
        ClassifierRule(
            type="number",
            description="Documents with numbers",
        ),
        ClassifierRule(
            type="research_paper",
            description="Research papers",
        ),
    ]


parameterize_sync_and_async = pytest.mark.parametrize("sync", [True, False])


@parameterize_sync_and_async
@pytest.mark.asyncio
async def test_classify_file_ids(
    classify_client: ClassifyClient,
    file_client: FileClient,
    simple_pdf_file_path: str,
    research_paper_path: str,
    classification_rules: list[ClassifierRule],
    sync: bool,
):
    """Test classifying files by their IDs"""
    # Upload test files first to get their IDs
    pdf_file = await file_client.upload_file(simple_pdf_file_path)
    research_paper_file = await file_client.upload_file(research_paper_path)

    # Classify the uploaded files
    if sync:
        results = classify_client.classify_file_ids(
            rules=classification_rules, file_ids=[pdf_file.id, research_paper_file.id]
        )
    else:
        results = await classify_client.aclassify_file_ids(
            rules=classification_rules, file_ids=[pdf_file.id, research_paper_file.id]
        )

    assert isinstance(results, ClassifyJobResults)
    assert len(results.items) == 2

    file_id_to_expected_type = {
        pdf_file.id: "number",
        research_paper_file.id: "research_paper",
    }
    # Verify each file got classified
    for item in results.items:
        expected_type = file_id_to_expected_type[item.file_id]
        assert item.result.type == expected_type


@parameterize_sync_and_async
@pytest.mark.asyncio
async def test_classify_file_path(
    classify_client: ClassifyClient,
    simple_pdf_file_path: str,
    classification_rules: list[ClassifierRule],
    sync: bool,
):
    """Test classifying a single file by path"""
    # Classify the file
    if sync:
        results = classify_client.classify_file_path(
            rules=classification_rules, file_input_path=simple_pdf_file_path
        )
    else:
        results = await classify_client.aclassify_file_path(
            rules=classification_rules, file_input_path=simple_pdf_file_path
        )

    assert isinstance(results, ClassifyJobResults)
    assert len(results.items) == 1

    # Verify the file got classified
    item = results.items[0]
    assert item.result.type == "number"


@parameterize_sync_and_async
@pytest.mark.asyncio
async def test_classify_file_paths(
    classify_client: ClassifyClient,
    file_client: FileClient,
    simple_pdf_file_path: str,
    research_paper_path: str,
    classification_rules: list[ClassifierRule],
    sync: bool,
):
    """Test classifying multiple files by paths"""
    # Classify all test files
    if sync:
        results = classify_client.classify_file_paths(
            rules=classification_rules,
            file_input_paths=[simple_pdf_file_path, research_paper_path],
        )
    else:
        results = await classify_client.aclassify_file_paths(
            rules=classification_rules,
            file_input_paths=[simple_pdf_file_path, research_paper_path],
        )

    assert isinstance(results, ClassifyJobResults)
    assert len(results.items) == 2

    file_name_to_expected_type = {
        os.path.basename(simple_pdf_file_path): "number",
        os.path.basename(research_paper_path): "research_paper",
    }
    # Verify each file got classified
    for item in results.items:
        file = await file_client.get_file(item.file_id)
        expected_type = file_name_to_expected_type[file.name]
        assert item.result.type == expected_type


@parameterize_sync_and_async
@pytest.mark.asyncio
async def test_classify_empty_file_list(
    classify_client: ClassifyClient,
    classification_rules: list[ClassifierRule],
    sync: bool,
):
    """Test classifying an empty list of files"""
    # This should throw an error
    with pytest.raises(UnprocessableEntityError):
        if sync:
            classify_client.classify_file_ids(rules=classification_rules, file_ids=[])
        else:
            await classify_client.aclassify_file_ids(
                rules=classification_rules, file_ids=[]
            )
