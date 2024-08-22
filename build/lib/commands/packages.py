import click
import subprocess
import os


@click.group()
@click.pass_context
def pip(ctx):
    """Commands for managing Python dependencies."""
    ctx.ensure_object(dict)
    ctx.obj['PARENT_DIR'] = ctx.obj.get('PARENT_DIR', '')
    pass

@click.command()
@click.pass_context
def install(ctx):
    """Install dependencies from each directory's setup.py."""
    parent_dir = ctx.obj['PARENT_DIR']
    for root, dirs, files in os.walk(parent_dir):
        if "setup.py" in files:
            click.echo(f"Installing package in {root}...")
            subprocess.run(["pip", "install", "."], cwd=root, check=True)
        else:
            click.echo(f"No setup.py found in {root}.")

@click.command()
@click.pass_context
def update(ctx):
    """Update dependencies from each directory's setup.py."""
    parent_dir = ctx.obj['PARENT_DIR']
    for root, dirs, files in os.walk(parent_dir):
        if "setup.py" in files:
            click.echo(f"Updating package in {root}...")
            subprocess.run(["pip", "install", "--upgrade", "."], cwd=root, check=True)
        else:
            click.echo(f"No setup.py found in {root}.")

@click.command()
@click.pass_context
def remove(ctx):
    """Uninstall packages from each directory's setup.py."""
    parent_dir = ctx.obj['PARENT_DIR']
    for root, dirs, files in os.walk(parent_dir):
        if "setup.py" in files:
            click.echo(f"Uninstalling package in {root}...")
            subprocess.run(["pip", "uninstall", "-y", "."], cwd=root, check=True)
        else:
            click.echo(f"No setup.py found in {root}.")

pip.add_command(install)
pip.add_command(update)
pip.add_command(remove)
