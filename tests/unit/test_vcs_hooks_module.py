"""Unit tests for VcsHooksModule install/uninstall/update/verify lifecycle."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from dev_stack.modules.vcs_hooks import HookEntry, HookManifest, VcsHooksModule


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a minimal repo structure for tests."""
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    ds_dir = tmp_path / ".dev-stack"
    ds_dir.mkdir()
    # Create a minimal pyproject.toml with dev-stack config
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.dev-stack.hooks]\n'
        'commit-msg = true\npre-push = true\npre-commit = false\n'
    )
    return tmp_path


@pytest.fixture
def module(repo: Path) -> VcsHooksModule:
    return VcsHooksModule(repo)


# ---------------------------------------------------------------------------
# HookManifest tests
# ---------------------------------------------------------------------------


class TestHookManifest:
    def test_to_dict_round_trip(self) -> None:
        entry = HookEntry(checksum="abc123", installed_at="2026-01-01T00:00:00Z", template_version="0.1.0")
        manifest = HookManifest(version="1.0", created="2026-01-01T00:00:00Z", updated="2026-01-01T00:00:00Z", hooks={"commit-msg": entry})
        data = manifest.to_dict()
        restored = HookManifest.from_dict(data)
        assert restored.version == "1.0"
        assert "commit-msg" in restored.hooks
        assert restored.hooks["commit-msg"].checksum == "abc123"

    def test_from_dict_empty_hooks(self) -> None:
        data = {"version": "1.0", "created": "now", "updated": "now", "hooks": {}}
        manifest = HookManifest.from_dict(data)
        assert manifest.hooks == {}


# ---------------------------------------------------------------------------
# install() tests
# ---------------------------------------------------------------------------


class TestInstall:
    def test_install_creates_hooks(self, module: VcsHooksModule, repo: Path) -> None:
        result = module.install()
        assert result.success is True
        # commit-msg and pre-push should be installed
        assert (repo / ".git" / "hooks" / "commit-msg").exists()
        assert (repo / ".git" / "hooks" / "pre-push").exists()
        # pre-commit should NOT be installed (disabled in config)
        assert not (repo / ".git" / "hooks" / "pre-commit").exists()

    def test_install_sets_executable_permission(self, module: VcsHooksModule, repo: Path) -> None:
        module.install()
        hook = repo / ".git" / "hooks" / "commit-msg"
        mode = hook.stat().st_mode
        assert mode & stat.S_IXUSR  # owner execute

    def test_install_writes_manifest(self, module: VcsHooksModule, repo: Path) -> None:
        module.install()
        manifest_path = repo / ".dev-stack" / "hooks-manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["version"] == "1.0"
        assert "commit-msg" in data["hooks"]
        assert "pre-push" in data["hooks"]

    def test_install_skips_unmanaged_hook(self, module: VcsHooksModule, repo: Path) -> None:
        """Existing non-managed hook should cause ConflictError."""
        hook = repo / ".git" / "hooks" / "commit-msg"
        hook.write_text("#!/bin/sh\nexit 0\n")
        from dev_stack.errors import ConflictError
        with pytest.raises(ConflictError):
            module.install()

    def test_install_force_overwrites_unmanaged(self, module: VcsHooksModule, repo: Path) -> None:
        hook = repo / ".git" / "hooks" / "commit-msg"
        hook.write_text("#!/bin/sh\nexit 0\n")
        result = module.install(force=True)
        assert result.success is True
        # Hook should now be managed
        content = hook.read_text()
        assert "managed by dev-stack" in content

    def test_install_overwrites_managed_hook(self, module: VcsHooksModule, repo: Path) -> None:
        """Previously managed hooks should be overwritten without force."""
        module.install()
        # Reinstall should succeed (hook is managed)
        result = module.install()
        assert result.success is True

    def test_install_with_pre_commit_enabled(self, repo: Path) -> None:
        """When pre-commit is enabled in config, it should be installed."""
        pyproject = repo / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n\n[tool.dev-stack.hooks]\n'
            'commit-msg = true\npre-push = true\npre-commit = true\n'
        )
        module = VcsHooksModule(repo)
        result = module.install()
        assert result.success
        assert (repo / ".git" / "hooks" / "pre-commit").exists()


# ---------------------------------------------------------------------------
# uninstall() tests
# ---------------------------------------------------------------------------


