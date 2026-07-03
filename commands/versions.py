"""
Version management commands for flamapy-dev.

This module provides commands for managing package versions across
multiple repositories, including viewing, checking, and bumping versions.

Example usage:
    $ flamapy-dev version show
    $ flamapy-dev version check
    $ flamapy-dev version bump 2.2.0
    $ flamapy-dev version release 2.2.0
"""

import subprocess
import re
import time
from pathlib import Path

import click

from commands.pypi import (
    get_internal_requirements,
    wait_for_internal_requirements,
    wait_for_package,
)

# Pause between consecutive tag pushes during a release. The simple-index check
# guarantees a dependency's release exists, but pip can still miss it for a short
# while (CDN propagation), which makes freshly triggered CI runs fail spuriously.
TAG_DELAY_SECONDS = 60


def normalize_version(version: str) -> str:
    """
    Strip a leading 'v'/'V' from a version string.

    Tags are built as f"v{version}" and pyproject/PyPI versions are stored
    unprefixed, so a "v2.6.0" argument would otherwise produce "vv2.6.0" tags
    and inconsistent pins.

    Example:
        >>> normalize_version("v2.6.0.dev10")
        '2.6.0.dev10'
        >>> normalize_version("2.6.0.dev10")
        '2.6.0.dev10'
    """
    return re.sub(r"^[vV](?=\d)", "", version.strip())


def to_stable_version(version: str) -> str:
    """
    Drop a PEP 440 pre/dev/post suffix, yielding the plain release version.

    Used to promote a development version to its stable counterpart: the
    leading ``N(.N)*`` release segment is kept and everything from the first
    non-numeric marker (``.dev``/``a``/``b``/``rc``/``.post``) is discarded.

    Example:
        >>> to_stable_version("2.6.0.dev11")
        '2.6.0'
        >>> to_stable_version("v2.6.0rc1")
        '2.6.0'
        >>> to_stable_version("2.6.0")
        '2.6.0'
    """
    normalized = normalize_version(version)
    m = re.match(r"^\d+(?:\.\d+)*", normalized)
    if not m:
        raise ValueError(f"Cannot derive a stable version from '{version}'")
    return m.group(0)


def extract_current_version(pyproject_path: Path) -> str:
    """
    Extract the version string from a pyproject.toml file.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        The version string (e.g., "2.1.0.dev1").

    Raises:
        ValueError: If no version is found in the file.

    Example:
        >>> from pathlib import Path
        >>> version = extract_current_version(Path("flamapy_fw/pyproject.toml"))
        >>> print(version)
        '2.1.0.dev1'
    """
    text = pyproject_path.read_text(encoding="utf-8")
    m = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise ValueError(f"No version found in {pyproject_path}")
    return m.group(1)


def extract_package_name(pyproject_path: Path) -> str:
    """
    Extract the package name from a pyproject.toml file.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        The package name (e.g., "flamapy-fw").

    Raises:
        ValueError: If no name is found in the file.

    Example:
        >>> from pathlib import Path
        >>> name = extract_package_name(Path("flamapy_fw/pyproject.toml"))
        >>> print(name)
        'flamapy-fw'
    """
    text = pyproject_path.read_text(encoding="utf-8")
    m = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise ValueError(f"No name found in {pyproject_path}")
    return m.group(1)


def parse_toml_dependencies(pyproject_path: Path) -> dict[str, str]:
    """
    Parse versioned dependencies from a pyproject.toml file.

    Extracts package names and version specifiers from the
    [project] dependencies array.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        Dictionary mapping package names to version strings.

    Example:
        >>> from pathlib import Path
        >>> deps = parse_toml_dependencies(Path("fm_metamodel/pyproject.toml"))
        >>> print(deps)
        {'flamapy-fw': '2.1.0.dev1', 'uvlparser': '2.0.1.dev61'}
    """
    deps: dict[str, str] = {}
    if not pyproject_path.exists():
        return deps
    text = pyproject_path.read_text(encoding="utf-8")
    for m in re.finditer(r'"([a-zA-Z0-9_-]+)[~>=<]+([^"]+)"', text):
        deps[m.group(1)] = m.group(2)
    return deps


def update_pyproject(pyproject_path: Path, old_version: str, new_version: str) -> bool:
    """
    Update the [project] version string in a pyproject.toml file.

    Args:
        pyproject_path: Path to the pyproject.toml file.
        old_version: The current version to replace.
        new_version: The new version to set.

    Returns:
        True if the version was updated, False otherwise.

    Example:
        >>> from pathlib import Path
        >>> updated = update_pyproject(
        ...     Path("flamapy_fw/pyproject.toml"),
        ...     "2.1.0.dev1",
        ...     "2.2.0"
        ... )
        >>> print(updated)
        True
    """
    text = pyproject_path.read_text(encoding="utf-8")
    pattern = r"(version\s*=\s*['\"])" + re.escape(old_version) + r"(['\"])"
    repl = r"\g<1>" + new_version + r"\g<2>"
    new_text, n = re.subn(pattern, repl, text)
    if n == 0:
        return False
    pyproject_path.write_text(new_text, encoding="utf-8")
    return True


