import click
import subprocess
import os
import re
from pathlib import Path

# Helper functions for bump logic


def extract_current_version(setup_path: Path) -> str:
    text = setup_path.read_text(encoding="utf-8")
    m = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise ValueError(f"No se encontró version en {setup_path}")
    return m.group(1)


def extract_package_name(setup_path: Path) -> str:
    text = setup_path.read_text(encoding="utf-8")
    m = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise ValueError(f"No se encontró name en {setup_path}")
    return m.group(1)


def update_setup_py(setup_path: Path, old_version: str, new_version: str):
    text = setup_path.read_text(encoding="utf-8")
    pattern = r"(version\s*=\s*['\"])" + re.escape(old_version) + r"(['\"])"
    repl = r"\g<1>" + new_version + r"\g<2>"
    new_text, n = re.subn(pattern, repl, text)
    if n == 0:
        click.echo(f"Advertencia: no se actualizó version en {setup_path}")
    else:
        setup_path.write_text(new_text, encoding="utf-8")
        click.echo(f"Actualizada version en {setup_path}: {old_version} -> {new_version}")


def update_requirements(req_path: Path, pkg_map: dict):
    text = req_path.read_text(encoding="utf-8")
    changed = False
    for pkg, (_, newv) in pkg_map.items():
        pattern = rf"{re.escape(pkg)}~=[^\s]+"
        repl = f"{pkg}~={newv}"
        new_text, n = re.subn(pattern, repl, text)
        if n > 0:
            text = new_text
            changed = True
            click.echo(f"Actualizada dependencia {pkg} en {req_path}: nueva versión -> {newv}")
    if changed:
        req_path.write_text(text, encoding="utf-8")


def bump_with_bump_my_version(repo: Path, files: list, new_version: str):
    cmd = ["bump-my-version", "--version", new_version, *files]
    subprocess.run(cmd, cwd=repo, check=True)
    click.echo(f"Ejecutado bump-my-version en {', '.join(files)}")


@click.group()
@click.pass_context
def version(ctx):
    """Commands for managing Python dependencies."""
    ctx.ensure_object(dict)
    ctx.obj["PARENT_DIR"] = ctx.obj.get("PARENT_DIR", os.curdir)
    ctx.obj["REPOS"] = ctx.obj.get("REPOS", {})


# New bump command: use ctx.obj['REPOS'] and a single version argument
@version.command()
@click.argument("new_version")
@click.pass_context
def bump(ctx, new_version):
    """Bump all repos listed in REPOS to the given version."""
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
            repo_info[pkg_name] = (repo, oldv, new_version)
        except Exception as e:
            click.echo(f"Error in {folder}: {e}")

    # Apply bumps
    for pkg_name, (repo, oldv, newv) in repo_info.items():
        click.echo(f"Bumping {pkg_name}: {oldv} -> {newv}")
        update_setup_py(repo / "setup.py", oldv, newv)
        req = repo / "requirements.txt"
        if req.exists():
            update_requirements(req, pkg_map)
            bump_with_bump_my_version(repo, [str(req)], new_version=newv)
    click.echo("Bump completed.")


version.add_command(bump)
