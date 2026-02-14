"""Tests for git rollback helpers."""
from __future__ import annotations

import subprocess
from pathlib import Path

from dev_stack.brownfield.rollback import (
    create_rollback_tag,
    delete_tags,
    list_rollback_tags,
    restore_rollback,
)


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo_root: Path) -> None:
    _run_git(repo_root, ["init"])
    _run_git(repo_root, ["config", "user.email", "dev-stack@example.com"])
    _run_git(repo_root, ["config", "user.name", "Dev Stack"])


def _commit_file(repo_root: Path, relative: str, content: str) -> Path:
    target = repo_root / relative
    target.write_text(content, encoding="utf-8")
    _run_git(repo_root, ["add", relative])
    _run_git(repo_root, ["commit", "-m", "test commit"])
    return target


def test_create_rollback_tag_without_commits(tmp_path) -> None:
    repo = tmp_path / "repo_no_commits"
    repo.mkdir()
    _init_repo(repo)

    tag = create_rollback_tag(repo)

    assert tag is None
    assert list_rollback_tags(repo) == []


def test_create_restore_and_delete_tag(tmp_path) -> None:
    repo = tmp_path / "repo_with_tag"
    repo.mkdir()
    _init_repo(repo)
    tracked_file = _commit_file(repo, "README.md", "original\n")

    tag = create_rollback_tag(repo)
    assert tag is not None

    tracked_file.write_text("modified\n", encoding="utf-8")
    restore_rollback(repo, tag)
    assert tracked_file.read_text(encoding="utf-8") == "original\n"

    tags = list_rollback_tags(repo)
    assert tag in tags

    delete_tags(repo, [tag])
    assert tag not in list_rollback_tags(repo)