def update_toml_dependencies(
    pyproject_path: Path, pkg_map: dict[str, tuple[str, str]]
) -> list[str]:
    """
    Update internal dependency versions in a pyproject.toml file.

    Updates version specifiers inside the [project] dependencies array.

    Args:
        pyproject_path: Path to the pyproject.toml file.
        pkg_map: Dictionary mapping package names to (old_version, new_version) tuples.

    Returns:
        List of package names that were updated.

    Example:
        >>> from pathlib import Path
        >>> pkg_map = {"flamapy-fw": ("2.1.0", "2.2.0")}
        >>> updated = update_toml_dependencies(
        ...     Path("fm_metamodel/pyproject.toml"),
        ...     pkg_map
        ... )
        >>> print(updated)
        ['flamapy-fw']
    """
    if not pyproject_path.exists():
        return []
    text = pyproject_path.read_text(encoding="utf-8")
    updated = []
    for pkg, (_, newv) in pkg_map.items():
        pattern = rf'({re.escape(pkg)}~=)[^",]+'
        repl = rf"\g<1>{newv}"
        new_text, n = re.subn(pattern, repl, text)
        if n > 0:
            text = new_text
            updated.append(pkg)
    if updated:
        pyproject_path.write_text(text, encoding="utf-8")
    return updated


@click.group()
@click.pass_context
def version(ctx: click.Context) -> None:
    """
    Commands for managing package versions.

    This command group provides tools for viewing, validating, and
    updating package versions across all repositories.

    \b
    Examples:
        $ flamapy-dev version show      # Show all versions
        $ flamapy-dev version check     # Validate version consistency
        $ flamapy-dev version bump 2.2.0  # Bump all versions
    """
    ctx.ensure_object(dict)
    ctx.obj["PARENT_DIR"] = ctx.obj.get("PARENT_DIR", ".")
    ctx.obj["REPOS"] = ctx.obj.get("REPOS", {})


@version.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """
    Show current versions of all packages and their dependencies.

    Displays each package's version and lists internal dependencies
    with their required versions, marking mismatches with ✗.

    \b
    Example:
        $ flamapy-dev version show

        ============================================================
        PACKAGE VERSIONS
        ============================================================

        flamapy_fw/
          Package: flamapy-fw v2.1.0.dev1

        fm_metamodel/
          Package: flamapy-fm v2.1.0.dev1
          Internal dependencies:
            - flamapy-fw~=2.1.0.dev1 ✓
          External dependencies:
            - uvlparser~=2.5.0.dev63
    """
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]

    # First pass: collect all package versions
    pkg_versions = {}
    for folder in repos:
        repo = Path(parent_dir) / folder
        pyproject = repo / "pyproject.toml"
        if not pyproject.exists():
            continue
        try:
            pkg_name = extract_package_name(pyproject)
            pkg_version = extract_current_version(pyproject)
            pkg_versions[pkg_name] = pkg_version
        except (ValueError, OSError):
            continue

    # Second pass: show versions with dependencies
    click.echo("\n" + "=" * 60)
    click.echo("PACKAGE VERSIONS")
    click.echo("=" * 60)

    for folder in repos:
        repo = Path(parent_dir) / folder
        pyproject = repo / "pyproject.toml"

        if not pyproject.exists():
            click.echo(f"\n{folder}: pyproject.toml not found")
            continue

        try:
            pkg_name = extract_package_name(pyproject)
            pkg_version = extract_current_version(pyproject)
            click.echo(f"\n{folder}/")
            click.echo(f"  Package: {pkg_name} v{pkg_version}")

            deps = parse_toml_dependencies(pyproject)
            internal_deps = {k: v for k, v in deps.items() if k in pkg_versions}
            external_deps = {k: v for k, v in deps.items() if k not in pkg_versions}
            if internal_deps:
                click.echo("  Internal dependencies:")
                for dep, ver in internal_deps.items():
                    actual = pkg_versions.get(dep, "?")
                    status = "✓" if ver == actual else f"✗ (actual: {actual})"
                    click.echo(f"    - {dep}~={ver} {status}")
            if external_deps:
                click.echo("  External dependencies:")
                for dep, ver in external_deps.items():
                    click.echo(f"    - {dep}~={ver}")
        except (ValueError, OSError) as e:
            click.echo(f"\n{folder}: Error - {e}")

    click.echo("\n" + "=" * 60)


