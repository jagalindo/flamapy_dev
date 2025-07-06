import click
import subprocess
import os
import shutil


@click.group()
@click.pass_context
def git(ctx):
    """Git-related commands."""
    ctx.ensure_object(dict)
    ctx.obj['REPOS'] = ctx.obj.get('REPOS', {})
    ctx.obj['PARENT_DIR'] = ctx.obj.get('PARENT_DIR', '')

@git.command()
@click.pass_context
def clone(ctx):
    """Clone all repositories."""
    repos = ctx.obj['REPOS']
    parent_dir = ctx.obj['PARENT_DIR']
    for repo_name, repo_url in repos.items():
        repo_dir = os.path.join(parent_dir, repo_name)
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Cloning {repo_name} from {repo_url}...")
            subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
        else:
            click.echo(f"{repo_name} already exists.")

@git.command()
@click.pass_context
def switch_develop(ctx):
    """Switch all repositories to the develop branch."""
    repos = ctx.obj['REPOS']
    parent_dir = ctx.obj['PARENT_DIR']
    for repo_name in repos.keys():
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Switching {repo_name} to branch develop...")
            subprocess.run(["git", "switch", "develop"], cwd=repo_dir, check=True)
        else:
            click.echo(f"{repo_name} does not exist.")

@click.command(name="switch_main_or_master")
@click.pass_context
def switch_main_or_master(ctx):
    """Switch all repositories to the main branch if it exists, otherwise to master."""
    repos = ctx.obj['REPOS']
    parent_dir = ctx.obj['PARENT_DIR']
    for repo_name in repos.keys():
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Checking branches for {repo_name}...")
            if subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/main"], cwd=repo_dir).returncode == 0:
                click.echo(f"Switching {repo_name} to branch main...")
                subprocess.run(["git", "switch", "main"], cwd=repo_dir, check=True)
            elif subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/master"], cwd=repo_dir).returncode == 0:
                click.echo(f"Switching {repo_name} to branch master...")
                subprocess.run(["git", "switch", "master"], cwd=repo_dir, check=True)
            else:
                click.echo(f"Neither 'main' nor 'master' branch exists for {repo_name}.")
        else:
            click.echo(f"{repo_name} does not exist.")

@click.command()
@click.pass_context
def pull(ctx):
    """Pull the latest changes for all repositories."""
    repos = ctx.obj['REPOS']
    parent_dir = ctx.obj['PARENT_DIR']
    for repo_name in repos.keys():
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Pulling latest changes for {repo_name}...")
            subprocess.run(["git", "pull"], cwd=repo_dir, check=True)
        else:
            click.echo(f"{repo_name} does not exist.")

@click.command()
@click.pass_context
def status(ctx):
    """Show status of all repositories."""
    repos = ctx.obj['REPOS']
    parent_dir = ctx.obj['PARENT_DIR']
    for repo_name in repos.keys():
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Status of {repo_name}:")
            subprocess.run(["git", "status"], cwd=repo_dir)
        else:
            click.echo(f"{repo_name} does not exist.")

@click.command()
@click.pass_context
def delete(ctx):
    """Delete all repository directories."""
    repos = ctx.obj['REPOS']
    parent_dir = ctx.obj['PARENT_DIR']
    for repo_name in repos.keys():
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(repo_dir):
            click.echo(f"Deleting directory {repo_dir}...")
            shutil.rmtree(repo_dir)
        else:
            click.echo(f"{repo_name} directory does not exist.")

git.add_command(clone)
git.add_command(switch_develop)
git.add_command(switch_main_or_master)
git.add_command(pull)
git.add_command(delete)
git.add_command(status)
