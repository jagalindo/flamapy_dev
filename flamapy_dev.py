import click
from commands import git, pip
import os

# Define the repositories and their URLs
REPOS = {
    "flamapy_fw": "https://github.com/flamapy/flamapy_fw.git",
    "fm_metamodel": "https://github.com/flamapy/fm_metamodel.git",
    "pysat_metamodel": "https://github.com/flamapy/pysat_metamodel.git",
    "bdd_metamodel": "https://github.com/flamapy/bdd_metamodel.git",
    "flamapy": "https://github.com/flamapy/flamapy.git",
    #"flamapy_rest": "https://github.com/flamapy/flamapy_rest.git",
    #"flamapy_docs": "https://github.com/flamapy/flamapy_docs.git",
    #"flamapy.github.io": "https://github.com/flamapy/flamapy.github.io.git"
}

# Define the default parent directory. Current directory is the default.
DEFAULT_PARENT_DIR = os.path.join(os.curdir)

@click.group()
@click.pass_context
@click.argument('parent_dir', 
                default=os.path.join(os.pardir), 
                type=click.Path(exists=True, 
                                file_okay=False, 
                                dir_okay=True, 
                                writable=True), 
                required=False, 
                metavar='[PARENT_DIR]',
)
def cli(ctx, parent_dir):
    """Manage flamapy repositories and dependencies with various commands.

    \b
    PARENT_DIR:
        - Optional positional argument. Specifies the parent directory where operations should be performed.
        - If not provided, the default is the current working directory.

    \b
    Examples:
        - Run commands in the default parent directory:
            $ flamapy-dev git clone
        
        - Run commands in a specific directory:
            $ flamapy-dev /path/to/parent_dir git clone
    """    
    ctx.ensure_object(dict)
    ctx.obj['REPOS'] = REPOS
    ctx.obj['PARENT_DIR'] = parent_dir
    pass

# Add command groups
cli.add_command(git)
cli.add_command(pip)