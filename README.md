# Flamapy-Dev CLI Tool

A command-line interface for managing multiple [flamapy](https://github.com/flamapy) repositories simultaneously. Clone, build, test, version-bump, and release all packages in one go.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Usage](#usage)
  - [Git Commands](#git-commands)
  - [Pip Commands](#pip-commands)
  - [Make Commands](#make-commands)
  - [Version Commands](#version-commands)
  - [Docs Commands](#docs-commands)
- [Common Workflows](#common-workflows)
- [Configuration](#configuration)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

```bash
# Install the tool
pip install flamapy-dev

# Clone all flamapy repositories
flamapy-dev git clone

# Install all packages in development mode
flamapy-dev pip install-dev

# Check that everything works
flamapy-dev make all

# See current package versions
flamapy-dev version show
```

## Installation

**Requirements:** Python >= 3.9

### From PyPI

```bash
pip install flamapy-dev
```

### From source (for development)

```bash
git clone https://github.com/jagalindo/flamapy_dev.git
cd flamapy_dev
python -m venv venv
source venv/bin/activate   # Linux/macOS
pip install -r requirements-dev.txt
pip install -e .
```

## Project Structure

```
flamapy_dev/
├── flamapy_dev.py          # CLI entry point and repository definitions
├── commands/
│   ├── __init__.py         # Exports all command groups
│   ├── repositories.py     # Git operations (clone, branch, tag, etc.)
│   ├── packages.py         # Pip operations (install, update, remove)
│   ├── make.py             # Make target execution (lint, test, mypy)
│   ├── versions.py         # Version management (show, check, bump, release)
│   ├── pypi.py             # PyPI availability utilities
│   └── docs.py             # Documentation generation
├── tests/
│   ├── __init__.py
│   ├── test_repositories.py
│   └── test_make.py
├── setup.py
├── pyproject.toml          # Ruff and mypy configuration
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Development dependencies
└── Makefile                # Project development targets
```

## Usage

All commands follow the pattern: `flamapy-dev [OPTIONS] <group> <command> [ARGS]`.

Use `--parent-dir PATH` (or `-d PATH`) to specify where repositories live (defaults to current directory).

```bash
# Work in a custom directory
flamapy-dev -d /path/to/repos git clone
```

### Git Commands

Manage all repositories at once.

```bash
# Clone all repositories
flamapy-dev git clone

# Switch all repos to the develop branch
flamapy-dev git switch_develop

# Switch all repos to main (falls back to master)
flamapy-dev git switch-main

# Pull latest changes in all repos
flamapy-dev git pull

# Show current branch for each repo
flamapy-dev git branch
# Output:
#   ==================================================
#   REPOSITORY BRANCHES
#   ==================================================
#     flamapy_fw: develop
#     fm_metamodel: develop
#     pysat_metamodel: develop
#   ==================================================
#   ✓ All repos on branch: develop

# Show uncommitted changes across repos
flamapy-dev git diff

# Show git status for all repos
flamapy-dev git status

# Commit all changes with the same message
flamapy-dev git commit-all "feat: add new feature"

# Push all repos
flamapy-dev git push-all

# Tag all repos with a specific version
flamapy-dev git tag_repo v2.1.0

# Tag repos using each repo's setup.py version
flamapy-dev git tag-from-setup

# Delete all cloned repo directories (use with caution!)
flamapy-dev git delete
```

### Pip Commands

Install, update, or remove packages across all repos.

```bash
# Install all packages from setup.py
flamapy-dev pip install

# Install in editable/development mode (recommended for development)
flamapy-dev pip install-dev
# Output:
#   Installing flamapy_fw in editable mode...
#     ✓ flamapy_fw installed
#   Installing fm_metamodel in editable mode...
#     ✓ fm_metamodel installed

# Update all packages
flamapy-dev pip update

# Uninstall all packages
flamapy-dev pip remove
```

### Make Commands

Run quality checks across all repos. Each repo is expected to have a `Makefile` with `lint`, `test`, and `mypy` targets.

```bash
# Run linting (ruff) in all repos
flamapy-dev make lint

# Run tests (pytest) in all repos
flamapy-dev make test

# Run type checking (mypy) in all repos
flamapy-dev make mypy

# Run all checks: lint → mypy → test
flamapy-dev make all

# Continue running even if a repo fails
flamapy-dev make all --continue-on-error
flamapy-dev make all -c
# Output:
#   ############################################################
#   # RUNNING: make lint
#   ############################################################
#   ...
#   ############################################################
#   # RUNNING: make mypy
#   ############################################################
#   ...
#   ============================================================
#   SUMMARY
#   ============================================================
#   Total passed: 18
#   Total failed: 0
```

### Version Commands

View, validate, and update versions across the entire distribution.

```bash
# Show versions of all packages and their internal dependencies
flamapy-dev version show
# Output:
#   ============================================================
#   PACKAGE VERSIONS
#   ============================================================
#
#   flamapy_fw/
#     Package: flamapy-fw v2.1.0
#
#   fm_metamodel/
#     Package: flamapy-fm v2.1.0
#     Internal dependencies:
#       - flamapy-fw~=2.1.0 ✓

# Check that all internal dependency versions are in sync
flamapy-dev version check
# Output (success): ✓ All internal dependencies are in sync!
# Output (failure): ❌ VERSION MISMATCHES FOUND:
#                     • fm_metamodel/requirements.txt: flamapy-fw~=2.0.0 but flamapy-fw is at v2.1.0

# Preview a version bump (no files changed)
flamapy-dev version bump 2.2.0 --dry-run
# Output:
#   [DRY RUN] Would bump 6 packages to v2.2.0:
#   flamapy_fw/
#     setup.py: 2.1.0 → 2.2.0
#   fm_metamodel/
#     setup.py: 2.1.0 → 2.2.0
#     requirements.txt: flamapy-fw → 2.2.0

# Apply the version bump
flamapy-dev version bump 2.2.0

# Full automated release: bump → commit → push → tag
# (waits for each package to appear on PyPI before tagging dependents)
flamapy-dev version release 2.2.0

# Release with options
flamapy-dev version release 2.2.0 --dry-run       # Simulate everything
flamapy-dev version release 2.2.0 --skip-tests     # Skip test step
```

### Docs Commands

Generate and view documentation.

```bash
# Show complete CLI help (all commands, all subcommands)
flamapy-dev docs show

# Show compact quick reference
flamapy-dev docs help-all
# Output:
#   FLAMAPY-DEV QUICK REFERENCE
#   ========================================
#
#   GIT COMMANDS:
#     git branch          Show the current branch for all repositories.
#     git clone           Clone all repositories defined in the...
#     git commit-all      Commit all changes in all repositories...
#     ...

# Generate markdown CLI reference file
flamapy-dev docs generate
flamapy-dev docs generate -o docs/cli-reference.md
```

## Common Workflows

### Setting up a development environment

```bash
flamapy-dev git clone                  # 1. Clone all repos
flamapy-dev git switch_develop         # 2. Switch to develop branch
flamapy-dev pip install-dev            # 3. Install in editable mode
flamapy-dev make all -c                # 4. Verify everything passes
```

### Making a cross-repo change

```bash
# ... make your changes across repos ...
flamapy-dev git diff                   # 1. Review changes
flamapy-dev make all -c                # 2. Run all checks
flamapy-dev git commit-all "feat: my change"  # 3. Commit everywhere
flamapy-dev git push-all               # 4. Push all repos
```

### Releasing a new version

```bash
flamapy-dev version release 2.2.0 --dry-run   # 1. Preview the release
flamapy-dev version release 2.2.0              # 2. Execute the release
# This will automatically:
#   - Run tests in all repos
#   - Bump setup.py and requirements.txt versions
#   - Commit changes
#   - Push to remote
#   - Create and push tags (waiting for PyPI between dependent packages)
```

## Configuration

### Managed Repositories

The repositories and their order are defined in `flamapy_dev.py`. Order matters because dependencies must be installed before dependents:

```python
REPOS = OrderedDict([
    ("flamapy_fw", "https://github.com/flamapy/flamapy_fw.git"),
    ("fm_metamodel", "https://github.com/flamapy/fm_metamodel.git"),
    ("pysat_metamodel", "https://github.com/flamapy/pysat_metamodel.git"),
    ("bdd_metamodel", "https://github.com/flamapy/bdd_metamodel.git"),
    ("z3_metamodel", "https://github.com/flamapy/z3_metamodel.git"),
    ("flamapy", "https://github.com/flamapy/flamapy.git"),
])
```

### Parent Directory

By default, all operations run in the current directory. Override with:

```bash
flamapy-dev --parent-dir /path/to/workspace git clone
```

## Development

### Running checks locally

```bash
make lint     # Run ruff linter
make test     # Run pytest
make mypy     # Run mypy type checker
make all      # Run everything
```

### Running tests

```bash
pytest tests/ -v
```

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
