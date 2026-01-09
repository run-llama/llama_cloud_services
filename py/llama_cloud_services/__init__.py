import warnings

from llama_cloud_services.parse import LlamaParse
from llama_cloud_services.extract import LlamaExtract, ExtractionAgent
from llama_cloud_services.utils import SourceText, FileInput
from llama_cloud_services.constants import EU_BASE_URL
from llama_cloud_services.index import (
    LlamaCloudCompositeRetriever,
    LlamaCloudIndex,
    LlamaCloudRetriever,
)

# Emit deprecation warning once when package is imported
warnings.warn(
    "This package (llama-cloud-services) is deprecated and will be maintained until May 1, 2026. "
    "Please migrate to the new package: pip install llama-cloud>=1.0 "
    "(https://github.com/run-llama/llama-cloud-py). "
    "The new package provides the same functionality with improved performance and support.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "LlamaParse",
    "LlamaExtract",
    "ExtractionAgent",
    "SourceText",
    "FileInput",
    "EU_BASE_URL",
    "LlamaCloudIndex",
    "LlamaCloudRetriever",
    "LlamaCloudCompositeRetriever",
]
