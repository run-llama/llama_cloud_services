import difflib
from pydantic import BaseModel
from typing import Any, Dict, List, Tuple, Type


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
