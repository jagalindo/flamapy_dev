"""
Documentation generation commands for flamapy-dev.

This module provides commands for generating and displaying
documentation for the flamapy-dev CLI tool.

Example usage:
    $ flamapy-dev docs show
    $ flamapy-dev docs generate
"""

import click
from pathlib import Path


@click.group()
@click.pass_context
def docs(ctx: click.Context) -> None:
    """
    Commands for generating and viewing documentation.

    This command group provides tools for displaying help
    and generating documentation files.

    \b
    Examples:
        $ flamapy-dev docs show       # Show full CLI documentation
        $ flamapy-dev docs generate   # Generate markdown documentation
    """
    ctx.ensure_object(dict)


def _get_cli() -> click.Group:
    """Import and return the CLI object (avoids circular import)."""
    from flamapy_dev import cli  # noqa: PLC0415
    return cli


def _get_command_help(cli: click.Group, ctx: click.Context, prefix: str = "") -> str:
    """
    Recursively get help text for a command and its subcommands.

    Args:
        cli: The Click command or group to document.
        ctx: Click context.
        prefix: Command prefix for nested commands.

    Returns:
        Formatted help text string.
    """
    output = []

    with ctx.scope() as sub_ctx:
        help_text = cli.get_help(sub_ctx)

    cmd_name = prefix if prefix else "flamapy-dev"
    output.append(f"\n{'='*60}")
    output.append(f"  {cmd_name}")
    output.append('='*60)
    output.append(help_text)

    if isinstance(cli, click.Group):
        for name, cmd in sorted(cli.commands.items()):
            sub_prefix = f"{prefix} {name}" if prefix else f"flamapy-dev {name}"
            sub_ctx = click.Context(cmd, parent=ctx, info_name=name)
            output.append(_get_command_help(cmd, sub_ctx, sub_prefix))

    return "\n".join(output)


@docs.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """
    Show complete CLI documentation.

    Displays help text for all commands and subcommands
    in a hierarchical format.

    \b
    Example:
        $ flamapy-dev docs show

        ============================================================
          flamapy-dev
        ============================================================
        Usage: flamapy-dev [OPTIONS] COMMAND [ARGS]...

        Manage flamapy repositories and dependencies with various commands.
        ...
    """
    cli = _get_cli()
    main_ctx = click.Context(cli)

    click.echo("\n" + "#" * 60)
    click.echo("#  FLAMAPY-DEV CLI DOCUMENTATION")
    click.echo("#" * 60)

    output = _get_command_help(cli, main_ctx)
    click.echo(output)


def _generate_command_docs(group: click.Group, group_name: str) -> list[str]:
    """Generate documentation for a command group."""
    lines = []

    # Create summary table
    lines.append("| Command | Description |")
    lines.append("|---------|-------------|")
    for cmd_name, cmd in sorted(group.commands.items()):
        short_help = cmd.get_short_help_str(limit=60)
        lines.append(f"| [`{cmd_name}`](#{group_name}-{cmd_name}) | {short_help} |")
    lines.append("")

    # Detailed documentation for each command
    for cmd_name, cmd in sorted(group.commands.items()):
        lines.extend(_generate_single_command_docs(cmd, cmd_name, group_name))

    return lines


def _generate_single_command_docs(cmd: click.Command, cmd_name: str, group_name: str) -> list[str]:
    """Generate documentation for a single command."""
    lines = []
    docstring = cmd.help or ""
    short_help = cmd.get_short_help_str()

    lines.extend([
        f"### {group_name} {cmd_name}",
        "",
        short_help,
        "",
    ])

    # Get parameters
    params = _extract_params(cmd)
    if params:
        lines.append("**Options:**")
        lines.append("")
        lines.append("| Option | Description |")
        lines.append("|--------|-------------|")
        lines.extend(params)
        lines.append("")

    # Extract example from docstring
    if "Example:" in docstring:
        lines.extend(_extract_example(docstring))

    return lines


def _extract_params(cmd: click.Command) -> list[str]:
    """Extract parameters from a command."""
    params = []
    for param in cmd.params:
        if isinstance(param, click.Option):
            opts = ", ".join(param.opts)
            help_text = param.help or ""
            params.append(f"| `{opts}` | {help_text} |")
        elif isinstance(param, click.Argument) and param.name:
            params.append(f"| `{param.name.upper()}` | Required argument |")
    return params


