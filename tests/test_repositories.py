from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from commands import repositories


class DummyProcess:
    def __init__(self, returncode=0):
        self.returncode = returncode


def _mock_path_is_dir(parent_dir, repo_name, return_value):
    """Create a side_effect for Path.is_dir() that checks the .git subpath."""
    original_is_dir = Path.is_dir

    def is_dir_side_effect(self):
        if str(self) == str(Path(parent_dir) / repo_name / ".git"):
            return return_value
        if str(self) == str(Path(parent_dir) / repo_name):
            return return_value
        return original_is_dir(self)

    return is_dir_side_effect


def test_switch_develop_no_branch():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=False), patch(
        "commands.repositories.subprocess.run"
    ) as run_mock:
        result = runner.invoke(repositories.switch_develop, obj=obj)
    assert result.exit_code == 0
    run_mock.assert_not_called()


def test_switch_main_prefers_main():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}

    def side_effect(args, cwd=None, check=False, **kwargs):
        if args[0:3] == ["git", "show-ref", "--verify"]:
            if args[-1] == "refs/heads/main":
                return DummyProcess(0)
            else:
                return DummyProcess(1)
        elif args[0:2] == ["git", "switch"]:
            return DummyProcess(0)
        return DummyProcess(0)

    with patch.object(Path, "is_dir", return_value=True), patch(
        "commands.repositories.subprocess.run", side_effect=side_effect
    ) as run_mock:
        result = runner.invoke(repositories.switch_main, obj=obj)

    assert result.exit_code == 0
    switch_calls = [
        call.args[0]
        for call in run_mock.call_args_list
        if call.args and call.args[0][0:2] == ["git", "switch"]
    ]
    assert switch_calls == [["git", "switch", "main"]]


def test_switch_main_uses_master():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}

    def side_effect(args, cwd=None, check=False, **kwargs):
        if args[0:3] == ["git", "show-ref", "--verify"]:
            if args[-1] == "refs/heads/main":
                return DummyProcess(1)
            else:  # master check
                return DummyProcess(0)
        elif args[0:2] == ["git", "switch"]:
            return DummyProcess(0)
        return DummyProcess(0)

    with patch.object(Path, "is_dir", return_value=True), patch(
        "commands.repositories.subprocess.run", side_effect=side_effect
    ) as run_mock:
        result = runner.invoke(repositories.switch_main, obj=obj)

    assert result.exit_code == 0
    switch_calls = [
        call.args[0]
        for call in run_mock.call_args_list
        if call.args and call.args[0][0:2] == ["git", "switch"]
    ]
    assert switch_calls == [["git", "switch", "master"]]


def test_switch_develop_creates_local_from_remote():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}

    def side_effect(args, cwd=None, check=False, **kwargs):
        if args[0:3] == ["git", "show-ref", "--verify"]:
            return DummyProcess(1)
        elif args[0:3] == ["git", "ls-remote", "--exit-code"]:
            return DummyProcess(0)
        elif args[0:2] == ["git", "switch"]:
            return DummyProcess(0)
        elif args[0:2] == ["git", "fetch"]:
            return DummyProcess(0)
        return DummyProcess(0)

    with patch.object(Path, "is_dir", return_value=True), patch(
        "commands.repositories.subprocess.run", side_effect=side_effect
    ) as run_mock:
        result = runner.invoke(repositories.switch_develop, obj=obj)

    assert result.exit_code == 0
    switch_calls = [
        call.args[0]
        for call in run_mock.call_args_list
        if call.args and call.args[0][0:2] == ["git", "switch"]
    ]
    assert switch_calls == [["git", "switch", "-c", "develop", "origin/develop"]]


def test_switch_develop_branch_missing_everywhere():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}

    def side_effect(args, cwd=None, check=False, **kwargs):
        if args[0:3] == ["git", "show-ref", "--verify"]:
            return DummyProcess(1)
        elif args[0:3] == ["git", "ls-remote", "--exit-code"]:
            return DummyProcess(1)
        elif args[0:2] == ["git", "switch"]:
            return DummyProcess(0)
        return DummyProcess(0)

    with patch.object(Path, "is_dir", return_value=True), patch(
        "commands.repositories.subprocess.run", side_effect=side_effect
    ) as run_mock:
        result = runner.invoke(repositories.switch_develop, obj=obj)

    assert result.exit_code == 0
    switch_calls = [
        call.args[0]
        for call in run_mock.call_args_list
        if call.args and call.args[0][0:2] == ["git", "switch"]
    ]
    assert switch_calls == []


