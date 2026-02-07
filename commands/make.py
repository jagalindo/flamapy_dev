"""
Make target execution commands for flamapy-dev.

This module provides commands for running make targets across
all repositories simultaneously, with support for error handling
and summary reporting.

Example usage:
    $ flamapy-dev make lint
    $ flamapy-dev make test --continue-on-error
    $ flamapy-dev make all
"""

import click
import subprocess
import os


@click.group()
@click.pass_context
def make(ctx: click.Context) -> None:
    """
    Run make targets on all repositories.

    This command group provides tools for executing make targets
    (lint, test, mypy) across all flamapy repositories.

    \b
    Examples:
        $ flamapy-dev make lint           # Run linting
        $ flamapy-dev make test           # Run tests
        $ flamapy-dev make mypy           # Run type checking
        $ flamapy-dev make all            # Run all checks
        $ flamapy-dev make all -c         # Continue on errors
    """
    ctx.ensure_object(dict)
    ctx.obj["PARENT_DIR"] = ctx.obj.get("PARENT_DIR", "")
    ctx.obj["REPOS"] = ctx.obj.get("REPOS", {})


def _run_make(
    ctx: click.Context,
    target: str,
    continue_on_error: bool = False
) -> tuple[list[str], list[str]]:
    """
    Run a make target on all repositories.

    Args:
        ctx: Click context with REPOS and PARENT_DIR.
        target: The make target to run (e.g., "lint", "test", "mypy").
        continue_on_error: If True, continue running even if a repo fails.

    Returns:
        Tuple of (succeeded, failed) repository name lists.

    Example:
        >>> succeeded, failed = _run_make(ctx, "test", continue_on_error=True)
        >>> print(f"Passed: {len(succeeded)}, Failed: {len(failed)}")
    """
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


def _print_summary(target: str, succeeded: list[str], failed: list[str]) -> None:
    """
    Print a summary of make execution results.

    Args:
        target: The make target that was run.
        succeeded: List of repository names that passed.
        failed: List of repository names that failed.

    Example:
        >>> _print_summary("test", ["flamapy_fw", "fm_metamodel"], ["pysat_metamodel"])
        ==================================================
        SUMMARY: make test
        ==================================================
        Passed: 2
        Failed: 1
          ✗ pysat_metamodel
    """
    click.echo(f"\n{'='*50}")
    click.echo(f"SUMMARY: make {target}")
    click.echo('='*50)
    click.echo(f"Passed: {len(succeeded)}")
    click.echo(f"Failed: {len(failed)}")
    if failed:
        for repo in failed:
            click.echo(f"  ✗ {repo}")


@make.command()
@click.option("--continue-on-error", "-c", is_flag=True, help="Continue even if a repo fails")
@click.pass_context
def lint(ctx: click.Context, continue_on_error: bool) -> None:
    """
    Execute 'make lint' in all repositories.

    Runs the lint target (ruff) in each repository to check
    for code style and quality issues.

    \b
    Options:
        --continue-on-error, -c: Don't stop on first failure

    \b
    Example:
        $ flamapy-dev make lint
        ==================================================
        Running 'make lint' in flamapy_fw
        ==================================================
        All checks passed!

        ==================================================
        SUMMARY: make lint
        ==================================================
        Passed: 6
        Failed: 0
    """
    succeeded, failed = _run_make(ctx, "lint", continue_on_error)
    _print_summary("lint", succeeded, failed)


@make.command(name="test")
@click.option("--continue-on-error", "-c", is_flag=True, help="Continue even if a repo fails")
@click.pass_context
def test_cmd(ctx: click.Context, continue_on_error: bool) -> None:
    """
    Execute 'make test' in all repositories.

    Runs the test target (pytest) in each repository.

    \b
    Options:
        --continue-on-error, -c: Don't stop on first failure

    \b
    Example:
        $ flamapy-dev make test
        ==================================================
        Running 'make test' in flamapy_fw
        ==================================================
        ===== 15 passed in 2.34s =====

        ==================================================
        SUMMARY: make test
        ==================================================
        Passed: 6
        Failed: 0
    """
    succeeded, failed = _run_make(ctx, "test", continue_on_error)
    _print_summary("test", succeeded, failed)


@make.command()
@click.option("--continue-on-error", "-c", is_flag=True, help="Continue even if a repo fails")
@click.pass_context
def mypy(ctx: click.Context, continue_on_error: bool) -> None:
    """
    Execute 'make mypy' in all repositories.

    Runs static type checking with mypy in each repository.

    \b
    Options:
        --continue-on-error, -c: Don't stop on first failure

    \b
    Example:
        $ flamapy-dev make mypy
        ==================================================
        Running 'make mypy' in flamapy_fw
        ==================================================
        Success: no issues found

        ==================================================
        SUMMARY: make mypy
        ==================================================
        Passed: 6
        Failed: 0
    """
    succeeded, failed = _run_make(ctx, "mypy", continue_on_error)
    _print_summary("mypy", succeeded, failed)


@make.command(name="all")
@click.option("--continue-on-error", "-c", is_flag=True, help="Continue even if a repo fails")
@click.pass_context
def all_targets(ctx: click.Context, continue_on_error: bool) -> None:
    """
    Execute 'make lint', 'make mypy', and 'make test' in all repositories.

    Runs all quality checks in sequence: lint → mypy → test.
    Useful for pre-commit or CI validation.

    \b
    Options:
        --continue-on-error, -c: Don't stop on first failure

    \b
    Example:
        $ flamapy-dev make all
        ############################################################
        # RUNNING: make lint
        ############################################################
        ...

        ############################################################
        # RUNNING: make mypy
        ############################################################
        ...

        ############################################################
        # RUNNING: make test
        ############################################################
        ...

        ============================================================
        SUMMARY
        ============================================================
        Total passed: 18
        Total failed: 0
    """
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
