import click
import os
import re
from pathlib import Path

# Helper functions for version management


def extract_current_version(setup_path: Path) -> str:
    """Extract version string from setup.py."""
    text = setup_path.read_text(encoding="utf-8")
    m = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise ValueError(f"No se encontró version en {setup_path}")
    return m.group(1)


def extract_package_name(setup_path: Path) -> str:
    """Extract package name from setup.py."""
    text = setup_path.read_text(encoding="utf-8")
    m = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise ValueError(f"No se encontró name en {setup_path}")
    return m.group(1)


def parse_requirements(req_path: Path) -> dict[str, str]:
    """Parse requirements.txt and return dict of {package_name: version_spec}."""
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
    """Update version in setup.py. Returns True if updated."""
    text = setup_path.read_text(encoding="utf-8")
    pattern = r"(version\s*=\s*['\"])" + re.escape(old_version) + r"(['\"])"
    repl = r"\g<1>" + new_version + r"\g<2>"
    new_text, n = re.subn(pattern, repl, text)
    if n == 0:
        return False
    setup_path.write_text(new_text, encoding="utf-8")
    return True


def update_requirements(req_path: Path, pkg_map: dict[str, tuple[str, str]]) -> list[str]:
    """Update requirements.txt with new versions. Returns list of updated packages."""
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
def version(ctx):
    """Commands for managing package versions."""
    ctx.ensure_object(dict)
    ctx.obj["PARENT_DIR"] = ctx.obj.get("PARENT_DIR", os.curdir)
    ctx.obj["REPOS"] = ctx.obj.get("REPOS", {})


@version.command()
@click.pass_context
def show(ctx):
    """Show current versions of all packages and their dependencies."""
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
def check(ctx):
    """Check if all internal dependencies have matching versions."""
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
    warnings = []

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
@click.pass_context
def bump(ctx, new_version):
    """Bump all repos to the given version and update internal dependencies."""
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

    click.echo(f"\nBumping {len(repo_info)} packages to v{new_version}...\n")

    # Apply bumps
    for folder, (repo, pkg_name, oldv, newv) in repo_info.items():
        click.echo(f"{folder}/")

        # Update setup.py
        if update_setup_py(repo / "setup.py", oldv, newv):
            click.echo(f"  ✓ setup.py: {oldv} → {newv}")
        else:
            click.echo(f"  ✗ setup.py: failed to update")

        # Update requirements.txt
        req = repo / "requirements.txt"
        if req.exists():
            updated = update_requirements(req, pkg_map)
            if updated:
                click.echo(f"  ✓ requirements.txt: updated {', '.join(updated)}")

    click.echo("\n✓ Bump completed.")
    click.echo("\nNext steps:")
    click.echo("  1. Review changes: flamapy-dev git status")
    click.echo("  2. Commit changes in each repo")
    click.echo("  3. Push and create releases")


version.add_command(show)
version.add_command(check)
version.add_command(bump)
