"""Unit tests for the dev-stack update command."""
from __future__ import annotations

import tomllib
from pathlib import Path

from click.testing import CliRunner

from dev_stack.cli.main import cli
from dev_stack.manifest import ModuleEntry, create_default, write_manifest


def test_update_requires_manifest() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".git").mkdir()

        result = runner.invoke(cli, ["update"])

        assert result.exit_code == 1
        assert "dev-stack.toml not found" in result.output


def test_update_detects_incomplete_marker() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".git").mkdir()
        manifest = create_default(["hooks"])
        manifest.modules["hooks"].version = "0.0.1"
        write_manifest(manifest, Path("dev-stack.toml"))
        marker = Path(".dev-stack/update-in-progress")
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("pending", encoding="utf-8")

        result = runner.invoke(cli, ["--json", "update"])

        assert result.exit_code == 1
        assert "previous dev-stack update did not complete" in result.output.lower()


def test_update_noop_when_versions_match() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".git").mkdir()
        manifest = create_default(["uv_project", "sphinx_docs", "hooks", "apm", "vcs_hooks"])
        write_manifest(manifest, Path("dev-stack.toml"))

        result = runner.invoke(cli, ["update"])

        assert result.exit_code == 0
        assert "No modules require updates." in result.output


def test_update_prompts_for_new_default_modules() -> None:
    """FR-032: new default modules are offered interactively, never auto-installed."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".git").mkdir()
        # Legacy manifest with only hooks — no uv_project, sphinx_docs, or speckit
        manifest = create_default(["hooks"])
        write_manifest(manifest, Path("dev-stack.toml"))

        # Decline all new module prompts
        result = runner.invoke(cli, ["update"], input="n\nn\nn\nn\n")

        assert result.exit_code == 0
        assert "New modules are available" in result.output
        assert "No new modules selected" in result.output


def test_update_json_mode_skips_new_module_prompt() -> None:
    """In --json mode the interactive prompt must not appear."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".git").mkdir()
        manifest = create_default(["hooks"])
        write_manifest(manifest, Path("dev-stack.toml"))

        result = runner.invoke(cli, ["--json", "update"])

        assert result.exit_code == 0
        assert "New modules are available" not in result.output


# ── T024-T027: Deprecated module handling ──────────────────────────


def test_update_deprecated_module_emits_info_and_no_error() -> None:
    """T024: speckit in manifest → info message emitted, exit 0."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".git").mkdir()
        manifest = create_default(["uv_project", "sphinx_docs", "hooks", "apm", "vcs_hooks"])
        manifest.modules["speckit"] = ModuleEntry(version="0.1.0", installed=True)
        write_manifest(manifest, Path("dev-stack.toml"))

        result = runner.invoke(cli, ["update"])

        assert result.exit_code == 0
        assert "Module 'speckit' has been removed" in result.output
        assert "apm" in result.output.lower()


def test_update_deprecated_module_writes_deprecated_true() -> None:
    """T025: speckit in manifest → deprecated = true written to TOML."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".git").mkdir()
        manifest = create_default(["uv_project", "sphinx_docs", "hooks", "apm", "vcs_hooks"])
        manifest.modules["speckit"] = ModuleEntry(version="0.1.0", installed=True)
        write_manifest(manifest, Path("dev-stack.toml"))

        result = runner.invoke(cli, ["update"])
        assert result.exit_code == 0

        data = tomllib.loads(Path("dev-stack.toml").read_text(encoding="utf-8"))
        assert data["modules"]["speckit"]["deprecated"] is True


def test_update_deprecated_module_with_installed_false() -> None:
    """T026: speckit with installed=false → still marks deprecated."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".git").mkdir()
        manifest = create_default(["uv_project", "sphinx_docs", "hooks", "apm", "vcs_hooks"])
        manifest.modules["speckit"] = ModuleEntry(version="0.1.0", installed=False)
        write_manifest(manifest, Path("dev-stack.toml"))

        result = runner.invoke(cli, ["update"])
        assert result.exit_code == 0

        data = tomllib.loads(Path("dev-stack.toml").read_text(encoding="utf-8"))
        assert data["modules"]["speckit"]["deprecated"] is True
        assert "Module 'speckit' has been removed" in result.output


def test_update_no_speckit_no_deprecation_message() -> None:
    """T027: manifest without speckit → no deprecation message."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".git").mkdir()
        manifest = create_default(["uv_project", "sphinx_docs", "hooks", "apm", "vcs_hooks"])
        write_manifest(manifest, Path("dev-stack.toml"))

        result = runner.invoke(cli, ["update"])
        assert result.exit_code == 0
        assert "deprecated" not in result.output.lower()
        assert "has been removed" not in result.output
