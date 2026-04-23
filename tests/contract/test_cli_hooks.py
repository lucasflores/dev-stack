"""Contract tests for ``hooks status`` JSON schema compliance."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dev_stack.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def repo_with_hooks(tmp_path: Path) -> Path:
    """Create a repo with installed hooks for contract testing."""
    import subprocess

    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.dev-stack.hooks]\n'
        'commit-msg = true\npre-push = true\npre-commit = false\n'
    )
    (tmp_path / ".dev-stack").mkdir(exist_ok=True)

    from dev_stack.modules.vcs_hooks import VcsHooksModule

    module = VcsHooksModule(tmp_path)
    module.install()
    return tmp_path


class TestHooksStatusJsonSchema:
    """Validate ``dev-stack hooks status --json`` output matches cli-contract.md."""

    def test_json_output_schema_with_installed_hooks(
        self, runner: CliRunner, repo_with_hooks: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(repo_with_hooks)
        result = runner.invoke(cli, ["--json", "hooks", "status"], catch_exceptions=False)

        assert result.exit_code == 0
        data = json.loads(result.output)

        # Top-level fields
        assert data["status"] in ("healthy", "degraded", "not_installed")
        assert "manifest_path" in data
        assert isinstance(data["hooks"], list)

        # Check each hook entry
        for hook in data["hooks"]:
            assert "name" in hook
            assert "installed" in hook
            if hook["installed"]:
                assert "path" in hook
                assert "checksum_expected" in hook
                assert "checksum_actual" in hook
                assert "modified" in hook
                assert "installed_at" in hook
                assert "template_version" in hook
            else:
                assert "configured" in hook

    def test_json_output_status_healthy(
        self, runner: CliRunner, repo_with_hooks: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(repo_with_hooks)
        result = runner.invoke(cli, ["--json", "hooks", "status"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["status"] == "healthy"

    def test_json_output_not_installed(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without hooks installed, status should be not_installed."""
        import subprocess

        subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\n')

        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["--json", "hooks", "status"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["status"] == "not_installed"
        assert all(not h["installed"] for h in data["hooks"])

    def test_json_output_degraded_when_hook_modified(
        self, runner: CliRunner, repo_with_hooks: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Modify a hook
        hook = repo_with_hooks / ".git" / "hooks" / "commit-msg"
        hook.write_text(hook.read_text() + "\n# modified")

        monkeypatch.chdir(repo_with_hooks)
        result = runner.invoke(cli, ["--json", "hooks", "status"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["status"] == "degraded"
        # Find the modified hook
        modified_hooks = [h for h in data["hooks"] if h.get("modified")]
        assert len(modified_hooks) >= 1


class TestPrepareCommitMsgHookInstallation:
    """Contract: prepare-commit-msg template is installed alongside pre-commit."""

    def test_prepare_commit_msg_installed_with_pre_commit(self, tmp_path: Path) -> None:
        """When pre-commit is enabled, prepare-commit-msg must also be installed."""
        import subprocess

        subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n\n[tool.dev-stack.hooks]\n'
            'commit-msg = true\npre-push = true\npre-commit = true\n'
        )
        (tmp_path / ".dev-stack").mkdir(exist_ok=True)

        from dev_stack.modules.vcs_hooks import VcsHooksModule

        module = VcsHooksModule(tmp_path)
        result = module.install()
        assert result.success

        pcm_hook = tmp_path / ".git" / "hooks" / "prepare-commit-msg"
        assert pcm_hook.exists(), "prepare-commit-msg hook must be installed"

        # Verify manifest includes it
        manifest_data = json.loads(
            (tmp_path / ".dev-stack" / "hooks-manifest.json").read_text()
        )
        assert "prepare-commit-msg" in manifest_data["hooks"]

    def test_template_exists_in_package(self) -> None:
        """The prepare-commit-msg templates must exist in the package."""
        from dev_stack.modules.vcs_hooks import HOOK_TEMPLATE_DIR

        assert (HOOK_TEMPLATE_DIR / "prepare-commit-msg").exists()
        assert (HOOK_TEMPLATE_DIR / "prepare-commit-msg.py").exists()


class TestHooksRunCommand:
    def test_pre_commit_dispatches_to_hooks_runner(self, runner: CliRunner) -> None:
        with patch("dev_stack.vcs.hooks_runner.run_pre_commit_hook", return_value=0) as mocked:
            result = runner.invoke(cli, ["hooks", "run", "pre-commit"], catch_exceptions=False)

        assert result.exit_code == 0
        mocked.assert_called_once_with()

    def test_prepare_commit_msg_dispatches_to_hooks_runner(self, runner: CliRunner) -> None:
        with patch("dev_stack.vcs.hooks_runner.run_prepare_commit_msg_hook", return_value=0) as mocked:
            result = runner.invoke(
                cli,
                ["hooks", "run", "prepare-commit-msg", "COMMIT_EDITMSG"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        mocked.assert_called_once_with("COMMIT_EDITMSG", source=None, commit_sha=None)

    def test_prepare_commit_msg_requires_message_file(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["hooks", "run", "prepare-commit-msg"], catch_exceptions=False)
        assert result.exit_code == 2
