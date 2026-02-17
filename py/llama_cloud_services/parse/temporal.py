"""Utilities for retrying LlamaParse activities in Temporal
specifically when they fail due to activity heartbeat timeout.

These utilities detect Temporal's ActivityError wrapping a TimeoutError
with timeout_type HEARTBEAT, without requiring a direct dependency on the
Temporal SDK.

Usage in a Temporal workflow::

    from temporalio import workflow
    from llama_cloud_services.parse.temporal import retry_on_heartbeat_timeout

    @workflow.defn
    class ParseWorkflow:
        @workflow.run
        async def run(self, input: ParseInput) -> ParseResult:
            parse_activity = workflow.start_activity(
                "llama_parse",
                input,
                start_to_close_timeout=timedelta(minutes=30),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=1),  # disable built-in retry
            )
            return await retry_on_heartbeat_timeout(parse_activity)
"""

import logging
from typing import Any, Awaitable, Callable, Optional, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)

# Temporal TimeoutType enum value for HEARTBEAT (from temporalio proto)
_TIMEOUT_TYPE_HEARTBEAT = 4


def is_heartbeat_timeout_error(error: BaseException) -> bool:
    """Check if an error is a Temporal activity heartbeat timeout error.

    Detects both the structured Temporal error types (ActivityError wrapping
    TimeoutError with timeout_type HEARTBEAT) and fallback string matching
    on the error message.

    Works with the ``temporalio`` Python SDK error types without requiring
    a direct import.

    Args:
        error: The exception to check.

    Returns:
        True if the error represents a heartbeat timeout.
    """
    error_type_name = type(error).__name__

    # Check for Temporal's ActivityError → TimeoutError chain
    if error_type_name in ("ActivityError", "ActivityFailure"):
        cause = getattr(error, "cause", None) or error.__cause__
        if cause is not None:
            cause_type_name = type(cause).__name__
            if cause_type_name in ("TimeoutError", "TimeoutFailure"):
                timeout_type = getattr(cause, "type", None) or getattr(
                    cause, "timeout_type", None
                )
                if timeout_type is not None:
                    # Handle both enum and int representations
                    timeout_type_val = (
                        timeout_type.value
                        if hasattr(timeout_type, "value")
                        else timeout_type
                    )
                    return timeout_type_val == _TIMEOUT_TYPE_HEARTBEAT

    # Fallback: match on error message
    message = str(error).lower()
    return "heartbeat timeout" in message or "heartbeat_timeout" in message


async def retry_on_heartbeat_timeout(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = 3,
    on_retry: Optional[Callable[[int, BaseException], None]] = None,
    **kwargs: Any,
) -> T:
    """Retry an async function only when it fails with a heartbeat timeout error.

    All other errors are raised immediately without retry.

    Designed for use in Temporal workflows to wrap activity calls so that
    transient heartbeat timeouts (e.g. from SIGTERM, event-loop blocking)
    are automatically retried while genuine failures propagate immediately.

    Args:
        fn: The async function to execute (typically a Temporal activity call).
        *args: Positional arguments passed to ``fn``.
        max_retries: Maximum number of retry attempts after the initial try
            (default: 3).
        on_retry: Optional callback invoked before each retry with the attempt
            number and the error.
        **kwargs: Keyword arguments passed to ``fn``.

    Returns:
        The result of the function.

    Raises:
        The original exception if it is not a heartbeat timeout or retries
        are exhausted.
    """
    last_error: Optional[BaseException] = None

    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except BaseException as err:
            last_error = err
            if is_heartbeat_timeout_error(err) and attempt < max_retries:
                logger.warning(
                    "LlamaParse activity failed with heartbeat timeout "
                    "(attempt %d/%d), retrying...",
                    attempt + 1,
                    max_retries,
                )
                if on_retry:
                    on_retry(attempt + 1, err)
                continue
            raise

    # Should not reach here, but satisfy type checker
    assert last_error is not None
    raise last_error
