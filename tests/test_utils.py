from pydantic import BaseModel
from llama_cloud_services.utils import check_extra_params


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
