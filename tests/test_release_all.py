import os
import sys
from pathlib import Path
from unittest.mock import patch

import click
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


def test_normalize_version_strips_leading_v():
    assert versions.normalize_version("v2.6.0.dev10") == "2.6.0.dev10"
    assert versions.normalize_version("V2.6.0") == "2.6.0"
    assert versions.normalize_version("2.6.0.dev10") == "2.6.0.dev10"
    # only a v directly prefixing a digit is stripped
    assert versions.normalize_version("vv2.6.0") == "vv2.6.0"


def test_bump_ide_writes_version_file(tmp_path):
    ide_dir = tmp_path / "flamapy-ide"
    ide_dir.mkdir()
    (ide_dir / "flamapy.version").write_text("2.6.0.dev5\n", encoding="utf-8")

    versions._bump_ide(str(tmp_path), "flamapy-ide", "2.6.0.dev10", dry_run=False)
    assert (ide_dir / "flamapy.version").read_text() == "2.6.0.dev10\n"


def test_bump_ide_dry_run_does_not_write(tmp_path):
    ide_dir = tmp_path / "flamapy-ide"
    ide_dir.mkdir()
    (ide_dir / "flamapy.version").write_text("2.6.0.dev5\n", encoding="utf-8")

    versions._bump_ide(str(tmp_path), "flamapy-ide", "2.6.0.dev10", dry_run=True)
    assert (ide_dir / "flamapy.version").read_text() == "2.6.0.dev5\n"


def test_wait_for_package_times_out():
    with patch("commands.pypi._package_available", return_value=False):
        with pytest.raises(TimeoutError):
            pypi.wait_for_package("flamapy", "9.9.9", check_interval=0, timeout=0)


def test_to_stable_version_drops_dev_and_pre_suffixes():
    assert versions.to_stable_version("2.6.0.dev11") == "2.6.0"
    assert versions.to_stable_version("v2.6.0.dev11") == "2.6.0"
    assert versions.to_stable_version("2.6.0rc1") == "2.6.0"
    assert versions.to_stable_version("2.6.0.post2") == "2.6.0"
    assert versions.to_stable_version("2.6.0") == "2.6.0"


def _write_pyproject(folder: Path, name: str, version: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n', encoding="utf-8"
    )


def test_derive_stable_version_from_consistent_dev_versions(tmp_path):
    _write_pyproject(tmp_path / "flamapy_fw", "flamapy-fw", "2.6.0.dev11")
    _write_pyproject(tmp_path / "fm_metamodel", "flamapy-fm", "2.6.0.dev11")
    repos = {"flamapy_fw": "u1", "fm_metamodel": "u2"}
    assert versions._derive_stable_version(str(tmp_path), repos) == "2.6.0"


def test_derive_stable_version_rejects_disagreeing_repos(tmp_path):
    _write_pyproject(tmp_path / "flamapy_fw", "flamapy-fw", "2.6.0.dev11")
    _write_pyproject(tmp_path / "fm_metamodel", "flamapy-fm", "2.7.0.dev1")
    repos = {"flamapy_fw": "u1", "fm_metamodel": "u2"}
    with pytest.raises(click.ClickException):
        versions._derive_stable_version(str(tmp_path), repos)


def test_stabilize_repos_merges_develop_to_main_and_tags_main():
    from unittest.mock import MagicMock

    calls = []

    def fake_run(args, cwd=None, **kwargs):
        calls.append(args)
        # Report a dirty tree so the bump gets committed.
        stdout = " M pyproject.toml" if args[:2] == ["git", "status"] else ""
        return MagicMock(returncode=0, stdout=stdout, stderr="")

    with patch.object(Path, "is_dir", return_value=True), \
         patch.object(Path, "exists", return_value=False), \
         patch("commands.versions.subprocess.run", side_effect=fake_run), \
         patch("commands.versions.time.sleep"):
        versions._stabilize_repos(
            "/tmp", {"repo1": "u1"}, "2.6.0", set(), dry_run=False
        )

    git_calls = [c for c in calls if c and c[0] == "git"]
    assert ["git", "checkout", "main"] in git_calls
    assert any(c[:3] == ["git", "merge", "--no-ff"] for c in git_calls)
    assert ["git", "push", "origin", "main"] in git_calls
    assert ["git", "tag", "v2.6.0", "main"] in git_calls
    assert ["git", "push", "origin", "v2.6.0"] in git_calls


