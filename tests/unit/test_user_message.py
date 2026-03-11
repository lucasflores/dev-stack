"""Tests for _user_message_provided() in pipeline stages."""
from __future__ import annotations

from pathlib import Path

from dev_stack.pipeline.stages import _user_message_provided


def test_returns_true_with_user_content(tmp_path: Path) -> None:
    """COMMIT_EDITMSG with user-supplied content → True."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "COMMIT_EDITMSG").write_text("feat: add new feature\n# comment line\n")
    assert _user_message_provided(tmp_path) is True


def test_returns_false_when_file_missing(tmp_path: Path) -> None:
    """No COMMIT_EDITMSG → False."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    assert _user_message_provided(tmp_path) is False


def test_returns_false_when_only_comments(tmp_path: Path) -> None:
    """COMMIT_EDITMSG with only comments/whitespace → False."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "COMMIT_EDITMSG").write_text("# Please enter commit message\n# Another comment\n\n")
    assert _user_message_provided(tmp_path) is False


def test_returns_false_when_empty(tmp_path: Path) -> None:
    """Empty COMMIT_EDITMSG → False."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "COMMIT_EDITMSG").write_text("")
    assert _user_message_provided(tmp_path) is False


def test_returns_false_when_git_dir_missing(tmp_path: Path) -> None:
    """No .git directory → False."""
    assert _user_message_provided(tmp_path) is False
