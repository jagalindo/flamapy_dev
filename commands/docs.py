"""
Documentation generation commands for flamapy-dev.

This module provides commands for generating and displaying
documentation for the flamapy-dev CLI tool.

Example usage:
    $ flamapy-dev docs show
    $ flamapy-dev docs generate
"""

import re
from pathlib import Path

import click


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


def _get_command_help(cli: click.Command, ctx: click.Context, prefix: str = "") -> str:
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


# ---------------------------------------------------------------------------
# Markdown generation helpers
# ---------------------------------------------------------------------------

def _extract_params(cmd: click.Command) -> list[str]:
    """Extract parameters from a command as markdown table rows."""
    params = []
    for param in cmd.params:
        if isinstance(param, click.Option):
            opts = ", ".join(f"`{o}`" for o in param.opts)
            help_text = param.help or ""
            default = ""
            if param.default is not None and param.default != ():
                if isinstance(param.is_flag, bool) and param.is_flag:
                    default = ""
                else:
                    default = f" (default: `{param.default}`)"
            params.append(f"| {opts} | {help_text}{default} |")
        elif isinstance(param, click.Argument) and param.name:
            required = "Yes" if param.required else "No"
            params.append(f"| `{param.name.upper()}` | Required: {required} |")
    return params


def _extract_docstring_sections(docstring: str) -> dict[str, str]:
    """
    Parse a Click docstring into sections.

    Returns a dict with keys like 'description', 'example', 'args', etc.
    """
    sections: dict[str, str] = {}
    if not docstring:
        return sections

    # Clean up Click's \b markers
    cleaned = docstring.replace("\\b\n", "").replace("\\b", "")

    # Get the description (everything before the first known section header)
    section_headers = ["Example:", "Examples:", "Args:", "Options:", "Returns:"]
    desc_end = len(cleaned)
    for header in section_headers:
        idx = cleaned.find(header)
        if idx != -1 and idx < desc_end:
            desc_end = idx

    description = cleaned[:desc_end].strip()
    if description:
        sections["description"] = description

    # Extract Example/Examples section
    for header in ["Example:", "Examples:"]:
        idx = cleaned.find(header)
        if idx == -1:
            continue
        example_text = cleaned[idx + len(header):]
        # Find end of example (next section header or end)
        end = len(example_text)
        for h in section_headers:
            if h == header:
                continue
            hi = example_text.find(h)
            if hi != -1 and hi < end:
                end = hi
        sections["example"] = example_text[:end].strip()
        break

    return sections


def _format_example_block(raw_example: str) -> list[str]:
    """Convert raw example text from docstring into formatted markdown blocks."""
    lines: list[str] = []
    in_code = False

    for raw_line in raw_example.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            continue

        is_command = stripped.startswith("$") or stripped.startswith("flamapy")
        cmd_text = stripped[2:].strip() if stripped.startswith("$") else stripped

        if is_command:
            if not in_code:
                lines.append("```bash")
                in_code = True
            lines.append(cmd_text)
        else:
            if in_code:
                lines.append("```")
                in_code = False
            lines.append(stripped)

    if in_code:
        lines.append("```")

    lines.append("")
    return lines


def _generate_single_command_docs(
    cmd: click.Command,
    cmd_name: str,
    group_name: str,
) -> list[str]:
    """Generate detailed markdown documentation for a single command."""
    lines: list[str] = []
    docstring = cmd.help or ""
    sections = _extract_docstring_sections(docstring)

    # Heading
    anchor = f"{group_name}-{cmd_name}"
    lines.extend([
        f"<a id=\"{anchor}\"></a>",
        f"### `flamapy-dev {group_name} {cmd_name}`",
        "",
    ])

    # Description
    desc = sections.get("description", cmd.get_short_help_str())
    # Remove leading/trailing whitespace per line
    desc_lines = [ln.strip() for ln in desc.split("\n") if ln.strip()]
    lines.extend(desc_lines)
    lines.append("")

    # Syntax
    parts = [f"flamapy-dev {group_name} {cmd_name}"]
    for param in cmd.params:
        if isinstance(param, click.Argument) and param.name:
            parts.append(f"<{param.name.upper()}>")
        elif isinstance(param, click.Option):
            parts.append("[OPTIONS]")
            break
    lines.append("```bash")
    lines.append(" ".join(parts))
    lines.append("```")
    lines.append("")

    # Parameters table
    params = _extract_params(cmd)
    if params:
        lines.append("**Parameters:**")
        lines.append("")
        lines.append("| Parameter | Description |")
        lines.append("|-----------|-------------|")
        lines.extend(params)
        lines.append("")

    # Example
    example = sections.get("example", "")
    if example:
        lines.append("**Example:**")
        lines.append("")
        lines.extend(_format_example_block(example))

    lines.append("---")
    lines.append("")
    return lines


