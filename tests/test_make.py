from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import importlib

make_cmd = importlib.import_module("commands.make")


def _mock_success() -> MagicMock:
    """Return a mock subprocess result with returncode 0."""
    m = MagicMock()
    m.returncode = 0
    return m


def _mock_failure() -> MagicMock:
    """Return a mock subprocess result with returncode 1."""
    m = MagicMock()
    m.returncode = 1
    return m


def test_make_lint_runs_in_repo():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=True), patch(
        "commands.make.subprocess.run", return_value=_mock_success()
    ) as run_mock:
        result = runner.invoke(make_cmd.lint, obj=obj)

    assert result.exit_code == 0
    run_mock.assert_called_with(["make", "lint"], cwd=Path("/tmp/repo1"), check=False)
    assert "Passed:  1" in result.output
    assert "Failed:  0" in result.output


def test_make_test_runs_in_repo():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=True), patch(
        "commands.make.subprocess.run", return_value=_mock_success()
    ) as run_mock:
        result = runner.invoke(make_cmd.test_cmd, obj=obj)

    assert result.exit_code == 0
    run_mock.assert_called_with(["make", "test"], cwd=Path("/tmp/repo1"), check=False)
    assert "Passed:  1" in result.output
    assert "Failed:  0" in result.output


def test_make_mypy_missing_repo():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=False), patch(
        "commands.make.subprocess.run"
    ) as run_mock:
        result = runner.invoke(make_cmd.mypy, obj=obj)

    assert result.exit_code == 0
    run_mock.assert_not_called()
    assert "Skipped (not found): 1" in result.output
    assert "flamapy-dev git clone" in result.output


def test_make_lint_failure_stops_on_error():
    runner = CliRunner()
    repos = {"repo1": "url1", "repo2": "url2"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=True), patch(
        "commands.make.subprocess.run", return_value=_mock_failure()
    ):
        result = runner.invoke(make_cmd.lint, obj=obj)

    assert result.exit_code == 0
    assert "Failed:  1" in result.output
    assert "✗ repo1" in result.output


def test_make_lint_continue_on_error():
    runner = CliRunner()
    repos = {"repo1": "url1", "repo2": "url2"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=True), patch(
        "commands.make.subprocess.run", return_value=_mock_failure()
    ):
        result = runner.invoke(make_cmd.lint, ["--continue-on-error"], obj=obj)

    assert result.exit_code == 0
    assert "Failed:  2" in result.output


def test_make_cov_runs_in_repo():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=True), patch(
        "commands.make.subprocess.run", return_value=_mock_success()
    ) as run_mock:
        result = runner.invoke(make_cmd.cov, obj=obj)

    assert result.exit_code == 0
    run_mock.assert_called_with(["make", "cov"], cwd=Path("/tmp/repo1"), check=False)
    assert "Passed:  1" in result.output


def test_make_all_not_found_repos_shown_once():
    runner = CliRunner()
    repos = {"missing": "url1", "present": "url2"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}

    def is_dir_side_effect(self: Path) -> bool:
        return "present" in str(self)

    with patch.object(Path, "is_dir", is_dir_side_effect), patch(
        "commands.make.subprocess.run", return_value=_mock_success()
    ):
        result = runner.invoke(make_cmd.all_targets, ["--continue-on-error"], obj=obj)

    assert result.exit_code == 0
    # "missing" should appear once in not_found, not three times
    assert result.output.count("? missing") == 1
    assert "flamapy-dev git clone" in result.output