def test_tag_repo_creates_and_pushes_tag():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=True), patch.object(
        Path, "exists", return_value=True
    ), patch("commands.repositories.wait_for_requirements") as wait_mock, patch(
        "commands.repositories.subprocess.run"
    ) as run_mock:
        result = runner.invoke(repositories.tag_repo, ["v1.0"], obj=obj)

    assert result.exit_code == 0
    wait_mock.assert_called_once()
    expected = [["git", "tag", "v1.0"], ["git", "push", "origin", "v1.0"]]
    calls = [c.args[0] for c in run_mock.call_args_list]
    assert calls == expected


def test_tag_repo_missing_repo():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=False), patch(
        "commands.repositories.wait_for_requirements"
    ) as wait_mock, patch("commands.repositories.subprocess.run") as run_mock:
        result = runner.invoke(repositories.tag_repo, ["v1.0"], obj=obj)

    assert result.exit_code == 0
    run_mock.assert_not_called()
    wait_mock.assert_not_called()


def test_tag_repo_processes_in_defined_order():
    runner = CliRunner()
    repos = {"first": "url1", "second": "url2", "third": "url3"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=True), patch.object(
        Path, "exists", return_value=False
    ), patch("commands.repositories.subprocess.run") as run_mock:
        result = runner.invoke(repositories.tag_repo, ["v1.0"], obj=obj)

    assert result.exit_code == 0
    expected_cwds = []
    for name in repos:
        repo_dir = Path("/tmp") / name
        expected_cwds.extend([repo_dir, repo_dir])
    cwds = [c.kwargs["cwd"] for c in run_mock.call_args_list]
    assert cwds == expected_cwds


def test_tag_from_setup_uses_version():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=True), patch.object(
        Path, "exists", return_value=True
    ), patch("commands.repositories.wait_for_requirements") as wait_mock, patch(
        "commands.repositories.extract_current_version", return_value="1.0"
    ) as ver_mock, patch("commands.repositories.subprocess.run") as run_mock:
        result = runner.invoke(repositories.tag_from_setup, obj=obj)

    assert result.exit_code == 0
    ver_mock.assert_called_once()
    expected = [["git", "tag", "v1.0"], ["git", "push", "origin", "v1.0"]]
    calls = [c.args[0] for c in run_mock.call_args_list]
    assert calls == expected


def test_tag_from_setup_missing_repo():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch.object(Path, "is_dir", return_value=False), patch(
        "commands.repositories.subprocess.run"
    ) as run_mock, patch(
        "commands.repositories.extract_current_version"
    ) as ver_mock:
        result = runner.invoke(repositories.tag_from_setup, obj=obj)

    assert result.exit_code == 0
    run_mock.assert_not_called()
    ver_mock.assert_not_called()


def test_repo_slug_handles_ssh_and_https():
    assert repositories._repo_slug("git@github.com:flamapy/flamapy_fw.git") == "flamapy/flamapy_fw"
    assert repositories._repo_slug("https://github.com/flamapy/flamapy_fw.git") == "flamapy/flamapy_fw"
    assert repositories._repo_slug("https://github.com/flamapy/flamapy_fw") == "flamapy/flamapy_fw"


def test_rerun_failed_requires_gh(tmp_path):
    runner = CliRunner()
    obj = {"REPOS": {"repo1": "git@github.com:org/repo1.git"}, "PARENT_DIR": str(tmp_path)}
    with patch("commands.repositories.shutil.which", return_value=None), patch(
        "commands.repositories.subprocess.run"
    ) as run_mock:
        result = runner.invoke(repositories.rerun_failed, obj=obj)
    assert result.exit_code == 0
    assert "'gh' CLI not found" in result.output
    run_mock.assert_not_called()


def _gh_run_list_output(runs):
    import json as _json

    return MagicMock(returncode=0, stdout=_json.dumps(runs), stderr="")


