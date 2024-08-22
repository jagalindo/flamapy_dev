import click
import subprocess
import os
import shutil


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

PARENT_DIR = ".."

@click.group()
def git():
    """Commands for managing Git repositories."""
    pass

@click.command()
def clone():
    """Clone all repositories."""
    for repo_name, repo_url in REPOS.items():
        repo_dir = os.path.join(PARENT_DIR, repo_name)
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Cloning {repo_name} from {repo_url}...")
            subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
        else:
            click.echo(f"{repo_name} already exists.")

@click.command()
def switch_develop():
    """Switch all repositories to the develop branch."""
    for repo_name in REPOS.keys():
        repo_dir = os.path.join(PARENT_DIR, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Switching {repo_name} to branch develop...")
            subprocess.run(["git", "switch", "develop"], cwd=repo_dir, check=True)
        else:
            click.echo(f"{repo_name} does not exist.")

@click.command()
def switch_main():
    """Switch all repositories to the main or master branch."""
    for repo_name in REPOS.keys():
        repo_dir = os.path.join(PARENT_DIR, repo_name)
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
def status():
    """Show status of all repositories."""
    for repo_name in REPOS.keys():
        repo_dir = os.path.join(PARENT_DIR, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Status of {repo_name}:")
            subprocess.run(["git", "status"], cwd=repo_dir)
        else:
            click.echo(f"{repo_name} does not exist.")

@click.command()
def delete():
    """Delete all repository directories."""
    for repo_name in REPOS.keys():
        repo_dir = os.path.join(PARENT_DIR, repo_name)
        if os.path.isdir(repo_dir):
            click.echo(f"Deleting directory {repo_dir}...")
            shutil.rmtree(repo_dir)
        else:
            click.echo(f"{repo_name} directory does not exist.")

git.add_command(clone)
git.add_command(switch_develop)
git.add_command(switch_main)
git.add_command(delete)
git.add_command(status)