def _collect_versions(parent_dir: str, repos: dict[str, str]) -> dict[str, tuple[str, str]]:
    """Collect package versions from all repos."""
    pkg_versions = {}
    for folder in repos:
        repo = Path(parent_dir) / folder
        pyproject = repo / "pyproject.toml"
        if not pyproject.exists():
            continue
        try:
            pkg_name = extract_package_name(pyproject)
            pkg_version = extract_current_version(pyproject)
            pkg_versions[pkg_name] = (folder, pkg_version)
        except (ValueError, OSError):
            continue
    return pkg_versions


def _find_version_errors(
    parent_dir: str,
    repos: dict[str, str],
    pkg_versions: dict[str, tuple[str, str]],
) -> list[str]:
    """Find version mismatches in pyproject.toml dependency declarations."""
    errors = []
    for folder in repos:
        repo = Path(parent_dir) / folder
        pyproject = repo / "pyproject.toml"
        if not pyproject.exists():
            continue
        deps = parse_toml_dependencies(pyproject)
        for dep, required_ver in deps.items():
            if dep in pkg_versions:
                _, actual_ver = pkg_versions[dep]
                if required_ver != actual_ver:
                    errors.append(
                        f"{folder}/pyproject.toml: {dep}~={required_ver} "
                        f"but {dep} is at v{actual_ver}"
                    )
    return errors


@version.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """
    Check if all internal dependencies have matching versions.

    Validates that the versions specified in pyproject.toml dependencies
    match the actual versions in the corresponding packages.
    Exits with code 1 if mismatches are found.

    \b
    Example:
        $ flamapy-dev version check
        ✓ All internal dependencies are in sync!
    """
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]

    pkg_versions = _collect_versions(parent_dir, repos)
    errors = _find_version_errors(parent_dir, repos, pkg_versions)

    if errors:
        click.echo("\n❌ VERSION MISMATCHES FOUND:\n")
        for err in errors:
            click.echo(f"  • {err}")
        click.echo(f"\nTotal: {len(errors)} error(s)")
        click.echo("\nRun 'flamapy-dev version bump <version>' to fix.")
        ctx.exit(1)
    else:
        click.echo("\n✓ All internal dependencies are in sync!")


def _gather_repo_info(
    parent_dir: str,
    repos: dict[str, str],
    new_version: str,
) -> tuple[dict[str, tuple[str, str]], dict[str, tuple[Path, str, str, str]]]:
    """Gather version info from all repos. Returns (pkg_map, repo_info)."""
    pkg_map: dict[str, tuple[str, str]] = {}
    repo_info: dict[str, tuple[Path, str, str, str]] = {}
    for folder in repos:
        repo = Path(parent_dir) / folder
        pyproject = repo / "pyproject.toml"
        if not pyproject.exists():
            click.echo(f"{folder}: pyproject.toml not found, skipping.")
            continue
        try:
            oldv = extract_current_version(pyproject)
            pkg_name = extract_package_name(pyproject)
            pkg_map[pkg_name] = (oldv, new_version)
            repo_info[folder] = (repo, pkg_name, oldv, new_version)
        except (ValueError, OSError) as e:
            click.echo(f"Error in {folder}: {e}")
    return pkg_map, repo_info


def _apply_bump(
    repo_info: dict[str, tuple[Path, str, str, str]],
    pkg_map: dict[str, tuple[str, str]],
    dry_run: bool,
) -> None:
    """Apply version bumps to all repos."""
    for folder, (repo, _, oldv, newv) in repo_info.items():
        pyproject = repo / "pyproject.toml"
        click.echo(f"{folder}/")
        click.echo(f"  pyproject.toml version: {oldv} → {newv}")

        deps = parse_toml_dependencies(pyproject)
        internal_deps = [dep for dep in deps if dep in pkg_map]
        if internal_deps:
            click.echo(f"  pyproject.toml deps: {', '.join(internal_deps)} → {newv}")

        if not dry_run:
            update_pyproject(pyproject, oldv, newv)
            if internal_deps:
                update_toml_dependencies(pyproject, pkg_map)


def _bump_ide(parent_dir: str, ide_repo: str, new_version: str, dry_run: bool) -> None:
    """Update the IDE's flamapy.version file to the new bundled flamapy version.

    Note the file points at an unpublished flamapy until the release lands on
    PyPI; `release-all` rewrites (and commits) it after waiting for publication.
    """
    repo_dir = Path(parent_dir) / ide_repo
    version_file = repo_dir / "flamapy.version"
    if not repo_dir.is_dir():
        click.echo(f"{ide_repo}/: not found, skipping.")
        return
    current = version_file.read_text().strip() if version_file.exists() else "(none)"
    click.echo(f"{ide_repo}/")
    click.echo(f"  flamapy.version: {current} → {new_version}")
    if not dry_run:
        version_file.write_text(f"{new_version}\n", encoding="utf-8")


