"""Unit tests for changelog generation — tests/unit/test_changelog.py

Covers:
- Group mapping (commit types → sections)
- AI/human-edited markers
- Missing git-cliff error handling
- Missing cliff.toml error handling
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dev_stack.vcs.changelog import ChangelogResult, generate_changelog


class TestGitCliffNotInstalled:
    """Error when git-cliff is not available."""

    def test_returns_error_when_not_installed(self, tmp_path: Path) -> None:
        with patch("dev_stack.vcs.changelog.shutil.which", return_value=None):
            result = generate_changelog(repo_root=tmp_path)

        assert result.success is False
        assert "not installed" in (result.error or "")
        assert result.help is not None
        assert "cargo install" in result.help or "brew install" in result.help


class TestMissingCliffToml:
    """Error when cliff.toml doesn't exist."""

    def test_returns_error_when_missing(self, tmp_path: Path) -> None:
        with patch("dev_stack.vcs.changelog.shutil.which", return_value="/usr/bin/git-cliff"):
            with patch("dev_stack.vcs.changelog.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout="git-cliff 2.4.0", returncode=0
                )
                result = generate_changelog(repo_root=tmp_path)

        assert result.success is False
        assert "cliff.toml" in (result.error or "")


class TestSuccessfulGeneration:
    """Successful changelog generation scenarios."""

    def _mock_cliff_output(self) -> str:
        return """
# Changelog

## [Unreleased]

### Features

- *(cli)* Add PR command 🤖
- *(vcs)* Add branch validation

### Bug Fixes

- *(hooks)* Fix permission issue 🤖 ✏️

"""

    def test_unreleased_mode(self, tmp_path: Path) -> None:
        (tmp_path / "cliff.toml").write_text("[changelog]\n")

        with patch("dev_stack.vcs.changelog.shutil.which", return_value="/usr/bin/git-cliff"):
            with patch("dev_stack.vcs.changelog.subprocess.run") as mock_run:
                # First call: version check
                ver_mock = MagicMock(stdout="git-cliff 2.4.0", returncode=0)
                # Second call: generation
                gen_mock = MagicMock(stdout=self._mock_cliff_output(), returncode=0)
                mock_run.side_effect = [ver_mock, gen_mock]

                result = generate_changelog(repo_root=tmp_path, unreleased=True)

        assert result.success is True
        assert result.mode == "unreleased"
        assert result.git_cliff_version == "2.4.0"
        assert result.ai_commits_annotated == 2  # Two 🤖 markers
        assert result.human_edited_annotated == 1  # One ✏️ marker
        assert result.versions_rendered == 1  # [Unreleased]
        assert result.total_commits_processed == 3  # Three "- " lines
        assert (tmp_path / "CHANGELOG.md").exists()

    def test_full_mode(self, tmp_path: Path) -> None:
        (tmp_path / "cliff.toml").write_text("[changelog]\n")

        with patch("dev_stack.vcs.changelog.shutil.which", return_value="/usr/bin/git-cliff"):
            with patch("dev_stack.vcs.changelog.subprocess.run") as mock_run:
                ver_mock = MagicMock(stdout="git-cliff 2.4.0", returncode=0)
                gen_mock = MagicMock(stdout="## [1.0.0]\n- feat: init\n", returncode=0)
                mock_run.side_effect = [ver_mock, gen_mock]

                result = generate_changelog(repo_root=tmp_path, full=True)

        assert result.success is True
        assert result.mode == "full"

    def test_custom_output_file(self, tmp_path: Path) -> None:
        (tmp_path / "cliff.toml").write_text("[changelog]\n")

        with patch("dev_stack.vcs.changelog.shutil.which", return_value="/usr/bin/git-cliff"):
            with patch("dev_stack.vcs.changelog.subprocess.run") as mock_run:
                ver_mock = MagicMock(stdout="git-cliff 2.4.0", returncode=0)
                gen_mock = MagicMock(stdout="# Changelog\n", returncode=0)
                mock_run.side_effect = [ver_mock, gen_mock]

                result = generate_changelog(
                    repo_root=tmp_path, output_file="docs/CHANGES.md"
                )

        assert result.success is True
        assert result.output_file == "docs/CHANGES.md"
        assert (tmp_path / "docs" / "CHANGES.md").exists()


class TestGitCliffFailure:
    """Handle git-cliff process failure."""

    def test_nonzero_exit_code(self, tmp_path: Path) -> None:
        (tmp_path / "cliff.toml").write_text("[changelog]\n")

        with patch("dev_stack.vcs.changelog.shutil.which", return_value="/usr/bin/git-cliff"):
            with patch("dev_stack.vcs.changelog.subprocess.run") as mock_run:
                ver_mock = MagicMock(stdout="git-cliff 2.4.0", returncode=0)
                gen_mock = MagicMock(stdout="", stderr="fatal: bad config", returncode=1)
                mock_run.side_effect = [ver_mock, gen_mock]

                result = generate_changelog(repo_root=tmp_path)

        assert result.success is False
        assert "failed" in (result.error or "").lower()
