import pytest
from unittest.mock import MagicMock, patch

import llama_cloud_services.index.base as base
from llama_cloud import (
    PipelineEmbeddingConfig_ManagedOpenaiEmbedding,
    Project,
    Pipeline,
    CloudDocument,
)
from llama_index.core.constants import DEFAULT_PROJECT_NAME
from llama_index.core.indices.managed.base import BaseManagedIndex
from llama_index.core.schema import Document
from llama_cloud_services.index import LlamaCloudIndex


# Simple test data as values, not fixtures
TEST_PROJECT = Project(id="proj-123", name="test-project", organization_id="org-123")

EMBEDDING_CONFIG = PipelineEmbeddingConfig_ManagedOpenaiEmbedding(
    type="MANAGED_OPENAI_EMBEDDING"
)
TEST_PIPELINE = Pipeline(
    id="pipe-456",
    name="test-pipeline",
    project_id="proj-123",
    embedding_config=PipelineEmbeddingConfig_ManagedOpenaiEmbedding(
        type="MANAGED_OPENAI_EMBEDDING"
    ),
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock client with sensible defaults."""
    client = MagicMock()
    client.projects.upsert_project.return_value = Project(
        id="default-proj", name=DEFAULT_PROJECT_NAME, organization_id="default-org"
    )
    client.pipelines.upsert_pipeline.return_value = Pipeline(
        id="default-pipe",
        name="default",
        project_id="default-proj",
        embedding_config=EMBEDDING_CONFIG,
    )
    client.pipelines.upsert_batch_pipeline_documents.return_value = [
        CloudDocument(id="doc-1", text="test", metadata={})
    ]
    return client


@pytest.fixture(autouse=True)
def base_patches(mock_client: MagicMock) -> None:
    """Auto-applied patches for all tests."""
    with (
        patch.object(base, "get_client", return_value=mock_client),
        patch.object(
            base,
            "resolve_project_and_pipeline",
            return_value=(TEST_PROJECT, TEST_PIPELINE),
        ),
        patch.object(base.LlamaCloudIndex, "wait_for_completion"),
    ):
        yield


def test_class() -> None:
    names_of_base_classes = [b.__name__ for b in LlamaCloudIndex.__mro__]
    assert BaseManagedIndex.__name__ in names_of_base_classes


def test_conflicting_index_identifiers() -> None:
    with pytest.raises(ValueError):
        LlamaCloudIndex(name="test", pipeline_id="test", index_id="test")


def test_from_documents_uses_provided_project_id(mock_client: MagicMock) -> None:
    provided_project_id = "proj-123"
    organization_id = "org-abc"
    index_name = "my_new_index"

    # Override resolve to return project with provided ID
    test_project = Project(
        id=provided_project_id, name="my_project", organization_id=organization_id
    )
    test_pipeline = Pipeline(
        id="pipe-xyz",
        name=index_name,
        project_id=provided_project_id,
        embedding_config=EMBEDDING_CONFIG,
    )

    with patch.object(
        base, "resolve_project_and_pipeline", return_value=(test_project, test_pipeline)
    ):
        docs = [Document(text="hello")]
        index = LlamaCloudIndex.from_documents(
            documents=docs,
            name=index_name,
            project_id=provided_project_id,
        )

    # Assert - project upsert not called; pipeline uses provided project_id
    mock_client.projects.upsert_project.assert_not_called()
    assert mock_client.pipelines.upsert_pipeline.call_count == 1
    assert (
        mock_client.pipelines.upsert_pipeline.call_args.kwargs["project_id"]
        == provided_project_id
    )
    assert index.project.id == provided_project_id


def test_from_documents_upserts_project_when_project_id_missing(
    mock_client: MagicMock,
) -> None:
    organization_id = "org-xyz"
    index_name = "my_new_index"

    # Project is created when project_id is not provided
    upserted_project = Project(
        id="proj-999", name=DEFAULT_PROJECT_NAME, organization_id=organization_id
    )
    mock_client.projects.upsert_project.return_value = upserted_project

    test_pipeline = Pipeline(
        id="pipe-xyz",
        name=index_name,
        project_id=upserted_project.id,
        embedding_config=EMBEDDING_CONFIG,
    )

    with patch.object(
        base,
        "resolve_project_and_pipeline",
        return_value=(upserted_project, test_pipeline),
    ):
        docs = [Document(text="world")]
        index = LlamaCloudIndex.from_documents(
            documents=docs,
            name=index_name,
            organization_id=organization_id,
        )

    # Assert - project was upserted with org id and default project name
    mock_client.projects.upsert_project.assert_called_once()
    kwargs = mock_client.projects.upsert_project.call_args.kwargs
    assert kwargs["organization_id"] == organization_id
    assert kwargs["request"].name == DEFAULT_PROJECT_NAME

    # Pipeline created under the upserted project id
    assert (
        mock_client.pipelines.upsert_pipeline.call_args.kwargs["project_id"]
        == upserted_project.id
    )
    assert index.project.id == upserted_project.id
