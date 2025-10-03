#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["click", "tomlkit", "packaging"]
# ///

"""
This is a script called by the changeset bot. Normally changeset can do the following things, but this is a mixed ts and python repo, so we need to do some extra things.

There's 2 things this does:
- Versioning: Makes changes that may be committed with the newest version.
- Releasing/Tagging: After versions are changed, we check each package to see if its released, and if not, we release it and tag it.

"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List
import urllib.request
import urllib.error

import click
import tomlkit
from packaging.version import Version


def _run_command(
    cmd: List[str], check: bool = True, capture: bool = True, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(
        cmd, check=check, capture_output=capture, text=True, cwd=cwd or Path.cwd()
    )


def update_python_versions(version: str) -> None:
    """llama-cloud-services and llama-parse share a version. llama-parse is just a silly sidecar that proxies to llama-cloud-services
    for compatibility.

    This function updates the version in both pyproject.toml files.
    """
    # Update main pyproject.toml
    main_path = Path("py/pyproject.toml")
    main_content = main_path.read_text()
    main_doc = tomlkit.parse(main_content)
    if main_doc["project"]["version"] != version:
        click.echo(f"Updating llama-cloud-services version to {version}")
        main_doc["project"]["version"] = version
    main_path.write_text(tomlkit.dumps(main_doc))

    # Update llama_parse/pyproject.toml
    parse_path = Path("py/llama_parse/pyproject.toml")
    parse_content = parse_path.read_text()
    parse_doc = tomlkit.parse(parse_content)
    if parse_doc["project"]["version"] != version:
        click.echo(f"Updating llama-parse version to {version}")
        parse_doc["project"]["version"] = version
        parse_path.write_text(tomlkit.dumps(parse_doc))

    # Update the dependency reference
    dependencies = parse_doc["project"]["dependencies"]
    for i, dep in enumerate(dependencies):
        if isinstance(dep, str) and dep.startswith("llama-cloud-services"):
            dependencies[i] = f"llama-cloud-services>={version}"
            break

    parse_path.write_text(tomlkit.dumps(parse_doc))

    click.echo(f"Updated Python packages to version {version}")


def lock_python_dependencies() -> None:
    """Lock Python dependencies."""
    try:
        _run_command(["uv", "lock"], capture=False)
        click.echo("Locked Python dependencies")
    except subprocess.CalledProcessError as e:
        click.echo(f"Warning: Failed to lock Python dependencies: {e}", err=True)


@click.group()
def cli() -> None:
    """Changeset-based version management for llama-cloud-services."""
    pass


@cli.command()
def version() -> None:
    """Apply changeset versions, and propagate them to Python packages."""
    # First, run changeset version to update all package.json files (including py/package.json)
    _run_command(["npx", "@changesets/cli", "version"], capture=False, check=True)

    # Get the updated Python package version from py/package.json (updated by changesets)
    py_package_path = Path("py/package.json")
    if not py_package_path.exists():
        click.echo("Python package.json not found", err=True)
        sys.exit(1)

    with open(py_package_path) as f:
        py_package = json.load(f)

    new_version = py_package["version"]
    # Update Python pyproject.toml files based on the package.json version
    update_python_versions(new_version)

    click.echo(f"Successfully propagated version {new_version} to all Python packages")


@cli.command()
@click.option("--tag", is_flag=True, help="Tag the packages after publishing")
@click.option("--dry-run", is_flag=True, help="Dry run the publish")
def publish(tag: bool, dry_run: bool) -> None:
    """Publish all packages."""
    # move to the root
    os.chdir(Path(__file__).parent.parent)

    if not os.getenv("NPM_TOKEN"):
        click.echo("NPM_TOKEN is not set, skipping publish", err=True)
        raise click.Abort("No token set")
    if not os.getenv("UV_PUBLISH_TOKEN"):
        click.echo("UV_PUBLISH_TOKEN is not set, skipping publish", err=True)
        raise click.Abort("No token set")
    if not os.getenv("LLAMA_PARSE_PYPI_TOKEN"):
        click.echo("LLAMA_PARSE_PYPI_TOKEN is not set, skipping publish", err=True)
        raise click.Abort("No token set")

    # not general script. Just checks each of the 2 packages to see if they need to be published.
    maybe_publish_ts_package(dry_run)
    maybe_publish_py_packages(dry_run)

    if tag:
        if dry_run:
            click.echo("Dry run, skipping tag. Would run:")
            click.echo("  npx @changesets/cli tag")
            click.echo("  git push --tags")
            return
        else:
            _run_command(["npx", "@changesets/cli", "tag"], check=True, capture=True)
            _run_command(["git", "push", "--tags"], check=True, capture=True)


def maybe_publish_ts_package(dry_run: bool) -> None:
    """Publish the ts package if it needs to be published."""
    target_dir = Path("ts/llama_cloud_services")
    ts_path_package = target_dir / "package.json"
    package_json = json.loads(ts_path_package.read_text())
    version = package_json["version"]

    # Check if this version is already published on npm
    result = _run_command(
        ["npm", "view", "llama-cloud-services", "versions", "--json"],
        check=True,
        capture=True,
        cwd=target_dir,
    )

    published_versions = json.loads(result.stdout)
    if version in published_versions:
        click.echo(
            f"npm  package llama-cloud-services@{version} already published, skipping"
        )
        return
    click.echo(f"Publishing llama-cloud-services@{version}")
    # defer to the package.json publish script
    if dry_run:
        click.echo("Dry run, skipping publish. Would run:")
        click.echo("  pnpm run publish")
        return
    else:
        output = _run_command(
            ["pnpm", "runpublish"], check=True, capture=True, cwd=target_dir
        )
        click.echo(output.stdout)


def maybe_publish_py_packages(dry_run: bool) -> None:
    """Publish the py packages if they need to be published."""
    for pyproject in list(Path("py").glob("*/pyproject.toml")) + [
        Path("py/pyproject.toml")
    ]:
        name, version = current_version(pyproject)
        if is_published(name, version):
            click.echo(f"PyPI package {name}@{version} already published, skipping")
            continue
        click.echo(f"Publishing {name}@{version}")

        # Use different tokens for different packages
        env = os.environ.copy()
        if name == "llama-parse":
            # llama-parse uses its own token
            env["UV_PUBLISH_TOKEN"] = os.environ["LLAMA_PARSE_PYPI_TOKEN"]
        else:
            # llama-cloud-services uses the main PyPI token
            env["UV_PUBLISH_TOKEN"] = os.environ["UV_PUBLISH_TOKEN"]

        if dry_run:
            token = env["UV_PUBLISH_TOKEN"]
            summary = (token[:3] + "***") if len(token) <= 6 else token[:6] + "****"
            click.echo(
                f"Dry run, skipping publish. Would run with publish token {summary}:"
            )
            click.echo("  uv publish --dry-run")
            return
        else:
            result = subprocess.run(
                ["uv", "publish"],
                check=True,
                capture_output=True,
                text=True,
                cwd=pyproject.parent,
                env=env,
            )
            click.echo(result.stdout)


def current_version(pyproject: Path) -> tuple[str, str]:
    """Return (package_name, version_str) taken from the given pyproject.toml."""
    doc = tomlkit.parse(pyproject.read_text())
    name = doc["project"]["name"]
    version = str(Version(doc["project"]["version"]))  # normalise
    return name, version


def is_published(
    name: str, version: str, index_url: str = "https://pypi.org/pypi"
) -> bool:
    """
    True  → `<name>==<version>` exists on the given index
    False → package missing *or* version missing
    """
    url = f"{index_url.rstrip('/')}/{name}/json"
    try:
        data = json.load(urllib.request.urlopen(url))
    except urllib.error.HTTPError as e:  # 404 → package not published at all
        if e.code == 404:
            return False
        raise  # any other error should surface
    return version in data["releases"]  # keys are version strings


if __name__ == "__main__":
    cli()
