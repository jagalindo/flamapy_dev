---
layout: default
title: Workflows
---

# Common Workflows

## Daily development

### Pull latest changes and verify

```bash
flamapy-dev git pull
flamapy-dev make all -c
```

### Make a cross-repo change

```bash
# ... edit files across repos ...

# Review what changed
flamapy-dev git diff

# Run all quality checks
flamapy-dev make all -c

# Commit with the same message everywhere
flamapy-dev git commit-all "feat: add new feature"

# Push all repos
flamapy-dev git push-all
```

### Check branch alignment

```bash
flamapy-dev git branch
```

Example output:

```text
==================================================
REPOSITORY BRANCHES
==================================================
  flamapy_fw: develop
  fm_metamodel: develop
  pysat_metamodel: develop
  bdd_metamodel: develop
  z3_metamodel: develop
  flamapy: develop
==================================================
✓ All repos on branch: develop
```

## Releasing a new version

### Step 1 — Preview the release

```bash
flamapy-dev version release 2.2.0 --dry-run
```

This shows exactly what will change without modifying any files:

```text
============================================================
RELEASE v2.2.0
============================================================
[DRY RUN MODE - no changes will be made]

📋 Step 1: Skipping tests

📋 Step 2: Bumping versions...
[DRY RUN] Would bump 6 packages to v2.2.0:
flamapy_fw/
  setup.py: 2.1.0 → 2.2.0
fm_metamodel/
  setup.py: 2.1.0 → 2.2.0
  requirements.txt: flamapy-fw → 2.2.0
...
```

### Step 2 — Execute the release

```bash
flamapy-dev version release 2.2.0
```

The release command automatically:

1. **Runs tests** in all repos
2. **Bumps versions** in `setup.py` and `requirements.txt`
3. **Commits** changes with message `chore: bump version to 2.2.0`
4. **Pushes** commits to remote
5. **Tags** each repo with `v2.2.0`, waiting for PyPI availability
   between dependent packages

### Useful options

```bash
# Skip tests (e.g., if CI already passed)
flamapy-dev version release 2.2.0 --skip-tests

# Bump versions without releasing
flamapy-dev version bump 2.2.0

# Check version consistency (CI-friendly, exits 1 on mismatch)
flamapy-dev version check
```

## Version management

### Show all versions and dependencies

```bash
flamapy-dev version show
```

Displays each package's version and validates internal dependency
versions. A `✓` means the dependency version matches, `✗` means
there is a mismatch.

### Bump without releasing

```bash
# Preview changes
flamapy-dev version bump 2.2.0 --dry-run

# Apply changes
flamapy-dev version bump 2.2.0
```

This updates `setup.py` versions and `requirements.txt` dependency
specifiers across all repos, but does not commit, push, or tag.

## Package management

### Install for development

```bash
flamapy-dev pip install-dev
```

Uses `pip install -e .` so code changes are reflected immediately.

### Reinstall everything cleanly

```bash
flamapy-dev pip remove
flamapy-dev pip install-dev
```

## Quality checks

### Run individual checks

```bash
flamapy-dev make lint    # Ruff linting
flamapy-dev make test    # Pytest
flamapy-dev make mypy    # Type checking
```

### Run all checks with a summary

```bash
flamapy-dev make all -c
```

The `-c` (`--continue-on-error`) flag ensures all repos are checked
even if some fail, giving you a complete summary:

```text
============================================================
SUMMARY
============================================================
Total passed: 18
Total failed: 0
```

## Next steps

- [CLI Reference](cli-reference.md) — complete command documentation
