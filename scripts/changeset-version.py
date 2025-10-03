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

from dataclasses import dataclass
import json
import os
import subprocess
from pathlib import Path
from typing import Any, List, cast
import urllib.request
import urllib.error
import re

import click
import tomlkit
from packaging.version import Version


def _run_command(
    cmd: List[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> None:
    """Run a command, streaming output to the console, and raise on failure."""
    subprocess.run(cmd, check=True, text=True, cwd=cwd or Path.cwd(), env=env)


def _run_and_capture(
    cmd: List[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> str:
    """Run a command and return stdout as text, raising on failure."""
    result = subprocess.run(
        cmd,
        check=True,
        text=True,
        cwd=cwd or Path.cwd(),
        env=env,
        capture_output=True,
    )
    return result.stdout


@dataclass
class Package:
    name: str
    version: str
    path: Path

    def python_package_name(self) -> str | None:
        if str(self.path).startswith("py"):
            return self.name.removesuffix("-py")
        return None


def _get_pnpm_workspace_packages() -> list[Package]:
    """Return directories for all workspace packages from pnpm list JSON output."""
    output = _run_and_capture(["pnpm", "list", "-r", "--depth=-1", "--json"])

    data = cast(list[dict[str, Any]], json.loads(output))
    packages: list[Package] = [
        Package(name=data["name"], version=data["version"], path=Path(data["path"]))
        for data in data
    ]
    return packages


def _sync_package_version_with_pyproject(
    package_dir: Path, packages: dict[str, Package], js_package_name: str
) -> None:
    """Sync version from package.json to pyproject.toml.

    Returns True if pyproject was changed, else False.
    """
    pyproject_path = package_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return

    package_version = packages[js_package_name].version
    py_doc = tomlkit.parse(pyproject_path.read_text())

    by_python_name = {
        pkg.python_package_name(): pkg
        for pkg in packages.values()
        if pkg.python_package_name()
    }

    current_version = py_doc["project"]["version"]
    assert isinstance(current_version, str)

    # update workspace dependency strings by replacing the first version after == or >=
    deps = py_doc["project"]["dependencies"] or []
    changed = False
    for i, dep in enumerate(deps):
        if not isinstance(dep, str):
            continue
        pkg = (cast(str, dep).split("==")[0]).split(">=")[0]
        if pkg not in by_python_name:
            continue
        target_version = by_python_name[pkg].version
        new_dep = re.sub(
            r"(==|>=)\s*([0-9A-Za-z_.+-]+)", rf"\1{target_version}", dep, count=1
        )
        if new_dep != dep:
            deps[i] = new_dep
            changed = True

    if current_version != package_version:
        py_doc["project"]["version"] = package_version
        changed = True

    if changed:
        pyproject_path.write_text(tomlkit.dumps(py_doc))
        click.echo(
            f"Updated {pyproject_path} version to {package_version} and synced dependency specs"
        )


def lock_python_dependencies() -> None:
    """Lock Python dependencies."""
    try:
        _run_command(["uv", "lock"])
        click.echo("Locked Python dependencies")
    except subprocess.CalledProcessError as e:
        click.echo(f"Warning: Failed to lock Python dependencies: {e}", err=True)


@click.group()
def cli() -> None:
    """Changeset-based version management for llama-cloud-services."""
    pass


@cli.command()
def version() -> None:
    """Apply changeset versions, then sync versions for co-located JS/Py packages.

    - Runs changesets to bump package.json versions.
    - Discovers all workspace packages via pnpm.
    - For any directory containing both package.json and pyproject.toml, and with
      package.json private: false, set pyproject [project].version to match the JS version.
    - If a pyproject is updated, run `uv sync` in that directory to update its lock file.
    """
    # Ensure we're at the repo root
    os.chdir(Path(__file__).parent.parent)

    # First, run changeset version to update all package.json files
    _run_command(["npx", "@changesets/cli", "version"])

    # Enumerate workspace packages and perform syncs
    packages = _get_pnpm_workspace_packages()
    version_map = {pkg.name: pkg for pkg in packages}
    for pkg in packages:
        _sync_package_version_with_pyproject(pkg.path, version_map, pkg.name)


@cli.command()
@click.option("--tag", is_flag=True, help="Tag the packages after publishing")
@click.option("--dry-run", is_flag=True, help="Dry run the publish")
@click.option("--js/--no-js", default=True, help="Publish the js package")
@click.option("--py/--no-py", default=True, help="Publish the py package")
def publish(tag: bool, dry_run: bool, js: bool, py: bool) -> None:
    """Publish all packages."""
    # move to the root
    os.chdir(Path(__file__).parent.parent)

    if js:
        if not os.getenv("NPM_TOKEN"):
            click.echo("NPM_TOKEN is not set, skipping publish", err=True)
            raise click.Abort("No token set")
    if py:
        if not os.getenv("LLAMA_PARSE_PYPI_TOKEN"):
            click.echo("LLAMA_PARSE_PYPI_TOKEN is not set, skipping publish", err=True)
            raise click.Abort("No token set")

    # not general script. Just checks each of the 2 packages to see if they need to be published.
    if js:
        maybe_publish_npm(dry_run)
    if py:
        maybe_publish_pypi(dry_run)

    if tag:
        if dry_run:
            click.echo("Dry run, skipping tag. Would run:")
            click.echo("  git tag llama-cloud-services@<version>")
        else:
            # Let changesets create JS-related tags as usual
            _run_command(["npx", "@changesets/cli", "tag"])
            _run_command(["git", "push", "--tags"])


def maybe_publish_npm(dry_run: bool) -> None:
    """Publish the ts package if it needs to be published."""
    target_dir = Path("ts/llama_cloud_services")
    ts_path_package = target_dir / "package.json"
    package_json = json.loads(ts_path_package.read_text())
    version = package_json["version"]

    # Check if this version is already published on npm
    result = subprocess.run(
        ["npm", "view", "llama-cloud-services", "versions", "--json"],
        check=True,
        capture_output=True,
        text=True,
        cwd=target_dir,
    )

    published_versions = json.loads(result.stdout)
    if version in published_versions:
        click.echo(
            f"npm  package llama-cloud-services@{version} already published, skipping"
        )
        return
    click.echo(f"Publishing npm package llama-cloud-services@{version}")
    # defer to the package.json publish script
    if dry_run:
        click.echo("Dry run, skipping publish. Would run:")
        click.echo("  pnpm run publish")
        return
    else:
        _run_command(["pnpm", "run", "build"], cwd=target_dir)
        _run_command(["pnpm", "publish"], cwd=target_dir)


def maybe_publish_pypi(dry_run: bool) -> None:
    """Publish the py packages if they need to be published."""
    for pyproject in list(Path("py").glob("*/pyproject.toml")) + [
        Path("py/pyproject.toml")
    ]:
        name, version = current_version(pyproject)
        if is_published(name, version):
            click.echo(f"PyPI package {name}@{version} already published, skipping")
            continue
        click.echo(f"Publishing PyPI package {name}@{version}")

        # Use different tokens for different packages
        env = os.environ.copy()
        token = os.environ["LLAMA_PARSE_PYPI_TOKEN"]
        env["UV_PUBLISH_TOKEN"] = token
        if dry_run:
            summary = (token[:3] + "***") if len(token) <= 6 else token[:6] + "****"
            click.echo(
                f"Dry run, skipping publish. Would run with publish token {summary}:"
            )
            click.echo("  uv build")
            click.echo("  uv publish")
        else:
            _run_command(["uv", "build"], cwd=pyproject.parent)
            _run_command(["uv", "publish"], cwd=pyproject.parent, env=env)


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
