"""Contract tests for ``hooks status`` JSON schema compliance."""
from __future__ import annotations

import json
import os
from pathlib import Path

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
