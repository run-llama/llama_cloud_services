import os
from typing import Any, Dict, List, Optional, Union

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

# Global storage for agents to cleanup
_TEST_AGENTS_TO_CLEANUP: List[str] = []


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


def pytest_sessionfinish(session, exitstatus):
    """Hook that runs after all tests complete - cleanup agents here"""
    print(
        f"pytest_sessionfinish hook called! Agents to cleanup: {_TEST_AGENTS_TO_CLEANUP}"
    )

    if _TEST_AGENTS_TO_CLEANUP:
        print("Creating cleanup client...")
        # Create a fresh client just for cleanup
        cleanup_client = LlamaExtract(
            api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
            base_url=os.getenv("LLAMA_CLOUD_BASE_URL"),
            project_id=os.getenv("LLAMA_CLOUD_PROJECT_ID"),
            verbose=True,
        )

        for agent_id in _TEST_AGENTS_TO_CLEANUP:
            try:
                print(f"Deleting agent {agent_id}...")
                cleanup_client.delete_agent(agent_id)
                print(f"Cleaned up agent {agent_id}")
            except Exception as e:
                print(f"Warning: Failed to delete agent {agent_id}: {e}")

        _TEST_AGENTS_TO_CLEANUP.clear()
        print("Agent cleanup completed")
    else:
        print("No agents to cleanup")


def register_agent_for_cleanup(agent_id: str):
    """Register an agent ID for cleanup at the end of the test session"""
    _TEST_AGENTS_TO_CLEANUP.append(agent_id)
