import click
from commands import git, pip, version, make
import os
from collections import OrderedDict

# Define the repositories and their URLs
REPOS = OrderedDict(
    [
        ("flamapy_fw", "https://github.com/flamapy/flamapy_fw.git"),
        ("fm_metamodel", "https://github.com/flamapy/fm_metamodel.git"),
        ("pysat_metamodel", "https://github.com/flamapy/pysat_metamodel.git"),
        ("bdd_metamodel", "https://github.com/flamapy/bdd_metamodel.git"),
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
def cli(ctx, parent_dir):
    """Manage flamapy repositories and dependencies with various commands.

    Examples:
        $ flamapy-dev git clone
        $ flamapy-dev --parent-dir /path/to/parent_dir git clone
    """
    ctx.ensure_object(dict)
    ctx.obj["REPOS"] = REPOS
    ctx.obj["PARENT_DIR"] = parent_dir
    pass


# Add command groups
cli.add_command(git)
cli.add_command(pip)
cli.add_command(version)
cli.add_command(make)

if __name__ == "__main__":
    cli()
