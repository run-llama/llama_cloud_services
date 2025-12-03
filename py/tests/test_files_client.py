import os
import pytest
from io import BytesIO
from llama_cloud.client import AsyncLlamaCloud
from llama_cloud.types import Project, File
from llama_cloud_services.files.client import FileClient
from tests.conftest import EndToEndTestSettings


@pytest.fixture
async def llama_cloud_client(
    e2e_test_settings: EndToEndTestSettings,
) -> AsyncLlamaCloud:
    return AsyncLlamaCloud(
        token=e2e_test_settings.LLAMA_CLOUD_API_KEY.get_secret_value(),
        base_url=e2e_test_settings.LLAMA_CLOUD_BASE_URL,
    )


@pytest.fixture
async def project(
    llama_cloud_client: AsyncLlamaCloud, e2e_test_settings: EndToEndTestSettings
) -> Project:
    projects = await llama_cloud_client.projects.list_projects(
        project_name=e2e_test_settings.LLAMA_CLOUD_PROJECT_NAME,
        organization_id=e2e_test_settings.LLAMA_CLOUD_ORGANIZATION_ID,
    )
    assert len(projects) == 1
    return projects[0]


@pytest.fixture
async def file_client(
    llama_cloud_client: AsyncLlamaCloud, project: Project, use_presigned_url: bool
) -> FileClient:
    return FileClient(
        llama_cloud_client,
        project_id=project.id,
        organization_id=project.organization_id,
        use_presigned_url=use_presigned_url,
    )


@pytest.fixture
def test_file() -> str:
    return "tests/test_files/index/Simple PDF Slides.pdf"


parametrize_use_presigned_url = pytest.mark.parametrize(
    "use_presigned_url", [True, False]
)


@parametrize_use_presigned_url
@pytest.mark.asyncio
async def test_upload_file_from_path(file_client: FileClient, test_file: str):
    """Test uploading a file from file path"""
    external_file_id = f"test_upload_path_{os.getpid()}"
    uploaded_file = await file_client.upload_file(test_file, external_file_id)

    assert isinstance(uploaded_file, File)
    expected_name = os.path.basename(test_file)
    assert uploaded_file.name == expected_name
    assert uploaded_file.external_file_id == external_file_id


@parametrize_use_presigned_url
@pytest.mark.asyncio
async def test_upload_bytes(
    file_client: FileClient, test_file: str, use_presigned_url: bool
):
    """Test uploading a file from bytes"""
    # Read file as bytes
    with open(test_file, "rb") as f:
        file_bytes = f.read()

    external_file_id = f"test_upload_bytes_{os.getpid()}"
    uploaded_file = await file_client.upload_bytes(file_bytes, external_file_id)

    assert isinstance(uploaded_file, File)
    expected_name = external_file_id
    assert uploaded_file.name == expected_name
    assert uploaded_file.external_file_id == external_file_id


@parametrize_use_presigned_url
@pytest.mark.asyncio
async def test_upload_buffer(
    file_client: FileClient, test_file: str, use_presigned_url: bool
):
    """Test uploading a file from buffer"""
    # Read file as bytes and create buffer
    with open(test_file, "rb") as f:
        file_bytes = f.read()

    buffer = BytesIO(file_bytes)
    file_size = len(file_bytes)
    external_file_id = f"test_upload_buffer_{os.getpid()}"

    uploaded_file = await file_client.upload_buffer(buffer, external_file_id, file_size)

    assert isinstance(uploaded_file, File)
    expected_name = external_file_id
    assert uploaded_file.name == expected_name
    assert uploaded_file.external_file_id == external_file_id


@parametrize_use_presigned_url
@pytest.mark.asyncio
async def test_get_file(file_client: FileClient, test_file: str):
    """Test retrieving a file by ID"""
    # Upload a file first
    external_file_id = f"test_get_file_{os.getpid()}"
    uploaded_file = await file_client.upload_file(test_file, external_file_id)

    # Retrieve the file by ID
    retrieved_file = await file_client.get_file(uploaded_file.id)

    assert isinstance(retrieved_file, File)
    assert retrieved_file == uploaded_file


@parametrize_use_presigned_url
@pytest.mark.asyncio
async def test_upload_with_default_external_id(file_client: FileClient, test_file: str):
    """Test uploading file with default external_file_id"""
    # Upload file without specifying external_file_id
    uploaded_file = await file_client.upload_file(test_file)

    assert isinstance(uploaded_file, File)
    assert uploaded_file.name == os.path.basename(test_file)
    assert uploaded_file.external_file_id == test_file


@parametrize_use_presigned_url
@pytest.mark.asyncio
async def test_read_file_content(file_client: FileClient, test_file: str):
    """Test reading a file content"""
    # Upload a file first
    external_file_id = f"test_read_file_content_{os.getpid()}"
    uploaded_file = await file_client.upload_file(test_file, external_file_id)

    # Read the file content
    file_content = await file_client.read_file_content(uploaded_file.id)
    with open(test_file, "rb") as f:
        expected_file_content = f.read()
    assert file_content == expected_file_content
