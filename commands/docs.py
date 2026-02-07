"""
Documentation generation commands for flamapy-dev.

This module provides commands for generating and displaying
documentation for the flamapy-dev CLI tool.

Example usage:
    $ flamapy-dev docs show
    $ flamapy-dev docs generate
"""

import click
import os
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

    # Get the command's own help
    with ctx.scope() as sub_ctx:
        help_text = cli.get_help(sub_ctx)

    cmd_name = prefix if prefix else "flamapy-dev"
    output.append(f"\n{'='*60}")
    output.append(f"  {cmd_name}")
    output.append('='*60)
    output.append(help_text)

    # If it's a group, recurse into subcommands
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
    # Import the main CLI to get all commands
    from flamapy_dev import cli

    # Create a context for the main CLI
    main_ctx = click.Context(cli)

    click.echo("\n" + "#" * 60)
    click.echo("#  FLAMAPY-DEV CLI DOCUMENTATION")
    click.echo("#" * 60)

    output = _get_command_help(cli, main_ctx)
    click.echo(output)


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
    from flamapy_dev import cli

    lines = [
        "# Flamapy-Dev CLI Reference",
        "",
        "This document provides a complete reference for the flamapy-dev CLI tool.",
        "",
        "## Table of Contents",
        "",
        "- [Global Options](#global-options)",
        "- [Git Commands](#git-commands)",
        "- [Pip Commands](#pip-commands)",
        "- [Make Commands](#make-commands)",
        "- [Version Commands](#version-commands)",
        "",
    ]

    # Global options
    lines.extend([
        "## Global Options",
        "",
        "```",
        "flamapy-dev [OPTIONS] COMMAND [ARGS]...",
        "",
        "Options:",
        "  -d, --parent-dir PATH  Parent directory where operations should be performed.",
        "  --help                 Show this message and exit.",
        "```",
        "",
    ])

    # Document each command group
    command_groups = [
        ("git", "Git Commands", "Git repository management"),
        ("pip", "Pip Commands", "Python package management"),
        ("make", "Make Commands", "Make target execution"),
        ("version", "Version Commands", "Version management"),
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
        ])

        # Get group help
        group_ctx = click.Context(group, info_name=group_name)
        lines.extend([
            "```",
            f"flamapy-dev {group_name} [OPTIONS] COMMAND [ARGS]...",
            "```",
            "",
        ])

        # Document subcommands
        if isinstance(group, click.Group):
            for cmd_name, cmd in sorted(group.commands.items()):
                cmd_ctx = click.Context(cmd, parent=group_ctx, info_name=cmd_name)
                help_text = cmd.get_short_help_str()
                docstring = cmd.help or ""

                lines.extend([
                    f"### `{group_name} {cmd_name}`",
                    "",
                    help_text,
                    "",
                ])

                # Extract example from docstring if present
                if "Example:" in docstring:
                    example_start = docstring.find("Example:")
                    example_text = docstring[example_start:]
                    # Clean up the example
                    example_lines = example_text.split("\n")
                    lines.append("```bash")
                    for line in example_lines[1:]:
                        line = line.strip()
                        if line.startswith("$"):
                            lines.append(line[2:])  # Remove "$ "
                        elif line and not line.startswith("Options:") and not line.startswith("Args:"):
                            if line.startswith("flamapy"):
                                lines.append(line)
                    lines.append("```")
                    lines.append("")

        lines.append("")

    # Write the file
    output_path = Path(output)
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
    from flamapy_dev import cli

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
