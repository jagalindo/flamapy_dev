from click.testing import CliRunner
from unittest.mock import patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from commands import repositories


class DummyProcess:
    def __init__(self, returncode=0):
        self.returncode = returncode


def test_switch_develop_no_branch():
    runner = CliRunner()
    repos = {"repo1": "url1"}
    obj = {"REPOS": repos, "PARENT_DIR": "/tmp"}
    with patch("commands.repositories.os.path.isdir", return_value=False), patch(
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

    with patch("commands.repositories.os.path.isdir", return_value=True), patch(
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

    with patch("commands.repositories.os.path.isdir", return_value=True), patch(
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

    with patch("commands.repositories.os.path.isdir", return_value=True), patch(
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

    with patch("commands.repositories.os.path.isdir", return_value=True), patch(
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
    with patch("commands.repositories.os.path.isdir", return_value=True), patch(
        "commands.repositories.os.path.exists", return_value=True
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
    with patch("commands.repositories.os.path.isdir", return_value=False), patch(
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
    with patch("commands.repositories.os.path.isdir", return_value=True), patch(
        "commands.repositories.os.path.exists", return_value=False
    ), patch("commands.repositories.subprocess.run") as run_mock:
        result = runner.invoke(repositories.tag_repo, ["v1.0"], obj=obj)

    assert result.exit_code == 0
    expected_cwds = []
    for name in repos:
        repo_dir = os.path.join("/tmp", name)
        expected_cwds.extend([repo_dir, repo_dir])
    cwds = [c.kwargs["cwd"] for c in run_mock.call_args_list]
    assert cwds == expected_cwds
