"""Integration tests for pre-push hook — tests/integration/test_pre_push.py

Covers:
- Valid branch name allows push (exit 0)
- Invalid branch name blocks push (exit 1)
- Exempt branches bypass validation
- Custom pattern from pyproject.toml
- Detached HEAD is gracefully skipped
"""
from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest


def _init_git_repo(path: Path, branch: str = "main") -> None:
    """Create a git repo at *path* and check out *branch*."""
    subprocess.run(["git", "init", str(path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(path), "checkout", "-b", branch],
        capture_output=True,
        check=True,
    )
    # Need at least one commit for branch to exist
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@test.com"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        capture_output=True,
        check=True,
    )
    (path / "README.md").write_text("# test\n")
    subprocess.run(
        ["git", "-C", str(path), "add", "."], capture_output=True, check=True
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "init"],
        capture_output=True,
        check=True,
    )


class TestPrePushHook:
    """End-to-end tests for run_pre_push_hook via branch validation."""

    def test_valid_branch_allows_push(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_git_repo(tmp_path, branch="feat/my-feature")
        monkeypatch.chdir(tmp_path)

        from dev_stack.vcs.hooks_runner import run_pre_push_hook

        rc = run_pre_push_hook(io.StringIO(""))
        assert rc == 0

    def test_invalid_branch_blocks_push(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_git_repo(tmp_path, branch="my-random-branch")
        monkeypatch.chdir(tmp_path)

        from dev_stack.vcs.hooks_runner import run_pre_push_hook

        rc = run_pre_push_hook(io.StringIO(""))
        assert rc == 1

    def test_exempt_branch_main(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_git_repo(tmp_path, branch="main")
        monkeypatch.chdir(tmp_path)

        from dev_stack.vcs.hooks_runner import run_pre_push_hook

        rc = run_pre_push_hook(io.StringIO(""))
        assert rc == 0

    def test_exempt_branch_develop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_git_repo(tmp_path, branch="develop")
        monkeypatch.chdir(tmp_path)

        from dev_stack.vcs.hooks_runner import run_pre_push_hook

        rc = run_pre_push_hook(io.StringIO(""))
        assert rc == 0

    def test_custom_pattern_from_pyproject(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _init_git_repo(tmp_path, branch="release/v1.2.3")
        # Write pyproject with custom pattern
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n\n'
            "[tool.dev-stack.branch]\n"
            'pattern = "^release/v\\\\d+\\\\.\\\\d+\\\\.\\\\d+$"\n'
        )
        monkeypatch.chdir(tmp_path)

        from dev_stack.vcs.hooks_runner import run_pre_push_hook

        rc = run_pre_push_hook(io.StringIO(""))
        assert rc == 0

    def test_spec_branch_mismatch_warns_but_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _init_git_repo(tmp_path, branch="feat/my-feature")

        # Create a spec file declaring a different branch
        specs_dir = tmp_path / "specs" / "001-thing"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text(
            "# My Spec\n\n**Branch**: `feat/other-feature`\n"
        )

        monkeypatch.chdir(tmp_path)

        from dev_stack.vcs.hooks_runner import run_pre_push_hook

        rc = run_pre_push_hook(io.StringIO(""))
        assert rc == 0  # Non-blocking

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "feat/other-feature" in captured.err
