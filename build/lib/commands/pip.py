import click
import subprocess
import os

PARENT_DIR = ".."

@click.group()
def pip():
    """Commands for managing Python dependencies."""
    pass

@click.command()
def install():
    """Install dependencies from each directory's setup.py."""
    for root, dirs, files in os.walk(PARENT_DIR):
        if "setup.py" in files:
            click.echo(f"Installing package in {root}...")
            subprocess.run(["pip", "install", "."], cwd=root, check=True)
        else:
            click.echo(f"No setup.py found in {root}.")

@click.command()
def update():
    """Update dependencies from each directory's setup.py."""
    for root, dirs, files in os.walk(PARENT_DIR):
        if "setup.py" in files:
            click.echo(f"Updating package in {root}...")
            subprocess.run(["pip", "install", "--upgrade", "."], cwd=root, check=True)
        else:
            click.echo(f"No setup.py found in {root}.")

@click.command()
def remove():
    """Uninstall packages from each directory's setup.py."""
    for root, dirs, files in os.walk(PARENT_DIR):
        if "setup.py" in files:
            click.echo(f"Uninstalling package in {root}...")
            subprocess.run(["pip", "uninstall", "-y", "."], cwd=root, check=True)
        else:
            click.echo(f"No setup.py found in {root}.")
