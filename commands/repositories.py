"""
Git repository management commands for flamapy-dev.

This module provides commands for managing multiple Git repositories
simultaneously, including cloning, branching, committing, and tagging.

Example usage:
    $ flamapy-dev git clone
    $ flamapy-dev git branch
    $ flamapy-dev git commit-all "feat: add new feature"
"""

import click
import subprocess
import os
import shutil
import time
import json
from pathlib import Path
from urllib import request, error
from packaging.requirements import Requirement
from commands.versions import extract_current_version


def _parse_requirements(req_file: str) -> list[Requirement]:
    """
    Parse a requirements.txt file and return a list of Requirement objects.

    Args:
        req_file: Path to the requirements.txt file.

    Returns:
        List of packaging.requirements.Requirement objects.

    Example:
        >>> reqs = _parse_requirements("requirements.txt")
        >>> for req in reqs:
        ...     print(req.name, req.specifier)
    """
    requirements = []
    if not os.path.exists(req_file):
        return requirements
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                requirements.append(Requirement(line))
            except Exception:
                continue
    return requirements


def _package_available(req: Requirement) -> bool:
    """
    Check if a package version is available on PyPI.

    Args:
        req: A Requirement object specifying the package and version constraints.

    Returns:
        True if the package version is available on PyPI, False otherwise.

    Example:
        >>> from packaging.requirements import Requirement
        >>> req = Requirement("flamapy-fw~=2.1.0")
        >>> _package_available(req)
        True
    """
    url = f"https://pypi.org/pypi/{req.name}/json"
    try:
        with request.urlopen(url, timeout=10) as resp:
            if resp.status != 200:
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


def wait_for_requirements(req_file: str, check_interval: int = 10) -> None:
    """
    Block until all requirements from a file are available on PyPI.

    This function is useful when releasing packages that depend on each other,
    ensuring that dependencies are published before dependent packages are tagged.

    Args:
        req_file: Path to the requirements.txt file.
        check_interval: Seconds to wait between PyPI checks (default: 10).

    Example:
        >>> wait_for_requirements("requirements.txt")
        # Blocks until all packages in requirements.txt are on PyPI
    """
    requirements = _parse_requirements(req_file)
    if not requirements:
        return
    while True:
        if all(_package_available(r) for r in requirements):
            return
        time.sleep(check_interval)


@click.group()
@click.pass_context
def git(ctx: click.Context) -> None:
    """
    Git-related commands for managing multiple repositories.

    This command group provides tools for cloning, updating, and managing
    multiple Git repositories simultaneously.

    \b
    Examples:
        $ flamapy-dev git clone          # Clone all repositories
        $ flamapy-dev git pull           # Pull all repositories
        $ flamapy-dev git branch         # Show branches of all repos
        $ flamapy-dev git status         # Show status of all repos
    """
    ctx.ensure_object(dict)
    ctx.obj["REPOS"] = ctx.obj.get("REPOS", {})
    ctx.obj["PARENT_DIR"] = ctx.obj.get("PARENT_DIR", "")


@git.command()
@click.pass_context
def clone(ctx: click.Context) -> None:
    """
    Clone all repositories defined in the configuration.

    Clones each repository to a subdirectory of the parent directory.
    Skips repositories that already exist.

    \b
    Example:
        $ flamapy-dev git clone
        Cloning flamapy_fw from https://github.com/flamapy/flamapy_fw.git...
        Cloning fm_metamodel from https://github.com/flamapy/fm_metamodel.git...
    """
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
def switch_develop(ctx: click.Context) -> None:
    """
    Switch all repositories to the 'develop' branch.

    If the branch exists locally, switches to it. If it only exists on
    the remote, fetches and creates a local tracking branch.

    \b
    Example:
        $ flamapy-dev git switch_develop
        Switching flamapy_fw to branch develop...
        Switching fm_metamodel to branch develop...
    """
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
def switch_main(ctx: click.Context) -> None:
    """
    Switch all repositories to 'main' or 'master' branch.

    Attempts to switch to 'main' first. If it doesn't exist,
    falls back to 'master'.

    \b
    Example:
        $ flamapy-dev git switch-main
        Switching flamapy_fw to branch main...
        Switching fm_metamodel to branch main...
    """
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
def pull(ctx: click.Context) -> None:
    """
    Pull the latest changes for all repositories.

    Executes 'git pull' in each repository directory.

    \b
    Example:
        $ flamapy-dev git pull
        Pulling latest changes for flamapy_fw...
        Already up to date.
    """
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
def status(ctx: click.Context) -> None:
    """
    Show the Git status of all repositories.

    Executes 'git status' in each repository directory.

    \b
    Example:
        $ flamapy-dev git status
        Status of flamapy_fw:
        On branch develop
        nothing to commit, working tree clean
    """
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
def delete(ctx: click.Context) -> None:
    """
    Delete all repository directories.

    WARNING: This permanently deletes all cloned repositories.
    Use with caution.

    \b
    Example:
        $ flamapy-dev git delete
        Deleting directory ./flamapy_fw...
        Deleting directory ./fm_metamodel...
    """
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
def tag_repo(ctx: click.Context, tag: str) -> None:
    """
    Create and push a Git tag to all repositories.

    Waits for PyPI dependencies to be available before tagging each repo.

    \b
    Args:
        tag: The tag name to create (e.g., "v2.1.0")

    \b
    Example:
        $ flamapy-dev git tag_repo v2.1.0
        Tagging flamapy_fw with v2.1.0...
        Pushing tag v2.1.0 for flamapy_fw...
    """
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


