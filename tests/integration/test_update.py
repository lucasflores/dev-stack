"""Integration tests for the dev-stack update command."""
from __future__ import annotations

import stat
import tomllib
from pathlib import Path

from click.testing import CliRunner

from dev_stack.cli.main import cli
from dev_stack.manifest import ModuleEntry, read_manifest, write_manifest
from dev_stack.modules.hooks import HooksModule


def test_update_reinstalls_modules_and_refreshes_manifest() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Simulate a Python project so stack profile includes Python modules
        Path("setup.py").write_text("# placeholder")
        init_result = runner.invoke(cli, ["init"])
        assert init_result.exit_code == 0, init_result.output

        manifest_path = Path("dev-stack.toml")
        hook_script = Path("scripts/hooks/pre-commit")
        assert manifest_path.exists()
        assert hook_script.exists()

        # Simulate an outdated stack by downgrading the manifest and removing the hook.
        manifest = read_manifest(manifest_path)
        manifest.modules["hooks"].version = "0.0.1"
        write_manifest(manifest, manifest_path)
        hook_script.unlink()

        update_result = runner.invoke(cli, ["update"])
        assert update_result.exit_code == 0, update_result.output

        updated_manifest = read_manifest(manifest_path)
        assert updated_manifest.modules["hooks"].version == HooksModule.VERSION
        assert hook_script.exists()
        assert hook_script.stat().st_mode & stat.S_IXUSR
        content = hook_script.read_text(encoding="utf-8")
        assert content
        assert content.startswith("#!")
        assert not Path(".dev-stack/update-in-progress").exists()


def test_update_handles_downstream_speckit_manifest() -> None:
    """T028/FR-009: downstream manifest with [modules.speckit] updates cleanly."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Simulate a Python project so stack profile includes Python modules
        Path("setup.py").write_text("# placeholder")
        # Bootstrap a working project first.
        init_result = runner.invoke(cli, ["init"])
        assert init_result.exit_code == 0, init_result.output

        # Inject [modules.speckit] to mimic a downstream project.
        manifest = read_manifest(Path("dev-stack.toml"))
        manifest.modules["speckit"] = ModuleEntry(version="0.1.0", installed=True)
        write_manifest(manifest, Path("dev-stack.toml"))

        # Run update — should handle speckit gracefully.
        update_result = runner.invoke(cli, ["update"])
        assert update_result.exit_code == 0, update_result.output
        assert "Module 'speckit' has been removed" in update_result.output

        # Verify deprecated flag persisted.
        data = tomllib.loads(Path("dev-stack.toml").read_text(encoding="utf-8"))
        assert data["modules"]["speckit"]["deprecated"] is True
