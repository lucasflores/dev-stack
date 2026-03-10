"""Integration tests for dev-stack init."""
from __future__ import annotations

import stat
import subprocess
import tomllib
from pathlib import Path

from click.testing import CliRunner

from dev_stack.cli.main import cli


def test_greenfield_init_creates_expected_files() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0, result.output

        manifest_path = Path("dev-stack.toml")
        assert manifest_path.exists()
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["stack"]["version"] == "0.1.0"
        assert manifest["modules"]["hooks"]["installed"] is True

        # UV project artifacts
        assert manifest["modules"]["uv_project"]["installed"] is True
        assert Path("pyproject.toml").exists()

        # Sphinx docs artifacts
        assert manifest["modules"]["sphinx_docs"]["installed"] is True
        assert Path("docs/conf.py").exists()
        assert Path("docs/index.rst").exists()
        assert Path("docs/Makefile").exists()

        hook_script = Path("scripts/hooks/pre-commit")
        git_hook = Path(".git/hooks/pre-commit")
        config_file = Path(".pre-commit-config.yaml")
        assert hook_script.exists()
        assert git_hook.exists()
        assert config_file.exists()
        assert hook_script.stat().st_mode & stat.S_IXUSR
        assert git_hook.stat().st_mode & stat.S_IXUSR

        # Idempotency: running again with --force should not change manifest content
        before = manifest_path.read_text(encoding="utf-8")
        result_second = runner.invoke(cli, ["init", "--force"])
        assert result_second.exit_code == 0, result_second.output
        after = manifest_path.read_text(encoding="utf-8")
        assert before == after


def test_greenfield_predecessor_creates_tests_and_deps() -> None:
    """T015: uv init --package → dev-stack init → tests exist, deps in pyproject.toml."""
    import shutil

    if not shutil.which("uv"):
        import pytest

        pytest.skip("uv CLI not available")

    runner = CliRunner()
    with runner.isolated_filesystem():
        # Simulate greenfield predecessor: git init + uv init --package
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True)
        subprocess.run(["uv", "init", "--package"], check=True, capture_output=True)

        assert Path("pyproject.toml").exists()
        assert not Path("tests").exists()  # uv init --package doesn't create tests/

        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0, result.output

        # Verify tests scaffold created (US1)
        assert Path("tests/__init__.py").exists()
        assert Path("tests/test_placeholder.py").exists()

        # Verify dev dependencies in pyproject.toml (US2)
        with open("pyproject.toml", "rb") as fh:
            data = tomllib.load(fh)
        opt_deps = data.get("project", {}).get("optional-dependencies", {})
        assert "dev" in opt_deps
        assert "docs" in opt_deps
        assert any("ruff" in dep for dep in opt_deps["dev"])
        assert any("pytest" in dep for dep in opt_deps["dev"])
        assert any("mypy" in dep for dep in opt_deps["dev"])

        # Verify tool config sections added
        tool = data.get("tool", {})
        assert "ruff" in tool
        assert "pytest" in tool
        assert "mypy" in tool