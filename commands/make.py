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


def _run_make(ctx, target: str):
    parent_dir = ctx.obj["PARENT_DIR"]
    repos = ctx.obj["REPOS"]
    for repo_name in repos:
        repo_dir = os.path.join(parent_dir, repo_name)
        if os.path.isdir(repo_dir):
            click.echo(f"Running 'make {target}' in {repo_dir}")
            subprocess.run(["make", target], cwd=repo_dir, check=True)
        else:
            click.echo(f"{repo_dir} does not exist.")


@make.command()
@click.pass_context
def lint(ctx):
    """Execute 'make lint' in all repositories."""
    _run_make(ctx, "lint")


@make.command(name="test")
@click.pass_context
def test_cmd(ctx):
    """Execute 'make test' in all repositories."""
    _run_make(ctx, "test")


@make.command()
@click.pass_context
def mypy(ctx):
    """Execute 'make mypy' in all repositories."""
    _run_make(ctx, "mypy")
