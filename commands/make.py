import click
import subprocess
import os


@click.group()
@click.pass_context
def make(ctx):
    """Run make targets on all repositories."""
    ctx.ensure_object(dict)
    ctx.obj["PARENT_DIR"] = ctx.obj.get("PARENT_DIR", "")
    ctx.obj["REPOS"] = ctx.obj.get("REPOS", {})


def _run_make(ctx, target: str, continue_on_error: bool = False) -> tuple[list[str], list[str]]:
    """Run make target on all repos. Returns (succeeded, failed) lists."""
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]
    succeeded = []
    failed = []

    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(repo_dir):
            click.echo(f"\n{'='*50}")
            click.echo(f"Running 'make {target}' in {repo_name}")
            click.echo('='*50)
            result = subprocess.run(
                ["make", target],
                cwd=repo_dir,
                check=False
            )
            if result.returncode == 0:
                succeeded.append(repo_name)
            else:
                failed.append(repo_name)
                if not continue_on_error:
                    click.echo(f"\n✗ Failed in {repo_name}. Use --continue-on-error to continue.")
                    break
        else:
            click.echo(f"{repo_dir} does not exist.")

    return succeeded, failed


@make.command()
@click.option("--continue-on-error", "-c", is_flag=True, help="Continue even if a repo fails")
@click.pass_context
def lint(ctx, continue_on_error):
    """Execute 'make lint' in all repositories."""
    succeeded, failed = _run_make(ctx, "lint", continue_on_error)
    _print_summary("lint", succeeded, failed)


@make.command(name="test")
@click.option("--continue-on-error", "-c", is_flag=True, help="Continue even if a repo fails")
@click.pass_context
def test_cmd(ctx, continue_on_error):
    """Execute 'make test' in all repositories."""
    succeeded, failed = _run_make(ctx, "test", continue_on_error)
    _print_summary("test", succeeded, failed)


@make.command()
@click.option("--continue-on-error", "-c", is_flag=True, help="Continue even if a repo fails")
@click.pass_context
def mypy(ctx, continue_on_error):
    """Execute 'make mypy' in all repositories."""
    succeeded, failed = _run_make(ctx, "mypy", continue_on_error)
    _print_summary("mypy", succeeded, failed)


@make.command(name="all")
@click.option("--continue-on-error", "-c", is_flag=True, help="Continue even if a repo fails")
@click.pass_context
def all_targets(ctx, continue_on_error):
    """Execute 'make lint', 'make mypy', and 'make test' in all repositories."""
    all_succeeded = []
    all_failed = []

    for target in ["lint", "mypy", "test"]:
        click.echo(f"\n{'#'*60}")
        click.echo(f"# RUNNING: make {target}")
        click.echo('#'*60)
        succeeded, failed = _run_make(ctx, target, continue_on_error)
        all_succeeded.extend([(repo, target) for repo in succeeded])
        all_failed.extend([(repo, target) for repo in failed])

        if failed and not continue_on_error:
            break

    click.echo(f"\n{'='*60}")
    click.echo("SUMMARY")
    click.echo('='*60)
    click.echo(f"Total passed: {len(all_succeeded)}")
    click.echo(f"Total failed: {len(all_failed)}")
    if all_failed:
        click.echo("\nFailed:")
        for repo, target in all_failed:
            click.echo(f"  ✗ {repo} ({target})")


def _print_summary(target: str, succeeded: list[str], failed: list[str]) -> None:
    """Print summary of make execution."""
    click.echo(f"\n{'='*50}")
    click.echo(f"SUMMARY: make {target}")
    click.echo('='*50)
    click.echo(f"Passed: {len(succeeded)}")
    click.echo(f"Failed: {len(failed)}")
    if failed:
        for repo in failed:
            click.echo(f"  ✗ {repo}")
