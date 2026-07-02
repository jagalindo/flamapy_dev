import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flamapy_dev
from commands import versions
from commands import pypi


def test_repos_include_new_public_plugins_but_not_private_gnn():
    repos = list(flamapy_dev.REPOS)
    for plugin in ("sdd_metamodel", "dnnf_metamodel", "sharpsat_metamodel", "flamapy_rest"):
        assert plugin in repos
    assert "gnn_metamodel" not in repos  # private, not on PyPI
    # dependency order: sat before the compilation plugins; flamapy before rest.
    assert repos.index("pysat_metamodel") < repos.index("sdd_metamodel")
    assert repos.index("sharpsat_metamodel") < repos.index("flamapy")
    assert repos.index("flamapy") < repos.index("flamapy_rest")


def test_ide_and_docs_artefacts_defined():
    assert flamapy_dev.IDE_REPO == "flamapy-ide"
    assert flamapy_dev.DOCS_REPO == "flamapy_docs"


def test_release_docs_merges_develop_into_main():
    calls = []

    def fake_run(args, cwd=None, capture_output=False, text=False, check=False):
        calls.append(args)

        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()

    with patch.object(Path, "is_dir", return_value=True), \
         patch("commands.versions.subprocess.run", side_effect=fake_run):
        versions._release_docs("/tmp", "flamapy_docs", dry_run=False)

    git_cmds = [c[1] for c in calls if c[0] == "git"]
    assert "checkout" in git_cmds and "merge" in git_cmds and "push" in git_cmds


def test_release_docs_dry_run_does_nothing():
    with patch.object(Path, "is_dir", return_value=True), \
         patch("commands.versions.subprocess.run") as run_mock:
        versions._release_docs("/tmp", "flamapy_docs", dry_run=True)
    run_mock.assert_not_called()


def test_release_ide_dry_run_does_not_touch_pypi_or_git():
    with patch.object(Path, "is_dir", return_value=True), \
         patch("commands.versions.subprocess.run") as run_mock, \
         patch("commands.versions.wait_for_package") as wait_mock:
        versions._release_ide("/tmp", "flamapy-ide", "2.6.0.dev9", dry_run=True)
    run_mock.assert_not_called()
    wait_mock.assert_not_called()


def test_wait_for_package_times_out():
    with patch("commands.pypi._package_available", return_value=False):
        with pytest.raises(TimeoutError):
            pypi.wait_for_package("flamapy", "9.9.9", check_interval=0, timeout=0)
