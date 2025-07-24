import os
from typing import List
from llama_cloud_services.extract import LlamaExtract

# Global storage for agents to cleanup
_TEST_AGENTS_TO_CLEANUP: List[str] = []


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
