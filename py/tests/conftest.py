import pytest
from llama_index.core.constants import DEFAULT_BASE_URL
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class EndToEndTestSettings(BaseSettings):
    LLAMA_CLOUD_BASE_URL: str = Field(
        description="The base URL of the LlamaCloud API", default=DEFAULT_BASE_URL
    )
    LLAMA_CLOUD_API_KEY: SecretStr = Field(
        description="The API key for the LlamaCloud API"
    )
    LLAMA_CLOUD_ORGANIZATION_ID: str | None = Field(
        default=None, description="The organization ID for the LlamaCloud API"
    )
    LLAMA_CLOUD_PROJECT_NAME: str = Field(
        description="The project name for the LlamaCloud API",
        default="framework_integration_test",
    )


@pytest.fixture
def e2e_test_settings() -> EndToEndTestSettings:
    return EndToEndTestSettings()