@version.command()
@click.argument("new_version")
@click.option("--dry-run", "-n", is_flag=True, help="Show changes without modifying")
@click.pass_context
def bump(ctx: click.Context, new_version: str, dry_run: bool) -> None:
    """
    Bump all repos to the given version and update internal dependencies.

    Also updates the IDE's flamapy.version file to the new version.
    A leading "v" in the version is stripped automatically.

    \b
    Args:
        new_version: The new version to set (e.g., "2.2.0")

    \b
    Example:
        $ flamapy-dev version bump 2.2.0 --dry-run
        $ flamapy-dev version bump 2.2.0
    """
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]
    ide_repo = ctx.obj.get("IDE_REPO", "flamapy-ide")
    new_version = normalize_version(new_version)

    pkg_map, repo_info = _gather_repo_info(parent_dir, repos, new_version)

    if dry_run:
        click.echo(f"\n[DRY RUN] Would bump {len(repo_info)} packages to v{new_version}:\n")
    else:
        click.echo(f"\nBumping {len(repo_info)} packages to v{new_version}...\n")

    _apply_bump(repo_info, pkg_map, dry_run)
    _bump_ide(parent_dir, ide_repo, new_version, dry_run)

    if dry_run:
        click.echo("\n[DRY RUN] No files were modified.")
    else:
        click.echo("\n✓ Bump completed.")


def _run_tests(parent_dir: str, repos: dict[str, str]) -> bool:
    """Run tests in all repos. Returns True if all pass."""
    click.echo("\n📋 Step 1: Running tests...")
    for repo_name in repos:
        repo_dir = Path(parent_dir) / repo_name
        if repo_dir.is_dir():
            result = subprocess.run(
                ["make", "test"], cwd=repo_dir, capture_output=True, check=False
            )
            if result.returncode != 0:
                click.echo(f"  ✗ Tests failed in {repo_name}")
                return False
            click.echo(f"  ✓ {repo_name}")
    click.echo("  All tests passed!")
    return True


def _commit_all(parent_dir: str, repos: dict[str, str], message: str) -> None:
    """Commit changes in all repos."""
    click.echo("\n📋 Step 3: Committing changes...")
    for repo_name in repos:
        repo_dir = Path(parent_dir) / repo_name
        if not (repo_dir / ".git").is_dir():
            continue
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir, capture_output=True, text=True, check=False
        )
        if not result.stdout.strip():
            continue
        subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=repo_dir, check=True)
        click.echo(f"  ✓ {repo_name}")


