from typing import Any, Dict, List, Union


def is_jupyter() -> bool:
    """Check if we're running in a Jupyter environment."""
    try:
        from IPython import get_ipython

        return get_ipython().__class__.__name__ == "ZMQInteractiveShell"
    except (ImportError, AttributeError):
        return False


JSONType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
JSONObjectType = Dict[str, JSONType]


class ExperimentalWarning(Warning):
    """Warning for experimental features."""

    pass
