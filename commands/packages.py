import click
import subprocess
import os


@click.group()
@click.pass_context
def pip(ctx):
    """Commands for managing Python dependencies."""
    ctx.ensure_object(dict)
    ctx.obj['PARENT_DIR'] = ctx.obj.get('PARENT_DIR', '')
    ctx.obj['REPOS'] = ctx.obj.get('REPOS', {})
    pass

def process_directories(ctx, command):
    parent_dir = ctx.obj['PARENT_DIR']
    repos = ctx.obj['REPOS']
    for repo_name in repos.keys():
        repo_dir = os.path.join(parent_dir, repo_name)
        setup_path = os.path.join(repo_dir, "setup.py")

        absolute_setup_path = os.path.abspath(setup_path)
        click.echo(f"Checking: {absolute_setup_path}")

        if os.path.exists(setup_path):
            click.echo(f"Processing {repo_dir}...")
            subprocess.run(f"pip {command} .", cwd=repo_dir, shell=True, check=True)
        else:
            click.echo(f"{repo_dir} does not contain a setup.py file.")

@click.command()
@click.pass_context
def install(ctx):
    """Install dependencies from each directory's setup.py."""
    process_directories(ctx, "install")

@click.command()
@click.pass_context
def update(ctx):
    """Update dependencies from each directory's setup.py."""
    process_directories(ctx, "install --upgrade")

@click.command()
@click.pass_context
def remove(ctx):
    """Uninstall packages from each directory's setup.py."""
    process_directories(ctx, "uninstall -y")

pip.add_command(install)
pip.add_command(update)
pip.add_command(remove)
