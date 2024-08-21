import click
from developer.flamapy_dev import git, pip

@click.group()
def cli():
    """Manage repositories and dependencies with various commands."""
    pass

# Add command groups
cli.add_command(git)
cli.add_command(pip)

if __name__ == '__main__':
    cli()


