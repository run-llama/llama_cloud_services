GIT_ROOT ?= $(shell git rev-parse --show-toplevel)

help:	## Show all Makefile targets.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'

format:	## Run code autoformatters (black).
	uv run pre-commit install
	git ls-files | xargs uv run pre-commit run black --files

lint:	## Run linters: pre-commit (black, ruff, codespell) and mypy
	uv run pre-commit install && git ls-files | xargs uv run pre-commit run --show-diff-on-failure --files

test:	## Run unit tests via pytest
	uv run pytest -v unit_tests/

.PHONY: e2e
e2e:	## Run all tests. Extract tests use lower parallelism due to API rate limits
	uv run pytest -v -n 8 --timeout=300 --session-timeout=1740 tests/extract/
	uv run pytest -v -n 32 --timeout=300 --session-timeout=1740 tests/ --ignore=tests/extract/
