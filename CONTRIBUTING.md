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

## Pre-commit Requirements

Before committing your changes, you need to complete two important steps:

### 1. Create a Changeset

Document your changes by creating a changeset:

```bash
npx @changesets/cli add
# or `pnpm pre-commit-version`
```

This will prompt you to describe your changes and select the appropriate version bump type. The changeset system will automatically handle version bumps for both TypeScript and Python packages when your PR is merged.

### 2. Run Pre-commit Checks

Ensure your code meets linting and formatting requirements:

**For Python changes:**

```bash
# Install pre-commit (one-time setup)
pip install pre-commit
pre-commit install

# Files will be automatically linted/formatted on commit
```

**For TypeScript changes:**

```bash
# Run from the root folder
pnpm pre-commit
```

**For mixed Python and TypeScript changes:**
Run both the pre-commit tool (for Python) and `pnpm pre-commit` (for TypeScript).

## Python

### Set Up

The two python packages, which can be found under `py/`, are:

- `llama-cloud-services`
- `llama-parse`

> [!NOTE]
>
> `llama-parse` mostly re-exports from `llama-cloud-services`, so you should not modify that directly.

These packages are managed through [uv](https://docs.astral.sh/uv/), so make sure to have uv [installed](https://docs.astral.sh/uv/getting-started/installation/).

### Tests

It is important to make sure all tests pass after your changes, and cover new features with suitable unit tests.

Tests are found in `py/tests/` (end to end) and `py/unit_tests/` (unit tests, no API key required) and you can execute them with:

```bash
pytest tests/ unit_tests/
```

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

## Release (maintainers only)

The release process is now automated using changesets:

1. **Version Bump PRs**: When changesets are present on main, a version bump PR is automatically created
2. **Release**: When the version bump PR is merged, tags are created and packages are published automatically
