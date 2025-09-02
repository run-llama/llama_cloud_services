# Python

## Installation

This project uses uv. Create a virtual environment, and run `uv sync`

## Versioning (Maintainers only)

Before merging your changes, make sure to bump the versions.

Make a version bump to `pyproject.toml`. If the underlying dependency on the llamacloud platform OpenAPI
sdk needs bumping, make sure to bring that in as well. If updating dependencies, run `uv lock`.

The legacy `llama_parse` package re-exports some of `llama_cloud_services` in the old namespace. The
versions need to be kept consistent to sidecar it with `llama_cloud_services`. Bump it's version in `llama_parse/pyproject.toml`, and also bump it's dependency version of `llama-cloud-services` to match.

**Note**: Don't worry about updating the `llama_parse/poetry.lock` file when bumping versions. The GitHub action will automatically run `poetry lock` for the llama_parse package during the build process (though it doesn't commit the updated lockfile back to the repo).

You can also do this with `./scripts/version-bump.py set 0.x.x` if you have `uv` installed.

Once the change is merged, push a tag `git tag -a v0.x.x -m 0.x.x` and `git push origin v0.x.x`.

This tagging step can be done with `./scripts/version-bump tag`.

# Typescript

## Installation

...

## Versioning

...
