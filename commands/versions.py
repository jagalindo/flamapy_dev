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

import click
import os
import re
from pathlib import Path


def extract_current_version(setup_path: Path) -> str:
    """
    Extract the version string from a setup.py file.

    Args:
        setup_path: Path to the setup.py file.

    Returns:
        The version string (e.g., "2.1.0.dev1").

    Raises:
        ValueError: If no version is found in the file.

    Example:
        >>> from pathlib import Path
        >>> version = extract_current_version(Path("flamapy_fw/setup.py"))
        >>> print(version)
        '2.1.0.dev1'
    """
    text = setup_path.read_text(encoding="utf-8")
    m = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise ValueError(f"No version found in {setup_path}")
    return m.group(1)


def extract_package_name(setup_path: Path) -> str:
    """
    Extract the package name from a setup.py file.

    Args:
        setup_path: Path to the setup.py file.

    Returns:
        The package name (e.g., "flamapy-fw").

    Raises:
        ValueError: If no name is found in the file.

    Example:
        >>> from pathlib import Path
        >>> name = extract_package_name(Path("flamapy_fw/setup.py"))
        >>> print(name)
        'flamapy-fw'
    """
    text = setup_path.read_text(encoding="utf-8")
    m = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise ValueError(f"No name found in {setup_path}")
    return m.group(1)


def parse_requirements(req_path: Path) -> dict[str, str]:
    """
    Parse a requirements.txt file and extract package versions.

    Args:
        req_path: Path to the requirements.txt file.

    Returns:
        Dictionary mapping package names to version specifiers.

    Example:
        >>> from pathlib import Path
        >>> deps = parse_requirements(Path("fm_metamodel/requirements.txt"))
        >>> print(deps)
        {'flamapy-fw': '2.1.0.dev1', 'uvlparser': '2.0.1'}
    """
    deps = {}
    if not req_path.exists():
        return deps
    text = req_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Match patterns like: flamapy-fw~=2.1.0.dev1 or flamapy-fw>=2.0.0
        m = re.match(r"([a-zA-Z0-9_-]+)([~>=<]+)(.+)", line)
        if m:
            deps[m.group(1)] = m.group(3)
    return deps


def update_setup_py(setup_path: Path, old_version: str, new_version: str) -> bool:
    """
    Update the version string in a setup.py file.

    Args:
        setup_path: Path to the setup.py file.
        old_version: The current version to replace.
        new_version: The new version to set.

    Returns:
        True if the version was updated, False otherwise.

    Example:
        >>> from pathlib import Path
        >>> updated = update_setup_py(
        ...     Path("flamapy_fw/setup.py"),
        ...     "2.1.0.dev1",
        ...     "2.2.0"
        ... )
        >>> print(updated)
        True
    """
    text = setup_path.read_text(encoding="utf-8")
    pattern = r"(version\s*=\s*['\"])" + re.escape(old_version) + r"(['\"])"
    repl = r"\g<1>" + new_version + r"\g<2>"
    new_text, n = re.subn(pattern, repl, text)
    if n == 0:
        return False
    setup_path.write_text(new_text, encoding="utf-8")
    return True


