import click
import subprocess
import os
import shutil
import time
import json
from urllib import request, error
from packaging.requirements import Requirement


def _parse_requirements(req_file: str):
    """Return a list of Requirement objects for the given requirements file."""
    requirements = []
    if not os.path.exists(req_file):
        return requirements
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip() # noqa: PLW2901
            if not line or line.startswith("#"):
                continue
            try:
                requirements.append(Requirement(line))
            except Exception:
                continue
    return requirements


def _package_available(req: Requirement) -> bool:
    """Return True if the given requirement is satisfied by a version on PyPI."""
    url = f"https://pypi.org/pypi/{req.name}/json"
    try:
        with request.urlopen(url, timeout=10) as resp:
            if resp.status != 200: # noqa: PLR2004
                return False
            data = json.load(resp)
    except error.URLError:
        return False
    except Exception:
        return False
    if not req.specifier:
        return True
    releases = data.get("releases", {})
    for ver in releases.keys():
        try:
            if req.specifier.contains(ver, prereleases=True):
                return True
        except Exception:
            continue
    return False


def wait_for_requirements(req_file: str, check_interval: int = 10):
    """Block until all requirements from req_file are available on PyPI."""
    requirements = _parse_requirements(req_file)
    if not requirements:
        return
    while True:
        if all(_package_available(r) for r in requirements):
            return
        time.sleep(check_interval)


@click.group()
@click.pass_context
def git(ctx):
    """Git-related commands."""
    ctx.ensure_object(dict)
    ctx.obj["REPOS"] = ctx.obj.get("REPOS", {})
    ctx.obj["PARENT_DIR"] = ctx.obj.get("PARENT_DIR", "")


@git.command()
@click.pass_context
def clone(ctx):
    """Clone all repositories."""
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
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
    """Switch all repositories to the develop branch if it exists."""
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Switching {repo_name} to branch develop...")
            if (
                subprocess.run(
                    ["git", "show-ref", "--verify", "--quiet", "refs/heads/develop"],
                    check=False,
                    cwd=repo_dir,
                ).returncode
                == 0
            ):
                subprocess.run(["git", "switch", "develop"], cwd=repo_dir, check=True)
            elif (
                subprocess.run(
                    ["git", "ls-remote", "--exit-code", "--heads", "origin", "develop"],
                    check=False,
                    cwd=repo_dir,
                ).returncode
                == 0
            ):
                subprocess.run(["git", "fetch", "origin"], cwd=repo_dir, check=True)
                subprocess.run(
                    ["git", "switch", "-c", "develop", "origin/develop"], cwd=repo_dir, check=True
                )
            else:
                click.echo("Branch 'develop' does not exist.")
        else:
            click.echo(f"{repo_name} does not exist.")


@click.command(name="switch-main")
@click.pass_context
def switch_main(ctx):
    """Switch all repositories to the main branch if it exists, otherwise to master."""
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Checking branches for {repo_name}...")
            if (
                subprocess.run(
                    ["git", "show-ref", "--verify", "--quiet", "refs/heads/main"],
                    check=False,
                    cwd=repo_dir,
                ).returncode
                == 0
            ):
                click.echo(f"Switching {repo_name} to branch main...")
                subprocess.run(["git", "switch", "main"], cwd=repo_dir, check=True)
            elif (
                subprocess.run(
                    ["git", "show-ref", "--verify", "--quiet", "refs/heads/master"],
                    check=False,
                    cwd=repo_dir,
                ).returncode
                == 0
            ):
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
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
    for repo_name in repos:
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
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            click.echo(f"Status of {repo_name}:")
            subprocess.run(["git", "status"], check=False, cwd=repo_dir)
        else:
            click.echo(f"{repo_name} does not exist.")


@click.command()
@click.pass_context
def delete(ctx):
    """Delete all repository directories."""
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(repo_dir):
            click.echo(f"Deleting directory {repo_dir}...")
            shutil.rmtree(repo_dir)
        else:
            click.echo(f"{repo_name} directory does not exist.")


@git.command()
@click.argument("tag")
@click.pass_context
def tag_repo(ctx, tag):
    """Create and push a Git tag to all repositories."""
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            req_file = os.path.join(repo_dir, "requirements.txt")
            if os.path.exists(req_file):
                click.echo(f"Waiting for PyPI packages of {repo_name}...")
                wait_for_requirements(req_file)
            click.echo(f"Tagging {repo_name} with {tag}...")
            subprocess.run(["git", "tag", tag], cwd=repo_dir, check=True)
            click.echo(f"Pushing tag {tag} for {repo_name}...")
            subprocess.run(["git", "push", "origin", tag], cwd=repo_dir, check=True)
        else:
            click.echo(f"{repo_name} does not exist.")


git.add_command(clone)
git.add_command(switch_develop)
git.add_command(switch_main)
git.add_command(pull)
git.add_command(delete)
git.add_command(status)
git.add_command(tag_repo)