def test_rerun_failed_reruns_latest_failure_only(tmp_path):
    """Only the newest failed run per (workflow, ref) is rerun; superseded failures are not."""
    runner = CliRunner()
    obj = {"REPOS": {"repo1": "git@github.com:org/repo1.git"}, "PARENT_DIR": str(tmp_path)}
    runs = [
        {"databaseId": 3, "status": "completed", "conclusion": "failure",
         "name": "publish", "headBranch": "v2.0.0", "createdAt": "2026-07-03T10:00"},
        {"databaseId": 2, "status": "completed", "conclusion": "failure",
         "name": "publish", "headBranch": "v2.0.0", "createdAt": "2026-07-03T09:00"},
        {"databaseId": 1, "status": "completed", "conclusion": "success",
         "name": "tests", "headBranch": "develop", "createdAt": "2026-07-03T08:00"},
    ]
    calls = []

    def side_effect(args, **kwargs):
        calls.append(args)
        if args[:3] == ["gh", "run", "list"]:
            return _gh_run_list_output(runs)
        if args[:3] == ["gh", "run", "rerun"]:
            return MagicMock(returncode=0, stdout="", stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("commands.repositories.shutil.which", return_value="/usr/bin/gh"), patch(
        "commands.repositories.subprocess.run", side_effect=side_effect
    ):
        result = runner.invoke(repositories.rerun_failed, obj=obj)

    assert result.exit_code == 0
    rerun_calls = [c for c in calls if c[:3] == ["gh", "run", "rerun"]]
    assert rerun_calls == [["gh", "run", "rerun", "3", "--failed", "--repo", "org/repo1"]]
    assert "1 run(s) rerun" in result.output


def test_rerun_failed_skips_repo_with_pending_pypi_deps(tmp_path):
    runner = CliRunner()
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir()
    (repo_dir / "pyproject.toml").write_text(
        '[project]\nname = "flamapy-fm"\nversion = "2.0.0"\n'
        'dependencies = ["flamapy-fw~=2.0.0"]\n',
        encoding="utf-8",
    )
    obj = {"REPOS": {"repo1": "git@github.com:org/repo1.git"}, "PARENT_DIR": str(tmp_path)}
    runs = [
        {"databaseId": 5, "status": "completed", "conclusion": "failure",
         "name": "publish", "headBranch": "v2.0.0", "createdAt": "2026-07-03T10:00"},
    ]
    calls = []

    def side_effect(args, **kwargs):
        calls.append(args)
        return _gh_run_list_output(runs)

    from packaging.requirements import Requirement

    with patch("commands.repositories.shutil.which", return_value="/usr/bin/gh"), patch(
        "commands.repositories.subprocess.run", side_effect=side_effect
    ), patch(
        "commands.repositories.unavailable_internal_requirements",
        return_value=[Requirement("flamapy-fw~=2.0.0")],
    ):
        result = runner.invoke(repositories.rerun_failed, obj=obj)

    assert result.exit_code == 0
    assert all(c[:3] != ["gh", "run", "rerun"] for c in calls)
    assert "Skipping" in result.output
    assert "flamapy-fw~=2.0.0" in result.output
    assert "repo(s) skipped" in result.output


def test_rerun_failed_dry_run_does_not_rerun(tmp_path):
    runner = CliRunner()
    obj = {"REPOS": {"repo1": "git@github.com:org/repo1.git"}, "PARENT_DIR": str(tmp_path)}
    runs = [
        {"databaseId": 7, "status": "completed", "conclusion": "failure",
         "name": "publish", "headBranch": "v2.0.0", "createdAt": "2026-07-03T10:00"},
    ]
    calls = []

    def side_effect(args, **kwargs):
        calls.append(args)
        return _gh_run_list_output(runs)

    with patch("commands.repositories.shutil.which", return_value="/usr/bin/gh"), patch(
        "commands.repositories.subprocess.run", side_effect=side_effect
    ):
        result = runner.invoke(repositories.rerun_failed, ["--dry-run"], obj=obj)

    assert result.exit_code == 0
    assert all(c[:3] != ["gh", "run", "rerun"] for c in calls)
    assert "[DRY RUN] Would rerun failed jobs of publish (v2.0.0, run 7)" in result.output


def test_rerun_failed_ignores_stale_tag_runs(tmp_path):
    """Failed runs on old version tags are skipped; current tag and branches are kept."""
    runner = CliRunner()
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir()
    (repo_dir / "pyproject.toml").write_text(
        '[project]\nname = "flamapy-fw"\nversion = "2.6.0"\n',
        encoding="utf-8",
    )
    obj = {"REPOS": {"repo1": "git@github.com:org/repo1.git"}, "PARENT_DIR": str(tmp_path)}
    runs = [
        {"databaseId": 10, "status": "completed", "conclusion": "failure",
         "name": "publish", "headBranch": "v2.6.0", "createdAt": "2026-07-03T10:00"},
        {"databaseId": 9, "status": "completed", "conclusion": "failure",
         "name": "tests", "headBranch": "develop", "createdAt": "2026-07-03T09:00"},
        {"databaseId": 8, "status": "completed", "conclusion": "failure",
         "name": "publish", "headBranch": "v2.5.0", "createdAt": "2026-07-01T10:00"},
    ]
    calls = []

    def side_effect(args, **kwargs):
        calls.append(args)
        if args[:3] == ["gh", "run", "list"]:
            return _gh_run_list_output(runs)
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("commands.repositories.shutil.which", return_value="/usr/bin/gh"), patch(
        "commands.repositories.subprocess.run", side_effect=side_effect
    ), patch(
        "commands.repositories.unavailable_internal_requirements", return_value=[]
    ):
        result = runner.invoke(repositories.rerun_failed, obj=obj)

    assert result.exit_code == 0
    rerun_ids = [c[3] for c in calls if c[:3] == ["gh", "run", "rerun"]]
    assert rerun_ids == ["10", "9"]
    assert "Ignoring stale tag run: publish (v2.5.0)" in result.output
