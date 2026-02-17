"""
Python package management commands for flamapy-dev.

This module provides commands for installing, updating, and removing
Python packages across all repositories.

Example usage:
    $ flamapy-dev pip install
    $ flamapy-dev pip install-dev
    $ flamapy-dev pip update
    $ flamapy-dev pip remove
"""

import subprocess
from pathlib import Path

import click


@click.group()
@click.pass_context
def pip(ctx: click.Context) -> None:
    """
    Commands for managing Python dependencies.

    This command group provides tools for installing, updating,
    and removing packages across all flamapy repositories.

    \b
    Examples:
        $ flamapy-dev pip install       # Install all packages
        $ flamapy-dev pip install-dev   # Install in editable mode
        $ flamapy-dev pip update        # Update all packages
        $ flamapy-dev pip remove        # Uninstall all packages
    """
    ctx.ensure_object(dict)
    ctx.obj["PARENT_DIR"] = ctx.obj.get("PARENT_DIR", "")
    ctx.obj["REPOS"] = ctx.obj.get("REPOS", {})


def process_directories(ctx: click.Context, command: str) -> None:
    """
    Execute a pip command in all repository directories.

    Args:
        ctx: Click context with REPOS and PARENT_DIR.
        command: The pip command to execute (e.g., "install", "install --upgrade").

    Example:
        >>> process_directories(ctx, "install")
        # Runs "pip install ." in each repository
    """
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    repos = ctx.obj["REPOS"]
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        setup_path = repo_dir / "setup.py"

        click.echo(f"Checking: {setup_path.resolve()}")

        if setup_path.exists():
            click.echo(f"Processing {repo_dir}...")
            subprocess.run(["pip", *command.split(), "."], cwd=repo_dir, check=True)
        else:
            click.echo(f"{repo_dir} does not contain a setup.py file.")


@click.command()
@click.pass_context
def install(ctx: click.Context) -> None:
    """
    Install packages from each repository's setup.py.

    Runs 'pip install .' in each repository directory.
    Packages are installed in the order defined in REPOS
    to ensure dependencies are satisfied.

    \b
    Example:
        $ flamapy-dev pip install
        Checking: /path/to/flamapy_fw/setup.py
        Processing /path/to/flamapy_fw...
        Successfully installed flamapy-fw-2.1.0
    """
    process_directories(ctx, "install")


@click.command(name="install-dev")
@click.pass_context
def install_dev(ctx: click.Context) -> None:
    """
    Install packages in editable mode for development.

    Runs 'pip install -e .' in each repository directory.
    Editable mode allows code changes to take effect immediately
    without reinstalling.

    \b
    Example:
        $ flamapy-dev pip install-dev
        Installing flamapy_fw in editable mode...
          ✓ flamapy_fw installed
        Installing fm_metamodel in editable mode...
          ✓ fm_metamodel installed
    """
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    repos = ctx.obj["REPOS"]
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        setup_path = repo_dir / "setup.py"

        if setup_path.exists():
            click.echo(f"Installing {repo_name} in editable mode...")
            result = subprocess.run(
                ["pip", "install", "-e", "."],
                cwd=repo_dir,
                check=False
            )
            if result.returncode == 0:
                click.echo(f"  ✓ {repo_name} installed")
            else:
                click.echo(f"  ✗ {repo_name} failed")
        else:
            click.echo(f"{repo_dir} does not contain a setup.py file.")


@click.command()
@click.pass_context
def update(ctx: click.Context) -> None:
    """
    Update packages from each repository's setup.py.

    Runs 'pip install --upgrade .' in each repository directory.

    \b
    Example:
        $ flamapy-dev pip update
        Checking: /path/to/flamapy_fw/setup.py
        Processing /path/to/flamapy_fw...
        Successfully installed flamapy-fw-2.2.0
    """
    process_directories(ctx, "install --upgrade")


@click.command()
@click.pass_context
def remove(ctx: click.Context) -> None:
    """
    Uninstall packages from each repository's setup.py.

    Runs 'pip uninstall -y .' in each repository directory.

    \b
    Example:
        $ flamapy-dev pip remove
        Checking: /path/to/flamapy_fw/setup.py
        Processing /path/to/flamapy_fw...
        Successfully uninstalled flamapy-fw-2.1.0
    """
    process_directories(ctx, "uninstall -y")


pip.add_command(install)
pip.add_command(install_dev)
pip.add_command(update)
pip.add_command(remove)
