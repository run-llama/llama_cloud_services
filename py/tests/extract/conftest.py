from typing import Any, Dict, Optional, Union

from llama_cloud.core.api_error import ApiError
from llama_cloud.types import ExtractConfig
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from llama_cloud_services.extract import ExtractionAgent, LlamaExtract


def _is_rate_limit_error(exception: BaseException) -> bool:
    """Check if the exception is a rate limit error (429)."""
    return isinstance(exception, ApiError) and exception.status_code == 429


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def create_agent_with_retry(
    extractor: LlamaExtract,
    name: str,
    data_schema: Union[Dict[str, Any], type[BaseModel]],
    config: Optional[ExtractConfig] = None,
) -> ExtractionAgent:
    """Create an extraction agent with retry logic for rate limiting."""
    return extractor.create_agent(name=name, data_schema=data_schema, config=config)


def pytest_configure(config):
    """Register custom markers for extract tests."""
    config.addinivalue_line("markers", "agent_name: custom agent name for test")
    config.addinivalue_line("markers", "agent_schema: custom agent schema for test")
