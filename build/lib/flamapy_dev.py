import click
from commands import git, pip
import os

# Define the repositories and their URLs
REPOS = {
    "flamapy": "https://github.com/flamapy/flamapy.git",
    "flamapy_fw": "https://github.com/flamapy/flamapy_fw.git",
    "flamapy_rest": "https://github.com/flamapy/flamapy_rest.git",
    "fm_metamodel": "https://github.com/flamapy/fm_metamodel.git",
    "pysat_metamodel": "https://github.com/flamapy/pysat_metamodel.git",
    "bdd_metamodel": "https://github.com/flamapy/bdd_metamodel.git",
    "flamapy_docs": "https://github.com/flamapy/flamapy_docs.git",
    "flamapy.github.io": "https://github.com/flamapy/flamapy.github.io.git"
}

#PARENT_DIR = os.path.join(os.pardir)
PARENT_DIR = os.path.join(os.curdir)

@click.group()
@click.pass_context
def cli(ctx):
    """Manage repositories and dependencies with various commands."""
    ctx.ensure_object(dict)
    ctx.obj['REPOS'] = REPOS
    ctx.obj['PARENT_DIR'] = PARENT_DIR
    pass

# Add command groups
cli.add_command(git)
cli.add_command(pip)