def _push_all(parent_dir: str, repos: dict[str, str]) -> None:
    """Push all repos to remote."""
    click.echo("\n📋 Step 4: Pushing commits...")
    for repo_name in repos:
        repo_dir = Path(parent_dir) / repo_name
        if (repo_dir / ".git").is_dir():
            result = subprocess.run(
                ["git", "push"],
                cwd=repo_dir, capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                click.echo(f"  ✓ {repo_name}")
            else:
                click.echo(f"  ✗ {repo_name}: {result.stderr.strip()}")


def _tag_all(
    parent_dir: str,
    repos: dict[str, str],
    new_version: str,
    internal_packages: set[str],
) -> None:
    """Create and push tags for all repos.

    Before tagging each repo, waits until its internal flamapy dependencies are
    available on PyPI.  External dependencies (setuptools, uvlparser, …) and
    build-system requirements are intentionally ignored — only the packages that
    are part of this coordinated release matter, because those are the ones whose
    PyPI releases are triggered by the tag push itself.

    Availability is checked against PyPI's *simple index* — the same index that
    pip (and therefore CI) resolves against — rather than the JSON API, which can
    report a version as available before it has propagated to the simple index.

    On top of that check, a TAG_DELAY_SECONDS pause separates consecutive tag
    pushes: even once the simple index lists a release, pip can briefly miss it
    while it propagates, so tagging a dependent repo immediately can still
    trigger a CI run that fails to install its dependencies.
    """
    click.echo("\n📋 Step 5: Creating and pushing tags...")

    first = True
    for repo_name in repos:
        repo_dir = Path(parent_dir) / repo_name
        if not (repo_dir / ".git").is_dir():
            continue

        if not first:
            click.echo(f"  ⏸ waiting {TAG_DELAY_SECONDS}s before tagging {repo_name} "
                       "(let PyPI propagate)...")
            time.sleep(TAG_DELAY_SECONDS)
        first = False

        tag = f"v{new_version}"
        pyproject = repo_dir / "pyproject.toml"

        if pyproject.exists():
            pending = get_internal_requirements(str(pyproject), internal_packages)
            if pending:
                pending_str = ", ".join(str(r) for r in pending)
                click.echo(f"  ⏳ {repo_name}: waiting for {pending_str} "
                           f"on the PyPI simple index...")
                wait_for_internal_requirements(str(pyproject), internal_packages)

        existing = subprocess.run(
            ["git", "tag", "-l", tag], cwd=repo_dir, capture_output=True, text=True, check=False
        )
        if existing.stdout.strip():
            click.echo(f"  ⚠ {repo_name}: tag {tag} already exists, skipping create")
        else:
            subprocess.run(["git", "tag", tag], cwd=repo_dir, check=True)

        push = subprocess.run(
            ["git", "push", "origin", tag],
            cwd=repo_dir, capture_output=True, text=True, check=False
        )
        if push.returncode != 0:
            click.echo(f"  ⚠ {repo_name}: tag {tag} already pushed, skipping")
        else:
            click.echo(f"  ✓ {repo_name}: tagged {tag}")


@version.command()
@click.argument("new_version")
@click.option("--dry-run", "-n", is_flag=True, help="Simulate without making changes")
@click.option("--skip-tests", is_flag=True, help="Skip running tests before release")
@click.pass_context
def release(ctx: click.Context, new_version: str, dry_run: bool, skip_tests: bool) -> None:
    """
    Full release workflow: bump versions, commit, tag, and push.

    This command automates the entire release process:
    1. Run tests in all repos (optional)
    2. Bump all package versions
    3. Commit changes in all repos
    4. Push commits to remote
    5. Create and push tags (waits for deps on the PyPI simple index)

    \b
    Args:
        new_version: The version to release (e.g., "2.2.0")

    \b
    Example:
        $ flamapy-dev version release 2.2.0 --dry-run
        $ flamapy-dev version release 2.2.0
    """
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]
    new_version = normalize_version(new_version)

    click.echo(f"\n{'='*60}")
    click.echo(f"RELEASE v{new_version}")
    click.echo('='*60)

    if dry_run:
        click.echo("[DRY RUN MODE - no changes will be made]\n")

    # Step 1: Run tests
    if not skip_tests and not dry_run:
        if not _run_tests(parent_dir, repos):
            click.echo("Release aborted. Fix tests and try again.")
            ctx.exit(1)
    else:
        click.echo("\n📋 Step 1: Skipping tests")

    # Step 2: Bump versions
    click.echo("\n📋 Step 2: Bumping versions...")
    pkg_map, _ = _gather_repo_info(parent_dir, repos, new_version)
    ctx.invoke(bump, new_version=new_version, dry_run=dry_run)

    if dry_run:
        click.echo("\n📋 Step 3-5: Would commit, push, and tag")
        click.echo(f"\n[DRY RUN] Release v{new_version} simulation complete.")
        return

    # Steps 3-5: Commit, push, and tag
    internal_packages = set(pkg_map.keys())
    _commit_all(parent_dir, repos, f"chore: bump version to {new_version}")
    _push_all(parent_dir, repos)
    _tag_all(parent_dir, repos, new_version, internal_packages)

    click.echo(f"\n{'='*60}")
    click.echo(f"✓ Release v{new_version} completed!")
    click.echo('='*60)


def _release_ide(parent_dir: str, ide_repo: str, new_version: str, dry_run: bool) -> None:
    """Release the IDE: bundle the just-published flamapy version and tag it.

    The IDE downloads ``flamapy==<new_version>`` at build time, so this first waits for that
    version on PyPI, then bumps ``flamapy.version``, commits/pushes, and tags ``v<new_version>``
    (synced to the flamapy version) — which triggers the IDE's docker + Pages release.
    """
    click.echo("\n📋 IDE: bundle flamapy and tag...")
    repo_dir = Path(parent_dir) / ide_repo
    if not (repo_dir / ".git").is_dir():
        click.echo(f"  ⚠ {ide_repo}: not found, skipping")
        return

    version_file = repo_dir / "flamapy.version"
    tag = f"v{new_version}"
    if dry_run:
        current = version_file.read_text().strip() if version_file.exists() else "?"
        click.echo(f"  [DRY RUN] {ide_repo}: flamapy.version {current} → {new_version}, "
                   f"commit/push, tag {tag}")
        return

    click.echo(f"  ⏳ waiting for flamapy=={new_version} on PyPI before bundling...")
    wait_for_package("flamapy", new_version)

    version_file.write_text(f"{new_version}\n", encoding="utf-8")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True, check=False
    )
    if status.stdout.strip():
        subprocess.run(["git", "add", "flamapy.version"], cwd=repo_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: bundle flamapy {new_version}"],
            cwd=repo_dir, check=True,
        )
        subprocess.run(["git", "push"], cwd=repo_dir, check=False)

    existing = subprocess.run(
        ["git", "tag", "-l", tag], cwd=repo_dir, capture_output=True, text=True, check=False
    )
    if existing.stdout.strip():
        click.echo(f"  ⚠ {ide_repo}: tag {tag} already exists, skipping")
        return
    subprocess.run(["git", "tag", tag], cwd=repo_dir, check=True)
    push = subprocess.run(
        ["git", "push", "origin", tag], cwd=repo_dir, capture_output=True, text=True, check=False
    )
    if push.returncode == 0:
        click.echo(f"  ✓ {ide_repo}: tagged {tag}")
    else:
        click.echo(f"  ⚠ {ide_repo}: {push.stderr.strip()}")


