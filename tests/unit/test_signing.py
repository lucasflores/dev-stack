"""Unit tests for dev_stack.vcs.signing — SSH signing utilities."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from dev_stack.vcs import SigningConfig
from dev_stack.vcs.signing import (
    UnsignedCommit,
    configure_ssh_signing,
    find_ssh_public_key,
    get_unsigned_agent_commits,
    supports_ssh_signing,
)


# ------------------------------------------------------------------
# find_ssh_public_key
# ------------------------------------------------------------------

class TestFindSshPublicKey:
    def test_finds_ed25519_first(self, tmp_path: Path) -> None:
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "id_ed25519.pub").write_text("ssh-ed25519 AAAA")
        (ssh_dir / "id_rsa.pub").write_text("ssh-rsa AAAA")

        with patch("dev_stack.vcs.signing.Path.home", return_value=tmp_path):
            result = find_ssh_public_key()
        assert result is not None
        assert "ed25519" in result

    def test_finds_rsa_if_no_ed25519(self, tmp_path: Path) -> None:
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "id_rsa.pub").write_text("ssh-rsa AAAA")

        with patch("dev_stack.vcs.signing.Path.home", return_value=tmp_path):
            result = find_ssh_public_key()
        assert result is not None
        assert "rsa" in result

    def test_returns_none_no_ssh_dir(self, tmp_path: Path) -> None:
        with patch("dev_stack.vcs.signing.Path.home", return_value=tmp_path):
            assert find_ssh_public_key() is None

    def test_returns_none_empty_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".ssh").mkdir()
        with patch("dev_stack.vcs.signing.Path.home", return_value=tmp_path):
            assert find_ssh_public_key() is None


# ------------------------------------------------------------------
# supports_ssh_signing
# ------------------------------------------------------------------

class TestSupportsSshSigning:
    def test_git_234_ok(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="git version 2.34.1")
        with patch("dev_stack.vcs.signing.subprocess.run", return_value=mock_result):
            assert supports_ssh_signing() is True

    def test_git_240_ok(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="git version 2.40.0")
        with patch("dev_stack.vcs.signing.subprocess.run", return_value=mock_result):
            assert supports_ssh_signing() is True

    def test_git_233_too_old(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="git version 2.33.0")
        with patch("dev_stack.vcs.signing.subprocess.run", return_value=mock_result):
            assert supports_ssh_signing() is False

    def test_git_not_found(self) -> None:
        with patch("dev_stack.vcs.signing.subprocess.run", side_effect=FileNotFoundError):
            assert supports_ssh_signing() is False

    def test_git_error(self) -> None:
        mock_result = MagicMock(returncode=1, stdout="")
        with patch("dev_stack.vcs.signing.subprocess.run", return_value=mock_result):
            assert supports_ssh_signing() is False


# ------------------------------------------------------------------
# configure_ssh_signing
# ------------------------------------------------------------------

class TestConfigureSshSigning:
    def test_not_enabled(self, tmp_path: Path) -> None:
        config = SigningConfig(enabled=False)
        ok, msg = configure_ssh_signing(tmp_path, config)
        assert ok is True
        assert "not enabled" in msg.lower()

    def test_git_too_old(self, tmp_path: Path) -> None:
        config = SigningConfig(enabled=True)
        with patch("dev_stack.vcs.signing.supports_ssh_signing", return_value=False):
            ok, msg = configure_ssh_signing(tmp_path, config)
        assert ok is False
        assert "2.34" in msg

    def test_no_key(self, tmp_path: Path) -> None:
        config = SigningConfig(enabled=True)
        with (
            patch("dev_stack.vcs.signing.supports_ssh_signing", return_value=True),
            patch("dev_stack.vcs.signing.find_ssh_public_key", return_value=None),
        ):
            ok, msg = configure_ssh_signing(tmp_path, config)
        assert ok is False
        assert "ssh-keygen" in msg.lower()

    def test_key_not_found(self, tmp_path: Path) -> None:
        config = SigningConfig(enabled=True, key="/nonexistent/key.pub")
        with patch("dev_stack.vcs.signing.supports_ssh_signing", return_value=True):
            ok, msg = configure_ssh_signing(tmp_path, config)
        assert ok is False
        assert "not found" in msg.lower()

    def test_success(self, tmp_path: Path) -> None:
        key = tmp_path / "id_ed25519.pub"
        key.write_text("ssh-ed25519 AAAA")
        config = SigningConfig(enabled=True, key=str(key))
        with (
            patch("dev_stack.vcs.signing.supports_ssh_signing", return_value=True),
            patch("dev_stack.vcs.signing.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            ok, msg = configure_ssh_signing(tmp_path, config)
        assert ok is True
        assert "configured" in msg.lower()
        # 3 git config calls
        assert mock_run.call_count == 3


# ------------------------------------------------------------------
# get_unsigned_agent_commits
# ------------------------------------------------------------------

class TestGetUnsignedAgentCommits:
    def test_empty_on_no_shas(self) -> None:
        assert get_unsigned_agent_commits("", "") == []

    def test_empty_on_git_error(self, tmp_path: Path) -> None:
        mock_result = MagicMock(returncode=128, stdout="")
        with patch("dev_stack.vcs.signing.subprocess.run", return_value=mock_result):
            result = get_unsigned_agent_commits("abc", "def", repo_root=tmp_path)
        assert result == []

    def test_detects_unsigned_agent_commit(self, tmp_path: Path) -> None:
        sep = "---FIELD---"
        row_sep = "---ROW---"
        body = "Some body text\nAgent: copilot\n"
        line = f"{'a' * 40}{sep}{'a' * 7}{sep}feat: add thing{sep}{body}{sep}N{row_sep}"

        mock_result = MagicMock(returncode=0, stdout=line)
        with patch("dev_stack.vcs.signing.subprocess.run", return_value=mock_result):
            result = get_unsigned_agent_commits("abc", "def", repo_root=tmp_path)
        assert len(result) == 1
        assert result[0].subject == "feat: add thing"

    def test_ignores_signed_agent_commit(self, tmp_path: Path) -> None:
        sep = "---FIELD---"
        row_sep = "---ROW---"
        body = "Agent: copilot\n"
        line = f"{'a' * 40}{sep}{'a' * 7}{sep}feat: add thing{sep}{body}{sep}G{row_sep}"

        mock_result = MagicMock(returncode=0, stdout=line)
        with patch("dev_stack.vcs.signing.subprocess.run", return_value=mock_result):
            result = get_unsigned_agent_commits("abc", "def", repo_root=tmp_path)
        assert len(result) == 0

    def test_ignores_human_unsigned_commit(self, tmp_path: Path) -> None:
        sep = "---FIELD---"
        row_sep = "---ROW---"
        body = "Some body, no Agent trailer\n"
        line = f"{'a' * 40}{sep}{'a' * 7}{sep}fix: typo{sep}{body}{sep}N{row_sep}"

        mock_result = MagicMock(returncode=0, stdout=line)
        with patch("dev_stack.vcs.signing.subprocess.run", return_value=mock_result):
            result = get_unsigned_agent_commits("abc", "def", repo_root=tmp_path)
        assert len(result) == 0

    def test_new_branch_null_sha(self, tmp_path: Path) -> None:
        """Remote SHA of all zeros means new branch — should use local_sha only."""
        sep = "---FIELD---"
        row_sep = "---ROW---"
        body = "Agent: copilot\n"
        line = f"{'a' * 40}{sep}{'a' * 7}{sep}feat: new{sep}{body}{sep}N{row_sep}"

        mock_result = MagicMock(returncode=0, stdout=line)
        with patch("dev_stack.vcs.signing.subprocess.run", return_value=mock_result) as mock_run:
            result = get_unsigned_agent_commits("abc123", "0" * 40, repo_root=tmp_path)
        assert len(result) == 1
        # Verify the rev range used is just the local SHA (not a diff)
        cmd = mock_run.call_args[0][0]
        assert "abc123" in cmd
        assert ".." not in " ".join(cmd)
