"""
Git repository management commands for flamapy-dev.

This module provides commands for managing multiple Git repositories
simultaneously, including cloning, branching, committing, and tagging.

Example usage:
    $ flamapy-dev git clone
    $ flamapy-dev git branch
    $ flamapy-dev git commit-all "feat: add new feature"
"""

import json
import shutil
import subprocess
from pathlib import Path

import click

from commands.pypi import wait_for_requirements
from commands.versions import extract_current_version


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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    for repo_name, repo_url in repos.items():
        repo_dir = parent_dir / repo_name
        if not (repo_dir / ".git").is_dir():
            click.echo(f"Cloning {repo_name} from {repo_url}...")
            subprocess.run(["git", "clone", repo_url, str(repo_dir)], check=True)
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if (repo_dir / ".git").is_dir():
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if (repo_dir / ".git").is_dir():
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if (repo_dir / ".git").is_dir():
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if (repo_dir / ".git").is_dir():
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if repo_dir.is_dir():
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if (repo_dir / ".git").is_dir():
            req_file = repo_dir / "requirements.txt"
            if req_file.exists():
                click.echo(f"Waiting for PyPI packages of {repo_name}...")
                wait_for_requirements(str(req_file))
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if (repo_dir / ".git").is_dir():
            setup_path = repo_dir / "setup.py"
            if not setup_path.exists():
                click.echo(f"setup.py not found in {repo_name}, skipping.")
                continue
            version = extract_current_version(setup_path)
            tag = f"v{version}"
            req_file = repo_dir / "requirements.txt"
            if req_file.exists():
                click.echo(f"Waiting for PyPI packages of {repo_name}...")
                wait_for_requirements(str(req_file))
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])

    click.echo("\n" + "=" * 50)
    click.echo("REPOSITORY BRANCHES")
    click.echo("=" * 50)

    branches: dict[str, str] = {}
    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if (repo_dir / ".git").is_dir():
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
        click.echo(f"✓ All repos on branch: {next(iter(unique_branches))}")
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])

    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if (repo_dir / ".git").is_dir():
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    committed = []
    skipped = []

    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if not (repo_dir / ".git").is_dir():
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
    parent_dir = Path(ctx.obj["PARENT_DIR"])
    pushed = []
    failed = []

    for repo_name in repos:
        repo_dir = parent_dir / repo_name
        if not (repo_dir / ".git").is_dir():
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


@git.command(name="actions")
@click.option("--limit", "-n", default=3, show_default=True, help="Number of recent runs to show per repo.")
@click.pass_context
def actions(ctx: click.Context, limit: int) -> None:
    """
    Show the latest GitHub Actions run results for all repositories.

    Uses the GitHub CLI (gh) to fetch recent workflow run statuses.
    Requires 'gh' to be installed and authenticated ('gh auth login').

    \b
    Example:
        $ flamapy-dev git actions
        $ flamapy-dev git actions --limit 5
    """
    repos = ctx.obj["REPOS"]

    if not shutil.which("gh"):
        click.echo("Error: 'gh' CLI not found. Install it from https://cli.github.com/")
        return

    click.echo("\n" + "=" * 60)
    click.echo("GITHUB ACTIONS - LATEST RUNS")
    click.echo("=" * 60)

    STATUS_ICON: dict[str, str] = {
        "success": "✓",
        "failure": "✗",
        "cancelled": "⊘",
        "skipped": "—",
    }

    for repo_name, repo_url in repos.items():
        repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")
        click.echo(f"\n{repo_name}  ({repo_path})")

        result = subprocess.run(
            [
                "gh", "run", "list",
                "--repo", repo_path,
                "--limit", str(limit),
                "--json", "status,conclusion,name,createdAt,headBranch",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            click.echo(f"  Error: {result.stderr.strip() or 'gh CLI failed (not authenticated?)'}")
            continue

        try:
            runs = json.loads(result.stdout)
        except json.JSONDecodeError:
            click.echo("  Could not parse gh output.")
            continue

        if not runs:
            click.echo("  No recent runs found.")
            continue

        for run in runs:
            status = run.get("status", "unknown")
            conclusion = run.get("conclusion") or status
            name = run.get("name", "unknown")
            branch = run.get("headBranch", "")
            created_at = run.get("createdAt", "")[:16].replace("T", " ")

            if status == "in_progress":
                icon = "⟳"
                label = "running"
            else:
                icon = STATUS_ICON.get(conclusion, "?")
                label = conclusion

            click.echo(f"  {icon} [{label:<10}] {name:<30} {branch:<15} {created_at}")

    click.echo("")


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
git.add_command(actions)