@git.command(name="tag-from-setup")
@click.pass_context
def tag_from_setup(ctx: click.Context) -> None:
    """
    Create and push Git tags based on setup.py versions.

    Reads the version from each repository's setup.py and creates
    a tag with the format "v{version}". Waits for PyPI dependencies
    before tagging.

    \b
    Example:
        $ flamapy-dev git tag-from-setup
        Tagging flamapy_fw with v2.1.0...
        Pushing tag v2.1.0 for flamapy_fw...
    """
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            setup_path = os.path.join(repo_dir, "setup.py")
            if not os.path.exists(setup_path):
                click.echo(f"setup.py not found in {repo_name}, skipping.")
                continue
            version = extract_current_version(Path(setup_path))
            tag = f"v{version}"
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


@git.command(name="branch")
@click.pass_context
def branch(ctx: click.Context) -> None:
    """
    Show the current branch for all repositories.

    Displays each repository's current branch and checks if all
    repositories are on the same branch.

    \b
    Example:
        $ flamapy-dev git branch
        ==================================================
        REPOSITORY BRANCHES
        ==================================================
          flamapy_fw: develop
          fm_metamodel: develop
        ==================================================
        ✓ All repos on branch: develop
    """
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]

    click.echo("\n" + "=" * 50)
    click.echo("REPOSITORY BRANCHES")
    click.echo("=" * 50)

    branches = {}
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False
            )
            current_branch = result.stdout.strip() or "(detached)"
            branches[repo_name] = current_branch
            click.echo(f"  {repo_name}: {current_branch}")
        else:
            click.echo(f"  {repo_name}: (not cloned)")

    unique_branches = set(branches.values())
    click.echo("=" * 50)
    if len(unique_branches) == 1:
        click.echo(f"✓ All repos on branch: {list(unique_branches)[0]}")
    else:
        click.echo("⚠ Repos are on different branches!")


@git.command(name="diff")
@click.pass_context
def diff(ctx: click.Context) -> None:
    """
    Show uncommitted changes in all repositories.

    Displays a summary of changes (--stat) for each repository
    that has uncommitted modifications.

    \b
    Example:
        $ flamapy-dev git diff
        === flamapy_fw ===
         setup.py | 2 +-
         1 file changed, 1 insertion(+), 1 deletion(-)
    """
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]

    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False
            )
            if result.stdout.strip():
                click.echo(f"\n=== {repo_name} ===")
                click.echo(result.stdout)


@git.command(name="commit-all")
@click.argument("message")
@click.pass_context
def commit_all(ctx: click.Context, message: str) -> None:
    """
    Commit all changes in all repositories with the same message.

    Stages all changes (git add -A) and commits with the provided
    message. Skips repositories with no changes.

    \b
    Args:
        message: The commit message to use for all repositories.

    \b
    Example:
        $ flamapy-dev git commit-all "feat: add new feature"
        ✓ flamapy_fw: committed
        ✓ fm_metamodel: committed
        Committed: 2, Skipped (no changes): 4
    """
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
    committed = []
    skipped = []

    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            continue

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False
        )

        if not result.stdout.strip():
            skipped.append(repo_name)
            continue

        subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            committed.append(repo_name)
            click.echo(f"✓ {repo_name}: committed")
        else:
            click.echo(f"✗ {repo_name}: {result.stderr.strip()}")

    click.echo(f"\nCommitted: {len(committed)}, Skipped (no changes): {len(skipped)}")


@git.command(name="push-all")
@click.pass_context
def push_all(ctx: click.Context) -> None:
    """
    Push all repositories to their remote.

    Executes 'git push' in each repository directory.

    \b
    Example:
        $ flamapy-dev git push-all
        ✓ flamapy_fw: pushed
        ✓ fm_metamodel: pushed
        Pushed: 6, Failed: 0
    """
    repos = ctx.obj["REPOS"]
    parent_dir = ctx.obj["PARENT_DIR"]
    pushed = []
    failed = []

    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            continue

        result = subprocess.run(
            ["git", "push"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            pushed.append(repo_name)
            click.echo(f"✓ {repo_name}: pushed")
        else:
            failed.append(repo_name)
            click.echo(f"✗ {repo_name}: {result.stderr.strip()}")

    click.echo(f"\nPushed: {len(pushed)}, Failed: {len(failed)}")


git.add_command(clone)
git.add_command(switch_develop)
git.add_command(switch_main)
git.add_command(pull)
git.add_command(delete)
git.add_command(status)
git.add_command(tag_repo)
git.add_command(tag_from_setup)
git.add_command(branch)
git.add_command(diff)
git.add_command(commit_all)
git.add_command(push_all)
