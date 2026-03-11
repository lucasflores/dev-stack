"""Tests for _auto_stage_outputs() in pipeline runner."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from dev_stack.pipeline.runner import _auto_stage_outputs


def test_stages_existing_files(tmp_path: Path) -> None:
    """Verify it stages files that exist on disk."""
    (tmp_path / ".git").mkdir()
    f1 = tmp_path / "file1.txt"
    f1.write_text("hello")

    with patch("dev_stack.pipeline.runner.subprocess.run") as mock_run:
        # check-ignore returns 1 (not ignored), git add returns 0
        mock_run.side_effect = [
            subprocess.CompletedProcess([], returncode=1),  # check-ignore
            subprocess.CompletedProcess([], returncode=0, stdout="", stderr=""),  # git add
        ]
        result = _auto_stage_outputs(tmp_path, [f1])

    assert result == ["file1.txt"]


def test_skips_nonexistent_paths(tmp_path: Path) -> None:
    """Verify it skips paths that don't exist on disk."""
    missing = tmp_path / "nonexistent.txt"
    result = _auto_stage_outputs(tmp_path, [missing])
    assert result == []


def test_skips_gitignored_paths(tmp_path: Path) -> None:
    """Verify it skips paths matched by .gitignore."""
    f1 = tmp_path / "ignored.txt"
    f1.write_text("hello")

    with patch("dev_stack.pipeline.runner.subprocess.run") as mock_run:
        # check-ignore returns 0 (is ignored)
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        result = _auto_stage_outputs(tmp_path, [f1])

    assert result == []


def test_logs_warning_on_git_add_failure(tmp_path: Path, caplog) -> None:
    """Verify it logs warnings when git add fails and continues."""
    f1 = tmp_path / "file1.txt"
    f1.write_text("hello")
    f2 = tmp_path / "file2.txt"
    f2.write_text("world")

    with patch("dev_stack.pipeline.runner.subprocess.run") as mock_run:
        mock_run.side_effect = [
            subprocess.CompletedProcess([], returncode=1),  # check-ignore f1 (not ignored)
            subprocess.CompletedProcess([], returncode=1, stdout="", stderr="error"),  # git add f1 fails
            subprocess.CompletedProcess([], returncode=1),  # check-ignore f2 (not ignored)
            subprocess.CompletedProcess([], returncode=0, stdout="", stderr=""),  # git add f2 ok
        ]
        result = _auto_stage_outputs(tmp_path, [f1, f2])

    assert result == ["file2.txt"]


def test_never_raises_exceptions(tmp_path: Path) -> None:
    """Verify it never raises exceptions, returns partial results."""
    f1 = tmp_path / "file1.txt"
    f1.write_text("hello")

    with patch("dev_stack.pipeline.runner.subprocess.run", side_effect=OSError("boom")):
        result = _auto_stage_outputs(tmp_path, [f1])

    assert isinstance(result, list)