def _release_docs(parent_dir: str, docs_repo: str, dry_run: bool) -> None:
    """Publish the docs site by merging develop → main (the site deploys from main)."""
    click.echo("\n📋 Docs: publish site (develop → main)...")
    repo_dir = Path(parent_dir) / docs_repo
    if not (repo_dir / ".git").is_dir():
        click.echo(f"  ⚠ {docs_repo}: not found, skipping")
        return
    if dry_run:
        click.echo(f"  [DRY RUN] {docs_repo}: merge develop → main and push (deploys Pages)")
        return

    steps = [
        ["git", "checkout", "main"],
        ["git", "merge", "--no-ff", "develop", "-m", "chore: publish docs"],
        ["git", "push", "origin", "main"],
        ["git", "checkout", "develop"],
    ]
    for step in steps:
        result = subprocess.run(
            step, cwd=repo_dir, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            click.echo(f"  ⚠ {docs_repo}: `{' '.join(step[1:])}` failed: {result.stderr.strip()}")
            subprocess.run(["git", "checkout", "develop"], cwd=repo_dir, check=False)
            return
    click.echo(f"  ✓ {docs_repo}: published (develop → main)")


def _derive_stable_version(parent_dir: str, repos: dict[str, str]) -> str:
    """Derive the single stable version implied by the repos' current versions.

    Each repo's current dev version is reduced to its release segment (see
    :func:`to_stable_version`); they must all agree, otherwise the caller should
    pass the version explicitly.
    """
    stables: dict[str, str] = {}
    for folder in repos:
        pyproject = Path(parent_dir) / folder / "pyproject.toml"
        if not pyproject.exists():
            continue
        try:
            stables[folder] = to_stable_version(extract_current_version(pyproject))
        except (ValueError, OSError):
            continue
    unique = set(stables.values())
    if not unique:
        raise click.ClickException("Could not read any package version to stabilize.")
    if len(unique) > 1:
        detail = ", ".join(f"{f}={v}" for f, v in sorted(stables.items()))
        raise click.ClickException(
            f"Repos disagree on the stable version ({detail}); pass it explicitly."
        )
    return next(iter(unique))


def _stabilize_preconditions(parent_dir: str, repos: dict[str, str]) -> list[str]:
    """Return reasons the repos are not ready to stabilize (empty list == ready).

    Each repo must be on ``develop``, have a clean working tree, and not be
    behind ``origin/develop``. Fetches first so the behind check is accurate.
    """
    problems: list[str] = []
    for folder in repos:
        repo_dir = Path(parent_dir) / folder
        if not (repo_dir / ".git").is_dir():
            continue
        subprocess.run(["git", "fetch", "origin", "--quiet"], cwd=repo_dir, check=False)
        current = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_dir, capture_output=True, text=True, check=False,
        ).stdout.strip()
        if current != "develop":
            problems.append(f"{folder}: on '{current or 'detached'}', expected 'develop'")
        if subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir, capture_output=True, text=True, check=False,
        ).stdout.strip():
            problems.append(f"{folder}: working tree is not clean")
        behind = subprocess.run(
            ["git", "rev-list", "--count", "develop..origin/develop"],
            cwd=repo_dir, capture_output=True, text=True, check=False,
        ).stdout.strip()
        if behind.isdigit() and int(behind) > 0:
            problems.append(
                f"{folder}: develop is {behind} commit(s) behind origin/develop (pull first)"
            )
    return problems


def _commit_repo(repo_dir: Path, message: str) -> bool:
    """Stage and commit all changes in a repo. Returns False if nothing to commit."""
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True, check=False
    )
    if not status.stdout.strip():
        return False
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_dir, check=True)
    return True