def update_requirements(req_path: Path, pkg_map: dict[str, tuple[str, str]]) -> list[str]:
    """
    Update internal dependency versions in a requirements.txt file.

    Args:
        req_path: Path to the requirements.txt file.
        pkg_map: Dictionary mapping package names to (old_version, new_version) tuples.

    Returns:
        List of package names that were updated.

    Example:
        >>> from pathlib import Path
        >>> pkg_map = {"flamapy-fw": ("2.1.0", "2.2.0")}
        >>> updated = update_requirements(
        ...     Path("fm_metamodel/requirements.txt"),
        ...     pkg_map
        ... )
        >>> print(updated)
        ['flamapy-fw']
    """
    if not req_path.exists():
        return []
    text = req_path.read_text(encoding="utf-8")
    updated = []
    for pkg, (_, newv) in pkg_map.items():
        pattern = rf"({re.escape(pkg)}~=)[^\s]+"
        repl = rf"\g<1>{newv}"
        new_text, n = re.subn(pattern, repl, text)
        if n > 0:
            text = new_text
            updated.append(pkg)
    if updated:
        req_path.write_text(text, encoding="utf-8")
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
    ctx.obj["PARENT_DIR"] = ctx.obj.get("PARENT_DIR", os.curdir)
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
    """
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]

    # First pass: collect all package versions
    pkg_versions = {}
    for folder in repos:
        repo = Path(parent_dir) / folder
        setup_py = repo / "setup.py"
        if not setup_py.exists():
            continue
        try:
            pkg_name = extract_package_name(setup_py)
            pkg_version = extract_current_version(setup_py)
            pkg_versions[pkg_name] = pkg_version
        except Exception:
            continue

    # Second pass: show versions with dependencies
    click.echo("\n" + "=" * 60)
    click.echo("PACKAGE VERSIONS")
    click.echo("=" * 60)

    for folder in repos:
        repo = Path(parent_dir) / folder
        setup_py = repo / "setup.py"
        req_file = repo / "requirements.txt"

        if not setup_py.exists():
            click.echo(f"\n{folder}: setup.py not found")
            continue

        try:
            pkg_name = extract_package_name(setup_py)
            pkg_version = extract_current_version(setup_py)
            click.echo(f"\n{folder}/")
            click.echo(f"  Package: {pkg_name} v{pkg_version}")

            if req_file.exists():
                deps = parse_requirements(req_file)
                internal_deps = {k: v for k, v in deps.items() if k in pkg_versions}
                if internal_deps:
                    click.echo("  Internal dependencies:")
                    for dep, ver in internal_deps.items():
                        actual = pkg_versions.get(dep, "?")
                        status = "✓" if ver == actual else f"✗ (actual: {actual})"
                        click.echo(f"    - {dep}~={ver} {status}")
        except Exception as e:
            click.echo(f"\n{folder}: Error - {e}")

    click.echo("\n" + "=" * 60)


@version.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """
    Check if all internal dependencies have matching versions.

    Validates that the versions specified in requirements.txt files
    match the actual versions in the corresponding setup.py files.
    Exits with code 1 if mismatches are found.

    \b
    Example:
        $ flamapy-dev version check
        ✓ All internal dependencies are in sync!

        $ flamapy-dev version check
        ❌ VERSION MISMATCHES FOUND:

          • fm_metamodel/requirements.txt: flamapy-fw~=2.0.0 but flamapy-fw is at v2.1.0

        Total: 1 error(s)
    """
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]

    # Collect all package versions
    pkg_versions = {}
    for folder in repos:
        repo = Path(parent_dir) / folder
        setup_py = repo / "setup.py"
        if not setup_py.exists():
            continue
        try:
            pkg_name = extract_package_name(setup_py)
            pkg_version = extract_current_version(setup_py)
            pkg_versions[pkg_name] = (folder, pkg_version)
        except Exception:
            continue

    # Check dependencies
    errors = []

    for folder in repos:
        repo = Path(parent_dir) / folder
        req_file = repo / "requirements.txt"

        if not req_file.exists():
            continue

        deps = parse_requirements(req_file)
        for dep, required_ver in deps.items():
            if dep in pkg_versions:
                _, actual_ver = pkg_versions[dep]
                if required_ver != actual_ver:
                    errors.append(
                        f"{folder}/requirements.txt: {dep}~={required_ver} "
                        f"but {dep} is at v{actual_ver}"
                    )

    if errors:
        click.echo("\n❌ VERSION MISMATCHES FOUND:\n")
        for err in errors:
            click.echo(f"  • {err}")
        click.echo(f"\nTotal: {len(errors)} error(s)")
        click.echo("\nRun 'flamapy-dev version bump <version>' to fix.")
        ctx.exit(1)
    else:
        click.echo("\n✓ All internal dependencies are in sync!")


@version.command()
@click.argument("new_version")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be changed without modifying files")
@click.pass_context
def bump(ctx: click.Context, new_version: str, dry_run: bool) -> None:
    """
    Bump all repos to the given version and update internal dependencies.

    Updates the version in each setup.py and updates all internal
    dependency references in requirements.txt files.

    \b
    Args:
        new_version: The new version to set (e.g., "2.2.0")

    \b
    Options:
        --dry-run, -n: Preview changes without modifying files

    \b
    Example:
        $ flamapy-dev version bump 2.2.0 --dry-run
        [DRY RUN] Would bump 6 packages to v2.2.0:

        flamapy_fw/
          setup.py: 2.1.0.dev1 → 2.2.0

        $ flamapy-dev version bump 2.2.0
        Bumping 6 packages to v2.2.0...

        flamapy_fw/
          ✓ setup.py: 2.1.0.dev1 → 2.2.0
    """
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]
    pkg_map = {}
    repo_info = {}

    # Gather info for each repo folder
    for folder in repos:
        repo = Path(parent_dir) / folder
        setup_py = repo / "setup.py"
        if not setup_py.exists():
            click.echo(f"{folder}: setup.py not found, skipping.")
            continue
        try:
            oldv = extract_current_version(setup_py)
            pkg_name = extract_package_name(setup_py)
            pkg_map[pkg_name] = (oldv, new_version)
            repo_info[folder] = (repo, pkg_name, oldv, new_version)
        except Exception as e:
            click.echo(f"Error in {folder}: {e}")

    if dry_run:
        click.echo(f"\n[DRY RUN] Would bump {len(repo_info)} packages to v{new_version}:\n")
    else:
        click.echo(f"\nBumping {len(repo_info)} packages to v{new_version}...\n")

    # Apply bumps (or show what would be done)
    for folder, (repo, pkg_name, oldv, newv) in repo_info.items():
        click.echo(f"{folder}/")
        click.echo(f"  setup.py: {oldv} → {newv}")

        # Check requirements.txt for internal deps
        req = repo / "requirements.txt"
        if req.exists():
            deps = parse_requirements(req)
            internal_deps = [dep for dep in deps if dep in pkg_map]
            if internal_deps:
                click.echo(f"  requirements.txt: {', '.join(internal_deps)} → {newv}")

        if not dry_run:
            # Actually update files
            update_setup_py(repo / "setup.py", oldv, newv)
            if req.exists():
                update_requirements(req, pkg_map)

    if dry_run:
        click.echo("\n[DRY RUN] No files were modified.")
        click.echo("Run without --dry-run to apply changes.")
    else:
        click.echo("\n✓ Bump completed.")
        click.echo("\nNext steps:")
        click.echo("  1. Review changes: flamapy-dev git status")
        click.echo("  2. Commit changes in each repo")
        click.echo("  3. Push and create releases")


@version.command()
@click.argument("new_version")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be done without executing")
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
    5. Create and push tags (waits for PyPI availability)

    \b
    Args:
        new_version: The version to release (e.g., "2.2.0")

    \b
    Options:
        --dry-run, -n: Simulate the release without making changes
        --skip-tests: Skip the test execution step

    \b
    Example:
        $ flamapy-dev version release 2.2.0 --dry-run
        ============================================================
        RELEASE v2.2.0
        ============================================================
        [DRY RUN MODE - no changes will be made]

        📋 Step 1: Skipping tests
        📋 Step 2: Bumping versions...
        ...

        $ flamapy-dev version release 2.2.0
        ============================================================
        RELEASE v2.2.0
        ============================================================

        📋 Step 1: Running tests...
          ✓ flamapy_fw
          ✓ fm_metamodel
        ...
    """
    import subprocess

    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]

    click.echo(f"\n{'='*60}")
    click.echo(f"RELEASE v{new_version}")
    click.echo('='*60)

    if dry_run:
        click.echo("[DRY RUN MODE - no changes will be made]\n")

    # Step 1: Run tests (optional)
    if not skip_tests and not dry_run:
        click.echo("\n📋 Step 1: Running tests...")
        for repo_name in repos:
            repo_dir = os.path.join(parent_dir, repo_name)
            if os.path.isdir(repo_dir):
                result = subprocess.run(
                    ["make", "test"],
                    cwd=repo_dir,
                    capture_output=True,
                    check=False
                )
                if result.returncode != 0:
                    click.echo(f"  ✗ Tests failed in {repo_name}")
                    click.echo("Release aborted. Fix tests and try again.")
                    ctx.exit(1)
                click.echo(f"  ✓ {repo_name}")
        click.echo("  All tests passed!")
    else:
        click.echo("\n📋 Step 1: Skipping tests")

    # Step 2: Bump versions
    click.echo("\n📋 Step 2: Bumping versions...")
    ctx.invoke(bump, new_version=new_version, dry_run=dry_run)

    if dry_run:
        click.echo("\n📋 Step 3: Would commit changes")
        click.echo("📋 Step 4: Would push commits")
        click.echo("📋 Step 5: Would create and push tags")
        click.echo(f"\n[DRY RUN] Release v{new_version} simulation complete.")
        return

    # Step 3: Commit changes
    click.echo("\n📋 Step 3: Committing changes...")
    commit_msg = f"chore: bump version to {new_version}"
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            continue

        # Check if there are changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False
        )
        if not result.stdout.strip():
            continue

        subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_dir, check=True)
        click.echo(f"  ✓ {repo_name}")

    # Step 4: Push commits
    click.echo("\n📋 Step 4: Pushing commits...")
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            result = subprocess.run(
                ["git", "push"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                click.echo(f"  ✓ {repo_name}")
            else:
                click.echo(f"  ✗ {repo_name}: {result.stderr.strip()}")

    # Step 5: Create and push tags (uses existing tag-from-setup logic)
    click.echo("\n📋 Step 5: Creating and pushing tags...")
    click.echo("  (Waiting for PyPI availability between repos...)")

    from commands.repositories import wait_for_requirements

    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            continue

        tag = f"v{new_version}"
        req_file = os.path.join(repo_dir, "requirements.txt")

        # Wait for dependencies to be available on PyPI
        if os.path.exists(req_file):
            click.echo(f"  ⏳ {repo_name}: waiting for dependencies...")
            wait_for_requirements(req_file)

        # Create and push tag
        subprocess.run(["git", "tag", tag], cwd=repo_dir, check=True)
        subprocess.run(["git", "push", "origin", tag], cwd=repo_dir, check=True)
        click.echo(f"  ✓ {repo_name}: tagged {tag}")

    click.echo(f"\n{'='*60}")
    click.echo(f"✓ Release v{new_version} completed!")
    click.echo('='*60)


version.add_command(show)
version.add_command(check)
version.add_command(bump)
version.add_command(release)
