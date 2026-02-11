import warnings
from llama_cloud_services.parse import (  # type: ignore[attr-defined]
    LlamaParse,
    ResultType,
    ParsingMode,
    FailedPageMode,
)

warnings.warn(
    "The 'llama-parse' package is deprecated and will no longer receive updates. "
    "Please migrate to the new unified SDK. "
    "See https://developers.llamaindex.ai/python/cloud/llamaparse/getting_started/ "
    "and https://github.com/run-llama/llama-cloud-py/blob/main/README.md for migration instructions.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["LlamaParse", "ResultType", "ParsingMode", "FailedPageMode"]