def _merge_develop_to_main(repo_dir: Path, message: str) -> bool:
    """Checkout main, merge develop --no-ff, push main, then return to develop.

    Returns True on success. On any failure the develop branch is restored and
    False is returned so the caller can skip tagging this repo.
    """
    steps = [
        ["git", "checkout", "main"],
        ["git", "merge", "--no-ff", "develop", "-m", message],
        ["git", "push", "origin", "main"],
    ]
    for step in steps:
        result = subprocess.run(step, cwd=repo_dir, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            click.echo(f"  ⚠ `{' '.join(step[1:])}` failed: {result.stderr.strip()}")
            subprocess.run(["git", "checkout", "develop"], cwd=repo_dir, check=False)
            return False
    subprocess.run(["git", "checkout", "develop"], cwd=repo_dir, check=False)
    return True


def _tag_main(repo_dir: Path, tag: str, folder: str) -> None:
    """Create ``tag`` on the local main ref and push it (idempotent)."""
    existing = subprocess.run(
        ["git", "tag", "-l", tag], cwd=repo_dir, capture_output=True, text=True, check=False
    )
    if existing.stdout.strip():
        click.echo(f"  ⚠ {folder}: tag {tag} already exists, skipping create")
    else:
        subprocess.run(["git", "tag", tag, "main"], cwd=repo_dir, check=True)
    push = subprocess.run(
        ["git", "push", "origin", tag], cwd=repo_dir, capture_output=True, text=True, check=False
    )
    if push.returncode == 0:
        click.echo(f"  ✓ {folder}: tagged {tag} on main")
    else:
        click.echo(f"  ⚠ {folder}: {push.stderr.strip() or 'tag already pushed'}")


def _stabilize_repos(
    parent_dir: str,
    repos: dict[str, str],
    new_version: str,
    internal_packages: set[str],
    dry_run: bool,
) -> None:
    """Commit the bump, merge develop→main, and tag v<version> on main, per repo.

    Repos are processed in dependency order. Because the tag push triggers each
    repo's stable PyPI publish, before tagging a repo we wait for its internal
    flamapy dependencies to appear on the PyPI simple index (the same check as
    :func:`_tag_all`), with a TAG_DELAY_SECONDS pause between consecutive repos
    to let PyPI propagate.
    """
    click.echo("\n📋 Steps 3-5: Commit, merge develop→main, and tag...")
    tag = f"v{new_version}"
    message = f"chore: release {new_version}"
    first = True
    for folder in repos:
        repo_dir = Path(parent_dir) / folder
        if not (repo_dir / ".git").is_dir():
            continue

        click.echo(f"\n{folder}/")
        if dry_run:
            click.echo(f"  [DRY RUN] commit bump on develop, push develop, "
                       f"merge develop→main + push, wait for deps, tag {tag} on main")
            continue

        _commit_repo(repo_dir, message)
        subprocess.run(["git", "push", "origin", "develop"], cwd=repo_dir, check=False)

        if not _merge_develop_to_main(repo_dir, message):
            click.echo(f"  ✗ {folder}: merge to main failed, not tagging")
            continue

        if not first:
            click.echo(f"  ⏸ waiting {TAG_DELAY_SECONDS}s before tagging {folder} "
                       "(let PyPI propagate)...")
            time.sleep(TAG_DELAY_SECONDS)
        first = False

        pyproject = repo_dir / "pyproject.toml"
        if pyproject.exists():
            pending = get_internal_requirements(str(pyproject), internal_packages)
            if pending:
                pending_str = ", ".join(str(r) for r in pending)
                click.echo(f"  ⏳ {folder}: waiting for {pending_str} "
                           "on the PyPI simple index...")
                wait_for_internal_requirements(str(pyproject), internal_packages)

        _tag_main(repo_dir, tag, folder)


@version.command()
@click.argument("new_version", required=False)
@click.option("--dry-run", "-n", is_flag=True, help="Simulate without making changes")
@click.option("--skip-tests", is_flag=True, help="Skip running tests before releasing")
@click.option("--skip-docs", is_flag=True, help="Skip publishing the docs site")
@click.option("--yes", "-y", is_flag=True, help="Do not prompt for confirmation")
@click.pass_context
def stabilize(  # noqa: PLR0913
    ctx: click.Context, new_version: str | None, dry_run: bool,
    skip_tests: bool, skip_docs: bool, yes: bool,
) -> None:
    """
    Promote the current dev version to a stable release.

    For every code repo (in dependency order) this drops the ``.devN`` suffix
    (e.g. 2.6.0.dev11 → 2.6.0), commits the bump on develop, merges
    develop → main, pushes both, and tags ``v<version>`` on main — which
    triggers each repo's stable PyPI publish. Finally it publishes the docs
    site (develop → main).

    The stable version is derived from the repos' current versions unless one is
    given explicitly.

    \b
    Examples:
        $ flamapy-dev version stabilize --dry-run
        $ flamapy-dev version stabilize
        $ flamapy-dev version stabilize 2.6.0 --skip-docs
    """
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]
    docs_repo = ctx.obj.get("DOCS_REPO", "flamapy_docs")

    stable = normalize_version(new_version) if new_version \
        else _derive_stable_version(parent_dir, repos)

    click.echo(f"\n{'='*60}")
    click.echo(f"STABILIZE → v{stable}")
    click.echo('='*60)
    if dry_run:
        click.echo("[DRY RUN MODE - no changes will be made]")

    # Preconditions: every repo on develop, clean, and up to date with origin.
    problems = _stabilize_preconditions(parent_dir, repos)
    if problems:
        click.echo("\n❌ Not ready to stabilize:\n")
        for problem in problems:
            click.echo(f"  • {problem}")
        if not dry_run:
            ctx.exit(1)
        click.echo("\n[DRY RUN] Continuing despite the problems above.")

    # Step 1: tests
    if not skip_tests and not dry_run:
        if not _run_tests(parent_dir, repos):
            click.echo("Stabilize aborted. Fix tests and try again.")
            ctx.exit(1)
    else:
        click.echo("\n📋 Step 1: Skipping tests")

    # Step 2: bump to the stable version (pyproject + internal pins) in the working tree.
    click.echo(f"\n📋 Step 2: Bumping versions → {stable}...")
    pkg_map, repo_info = _gather_repo_info(parent_dir, repos, stable)
    _apply_bump(repo_info, pkg_map, dry_run)

    if not dry_run and not yes:
        click.confirm(
            f"\nProceed to commit, merge develop→main, and tag v{stable} across "
            f"{len(repo_info)} repos (this triggers the stable PyPI publish)?",
            abort=True,
        )

    # Steps 3-5: per repo — commit+push develop, merge→main+push, tag main (with PyPI wait).
    internal_packages = set(pkg_map.keys())
    _stabilize_repos(parent_dir, repos, stable, internal_packages, dry_run)

    # Step 6: publish the docs site (develop → main).
    if not skip_docs:
        _release_docs(parent_dir, docs_repo, dry_run)

    click.echo(f"\n{'='*60}")
    verb = "simulation complete" if dry_run else "completed"
    click.echo(f"✓ Stabilize v{stable} {verb}!")
    if not dry_run:
        click.echo(f"ℹ develop now sits at v{stable}; bump it to the next dev version when ready.")
    click.echo('='*60)