def _extract_example(docstring: str) -> list[str]:
    """Extract example section from docstring."""
    lines = []
    example_start = docstring.find("Example:")
    example_text = docstring[example_start:]
    example_lines = example_text.split("\n")

    lines.append("**Example:**")
    lines.append("")
    lines.append("```bash")
    for ex_line in example_lines[1:]:
        stripped = ex_line.strip()
        if stripped.startswith("$"):
            lines.append(stripped[2:])
        elif stripped.startswith("flamapy"):
            lines.append(stripped)
        elif stripped.startswith("===") or stripped.startswith("---"):
            break
    lines.append("```")
    lines.append("")
    return lines


@docs.command()
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="CLI_REFERENCE.md",
    help="Output file path"
)
@click.pass_context
def generate(ctx: click.Context, output: str) -> None:
    """
    Generate markdown documentation for all commands.

    Creates a markdown file with complete CLI reference
    including all commands, options, and examples.

    \b
    Options:
        --output, -o: Output file path (default: CLI_REFERENCE.md)

    \b
    Example:
        $ flamapy-dev docs generate
        ✓ Documentation generated: CLI_REFERENCE.md

        $ flamapy-dev docs generate -o docs/cli.md
        ✓ Documentation generated: docs/cli.md
    """
    cli = _get_cli()

    lines = [
        "---",
        "layout: default",
        "title: CLI Reference",
        "---",
        "",
        "# Flamapy-Dev CLI Reference",
        "",
        "Complete reference for the flamapy-dev command-line interface.",
        "",
        "## Table of Contents",
        "",
        "- [Global Options](#global-options)",
        "- [Git Commands](#git-commands)",
        "- [Pip Commands](#pip-commands)",
        "- [Make Commands](#make-commands)",
        "- [Version Commands](#version-commands)",
        "- [Docs Commands](#docs-commands)",
        "",
        "---",
        "",
        "## Global Options",
        "",
        "```bash",
        "flamapy-dev [OPTIONS] COMMAND [ARGS]...",
        "```",
        "",
        "| Option | Description |",
        "|--------|-------------|",
        "| `-d, --parent-dir PATH` | Parent directory for operations |",
        "| `--help` | Show help message and exit |",
        "",
        "---",
        "",
    ]

    # Document each command group
    command_groups = [
        ("git", "Git Commands", "Repository management commands"),
        ("pip", "Pip Commands", "Python package management"),
        ("make", "Make Commands", "Execute make targets across repos"),
        ("version", "Version Commands", "Version management commands"),
        ("docs", "Docs Commands", "Documentation generation"),
    ]

    for group_name, title, description in command_groups:
        if group_name not in cli.commands:
            continue

        group = cli.commands[group_name]
        lines.extend([
            f"## {title}",
            "",
            f"{description}.",
            "",
            "```bash",
            f"flamapy-dev {group_name} COMMAND [OPTIONS]",
            "```",
            "",
        ])

        if isinstance(group, click.Group):
            lines.extend(_generate_command_docs(group, group_name))

        lines.extend(["---", ""])

    lines.extend([
        "",
        "*Generated automatically by `flamapy-dev docs generate`*",
    ])

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    click.echo(f"✓ Documentation generated: {output}")


@docs.command()
@click.pass_context
def help_all(ctx: click.Context) -> None:
    """
    Show help for all commands in a compact format.

    Displays a quick reference of all available commands
    with their short descriptions.

    \b
    Example:
        $ flamapy-dev docs help-all

        FLAMAPY-DEV QUICK REFERENCE
        ===========================

        git clone          Clone all repositories
        git pull           Pull the latest changes
        ...
    """
    cli = _get_cli()

    click.echo("\nFLAMAPY-DEV QUICK REFERENCE")
    click.echo("=" * 40)

    for group_name in ["git", "pip", "make", "version", "docs"]:
        if group_name not in cli.commands:
            continue

        group = cli.commands[group_name]
        click.echo(f"\n{group_name.upper()} COMMANDS:")

        if isinstance(group, click.Group):
            for cmd_name, cmd in sorted(group.commands.items()):
                short_help = cmd.get_short_help_str(limit=50)
                click.echo(f"  {group_name} {cmd_name:15} {short_help}")

    click.echo("")
