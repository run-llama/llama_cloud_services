import toml  # type: ignore [import]
import json


def test_versions_equal(
    package_data: dict, toml_data: dict, parse_toml_data: dict
) -> None:
    llama_cloud_version = toml_data["project"]["version"]
    package_version = package_data["version"]
    parse_version = parse_toml_data["project"]["version"]
    parse_dep_version = parse_toml_data["project"]["dependencies"][0].split(">=")[1]
    try:
        assert (
            llama_cloud_version == package_version
            and llama_cloud_version == parse_version
            and llama_cloud_version == parse_dep_version
        )
        print("0")
    except AssertionError:
        print("1")


with open("package.json", "r") as p:
    package_data = json.load(p)

with open("pyproject.toml", "r") as t:
    toml_data = toml.load(t)

with open("llama_parse/pyproject.toml", "r") as pt:
    parse_toml_data = toml.load(pt)

test_versions_equal(package_data, toml_data, parse_toml_data)