@version.command(name="release-all")
@click.argument("new_version")
@click.option("--dry-run", "-n", is_flag=True, help="Simulate without making changes")
@click.option("--skip-tests", is_flag=True, help="Skip running tests before release")
@click.option("--skip-plugins", is_flag=True, help="Skip the coordinated PyPI plugin release")
@click.option("--skip-ide", is_flag=True, help="Skip releasing the IDE")
@click.option("--skip-docs", is_flag=True, help="Skip publishing the docs site")
@click.pass_context
def release_all(  # noqa: PLR0913
    ctx: click.Context, new_version: str, dry_run: bool,
    skip_tests: bool, skip_plugins: bool, skip_ide: bool, skip_docs: bool,
) -> None:
    """
    Release every artefact: the PyPI plugins, then the IDE, then the docs site.

    Order matters: the plugins publish to PyPI first; the IDE then bundles the published
    flamapy version and ships (docker + Pages); finally the docs site is published (develop → main).

    \b
    Examples:
        $ flamapy-dev version release-all 2.6.0.dev8 --dry-run
        $ flamapy-dev version release-all 2.6.0.dev8
        $ flamapy-dev version release-all 2.6.0.dev8 --skip-docs
    """
    parent_dir = ctx.obj["PARENT_DIR"]
    ide_repo = ctx.obj.get("IDE_REPO", "flamapy-ide")
    docs_repo = ctx.obj.get("DOCS_REPO", "flamapy_docs")
    new_version = normalize_version(new_version)

    click.echo(f"\n{'='*60}")
    click.echo(f"RELEASE-ALL v{new_version}")
    click.echo('='*60)

    if not skip_plugins:
        ctx.invoke(release, new_version=new_version, dry_run=dry_run, skip_tests=skip_tests)
    else:
        click.echo("\n📋 Skipping PyPI plugin release")

    if not skip_ide:
        _release_ide(parent_dir, ide_repo, new_version, dry_run)
    if not skip_docs:
        _release_docs(parent_dir, docs_repo, dry_run)

    click.echo(f"\n{'='*60}")
    verb = "simulation complete" if dry_run else "completed"
    click.echo(f"✓ Release-all v{new_version} {verb}!")
    click.echo('='*60)


version.add_command(show)
version.add_command(check)
version.add_command(bump)
version.add_command(release)
version.add_command(stabilize)
version.add_command(release_all)
