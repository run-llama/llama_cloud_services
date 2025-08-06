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

### Pre-Commit Versioning

Once you made your changes and tested them, **prior to committing** you should create a changeset to document your changes:

```bash
pnpm pre-commit-version
```

This will prompt you to describe your changes and select the appropriate version bump type. The changeset system will automatically handle version bumps for both TypeScript and Python packages when your PR is merged.

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

Once you made your changes and tested them, **prior to committing** you should create a changeset:

```bash
pnpm pre-commit-version
```

This will prompt you to describe your changes and select the appropriate version bump type. The changeset system will automatically handle version bumps for both TypeScript and Python packages when your PR is merged.

### Pre-commit checks

Before you commit, your files should pass the linting and formatting requirements. In order to do that, run (from the root folder):

```bash
pnpm pre-commit
```

The files will be then automatically linted and formatted according to the requirements.

## TypeScript _and_ Python

If you change **both PY and TS**, create a changeset as normal:

```bash
pnpm pre-commit-version
```

The changeset system will automatically detect that both packages should be updated.

## Release (maintainers only)

The release process is now automated using changesets:

1. **Version Bump PRs**: When changesets are present on main, a version bump PR is automatically created
2. **Release**: When the version bump PR is merged, tags are created and packages are published automatically

### Manual Release

For manual releases, create tags manually:

```bash
# Create and push tags to trigger release workflows
git tag v0.7.0
git tag llama-cloud-services@0.7.0
git push origin v0.7.0 llama-cloud-services@0.7.0
```

### Manual Version Management

For testing or manual version management:

```bash
# Check version status
./scripts/changeset-version.py status

# Set a specific version across all packages
./scripts/changeset-version.py set-version 0.7.0

# Apply pending changesets (propagates to Python packages)
./scripts/changeset-version.py apply

# Build and publish all packages (uses changesets)
pnpm release
```
