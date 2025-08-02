import os
import pytest
from io import BytesIO
from llama_cloud.client import AsyncLlamaCloud
from llama_cloud.types import Project, File
from llama_index.core.constants import DEFAULT_BASE_URL
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from llama_cloud_services.files.client import FileClient

class TestSettings(BaseSettings):
    LLAMA_CLOUD_BASE_URL: str = Field(description="The base URL of the LlamaCloud API", default=DEFAULT_BASE_URL)
    LLAMA_CLOUD_API_KEY: SecretStr = Field(description="The API key for the LlamaCloud API")
    LLAMA_CLOUD_ORGANIZATION_ID: str = Field(description="The organization ID for the LlamaCloud API")
    LLAMA_CLOUD_PROJECT_NAME: str = Field(description="The project name for the LlamaCloud API", default="framework_integration_test")


@pytest.fixture
def settings() -> TestSettings:
    return TestSettings()


@pytest.fixture
async def llama_cloud_client(settings: TestSettings) -> AsyncLlamaCloud:
    return AsyncLlamaCloud(
        token=settings.LLAMA_CLOUD_API_KEY.get_secret_value(),
        base_url=settings.LLAMA_CLOUD_BASE_URL,
    )


@pytest.fixture
async def project(llama_cloud_client: AsyncLlamaCloud, settings: TestSettings) -> Project:
    projects = await llama_cloud_client.projects.list_projects(
        project_name=settings.LLAMA_CLOUD_PROJECT_NAME,
        organization_id=settings.LLAMA_CLOUD_ORGANIZATION_ID,
    )
    assert len(projects) == 1
    return projects[0]


@pytest.fixture
async def file_client(llama_cloud_client: AsyncLlamaCloud, project: Project, use_presigned_url: bool) -> FileClient:
    return FileClient(
        llama_cloud_client, 
        project_id=project.id, 
        organization_id=project.organization_id,
        use_presigned_url=use_presigned_url
    )


@pytest.fixture
def test_file() -> str:
    return "tests/test_files/index/Simple PDF Slides.pdf"


parametrize_use_presigned_url = pytest.mark.parametrize("use_presigned_url", [True, False])


@parametrize_use_presigned_url
@pytest.mark.asyncio
async def test_upload_file_from_path(file_client: FileClient, test_file: str, use_presigned_url: bool):
    """Test uploading a file from file path"""
    external_file_id = f"test_upload_path_{os.getpid()}"
    uploaded_file = await file_client.upload_file(test_file, external_file_id)

    assert isinstance(uploaded_file, File)
    expected_name = external_file_id if use_presigned_url else os.path.basename(test_file)
    assert uploaded_file.name == expected_name
    assert uploaded_file.external_file_id == external_file_id


@parametrize_use_presigned_url
@pytest.mark.asyncio
async def test_upload_bytes(file_client: FileClient, test_file: str, use_presigned_url: bool):
    """Test uploading a file from bytes"""
    # Read file as bytes
    with open(test_file, "rb") as f:
        file_bytes = f.read()
    
    external_file_id = f"test_upload_bytes_{os.getpid()}"
    uploaded_file = await file_client.upload_bytes(file_bytes, external_file_id)
    
    assert isinstance(uploaded_file, File)
    expected_name = external_file_id if use_presigned_url else "upload"
    assert uploaded_file.name == expected_name
    assert uploaded_file.external_file_id == external_file_id


@parametrize_use_presigned_url
@pytest.mark.asyncio
async def test_upload_buffer(file_client: FileClient, test_file: str, use_presigned_url: bool):
    """Test uploading a file from buffer"""
    # Read file as bytes and create buffer
    with open(test_file, "rb") as f:
        file_bytes = f.read()
    
    buffer = BytesIO(file_bytes)
    file_size = len(file_bytes)
    external_file_id = f"test_upload_buffer_{os.getpid()}"
    
    uploaded_file = await file_client.upload_buffer(buffer, external_file_id, file_size)
    
    assert isinstance(uploaded_file, File)
    expected_name = external_file_id if use_presigned_url else "upload"
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
async def test_upload_with_default_external_id(file_client: FileClient, test_file: str, use_presigned_url: bool):
    """Test uploading file with default external_file_id"""    
    # Upload file without specifying external_file_id
    uploaded_file = await file_client.upload_file(test_file)
    
    assert isinstance(uploaded_file, File)
    expected_name = test_file if use_presigned_url else os.path.basename(test_file)
    assert uploaded_file.name == expected_name
    assert uploaded_file.external_file_id == test_file
