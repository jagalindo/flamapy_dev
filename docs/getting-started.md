---
layout: default
title: Getting Started
---

# Getting Started

## Requirements

- Python >= 3.9
- Git

## Installation

### From PyPI (recommended)

```bash
pip install flamapy-dev
```

### From source (for development)

```bash
git clone https://github.com/jagalindo/flamapy_dev.git
cd flamapy_dev
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

## First Steps

### 1. Clone all repositories

```bash
flamapy-dev git clone
```

This clones all flamapy repositories into the current directory:

```
./
├── flamapy_fw/
├── fm_metamodel/
├── pysat_metamodel/
├── bdd_metamodel/
├── z3_metamodel/
└── flamapy/
```

### 2. Switch to develop branch

```bash
flamapy-dev git switch_develop
```

All repos are switched to the `develop` branch. If the branch only
exists on the remote, a local tracking branch is created automatically.

### 3. Install in development mode

```bash
flamapy-dev pip install-dev
```

Installs every package in editable mode (`pip install -e .`) so code
changes take effect immediately without reinstalling.

Example output:

```text
Installing flamapy_fw in editable mode...
  ✓ flamapy_fw installed
Installing fm_metamodel in editable mode...
  ✓ fm_metamodel installed
...
```

### 4. Verify the setup

```bash
flamapy-dev make all -c
```

Runs lint, mypy, and tests across all repos. The `-c` flag means
"continue on error" so you see the full report even if one repo fails.

### 5. Check versions

```bash
flamapy-dev version show
```

Example output:

```text
============================================================
PACKAGE VERSIONS
============================================================

flamapy_fw/
  Package: flamapy-fw v2.1.0

fm_metamodel/
  Package: flamapy-fm v2.1.0
  Internal dependencies:
    - flamapy-fw~=2.1.0 ✓
```

## Using a custom directory

By default, flamapy-dev operates in the current directory. To use a
different workspace:

```bash
flamapy-dev --parent-dir /path/to/workspace git clone
flamapy-dev -d /path/to/workspace version show
```

## Next steps

- [Common Workflows](workflows.md) — day-to-day development patterns
- [CLI Reference](cli-reference.md) — complete command documentation