class TestUninstall:
    def test_uninstall_removes_managed_hooks(self, module: VcsHooksModule, repo: Path) -> None:
        module.install()
        result = module.uninstall()
        assert result.success is True
        assert not (repo / ".git" / "hooks" / "commit-msg").exists()
        assert not (repo / ".git" / "hooks" / "pre-push").exists()

    def test_uninstall_removes_manifest(self, module: VcsHooksModule, repo: Path) -> None:
        module.install()
        module.uninstall()
        assert not (repo / ".dev-stack" / "hooks-manifest.json").exists()

    def test_uninstall_skips_modified_hook(self, module: VcsHooksModule, repo: Path) -> None:
        module.install()
        # Manually modify the hook
        hook = repo / ".git" / "hooks" / "commit-msg"
        hook.write_text(hook.read_text() + "\n# user edit")
        result = module.uninstall()
        assert result.success is True
        assert len(result.warnings) > 0
        assert hook.exists()  # Should not be deleted

    def test_uninstall_no_manifest(self, module: VcsHooksModule, repo: Path) -> None:
        """Uninstall with no manifest should succeed gracefully."""
        result = module.uninstall()
        assert result.success is True


# ---------------------------------------------------------------------------
# update() tests
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_update_unmodified_hook(self, module: VcsHooksModule, repo: Path) -> None:
        module.install()
        result = module.update()
        assert result.success is True

    def test_update_skips_modified_hook(self, module: VcsHooksModule, repo: Path) -> None:
        module.install()
        hook = repo / ".git" / "hooks" / "commit-msg"
        hook.write_text(hook.read_text() + "\n# user edit")
        result = module.update()
        assert result.success is True
        assert any("manually modified" in w for w in result.warnings)

    def test_update_without_manifest_fails(self, module: VcsHooksModule, repo: Path) -> None:
        result = module.update()
        assert result.success is False


# ---------------------------------------------------------------------------
# verify() tests
# ---------------------------------------------------------------------------


class TestVerify:
    def test_verify_healthy(self, module: VcsHooksModule, repo: Path) -> None:
        # Need constitution template and instructions for full health
        (repo / "constitution-template.md").write_text("# Constitution")
        (repo / ".dev-stack" / "instructions.md").write_text("# Instructions")
        module.install()
        status = module.verify()
        assert status.healthy is True
        assert status.issue is None

    def test_verify_not_installed(self, module: VcsHooksModule, repo: Path) -> None:
        status = module.verify()
        assert status.installed is False
        assert status.healthy is False

    def test_verify_missing_hook_file(self, module: VcsHooksModule, repo: Path) -> None:
        (repo / "constitution-template.md").write_text("# Constitution")
        (repo / ".dev-stack" / "instructions.md").write_text("# Instructions")
        module.install()
        # Delete a hook file
        (repo / ".git" / "hooks" / "commit-msg").unlink()
        status = module.verify()
        assert status.healthy is False
        assert "missing" in status.issue

    def test_verify_checksum_mismatch(self, module: VcsHooksModule, repo: Path) -> None:
        (repo / "constitution-template.md").write_text("# Constitution")
        (repo / ".dev-stack" / "instructions.md").write_text("# Instructions")
        module.install()
        # Modify a hook
        hook = repo / ".git" / "hooks" / "commit-msg"
        hook.write_text(hook.read_text() + "\n# modified")
        status = module.verify()
        assert status.healthy is False
        assert "checksum mismatch" in status.issue


# ---------------------------------------------------------------------------
# Agent file creation tests (US1)
# ---------------------------------------------------------------------------


