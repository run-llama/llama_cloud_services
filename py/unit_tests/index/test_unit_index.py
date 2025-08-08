import pytest

from llama_index.core.indices.managed.base import BaseManagedIndex
from llama_cloud_services.index import (
    LlamaCloudIndex,
)


def test_class():
    names_of_base_classes = [b.__name__ for b in LlamaCloudIndex.__mro__]
    assert BaseManagedIndex.__name__ in names_of_base_classes


def test_conflicting_index_identifiers():
    with pytest.raises(ValueError):
        LlamaCloudIndex(name="test", pipeline_id="test", index_id="test")
