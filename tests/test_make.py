from click.testing import CliRunner
from unittest.mock import patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import importlib

make_cmd = importlib.import_module("commands.make")


def test_make_lint_runs_in_repo():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch("commands.make.os.path.isdir", return_value=True), patch(
        "commands.make.subprocess.run"
    ) as run_mock:
        result = runner.invoke(make_cmd.lint, obj=obj)

    assert result.exit_code == 0
    run_mock.assert_called_with(["make", "lint"], cwd="/tmp/repo1", check=True)


def test_make_test_runs_in_repo():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch("commands.make.os.path.isdir", return_value=True), patch(
        "commands.make.subprocess.run"
    ) as run_mock:
        result = runner.invoke(make_cmd.test_cmd, obj=obj)

    assert result.exit_code == 0
    run_mock.assert_called_with(["make", "test"], cwd="/tmp/repo1", check=True)


def test_make_mypy_missing_repo():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch("commands.make.os.path.isdir", return_value=False), patch(
        "commands.make.subprocess.run"
    ) as run_mock:
        result = runner.invoke(make_cmd.mypy, obj=obj)

    assert result.exit_code == 0
    run_mock.assert_not_called()
