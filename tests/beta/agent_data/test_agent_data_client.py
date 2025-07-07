import os
import httpx
import pytest
import uuid
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

from llama_cloud.client import AsyncLlamaCloud
from llama_cloud_services.beta.agent_data import AsyncAgentDataClient


class TrailingSlashHttpxClient(httpx.AsyncClient):
    """Custom httpx client that ensures all URLs have trailing slashes"""

    async def request(self, method, url, **kwargs):
        # Convert URL to string and ensure trailing slash
        url_str = str(url)
        if not url_str.endswith("/") and "?" not in url_str:
            url_str += "/"
        self.headers["Authorization"] = f"Bearer {LLAMA_CLOUD_API_KEY}"
        kwargs.pop("headers", None)
        return await super().request(method, url_str, headers=self.headers, **kwargs)


# Load environment variables
def load_test_dotenv():
    dotenv_path = Path(__file__).parent.parent.parent.parent / ".env.dev"
    load_dotenv(dotenv_path, override=True)


load_test_dotenv()

# Get configuration from environment
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
LLAMA_CLOUD_BASE_URL = os.getenv("LLAMA_CLOUD_BASE_URL")
LLAMA_DEPLOY_DEPLOYMENT_NAME = os.getenv("LLAMA_DEPLOY_DEPLOYMENT_NAME")


class TestData(BaseModel):
    """Simple test data model for agent data testing"""

    name: str
    test_id: str
    value: int


# Skip all tests if API key is not set
@pytest.mark.asyncio
@pytest.mark.skipif(
    not LLAMA_CLOUD_API_KEY or not LLAMA_DEPLOY_DEPLOYMENT_NAME,
    reason="LLAMA_CLOUD_API_KEY or LLAMA_DEPLOY_DEPLOYMENT_NAME not set",
)
async def test_agent_data_crud_operations():
    """Test basic CRUD operations for agent data with automatic cleanup"""
    # Create unique test identifier to avoid conflicts
    test_id = str(uuid.uuid4())

    # Set up client
    client = AsyncLlamaCloud(
        token=LLAMA_CLOUD_API_KEY,
        base_url=LLAMA_CLOUD_BASE_URL,
        httpx_client=TrailingSlashHttpxClient(timeout=60, follow_redirects=True),
    )

    # Create agent data client with unique collection name
    agent_data_client = AsyncAgentDataClient(
        client=client,
        type=TestData,
        collection_name=f"test-collection-{test_id[:8]}",
        agent_url_id=LLAMA_DEPLOY_DEPLOYMENT_NAME,
    )

    # Create test data
    test_data = TestData(name="test-item", test_id=test_id, value=42)

    created_item = None
    try:
        # Test CREATE
        created_item = await agent_data_client.create_agent_data(test_data)
        assert created_item.data.name == "test-item"
        assert created_item.data.test_id == test_id
        assert created_item.data.value == 42
        assert created_item.id is not None

        # Test READ
        retrieved_item = await agent_data_client.get_agent_data(created_item.id)
        assert retrieved_item.id == created_item.id
        assert retrieved_item.data.name == "test-item"
        assert retrieved_item.data.test_id == test_id
        assert retrieved_item.data.value == 42

        # Test SEARCH
        search_results = await agent_data_client.search_agent_data(
            filter={"test_id": {"eq": test_id}}, page_size=10, include_total=True
        )
        assert len(search_results.items) == 1
        assert search_results.items[0].data.test_id == test_id
        assert search_results.total == 1

        # Test AGGREGATE
        aggregate_results = await agent_data_client.aggregate_agent_data(
            group_by=["test_id"], count=True
        )
        assert len(aggregate_results.items) == 1
        assert aggregate_results.items[0].group_key["test_id"] == test_id
        assert aggregate_results.items[0].count == 1

        # Test UPDATE
        updated_data = TestData(name="updated-item", test_id=test_id, value=84)
        updated_item = await agent_data_client.update_agent_data(
            created_item.id, updated_data
        )
        assert updated_item.data.name == "updated-item"
        assert updated_item.data.value == 84
        assert updated_item.id == created_item.id

        # Verify update persisted
        verified_item = await agent_data_client.get_agent_data(created_item.id)
        assert verified_item.data.name == "updated-item"
        assert verified_item.data.value == 84

    finally:
        # Clean up test data
        if created_item is not None:
            try:
                await agent_data_client.delete_agent_data(created_item.id)
            except Exception as e:
                print(f"Warning: Failed to cleanup test data {created_item.id}: {e}")
