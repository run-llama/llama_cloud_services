#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["click", "tomlkit", "packaging"]
# ///

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import tomlkit
from packaging.version import Version


def run_command(cmd: List[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        cwd=Path.cwd()
    )


def get_changeset_status() -> Optional[Dict]:
    """Get the current changeset status."""
    try:
        result = run_command(["pnpm", "changeset", "status", "--output", ".changeset/status.json"])
        if result.returncode != 0:
            return None
        
        status_file = Path(".changeset/status.json")
        if not status_file.exists():
            return None
            
        with open(status_file) as f:
            status = json.load(f)
        
        # Clean up the status file
        status_file.unlink()
        return status
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return None


def update_python_versions(version: str) -> None:
    """Update Python package versions using tomlkit to preserve formatting."""
    # Update main pyproject.toml
    main_path = Path("py/pyproject.toml")
    main_content = main_path.read_text()
    main_doc = tomlkit.parse(main_content)
    main_doc["project"]["version"] = version
    main_path.write_text(tomlkit.dumps(main_doc))
    
    # Update llama_parse/pyproject.toml
    parse_path = Path("py/llama_parse/pyproject.toml")
    parse_content = parse_path.read_text()
    parse_doc = tomlkit.parse(parse_content)
    parse_doc["project"]["version"] = version
    
    # Update the dependency reference
    dependencies = parse_doc["project"]["dependencies"]
    for i, dep in enumerate(dependencies):
        if isinstance(dep, str) and dep.startswith("llama-cloud-services"):
            dependencies[i] = f"llama-cloud-services>={version}"
            break
    
    parse_path.write_text(tomlkit.dumps(parse_doc))
    
    click.echo(f"Updated Python packages to version {version}")


# update_python_package_json removed - changesets handles py/package.json directly


def lock_python_dependencies() -> None:
    """Lock Python dependencies."""
    try:
        run_command(["uv", "lock"], capture=False)
        click.echo("Locked Python dependencies")
    except subprocess.CalledProcessError as e:
        click.echo(f"Warning: Failed to lock Python dependencies: {e}", err=True)


# Tag functionality removed for now - will be handled by GitHub Actions


def validate_python_versions() -> bool:
    """Validate that Python versions are consistent."""
    try:
        # Read main pyproject.toml
        main_path = Path("py/pyproject.toml")
        main_content = main_path.read_text()
        main_doc = tomlkit.parse(main_content)
        main_version = str(main_doc["project"]["version"])
        
        # Read llama_parse pyproject.toml
        parse_path = Path("py/llama_parse/pyproject.toml")
        parse_content = parse_path.read_text()
        parse_doc = tomlkit.parse(parse_content)
        parse_version = str(parse_doc["project"]["version"])
        
        # Check dependency version
        dependencies = parse_doc["project"]["dependencies"]
        dep_version = None
        for dep in dependencies:
            if isinstance(dep, str) and dep.startswith("llama-cloud-services"):
                if ">=" in dep:
                    dep_version = dep.split(">=")[1]
                break
        
        # Read package.json if it exists
        py_package_path = Path("py/package.json")
        package_version = None
        if py_package_path.exists():
            with open(py_package_path) as f:
                data = json.load(f)
            package_version = data.get("version")
        
        # Validate consistency
        versions_match = (
            main_version == parse_version and
            (dep_version is None or dep_version == main_version) and
            (package_version is None or package_version == main_version)
        )
        
        if not versions_match:
            click.echo(f"Version mismatch: main={main_version}, parse={parse_version}, "
                      f"dep={dep_version}, package={package_version}", err=True)
        
        return versions_match
        
    except Exception as e:
        click.echo(f"Error validating versions: {e}", err=True)
        return False


@click.group()
def cli():
    """Changeset-based version management for llama-cloud-services."""
    pass


@cli.command()
def apply():
    """Apply changeset version changes to Python packages."""
    # First, run changeset version to update all package.json files (including py/package.json)
    try:
        result = run_command(["pnpm", "changeset", "version"], capture=False)
        if result.returncode != 0:
            click.echo("Failed to apply changeset versions", err=True)
            sys.exit(1)
    except subprocess.CalledProcessError:
        click.echo("Failed to apply changeset versions", err=True)
        sys.exit(1)
    
    # Get the updated Python package version from py/package.json (updated by changesets)
    py_package_path = Path("py/package.json")
    if not py_package_path.exists():
        click.echo("Python package.json not found", err=True)
        sys.exit(1)
    
    with open(py_package_path) as f:
        py_package = json.load(f)
    
    new_version = py_package["version"]
    click.echo(f"Propagating version {new_version} from py/package.json to pyproject.toml files")
    
    # Update Python pyproject.toml files based on the package.json version
    update_python_versions(new_version)
    
    # Lock dependencies
    lock_python_dependencies()
    
    # Validate
    if not validate_python_versions():
        click.echo("Version validation failed", err=True)
        sys.exit(1)
    
    click.echo(f"Successfully propagated version {new_version} to all Python packages")


@cli.command()
def status():
    """Show current changeset status and version consistency."""
    changeset_status = get_changeset_status()
    
    if changeset_status and changeset_status.get("changesets"):
        click.echo("Pending changesets found:")
        for changeset in changeset_status["changesets"]:
            click.echo(f"  - {changeset.get('summary', 'No summary')}")
            for release in changeset.get("releases", []):
                click.echo(f"    {release['name']}: {release['type']}")
    else:
        click.echo("No pending changesets")
    
    # Check version consistency
    if validate_python_versions():
        click.echo("✅ All versions are consistent")
    else:
        click.echo("❌ Version inconsistencies detected")


@cli.command()
@click.argument("version")
def set_version(version: str):
    """Manually set version across all packages."""
    try:
        # Validate version format
        Version(version)
    except Exception:
        click.echo(f"Invalid version format: {version}", err=True)
        sys.exit(1)
    
    # Update TypeScript package
    ts_package_path = Path("ts/llama_cloud_services/package.json")
    if ts_package_path.exists():
        with open(ts_package_path) as f:
            ts_package = json.load(f)
        ts_package["version"] = version
        with open(ts_package_path, "w") as f:
            json.dump(ts_package, f, indent=2)
        click.echo(f"Updated TypeScript package to version {version}")
    
    # Update Python packages
    update_python_versions(version)
# Python package.json will be updated by changesets
    
    # Lock dependencies
    lock_python_dependencies()
    
    # Validate
    if not validate_python_versions():
        click.echo("Version validation failed", err=True)
        sys.exit(1)
    
    click.echo(f"Successfully set all packages to version {version}")


# Tag command removed - tagging will be handled by GitHub Actions


# Publish commands removed - now handled by package.json scripts and changesets


if __name__ == "__main__":
    cli()