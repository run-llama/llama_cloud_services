import pytest

from llama_cloud_services.parse.temporal import (
    is_heartbeat_timeout_error,
    retry_on_heartbeat_timeout,
)


class FakeTimeoutError(Exception):
    """Mimics temporalio.exceptions.TimeoutError with a type attribute."""

    def __init__(self, timeout_type):
        super().__init__("timeout")
        self.type = timeout_type


class FakeTimeoutType:
    """Mimics temporalio.exceptions.TimeoutType enum."""

    HEARTBEAT = 4
    START_TO_CLOSE = 1


class FakeActivityError(Exception):
    """Mimics temporalio.exceptions.ActivityError with a cause."""

    def __init__(self, cause=None):
        super().__init__("activity error")
        self.__cause__ = cause


# Make the class names match what the code checks
FakeTimeoutError.__name__ = "TimeoutError"
FakeActivityError.__name__ = "ActivityError"


class TestIsHeartbeatTimeoutError:
    def test_detects_activity_error_with_heartbeat_timeout(self):
        timeout_err = FakeTimeoutError(FakeTimeoutType.HEARTBEAT)
        activity_err = FakeActivityError(cause=timeout_err)
        assert is_heartbeat_timeout_error(activity_err) is True

    def test_rejects_activity_error_with_start_to_close_timeout(self):
        timeout_err = FakeTimeoutError(FakeTimeoutType.START_TO_CLOSE)
        activity_err = FakeActivityError(cause=timeout_err)
        assert is_heartbeat_timeout_error(activity_err) is False

    def test_rejects_activity_error_with_non_timeout_cause(self):
        other_err = ValueError("some other error")
        activity_err = FakeActivityError(cause=other_err)
        assert is_heartbeat_timeout_error(activity_err) is False

    def test_detects_heartbeat_timeout_from_message(self):
        err = Exception("activity Heartbeat timeout")
        assert is_heartbeat_timeout_error(err) is True

    def test_detects_heartbeat_timeout_underscore_from_message(self):
        err = Exception("Failed due to heartbeat_timeout")
        assert is_heartbeat_timeout_error(err) is True

    def test_rejects_non_heartbeat_errors(self):
        err = Exception("Connection refused")
        assert is_heartbeat_timeout_error(err) is False

    def test_handles_none_error(self):
        assert is_heartbeat_timeout_error(ValueError()) is False

    def test_detects_heartbeat_timeout_with_enum_value_attr(self):
        """Test with an enum-like type that has .value."""

        class EnumLike:
            value = 4

        timeout_err = FakeTimeoutError(EnumLike())
        activity_err = FakeActivityError(cause=timeout_err)
        assert is_heartbeat_timeout_error(activity_err) is True


class TestRetryOnHeartbeatTimeout:
    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        async def success():
            return "ok"

        result = await retry_on_heartbeat_timeout(success)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retries_on_heartbeat_timeout(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                timeout_err = FakeTimeoutError(FakeTimeoutType.HEARTBEAT)
                raise FakeActivityError(cause=timeout_err)
            return "recovered"

        result = await retry_on_heartbeat_timeout(flaky, max_retries=3)
        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_on_non_heartbeat_errors(self):
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Application error")

        with pytest.raises(ValueError, match="Application error"):
            await retry_on_heartbeat_timeout(always_fail)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_exhausts_retries_on_persistent_heartbeat_timeout(self):
        call_count = 0

        async def always_heartbeat_timeout():
            nonlocal call_count
            call_count += 1
            timeout_err = FakeTimeoutError(FakeTimeoutType.HEARTBEAT)
            raise FakeActivityError(cause=timeout_err)

        with pytest.raises(FakeActivityError):
            await retry_on_heartbeat_timeout(
                always_heartbeat_timeout, max_retries=2
            )
        assert call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_calls_on_retry_callback(self):
        retries_seen = []

        def on_retry(attempt, error):
            retries_seen.append(attempt)

        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                timeout_err = FakeTimeoutError(FakeTimeoutType.HEARTBEAT)
                raise FakeActivityError(cause=timeout_err)
            return "ok"

        result = await retry_on_heartbeat_timeout(
            flaky, max_retries=3, on_retry=on_retry
        )
        assert result == "ok"
        assert retries_seen == [1, 2]

    @pytest.mark.asyncio
    async def test_defaults_to_3_retries(self):
        call_count = 0

        async def always_heartbeat_timeout():
            nonlocal call_count
            call_count += 1
            timeout_err = FakeTimeoutError(FakeTimeoutType.HEARTBEAT)
            raise FakeActivityError(cause=timeout_err)

        with pytest.raises(FakeActivityError):
            await retry_on_heartbeat_timeout(always_heartbeat_timeout)
        assert call_count == 4  # initial + 3 retries

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        async def add(a, b, extra=0):
            return a + b + extra

        result = await retry_on_heartbeat_timeout(add, 1, 2, extra=10)
        assert result == 13

    @pytest.mark.asyncio
    async def test_retries_on_message_match(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("activity Heartbeat timeout")
            return "recovered"

        result = await retry_on_heartbeat_timeout(flaky, max_retries=3)
        assert result == "recovered"
        assert call_count == 2
