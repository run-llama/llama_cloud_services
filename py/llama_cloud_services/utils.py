import os
import importlib.metadata
from contextlib import contextmanager
from typing import Generator
import difflib
from llama_cloud.types import StatusEnum
import httpx
import packaging.version
from pydantic import BaseModel
from typing import Any, Dict, List, Tuple, Type

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
