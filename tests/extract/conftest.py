import os
from llama_cloud_services.extract import LlamaExtract


def pytest_sessionfinish(session, exitstatus):
    """Hook that runs after all tests complete - cleanup agents here"""
    # Get agents to cleanup from pytest config
    agents_to_cleanup = getattr(session.config, "_test_agents_cleanup", [])
    print(f"pytest_sessionfinish hook called! Agents to cleanup: {agents_to_cleanup}")

    if agents_to_cleanup:
        print("Creating cleanup client...")
        # Create a fresh client just for cleanup
        cleanup_client = LlamaExtract(
            api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
            base_url=os.getenv("LLAMA_CLOUD_BASE_URL"),
            project_id=os.getenv("LLAMA_CLOUD_PROJECT_ID"),
            verbose=True,
        )

        for agent_id in agents_to_cleanup:
            try:
                print(f"Deleting agent {agent_id}...")
                cleanup_client.delete_agent(agent_id)
                print(f"Cleaned up agent {agent_id}")
            except Exception as e:
                print(f"Warning: Failed to delete agent {agent_id}: {e}")

        # Clear the list
        session.config._test_agents_cleanup.clear()
        print("Agent cleanup completed")
    else:
        print("No agents to cleanup")
