from unittest.mock import Mock

import httpx
import pytest
from pydantic import BaseModel
from llama_cloud_services.utils import check_extra_params, check_for_updates


class MyModel(BaseModel):
    name: str
    age: int
    email: str
    is_active: bool


def test_check_extra_params_no_extra():
    """Test when all parameters are valid - should return empty lists."""
    data = {"name": "John", "age": 25, "email": "john@example.com", "is_active": True}

    extra_params, suggestions = check_extra_params(MyModel, data)

    assert extra_params == []
    assert suggestions == []


def test_check_extra_params_with_typos():
    """Test when there are extra parameters that are close to valid ones (typos)."""
    data = {
        "name": "John",
        "age": 25,
        "emial": "john@example.com",  # typo: emial instead of email
        "is_activ": True,  # typo: is_activ instead of is_active
        "address": "123 Main St",  # completely different parameter
    }

    extra_params, suggestions = check_extra_params(MyModel, data)

    assert len(extra_params) == 3
    assert "emial" in extra_params
    assert "is_activ" in extra_params
    assert "address" in extra_params

    # Check that typo suggestions are provided
    assert len(suggestions) == 3
    assert "Did you mean 'email' instead of 'emial'?" in suggestions[0]
    assert "Did you mean 'is_active' instead of 'is_activ'?" in suggestions[1]
    assert "check the documentation or update the package" in suggestions[2]


def test_check_extra_params_completely_invalid():
    """Test when there are extra parameters with no close matches."""
    data = {
        "name": "John",
        "xyz": "invalid",
        "random_field": 123,
        "completely_different": True,
    }

    extra_params, suggestions = check_extra_params(MyModel, data)

    assert len(extra_params) == 3
    assert "xyz" in extra_params
    assert "random_field" in extra_params
    assert "completely_different" in extra_params

    # All suggestions should be generic (no close matches)
    assert len(suggestions) == 3
    for suggestion in suggestions:
        assert "check the documentation or update the package" in suggestion
        assert "Did you mean" not in suggestion


@pytest.mark.asyncio
async def test_check_for_updates(capsys: pytest.CaptureFixture):
    """Test update checker."""

    mock_response = Mock()
    mock_client = Mock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    mock_response.json.return_value = {"info": {"version": "0.0.0"}}
    assert not await check_for_updates(mock_client)
    out, err = capsys.readouterr()
    assert not out and not err

    assert not await check_for_updates(mock_client, quiet=False)
    out, _ = capsys.readouterr()
    assert "up to date" in out

    mock_response.json.return_value = {"info": {"version": "999.0.0"}}
    assert await check_for_updates(mock_client)
    out, err = capsys.readouterr()
    assert not out and not err

    assert await check_for_updates(mock_client, quiet=False)
    out, _ = capsys.readouterr()
    assert "out of date" in out
