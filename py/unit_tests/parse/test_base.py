from collections.abc import Generator
import pytest
import os

from llama_cloud_services.parse.base import LlamaParse


@pytest.fixture(autouse=True)
def clear_env() -> Generator[None, None, None]:
    """entirely clear the environment, and then reset after test completion"""
    original_env = os.environ.copy()
    os.environ.clear()
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original_env)


def test_should_obtain_api_key_base_url_from_env_vars():
    os.environ["LLAMA_CLOUD_API_KEY"] = "test-api-key"
    os.environ["LLAMA_CLOUD_BASE_URL"] = "https://example.test"

    client = LlamaParse()
    assert client.api_key == "test-api-key"
    assert client.base_url == "https://example.test"


def test_should_be_able_to_pass_api_key_base_url_as_kwargs():
    os.environ["LLAMA_CLOUD_API_KEY"] = "not-this-one"
    os.environ["LLAMA_CLOUD_BASE_URL"] = "https://wrong.site"

    client = LlamaParse(
        api_key="test-api-key",
        base_url="https://example.test",
    )
    assert client.api_key == "test-api-key"
    assert client.base_url == "https://example.test"


def test_should_raise_error_if_api_key_is_not_provided():
    with pytest.raises(ValueError, match="The API key is required."):
        LlamaParse()


def test_should_default_to_llama_cloud_base_url_if_not_provided():
    client = LlamaParse(
        api_key="test-api-key",
    )
    assert client.base_url == "https://api.cloud.llamaindex.ai"


def test_json_parseable():
    os.environ["LLAMA_CLOUD_API_KEY"] = "test-api-key"
    client2 = LlamaParse.model_validate_json('{"base_url":"https://example.test"}')
    assert client2.api_key == "test-api-key"
    assert client2.base_url == "https://example.test"
