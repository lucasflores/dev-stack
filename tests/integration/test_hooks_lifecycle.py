"""Integration tests for hooks lifecycle: init → status → modify → update → uninstall."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dev_stack.modules.vcs_hooks import VcsHooksModule


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create an actual git repository for integration tests."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        capture_output=True,
        cwd=tmp_path,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        capture_output=True,
        cwd=tmp_path,
    )

    # Create pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.dev-stack.hooks]\n'
        'commit-msg = true\npre-push = true\npre-commit = false\n'
    )

    # Create .dev-stack directory
    (tmp_path / ".dev-stack").mkdir(exist_ok=True)

    return tmp_path


class TestHooksLifecycle:
    """Full lifecycle: install → verify → status → modify → update → uninstall."""

    def test_full_lifecycle(self, git_repo: Path) -> None:
        module = VcsHooksModule(git_repo)

        # 1. Install
        install_result = module.install()
        assert install_result.success
        assert (git_repo / ".git" / "hooks" / "commit-msg").exists()
        assert (git_repo / ".git" / "hooks" / "pre-push").exists()

        # 2. Verify — healthy (but note constitution/instructions missing)
        manifest_path = git_repo / ".dev-stack" / "hooks-manifest.json"
        assert manifest_path.exists()
        manifest_data = json.loads(manifest_path.read_text())
        assert "commit-msg" in manifest_data["hooks"]
        assert "pre-push" in manifest_data["hooks"]

        # 3. Modify a hook
        hook = git_repo / ".git" / "hooks" / "commit-msg"
        original_content = hook.read_text()
        hook.write_text(original_content + "\n# modified by user")

        # 4. Update — should skip modified hook
        update_result = module.update()
        assert update_result.success
        assert any("manually modified" in w for w in update_result.warnings)

        # 5. Verify — should detect mismatch
        status = module.verify()
        assert "checksum mismatch" in (status.issue or "")

        # 6. Uninstall — should skip modified hook, remove matching hook
        uninstall_result = module.uninstall()
        assert uninstall_result.success
        # commit-msg was modified — should still exist
        assert (git_repo / ".git" / "hooks" / "commit-msg").exists()
        # pre-push was unmodified — should be deleted
        assert not (git_repo / ".git" / "hooks" / "pre-push").exists()
        # Manifest should be deleted
        assert not manifest_path.exists()

    def test_reinstall_overwrites_managed_hooks(self, git_repo: Path) -> None:
        module = VcsHooksModule(git_repo)

        module.install()
        # Second install should succeed (hooks are managed)
        result = module.install()
        assert result.success

    def test_install_with_no_pyproject_uses_defaults(self, git_repo: Path) -> None:
        """Without pyproject.toml, defaults enable commit-msg + pre-push."""
        (git_repo / "pyproject.toml").unlink()
        module = VcsHooksModule(git_repo)
        result = module.install()
        assert result.success
        assert (git_repo / ".git" / "hooks" / "commit-msg").exists()
        assert (git_repo / ".git" / "hooks" / "pre-push").exists()


class TestPrepareCommitMsgHookLifecycle:
    """Integration tests for the prepare-commit-msg hook."""

    def test_hook_installed_when_pre_commit_enabled(self, git_repo: Path) -> None:
        """prepare-commit-msg hook is installed alongside pre-commit."""
        # Enable pre-commit in config
        pyproject = git_repo / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n\n[tool.dev-stack.hooks]\n'
            'commit-msg = true\npre-push = true\npre-commit = true\n'
        )
        module = VcsHooksModule(git_repo)
        result = module.install()
        assert result.success
        pcm_hook = git_repo / ".git" / "hooks" / "prepare-commit-msg"
        assert pcm_hook.exists()
        # Verify it's in the manifest
        manifest_path = git_repo / ".dev-stack" / "hooks-manifest.json"
        manifest_data = json.loads(manifest_path.read_text())
        assert "prepare-commit-msg" in manifest_data["hooks"]

    def test_hook_not_installed_when_pre_commit_disabled(self, git_repo: Path) -> None:
        """prepare-commit-msg hook is NOT installed when pre-commit is disabled."""
        module = VcsHooksModule(git_repo)
        result = module.install()
        assert result.success
        pcm_hook = git_repo / ".git" / "hooks" / "prepare-commit-msg"
        assert not pcm_hook.exists()

    def test_source_arg_skips_for_dash_m(self, git_repo: Path) -> None:
        """run_prepare_commit_msg_hook exits 0 when source='message'."""
        from dev_stack.vcs.hooks_runner import run_prepare_commit_msg_hook

        msg_file = git_repo / ".git" / "COMMIT_EDITMSG"
        msg_file.write_text("user message\n")
        result = run_prepare_commit_msg_hook(str(msg_file), source="message")
        assert result == 0

    def test_source_arg_skips_for_amend(self, git_repo: Path) -> None:
        """run_prepare_commit_msg_hook exits 0 when source='commit'."""
        from dev_stack.vcs.hooks_runner import run_prepare_commit_msg_hook

        msg_file = git_repo / ".git" / "COMMIT_EDITMSG"
        msg_file.write_text("amend message\n")
        result = run_prepare_commit_msg_hook(str(msg_file), source="commit", commit_sha="abc123")
        assert result == 0
