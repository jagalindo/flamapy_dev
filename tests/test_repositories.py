from click.testing import CliRunner
from unittest.mock import patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from commands import repositories

class DummyProcess:
    def __init__(self, returncode=0):
        self.returncode = returncode


def test_switch_develop_no_branch():
    runner = CliRunner()
    repos = {'repo1': 'url1'}
    obj = {'REPOS': repos, 'PARENT_DIR': '/tmp'}
    with patch('commands.repositories.os.path.isdir', return_value=False) as isdir_mock, \
         patch('commands.repositories.subprocess.run') as run_mock:
        result = runner.invoke(repositories.switch_develop, obj=obj)
    assert result.exit_code == 0
    run_mock.assert_not_called()


def test_switch_main_or_master_prefers_main():
    runner = CliRunner()
    repos = {'repo1': 'url1'}
    obj = {'REPOS': repos, 'PARENT_DIR': '/tmp'}

    def side_effect(args, cwd=None, check=False, **kwargs):
        if args[0:3] == ['git', 'show-ref', '--verify']:
            if args[-1] == 'refs/heads/main':
                return DummyProcess(0)
            else:
                return DummyProcess(1)
        elif args[0:2] == ['git', 'switch']:
            return DummyProcess(0)
        return DummyProcess(0)

    with patch('commands.repositories.os.path.isdir', return_value=True), \
         patch('commands.repositories.subprocess.run', side_effect=side_effect) as run_mock:
        result = runner.invoke(repositories.switch_main_or_master, obj=obj)

    assert result.exit_code == 0
    switch_calls = [call.args[0] for call in run_mock.call_args_list if call.args and call.args[0][0:2] == ['git', 'switch']]
    assert switch_calls == [['git', 'switch', 'main']]


def test_switch_main_or_master_uses_master():
    runner = CliRunner()
    repos = {'repo1': 'url1'}
    obj = {'REPOS': repos, 'PARENT_DIR': '/tmp'}

    def side_effect(args, cwd=None, check=False, **kwargs):
        if args[0:3] == ['git', 'show-ref', '--verify']:
            if args[-1] == 'refs/heads/main':
                return DummyProcess(1)
            else:  # master check
                return DummyProcess(0)
        elif args[0:2] == ['git', 'switch']:
            return DummyProcess(0)
        return DummyProcess(0)

    with patch('commands.repositories.os.path.isdir', return_value=True), \
         patch('commands.repositories.subprocess.run', side_effect=side_effect) as run_mock:
        result = runner.invoke(repositories.switch_main_or_master, obj=obj)

    assert result.exit_code == 0
    switch_calls = [call.args[0] for call in run_mock.call_args_list if call.args and call.args[0][0:2] == ['git', 'switch']]
    assert switch_calls == [['git', 'switch', 'master']]
