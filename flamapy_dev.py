"""
Flamapy Development CLI Tool.

This is the main entry point for the flamapy-dev CLI, which provides
commands for managing multiple flamapy repositories simultaneously.

Example usage:
    $ flamapy-dev git clone           # Clone all repositories
    $ flamapy-dev version show        # Show package versions
    $ flamapy-dev make all            # Run all checks
    $ flamapy-dev docs help-all       # Show quick reference

For more information, see:
    $ flamapy-dev --help
    $ flamapy-dev docs show
"""

import click
from commands import git, pip, version, make, docs
import os
from collections import OrderedDict

# Define the repositories and their URLs.
# Order matters: dependencies must come before dependents.
REPOS = OrderedDict(
    [
        ("flamapy_fw", "https://github.com/flamapy/flamapy_fw.git"),
        ("fm_metamodel", "https://github.com/flamapy/fm_metamodel.git"),
        ("pysat_metamodel", "https://github.com/flamapy/pysat_metamodel.git"),
        ("bdd_metamodel", "https://github.com/flamapy/bdd_metamodel.git"),
        ("z3_metamodel", "https://github.com/flamapy/z3_metamodel.git"),
        ("flamapy", "https://github.com/flamapy/flamapy.git"),
        # ("flamapy_rest", "https://github.com/flamapy/flamapy_rest.git"),
        # ("flamapy_docs", "https://github.com/flamapy/flamapy_docs.git"),
        # ("flamapy.github.io", "https://github.com/flamapy/flamapy.github.io.git"),
    ]
)

# Define the default parent directory as the current directory.
DEFAULT_PARENT_DIR = os.curdir


@click.group()
@click.pass_context
@click.option(
    "--parent-dir",
    "-d",
    default=DEFAULT_PARENT_DIR,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    show_default=True,
    help="Parent directory where operations should be performed.",
)
def cli(ctx: click.Context, parent_dir: str) -> None:
    """
    Manage flamapy repositories and dependencies with various commands.

    This CLI tool helps manage multiple flamapy repositories simultaneously,
    including git operations, package management, version control, and
    quality checks.

    \b
    Command Groups:
        git      - Repository management (clone, pull, branch, etc.)
        pip      - Package management (install, update, remove)
        make     - Run make targets (lint, test, mypy)
        version  - Version management (show, check, bump, release)
        docs     - Documentation (show, generate)

    \b
    Examples:
        $ flamapy-dev git clone
        $ flamapy-dev --parent-dir /path/to/repos git pull
        $ flamapy-dev version show
        $ flamapy-dev make all -c

    \b
    For detailed help on any command:
        $ flamapy-dev <command> --help
        $ flamapy-dev <command> <subcommand> --help
    """
    ctx.ensure_object(dict)
    ctx.obj["REPOS"] = REPOS
    ctx.obj["PARENT_DIR"] = parent_dir


# Add command groups
cli.add_command(docs)
cli.add_command(git)
cli.add_command(make)
cli.add_command(pip)
cli.add_command(version)

if __name__ == "__main__":
    cli()
