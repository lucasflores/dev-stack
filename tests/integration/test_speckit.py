"""Integration tests for Spec Kit module."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from dev_stack.cli.main import cli


def _write_fake_uv(bin_dir: Path) -> None:
    script = """#!/usr/bin/env bash
set -e
if [[ "$1" == "tool" && "$2" == "install" && "$3" == "spec-kit" ]]; then
    exit 0
fi
if [[ "$1" == "tool" && "$2" == "run" && "$3" == "spec-kit" ]]; then
    shift 3
    if [[ "$1" == "--" ]]; then
        shift
    fi
    if [[ "$1" == "--version" ]]; then
        echo "spec-kit 0.0-test"
        exit 0
    fi
fi
exit 0
"""
    uv_path = bin_dir / "uv"
    uv_path.write_text(script, encoding="utf-8")
    uv_path.chmod(0o755)


def test_specify_scaffold_and_cli_available() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        fake_bin = Path("fake-bin")
        fake_bin.mkdir()
        _write_fake_uv(fake_bin)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

        result = runner.invoke(cli, ["init"], env=env)
        assert result.exit_code == 0, result.output

        specify_root = Path(".specify")
        assert (specify_root / "memory/constitution.md").exists()
        assert (specify_root / "templates/plan-template.md").exists()
        assert (specify_root / "scripts/bash/check-prerequisites.sh").exists()

        shim_path = Path(".dev-stack/bin/specify")
        assert shim_path.exists()

        env_for_specify = env.copy()
        env_for_specify["PATH"] = f"{shim_path.parent}:{fake_bin}:{env_for_specify.get('PATH', '')}"
        proc = subprocess.run(
            ["specify", "--version"],
            capture_output=True,
            text=True,
            env=env_for_specify,
        )
        assert proc.returncode == 0
        assert "spec-kit" in proc.stdout.strip()

        # LazySpecKit prompt installed
        prompt_path = Path(".github/prompts/LazySpecKit.prompt.md")
        assert prompt_path.exists(), "LazySpecKit prompt not installed"
        assert prompt_path.stat().st_size > 0

        # Vendored reviewers installed
        reviewers_dir = Path(".lazyspeckit/reviewers")
        assert reviewers_dir.is_dir(), ".lazyspeckit/reviewers directory missing"
        reviewer_files = list(reviewers_dir.glob("*.md"))
        # At minimum the 2 vendored reviewers (code-quality.md, test.md) must be present
        vendored_names = {"code-quality.md", "test.md"}
        installed_names = {f.name for f in reviewer_files}
        assert vendored_names.issubset(installed_names), (
            f"Missing vendored reviewers: {vendored_names - installed_names}"
        )