def test_release_branch_detects_main_and_master():
    from unittest.mock import MagicMock

    def make_fake(present):
        def fake_run(args, cwd=None, **kwargs):
            # `git show-ref --verify --quiet refs/heads/<b>` and
            # `git ls-remote --exit-code --heads origin <b>` succeed only for `present`.
            ref = args[-1]
            branch = ref.rsplit("/", 1)[-1]
            rc = 0 if branch == present else 1
            return MagicMock(returncode=rc, stdout="", stderr="")
        return fake_run

    with patch("commands.versions.subprocess.run", side_effect=make_fake("main")):
        assert versions._release_branch(Path("/tmp/repo")) == "main"
    with patch("commands.versions.subprocess.run", side_effect=make_fake("master")):
        assert versions._release_branch(Path("/tmp/repo")) == "master"


def test_stabilize_repos_tags_master_repo_on_master():
    from unittest.mock import MagicMock

    calls = []

    def fake_run(args, cwd=None, **kwargs):
        calls.append(args)
        # This repo only has 'master' (no 'main') on refs/heads or origin.
        if args[:2] == ["git", "show-ref"] or args[:2] == ["git", "ls-remote"]:
            rc = 0 if args[-1].rsplit("/", 1)[-1] == "master" else 1
            return MagicMock(returncode=rc, stdout="", stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(Path, "is_dir", return_value=True), \
         patch.object(Path, "exists", return_value=False), \
         patch("commands.versions.subprocess.run", side_effect=fake_run), \
         patch("commands.versions.time.sleep"):
        versions._stabilize_repos("/tmp", {"repo1": "u1"}, "2.6.0", set(), dry_run=False)

    git_calls = [c for c in calls if c and c[0] == "git"]
    assert ["git", "checkout", "master"] in git_calls
    assert ["git", "push", "origin", "master"] in git_calls
    assert ["git", "tag", "v2.6.0", "master"] in git_calls
    assert ["git", "checkout", "main"] not in git_calls


def test_stabilize_repos_dry_run_runs_no_mutating_git():
    """Dry-run may query the release branch (read-only) but must not commit/merge/push/tag."""
    from unittest.mock import MagicMock

    calls = []

    def fake_run(args, cwd=None, **kwargs):
        calls.append(args)
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(Path, "is_dir", return_value=True), \
         patch("commands.versions.subprocess.run", side_effect=fake_run), \
         patch("commands.versions.time.sleep") as sleep_mock:
        versions._stabilize_repos(
            "/tmp", {"repo1": "u1", "repo2": "u2"}, "2.6.0", set(), dry_run=True
        )

    mutating = {"commit", "merge", "push", "tag", "checkout", "add"}
    assert not [c for c in calls if c and c[0] == "git" and c[1] in mutating]
    sleep_mock.assert_not_called()


def test_merge_develop_to_main_restores_develop_on_failure():
    from unittest.mock import MagicMock

    calls = []

    def fake_run(args, cwd=None, **kwargs):
        calls.append(args)
        # Fail the merge step; everything else succeeds.
        rc = 1 if args[:2] == ["git", "merge"] else 0
        return MagicMock(returncode=rc, stdout="", stderr="conflict")

    with patch("commands.versions.subprocess.run", side_effect=fake_run):
        result = versions._merge_develop_to_main(Path("/tmp/repo"), "chore: release 2.6.0")

    assert result is None
    # After a failed merge we must return to develop and never push the release branch.
    assert ["git", "checkout", "develop"] in calls
    assert ["git", "push", "origin", "main"] not in calls
    assert ["git", "push", "origin", "master"] not in calls


def test_stabilize_repos_pauses_between_repos_but_not_before_first():
    """A TAG_DELAY_SECONDS pause separates consecutive repos' tag pushes only."""
    from unittest.mock import MagicMock

    def fake_run(args, cwd=None, **kwargs):
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(Path, "is_dir", return_value=True), \
         patch.object(Path, "exists", return_value=False), \
         patch("commands.versions.subprocess.run", side_effect=fake_run), \
         patch("commands.versions.time.sleep") as sleep_mock:
        versions._stabilize_repos(
            "/tmp", {"r1": "u1", "r2": "u2", "r3": "u3"}, "2.6.0", set(), dry_run=False
        )

    assert sleep_mock.call_count == 2
    sleep_mock.assert_called_with(versions.TAG_DELAY_SECONDS)


def test_tag_all_pauses_between_repos_but_not_before_first():
    """_tag_all sleeps TAG_DELAY_SECONDS between consecutive tag pushes only."""
    from unittest.mock import MagicMock

    def fake_run(args, cwd=None, **kwargs):
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(Path, "is_dir", return_value=True), \
         patch.object(Path, "exists", return_value=False), \
         patch("commands.versions.subprocess.run", side_effect=fake_run), \
         patch("commands.versions.time.sleep") as sleep_mock:
        versions._tag_all("/tmp", {"repo1": "u1", "repo2": "u2", "repo3": "u3"},
                          "2.0.0", set())

    assert sleep_mock.call_count == 2
    sleep_mock.assert_called_with(versions.TAG_DELAY_SECONDS)
