#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["click", "tomlkit"]
# ///

import click
import subprocess
import sys
import tomlkit
from pathlib import Path
import json


def get_current_versions() -> tuple[str, str, str, str | None]:
    """Get current versions from both pyproject.toml files and TS package.json."""
    # Read main pyproject.toml
    main_content = Path("py/pyproject.toml").read_text()
    main_doc = tomlkit.parse(main_content)
    main_version = main_doc["project"]["version"]

    # Read llama_parse/pyproject.toml
    llama_parse_content = Path("py/llama_parse/pyproject.toml").read_text()
    llama_parse_doc = tomlkit.parse(llama_parse_content)
    llama_parse_version = llama_parse_doc["project"]["version"]
    # Find llama-cloud-services dependency in the dependencies list
    dependency_version = None
    for dep in llama_parse_doc["project"]["dependencies"]:
        if isinstance(dep, str) and dep.startswith("llama-cloud-services"):
            dependency_version = (
                dep.split("==")[1]
                if "==" in dep
                else dep.split(">=")[1]
                if ">=" in dep
                else None
            )
            break

    # Read TypeScript package.json version via helper
    ts_version: str = get_ts_version()

    return (
        str(main_version),
        str(llama_parse_version),
        str(dependency_version),
        str(ts_version) if ts_version is not None else None,
    )


def validate_versions(
    main_version: str,
    llama_parse_version: str,
    dependency_version: str,
) -> list[str]:
    """Validate that versions are consistent and return warnings."""
    warnings = []

    if main_version != llama_parse_version:
        warnings.append(
            f"Version mismatch: main={main_version}, llama_parse={llama_parse_version}"
        )

    # Extract version from dependency string (e.g., ">=0.6.51" -> "0.6.51")
    if dependency_version and dependency_version.startswith(">="):
        dep_ver = dependency_version[2:]
        if dep_ver != main_version:
            warnings.append(
                f"Dependency version mismatch: dependency={dep_ver}, main={main_version}"
            )

    return warnings


def set_version(version: str) -> None:
    """Set version across Python projects (no TS change)."""
    # Update main pyproject.toml
    main_content = Path("py/pyproject.toml").read_text()
    main_doc = tomlkit.parse(main_content)
    main_doc["project"]["version"] = version
    Path("py/pyproject.toml").write_text(tomlkit.dumps(main_doc))

    # Update llama_parse/pyproject.toml
    llama_parse_content = Path("py/llama_parse/pyproject.toml").read_text()
    llama_parse_doc = tomlkit.parse(llama_parse_content)
    llama_parse_doc["project"]["version"] = version
    for dep_index, dep in enumerate(llama_parse_doc["project"]["dependencies"]):
        if isinstance(dep, str) and dep.startswith("llama-cloud-services"):
            llama_parse_doc["project"]["dependencies"][
                dep_index
            ] = f"llama-cloud-services>={version}"
            break
    Path("py/llama_parse/pyproject.toml").write_text(tomlkit.dumps(llama_parse_doc))

    click.echo(f"Updated Python versions to {version}")


def get_ts_version() -> str:
    """Read TypeScript package.json version (if present)."""
    ts_package_path = Path("ts/llama_cloud_services/package.json")
    package_data = json.loads(ts_package_path.read_text())
    data = package_data.get("version")
    if data is None:
        raise RuntimeError("TypeScript package.json version not found")
    return data


def set_ts_version(version: str) -> None:
    """Set TypeScript package.json version only."""
    ts_package_path = Path("ts/llama_cloud_services/package.json")
    package_data = json.loads(ts_package_path.read_text())
    package_data["version"] = version
    ts_package_path.write_text(json.dumps(package_data, indent=2) + "\n")
    click.echo(f"Updated TypeScript package.json version to {version}")


def get_current_branch() -> str:
    """Get the current git branch."""
    result = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def create_if_not_exists(version: str) -> str:
    """Create a git tag and push it."""
    current_branch = get_current_branch()
    if current_branch != "main":
        click.echo(
            f"Error: Not on main branch (currently on {current_branch})", err=True
        )
        sys.exit(1)

    tag_name = f"v{version}" if version[0].isdigit() else version
    if not tag_exists(tag_name):
        # Create tag
        subprocess.run(["git", "tag", tag_name], check=True)
        click.echo(f"Created tag {tag_name}")
    else:
        click.echo(f"Tag {tag_name} already exists")
    return tag_name


def tag_exists(tag_name: str) -> bool:
    """Check if a git tag exists."""
    result = subprocess.run(
        ["git", "tag", "-l", tag_name], capture_output=True, text=True, check=True
    )
    return tag_name in result.stdout.strip()


def push_tag(tag_name: str) -> None:
    """Push a git tag."""
    subprocess.run(["git", "push", "origin", tag_name], check=True)
    click.echo(f"Pushed tag {tag_name}")


@click.group()
def cli() -> None:
    """Version management for llama-cloud-services."""
    pass


@cli.command()
def get() -> None:
    """Get current versions and show validation warnings."""
    (
        main_version,
        llama_parse_version,
        dependency_version,
        ts_version,
    ) = get_current_versions()

    click.echo("Current versions:")
    click.echo(f"  llama-cloud-services: {main_version}")
    click.echo(f"  llama-parse: {llama_parse_version}")
    click.echo(f"  dependency reference: {dependency_version}")
    click.echo(f"  typescript package: {ts_version}")

    warnings = validate_versions(main_version, llama_parse_version, dependency_version)
    if warnings:
        click.echo("\nValidation warnings:")
        for warning in warnings:
            click.echo(f"  ⚠️  {warning}")
    else:
        click.echo("\n✅ All versions are consistent")


@cli.command()
@click.argument("version")
@click.option("--js", is_flag=True, help="Update TypeScript package.json only")
def set(version: str, js: bool) -> None:
    """Set version for Python, TypeScript, or both (default: Python only)."""

    if js:
        set_ts_version(version)
        return
    else:
        set_version(version)


@cli.command()
@click.option(
    "--version", help="Version to tag (uses current version if not specified)"
)
@click.option(
    "--push",
    is_flag=True,
    help="Push the tag to the remote repository",
)
@click.option(
    "--js",
    is_flag=True,
    help="tag TypeScript package.json only",
)
def tag(version: str | None = None, push: bool = False, js: bool = False) -> None:
    """Create and push a git tag for the current version."""
    if not version:
        main_version, _, _, js_version = get_current_versions()
        version = f"llama-cloud-services@{js_version}" if js else main_version

    tag_name = create_if_not_exists(version)
    if push:
        push_tag(tag_name)


if __name__ == "__main__":
    cli()
