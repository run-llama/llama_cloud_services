# Contribute to `llama-cloud-services`

## Common Patterns

### Issues

One of the forms of contribution can be issues.

Issues should be used when there are bugs or feature request you would like to bring to the attention of the maintainers.

When opening an issue:

- preferably, use the provided templates
- check for other issues (closed and open) to avoid duplicates
- try to be detailed and specific, reporting all the pieces the maintainer would need to have in order to reproduce your issue.

### Pull requests

In order to open a valid pull request:

- Fork the repository
- Checkout a secondary branch (common prefixes for secondary branches include: `fix`, `feat`, `chore`, `docs`). We tend to prefer the naming convention that uses `/`, such as: `fix/your-awesome-bug-fix`.
- Add and commit the changes to the secondary branch, following language-specific logic (see below)
- When the changes are pushed to your branch, open a pull request

## Python

### Set Up

The two python packages, which can be found under `py/llama-cloud-services-py/`, are:

- `llama-cloud-services`
- `llama-parse`

> [!NOTE]
>
> `llama-parse` mostly re-exports from `llama-cloud-services`, so you should not modify that directly.

These packages are managed through [uv](https://docs.astral.sh/uv/), so make sure to have uv [installed](https://docs.astral.sh/uv/getting-started/installation/).

### Tests

It is important to make sure all tests pass after your changes, and cover new features with suitable unit tests.

Tests are found in `py/llama-cloud-services-py/tests/` and you can execute them with:

```bash
pytest tests/**/test_*.py
```

### Pre-Commit Versioning

Once you made your changes and tested them, **prior to committing** you should run (from the root folder) two commands to automatically bump the version of python packages:

1. `pnpm pre-commit-version`: this will prompt you to choose what package's version you want to bump and what kind of bump you want to perform. Choose `@llama_cloud_services/llama-cloud-services-py` for python and choose the version bump according to the type of changing you made.
2. `pnpm new-version-py`: this will bump the version in the `pyproject.toml` for all the python packages

### Pre-commit checks

Before you commit, your files should pass the linting and formatting requirements. In order to do that, you should have `pre-commit` installed and set-up in your repository:

```bash
pip install pre-commit
pre-commit install
```

Once you have that set up, the files will be automatically linted and formatted according to the requirements.

## TypeScript

### Set Up

The TypeScript package, which can be found under `ts/llama_cloud_services/`, is managed through [`pnpm`](https://pnpm.io), so make sure to have it [installed](https://pnpm.io/installation).

In order to be able to run and test the package, make sure to install all the dependencies:

```bash
pnpm install
```

### Activate Test Mode

In order to activate test mode (to dynamically test your changes while you are performing them) you can use:

```bash
pnpm turbo run dev
```

### Test

It is important to make sure all tests pass after your changes, and cover new features with suitable unit tests.

Tests are found in `ts/llama_cloud_services/tests/` and you can execute them with:

```bash
pnpm test
```

### Pre-Commit Versioning

Once you made your changes and tested them, **prior to committing** you should run (from the root folder) two commands to automatically bump the version of python packages:

1. `pnpm pre-commit-version`: this will prompt you to choose what package's version you want to bump and what kind of bump you want to perform. Choose `llama-cloud-services` for TypeScript and choose the version bump according to the type of changing you made.
2. `pnpm new-version-ts`: this will build the package and bump the version in `package.json`.

### Pre-commit checks

Before you commit, your files should pass the linting and formatting requirements. In order to do that, run (from the root folder):

```bash
pnpm pre-commit
```

The files will be then automatically linted and formatted according to the requirements.

## TypeScript _and_ Python

If you change **both PY and TS**, for versioning run:

```bash
pnpm pre-commit-version # choose both packages
pnpm new-version # bumps the version for both packages
```

## Release (maintainers only)

### Python

To release `llama-cloud-services` and `llama-parse` in Python, run:

```bash
git checkout main
git pull
git tag <your-version> # e.g. v0.7.0
git push <your-version>
```

> [!NOTE]
>
> The tag must start with `v`

This will trigger the release workflow automatically.

### TypeScript

To release `llama-cloud-services` in TypeScript, run:

```bash
git checkout main
git pull
git tag llama-cloud-services@<your-version> # e.g. llama-cloud-services@0.3.0
git push origin llama-cloud-services@<your-version>
```

This will trigger the release workflow automatically.
