"""Tests for source-arg-based message detection in prepare-commit-msg hook.

Replaces old _user_message_provided() tests — detection now uses
the hook's source argument instead of COMMIT_EDITMSG.
"""
from __future__ import annotations

from unittest.mock import patch

from dev_stack.vcs.hooks_runner import _SKIP_SOURCES, run_prepare_commit_msg_hook


class TestSourceArgGating:
    """Verify source-arg early-exit logic in run_prepare_commit_msg_hook."""

    def test_source_message_skips_generation(self, tmp_path):
        """source='message' (-m flag) → exit 0, no pipeline run."""
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("user message\n")
        result = run_prepare_commit_msg_hook(str(msg_file), source="message")
        assert result == 0

    def test_source_commit_skips_generation(self, tmp_path):
        """source='commit' (--amend) → exit 0, no pipeline run."""
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("existing message\n")
        result = run_prepare_commit_msg_hook(str(msg_file), source="commit", commit_sha="abc123")
        assert result == 0

    def test_source_merge_skips_generation(self):
        """source='merge' → exit 0, no pipeline run."""
        result = run_prepare_commit_msg_hook("/dev/null", source="merge")
        assert result == 0

    def test_source_squash_skips_generation(self):
        """source='squash' → exit 0, no pipeline run."""
        result = run_prepare_commit_msg_hook("/dev/null", source="squash")
        assert result == 0

    def test_empty_source_string_treated_as_none(self, tmp_path):
        """source='' (empty string) → normalize to None, attempt generation."""
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("")
        with patch("dev_stack.vcs.hooks_runner._get_repo_root", return_value=None):
            result = run_prepare_commit_msg_hook(str(msg_file), source="")
        assert result == 0  # graceful exit when no repo root

    def test_skip_sources_completeness(self):
        """All documented skip sources are in the set."""
        assert _SKIP_SOURCES == {"message", "commit", "merge", "squash"}

    def test_source_none_attempts_generation(self, tmp_path):
        """source=None (plain git commit) → attempts generation."""
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("")
        with patch("dev_stack.vcs.hooks_runner._get_repo_root", return_value=None):
            result = run_prepare_commit_msg_hook(str(msg_file), source=None)
        assert result == 0

    def test_source_template_attempts_generation(self, tmp_path):
        """source='template' → attempts generation (template present but no user content)."""
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("")
        with patch("dev_stack.vcs.hooks_runner._get_repo_root", return_value=None):
            result = run_prepare_commit_msg_hook(str(msg_file), source="template")
        assert result == 0

