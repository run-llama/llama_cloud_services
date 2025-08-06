import toml  # type: ignore [import]
import json


def change_parse_dep(data: dict, version: str) -> dict:
    dep, ver = (
        data["project"]["dependencies"][0].split(">=")[0],
        data["project"]["dependencies"][0].split(">=")[1],
    )
    ver = version
    dependency = dep + ">=" + ver
    data["project"]["dependencies"].insert(0, dependency)
    data["project"]["dependencies"].pop(1)
    return data


with open("py/package.json", "r") as p:
    package_data = json.load(p)

with open("py/pyproject.toml", "r") as t:
    toml_data = toml.load(t)

with open("py/llama_parse/pyproject.toml", "r") as pt:
    parse_toml_data = toml.load(pt)

toml_data["project"]["version"] = package_data["version"]
parse_toml_data["project"]["version"] = package_data["version"]
parse_toml_data = change_parse_dep(parse_toml_data, package_data["version"])

with open("py/pyproject.toml", "w") as w:
    toml.dump(toml_data, w)

with open("py/llama_parse/pyproject.toml", "w") as pw:
    toml.dump(parse_toml_data, pw)