class TestAgentFileCreation:
    """Tests for proactive agent instruction file creation (010)."""

    @pytest.fixture
    def claude_module(self, repo: Path) -> VcsHooksModule:
        return VcsHooksModule(repo, {"agent": {"cli": "claude"}})

    def test_init_creates_agent_file_for_claude(self, claude_module: VcsHooksModule, repo: Path) -> None:
        result = claude_module.install()
        agent_file = repo / "CLAUDE.md"
        assert agent_file.exists()
        content = agent_file.read_text()
        assert "DEV-STACK:BEGIN:DEV-STACK:INSTRUCTIONS" in content
        assert "DEV-STACK:END:DEV-STACK:INSTRUCTIONS" in content

    def test_init_creates_copilot_instructions_with_github_dir(self, repo: Path) -> None:
        module = VcsHooksModule(repo, {"agent": {"cli": "copilot"}})
        module.install()
        agent_file = repo / ".github" / "copilot-instructions.md"
        assert agent_file.exists()
        assert (repo / ".github").is_dir()
        content = agent_file.read_text()
        assert "DEV-STACK:BEGIN:DEV-STACK:INSTRUCTIONS" in content

    def test_init_creates_cursorrules_file(self, repo: Path) -> None:
        module = VcsHooksModule(repo, {"agent": {"cli": "cursor"}})
        module.install()
        agent_file = repo / ".cursorrules"
        assert agent_file.exists()
        content = agent_file.read_text()
        assert "DEV-STACK:BEGIN:DEV-STACK:INSTRUCTIONS" in content

    def test_init_no_agent_skips_agent_file(self, repo: Path) -> None:
        module = VcsHooksModule(repo, {"agent": {"cli": "none"}})
        module.install()
        assert not (repo / "CLAUDE.md").exists()
        assert not (repo / ".github" / "copilot-instructions.md").exists()
        assert not (repo / ".cursorrules").exists()

    def test_init_agent_file_in_files_created(self, claude_module: VcsHooksModule, repo: Path) -> None:
        result = claude_module.install()
        agent_path = repo / "CLAUDE.md"
        assert agent_path in result.files_created

    def test_init_preserves_existing_agent_file_content(self, claude_module: VcsHooksModule, repo: Path) -> None:
        """Brownfield: existing user content is preserved when managed section is added."""
        agent_file = repo / "CLAUDE.md"
        agent_file.write_text("# My Custom Rules\n\nDo not touch my stuff.\n")
        claude_module.install()
        content = agent_file.read_text()
        assert "My Custom Rules" in content
        assert "Do not touch my stuff." in content
        assert "DEV-STACK:BEGIN:DEV-STACK:INSTRUCTIONS" in content

    def test_reinit_updates_managed_section_idempotently(self, claude_module: VcsHooksModule, repo: Path) -> None:
        """Calling install twice should leave exactly one managed section."""
        claude_module.install()
        claude_module.install()
        content = (repo / "CLAUDE.md").read_text()
        assert content.count("DEV-STACK:BEGIN:DEV-STACK:INSTRUCTIONS") == 1
        assert content.count("DEV-STACK:END:DEV-STACK:INSTRUCTIONS") == 1


# ---------------------------------------------------------------------------
# Agent file lifecycle tests (US3)
# ---------------------------------------------------------------------------


class TestAgentFileLifecycle:
    """Tests for update and uninstall of agent instruction files (010 US3)."""

    @pytest.fixture
    def claude_module(self, repo: Path) -> VcsHooksModule:
        return VcsHooksModule(repo, {"agent": {"cli": "claude"}})

    def test_update_refreshes_agent_file_managed_section(self, claude_module: VcsHooksModule, repo: Path) -> None:
        claude_module.install()
        agent_file = repo / "CLAUDE.md"
        assert agent_file.exists()
        # The update should succeed and keep the managed section
        result = claude_module.update()
        assert result.success is True
        content = agent_file.read_text()
        assert "DEV-STACK:BEGIN:DEV-STACK:INSTRUCTIONS" in content

    def test_update_after_agent_switch_creates_new_file(self, repo: Path) -> None:
        """Switching agent creates new file; old file remains."""
        claude_mod = VcsHooksModule(repo, {"agent": {"cli": "claude"}})
        claude_mod.install()
        assert (repo / "CLAUDE.md").exists()
        # Now update with copilot manifest
        copilot_mod = VcsHooksModule(repo, {"agent": {"cli": "copilot"}})
        result = copilot_mod.update()
        assert result.success is True
        assert (repo / ".github" / "copilot-instructions.md").exists()
        # Old claude file should still exist untouched
        assert (repo / "CLAUDE.md").exists()

    def test_uninstall_deletes_devstack_only_agent_file(self, claude_module: VcsHooksModule, repo: Path) -> None:
        """Agent file with only managed content gets deleted on uninstall."""
        claude_module.install()
        agent_file = repo / "CLAUDE.md"
        assert agent_file.exists()
        result = claude_module.uninstall()
        assert result.success is True
        assert not agent_file.exists()
        assert agent_file in result.files_deleted

    def test_uninstall_preserves_user_content_in_agent_file(self, claude_module: VcsHooksModule, repo: Path) -> None:
        """Agent file with user content should keep file but remove managed section."""
        claude_module.install()
        agent_file = repo / "CLAUDE.md"
        # Append user content outside the managed block
        original = agent_file.read_text()
        agent_file.write_text(original + "\n# My custom rules\n")
        result = claude_module.uninstall()
        assert result.success is True
        assert agent_file.exists()
        content = agent_file.read_text()
        assert "My custom rules" in content
        assert "DEV-STACK:BEGIN:DEV-STACK:INSTRUCTIONS" not in content
