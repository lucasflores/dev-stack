"""Integration tests for the dev-stack update command."""
from __future__ import annotations

import stat
from pathlib import Path

from click.testing import CliRunner

from dev_stack.cli.main import cli
from dev_stack.manifest import read_manifest, write_manifest
from dev_stack.modules.hooks import HooksModule


def test_update_reinstalls_modules_and_refreshes_manifest() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
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