def _generate_command_group_docs(group: click.Group, group_name: str) -> list[str]:
    """Generate documentation for a full command group."""
    lines: list[str] = []

    # Summary table
    lines.append("| Command | Description |")
    lines.append("|---------|-------------|")
    for cmd_name, cmd in sorted(group.commands.items()):
        short_help = cmd.get_short_help_str(limit=72)
        anchor = f"{group_name}-{cmd_name}"
        lines.append(f"| [`{cmd_name}`](#{anchor}) | {short_help} |")
    lines.append("")

    # Detailed docs for each command
    for cmd_name, cmd in sorted(group.commands.items()):
        lines.extend(_generate_single_command_docs(cmd, cmd_name, group_name))

    return lines


def _generate_workflows_section() -> list[str]:
    """Generate the common workflows section."""
    return [
        "## Common Workflows",
        "",
        "### Setting up a development environment",
        "",
        "```bash",
        "# 1. Clone all repositories",
        "flamapy-dev git clone",
        "",
        "# 2. Switch to develop branch",
        "flamapy-dev git switch_develop",
        "",
        "# 3. Install in editable mode",
        "flamapy-dev pip install-dev",
        "",
        "# 4. Verify everything passes",
        "flamapy-dev make all -c",
        "```",
        "",
        "### Making a cross-repository change",
        "",
        "```bash",
        "# ... make your changes across repos ...",
        "",
        "# 1. Review changes",
        "flamapy-dev git diff",
        "",
        "# 2. Run all checks",
        "flamapy-dev make all -c",
        "",
        "# 3. Commit everywhere",
        'flamapy-dev git commit-all "feat: add new feature"',
        "",
        "# 4. Push all repos",
        "flamapy-dev git push-all",
        "```",
        "",
        "### Releasing a new version",
        "",
        "```bash",
        "# 1. Preview the release (no files changed)",
        "flamapy-dev version release 2.2.0 --dry-run",
        "",
        "# 2. Execute the PyPI plugin release",
        "flamapy-dev version release 2.2.0",
        "# Automatically: test → bump → commit → push → tag",
        "# Waits for PyPI availability between dependent packages",
        "",
        "# 3. If CI jobs failed because PyPI hadn't caught up yet",
        "flamapy-dev git rerun-failed --dry-run   # preview",
        "flamapy-dev git rerun-failed             # rerun only the failed jobs",
        "```",
        "",
        "### Releasing every artefact (plugins + IDE + docs)",
        "",
        "```bash",
        "# Preview the whole coordinated release",
        "flamapy-dev version release-all 2.2.0 --dry-run",
        "",
        "# Release the PyPI plugins, then the IDE (bundles the published flamapy",
        "# version and ships docker + Pages), then publish the docs (develop → main)",
        "flamapy-dev version release-all 2.2.0",
        "",
        "# Skip parts as needed",
        "flamapy-dev version release-all 2.2.0 --skip-docs",
        "```",
        "",
        "### Checking version consistency",
        "",
        "```bash",
        "# Show versions and dependency status",
        "flamapy-dev version show",
        "",
        "# Check for mismatches (CI-friendly, exits 1 on error)",
        "flamapy-dev version check",
        "",
        "# Fix mismatches by bumping to a common version",
        "flamapy-dev version bump 2.2.0",
        "```",
        "",
    ]


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
        "Complete reference for the `flamapy-dev` command-line interface.",
        "",
        "> **Tip:** Run `flamapy-dev docs help-all` for a quick command summary "
        "or `flamapy-dev <group> <command> --help` for individual help.",
        "",
        "## Table of Contents",
        "",
        "- [Global Options](#global-options)",
    ]

    # Build ToC dynamically
    command_groups = [
        ("git", "Git Commands", "Repository management (clone, branch, tag, push)"),
        ("pip", "Pip Commands", "Python package management (install, update, remove)"),
        ("make", "Make Commands", "Execute make targets across all repos (lint, test, mypy)"),
        ("version", "Version Commands", "Version management (show, check, bump, release)"),
        ("docs", "Docs Commands", "Documentation generation and viewing"),
    ]

    for group_name, title, _ in command_groups:
        if group_name in cli.commands:
            lines.append(f"- [{title}](#{group_name}-commands)")

    lines.extend([
        "- [Common Workflows](#common-workflows)",
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
        "| `-d`, `--parent-dir` PATH | Parent directory where repositories live "
        "(default: current directory) |",
        "| `--help` | Show help message and exit |",
        "",
        "**Example:**",
        "",
        "```bash",
        "# Operate on repos in a custom directory",
        "flamapy-dev --parent-dir /path/to/workspace git clone",
        "flamapy-dev -d ~/flamapy git branch",
        "```",
        "",
        "---",
        "",
    ])

    # Generate docs for each command group
    for group_name, title, description in command_groups:
        if group_name not in cli.commands:
            continue

        group = cli.commands[group_name]
        lines.extend([
            f"<a id=\"{group_name}-commands\"></a>",
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
            lines.extend(_generate_command_group_docs(group, group_name))

        lines.extend(["---", ""])

    # Add workflows section
    lines.extend(_generate_workflows_section())

    lines.extend([
        "---",
        "",
        "*Generated automatically by `flamapy-dev docs generate`*",
    ])

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Clean up excessive blank lines
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    output_path.write_text(text, encoding="utf-8")
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
