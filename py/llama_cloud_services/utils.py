import os
import importlib.metadata
from contextlib import contextmanager
from typing import Generator
import difflib
from llama_cloud.types import StatusEnum, File
import httpx
import packaging.version
from pydantic import BaseModel
from typing import Any, Dict, List, Tuple, Type, Union, Optional
from io import BufferedIOBase, TextIOWrapper
from pathlib import Path
import secrets

# Asyncio error messages
nest_asyncio_err = "cannot be called from a running event loop"
nest_asyncio_msg = (
    "The event loop is already running. "
    "Add `import nest_asyncio; nest_asyncio.apply()` to your code to fix this issue."
)


def check_extra_params(
    model_cls: Type[BaseModel], data: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    # check if one of the parameters is unused, and warn the user
    model_attributes = set(model_cls.model_fields.keys())
    extra_params = [param for param in data.keys() if param not in model_attributes]

    suggestions: List[str] = []
    if extra_params:
        # for each unused parameter, check if it is similar to a valid parameter and suggest a typo correction, else suggest to check the documentation / update the package
        for param in extra_params:
            similar_params = difflib.get_close_matches(
                param, model_attributes, n=1, cutoff=0.8
            )
            if similar_params:
                suggestions.append(
                    f"'{param}' is not a valid parameter. Did you mean '{similar_params[0]}' instead of '{param}'?"
                )
            else:
                suggestions.append(
                    f"'{param}' is not a valid parameter. Please check the documentation or update the package."
                )

    return extra_params, suggestions


def is_terminal_status(status: StatusEnum) -> bool:
    """
    Check if a status is terminal, i.e. the job is done and no more updates are expected.
    Note: this must be updated if the status enum is updated.

    Args:
        status: The status to check

    Returns:
        True if the status is terminal, False otherwise
    """
    return status in {
        StatusEnum.SUCCESS,
        StatusEnum.ERROR,
        StatusEnum.CANCELLED,
        StatusEnum.PARTIAL_SUCCESS,
    }


async def check_for_updates(client: httpx.AsyncClient, quiet: bool = True) -> bool:
    """Check if an SDK update is available.

    Args:
        client: HTTPX client to use.
        quiet: If False, update availability will also be printed to stdout.

    Returns: True if an update is available.

    Raises:
        ValueError: Failed to get a valid release version from PyPI.
    """
    package_name = "llama-cloud-services"
    r = await client.get(f"https://pypi.org/pypi/{package_name}/json")
    version = r.json().get("info", {}).get("version", "")
    if not version:
        raise ValueError("Failed to fetch package info from PyPI")
    latest = packaging.version.parse(version)
    current = packaging.version.parse(importlib.metadata.version(package_name))
    if current < latest:
        if not quiet:
            msg = [
                f"\u26A0\uFE0F {package_name} is out of date",
                f"Current version: {current} | Latest: {latest}",
                "To upgrade: pip install -U --force-reinstall llama-cloud-services",
            ]
            print(os.linesep.join(msg))
        return True
    elif not quiet:
        print(f"{package_name} is up to date")
    return False


@contextmanager
def augment_async_errors() -> Generator[None, None, None]:
    """Context manager to add helpful information for errors due to nested event loops."""
    try:
        yield
    except RuntimeError as e:
        if nest_asyncio_err in str(e):
            raise RuntimeError(nest_asyncio_msg)
        raise


class SourceText:
    """
    A wrapper class for providing text or file input with optional filename specification.

    This class allows you to provide input in multiple ways:
    - Direct text content via text_content parameter
    - File paths as strings or Path objects
    - Raw bytes
    - File-like objects (BufferedIOBase, TextIOWrapper)
    - Already-uploaded file ID via file_id parameter

    Args:
        file: The file input (bytes, file-like object, str path, or Path).
              Mutually exclusive with text_content and file_id.
        text_content: Raw text content to process. Mutually exclusive with file and file_id.
        file_id: ID of an already-uploaded file. Mutually exclusive with file and text_content.
        filename: Optional filename. Required for bytes/file-like objects without names.
                  If not provided, will be auto-generated for text_content or inferred from paths.

    Examples:
        # Direct text input
        source = SourceText(text_content="Hello world")

        # File path
        source = SourceText(file="document.pdf")

        # Bytes with filename
        source = SourceText(file=b"...", filename="document.pdf")

        # File-like object (will read from current position)
        with open("document.pdf", "rb") as f:
            source = SourceText(file=f)

        # Already-uploaded file
        source = SourceText(file_id="file_abc123")
    """

    def __init__(
        self,
        *,
        file: Union[bytes, BufferedIOBase, TextIOWrapper, str, Path, None] = None,
        text_content: Optional[str] = None,
        file_id: Optional[str] = None,
        filename: Optional[str] = None,
    ):
        self.file = file
        self.filename = filename
        self.text_content = text_content
        self.file_id = file_id
        self._validate()

    def _validate(self) -> None:
        """Ensure filename is provided when needed."""
        # Check that exactly one of file, text_content, or file_id is provided
        provided = sum(
            [
                self.file is not None,
                self.text_content is not None,
                self.file_id is not None,
            ]
        )

        if provided == 0:
            raise ValueError("One of file, text_content, or file_id must be provided.")
        elif provided > 1:
            raise ValueError(
                "Only one of file, text_content, or file_id can be provided."
            )

        # If file_id is provided, we don't need filename validation
        if self.file_id is not None:
            return

        if self.text_content is not None:
            if not self.filename:
                random_hex = secrets.token_hex(4)
                self.filename = f"text_input_{random_hex}.txt"
            return

        if isinstance(self.file, (bytes, BufferedIOBase, TextIOWrapper)):
            if not self.filename and hasattr(self.file, "name"):
                self.filename = os.path.basename(str(self.file.name))
            elif self.filename is None and not hasattr(self.file, "name"):
                raise ValueError(
                    "filename must be provided when file is bytes or a file-like object without a name"
                )
        elif isinstance(self.file, (str, Path)):
            if not self.filename:
                self.filename = os.path.basename(str(self.file))
        else:
            raise ValueError(f"Unsupported file type: {type(self.file)}")


# Type alias for file input that can be used across services
FileInput = Union[str, Path, BufferedIOBase, SourceText, File]
