---
layout: default
title: Home
---

# Flamapy-Dev CLI Tool

A command-line interface for managing multiple
[flamapy](https://github.com/flamapy) repositories simultaneously.
Clone, build, test, version-bump, and release all packages in one go.

## Quick Start

```bash
# Install
pip install flamapy-dev

# Clone all repositories
flamapy-dev git clone

# Install in development mode
flamapy-dev pip install-dev

# Run all quality checks
flamapy-dev make all

# Show package versions
flamapy-dev version show
```

## Documentation

| Page | Description |
|------|-------------|
| [Getting Started](getting-started.md) | Installation, setup, and first steps |
| [Workflows](workflows.md) | Common development and release workflows |
| [CLI Reference](cli-reference.md) | Complete command reference |

## Command Groups

| Group | Description | Key Commands |
|-------|-------------|--------------|
| **git** | Repository management | `clone`, `pull`, `branch`, `commit-all`, `push-all`, `tag-from-setup` |
| **pip** | Package management | `install`, `install-dev`, `update`, `remove` |
| **make** | Quality checks | `lint`, `test`, `mypy`, `all` |
| **version** | Version management | `show`, `check`, `bump`, `release` |
| **docs** | Documentation | `show`, `generate`, `help-all` |
