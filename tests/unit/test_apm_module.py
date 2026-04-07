"""Unit tests for APMModule install flow and helpers."""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dev_stack.modules.apm import APMModule, LOCKFILE, MANIFEST_FILE


@pytest.fixture()
def apm(tmp_path: Path) -> APMModule:
    return APMModule(tmp_path)


# ── _check_apm_cli ──────────────────────────────────────────────────


class TestCheckApmCli:
    def test_apm_found_good_version(self, apm: APMModule) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/apm"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "--version"], returncode=0, stdout="apm 0.9.0\n", stderr=""
            )
            ok, msg = apm._check_apm_cli()
            assert ok is True
            assert "0.9.0" in msg

    def test_apm_not_found(self, apm: APMModule) -> None:
        with patch("shutil.which", return_value=None):
            ok, msg = apm._check_apm_cli()
            assert ok is False
            assert "not found" in msg.lower()

    def test_apm_version_too_old(self, apm: APMModule) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/apm"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "--version"], returncode=0, stdout="apm 0.5.0\n", stderr=""
            )
            ok, msg = apm._check_apm_cli()
            assert ok is False
            assert "below minimum" in msg.lower()

    def test_apm_ansi_decorated_version(self, apm: APMModule) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/apm"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "--version"], returncode=0,
                stdout="\x1b[1m0.9.0\x1b[0m\n", stderr=""
            )
            ok, msg = apm._check_apm_cli()
            assert ok is True
            assert "0.9.0" in msg

    def test_apm_rich_box_drawing_version(self, apm: APMModule) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/apm"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "--version"], returncode=0,
                stdout="╭─ apm v0.9.0 ─╮\n", stderr=""
            )
            ok, msg = apm._check_apm_cli()
            assert ok is True
            assert "0.9.0" in msg

    def test_apm_no_semver_match(self, apm: APMModule) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/apm"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "--version"], returncode=0,
                stdout="apm (no version)\n", stderr=""
            )
            ok, msg = apm._check_apm_cli()
            assert ok is False
            assert "could not parse" in msg.lower()


# ── _bootstrap_manifest ─────────────────────────────────────────────


class TestBootstrapManifest:
    def test_create_when_missing(self, apm: APMModule) -> None:
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        assert manifest_path.exists()
        content = yaml.safe_load(manifest_path.read_text())
        assert "dependencies" in content
        assert len(content["dependencies"]["mcp"]) == 3

    def test_skip_when_exists(self, apm: APMModule) -> None:
        # Pre-create manifest
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text("name: existing\n")
        manifest_path = apm._bootstrap_manifest(force=False, strategy="skip")
        assert manifest_path.read_text() == "name: existing\n"

    def test_overwrite_when_exists(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text("name: existing\n")
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        content = yaml.safe_load(manifest_path.read_text())
        assert len(content["dependencies"]["mcp"]) == 3

    def test_merge_adds_missing_defaults(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {
                "mcp": [
                    "io.github.github/github-mcp-server",
                    "ghcr.io/custom/my-server",
                ]
            }
        }))
        manifest_path = apm._bootstrap_manifest(force=False, strategy="merge")
        content = yaml.safe_load(manifest_path.read_text())
        mcp_list = content["dependencies"]["mcp"]
        # Original 2 + 2 missing defaults = 4
        assert len(mcp_list) == 4
        # Custom server preserved
        assert "ghcr.io/custom/my-server" in mcp_list

    def test_force_overwrites_existing(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text("name: existing\n")
        manifest_path = apm._bootstrap_manifest(force=True)
        content = yaml.safe_load(manifest_path.read_text())
        assert len(content["dependencies"]["mcp"]) == 3

    def test_ci_noninteractive_defaults_to_skip(self, apm: APMModule) -> None:
        """In non-interactive mode, _bootstrap_manifest defaults to skip."""
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text("name: existing\n")
        with patch("click.get_text_stream") as mock_stream:
            mock_stream.return_value.isatty.return_value = False
            manifest_path = apm._bootstrap_manifest(force=False)
            assert manifest_path.read_text() == "name: existing\n"


# ── install ─────────────────────────────────────────────────────────


class TestInstall:
    def test_install_success(self, apm: APMModule) -> None:
        with patch.object(apm, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(apm, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "install"], returncode=0, stdout="All installed\n", stderr=""
            )
            # Create lockfile to simulate APM output
            (apm.repo_root / LOCKFILE).write_text("lockfile_version: '1.0'\n")
            result = apm.install()
            assert result.success is True

    def test_install_cli_missing(self, apm: APMModule) -> None:
        with patch.object(apm, "_check_apm_cli", return_value=(False, "APM CLI not found")):
            result = apm.install()
            assert result.success is False
            assert "not found" in result.message.lower()

    def test_install_partial_failure(self, apm: APMModule) -> None:
        with patch.object(apm, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(apm, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "install"],
                returncode=1,
                stdout="",
                stderr="Error: package notebooklm-mcp not found in registry\n",
            )
            result = apm.install()
            assert result.success is False
            assert len(result.warnings) > 0


# ── _parse_install_result ───────────────────────────────────────────


class TestParseInstallResult:
    def test_all_pass(self, apm: APMModule) -> None:
        manifest_path = apm.repo_root / MANIFEST_FILE
        manifest_path.write_text("name: test\n")
        (apm.repo_root / LOCKFILE).write_text("lockfile_version: '1.0'\n")
        result_cp = subprocess.CompletedProcess(
            args=["apm", "install"], returncode=0, stdout="All installed\n", stderr=""
        )
        result = apm._parse_install_result(result_cp, manifest_path)
        assert result.success is True
        assert len(result.files_created) == 2  # manifest + lockfile

    def test_partial_failure(self, apm: APMModule) -> None:
        manifest_path = apm.repo_root / MANIFEST_FILE
        manifest_path.write_text("name: test\n")
        result_cp = subprocess.CompletedProcess(
            args=["apm", "install"],
            returncode=1,
            stdout="",
            stderr="Error: notebooklm-mcp not found\nError: huggingface-mcp failed",
        )
        result = apm._parse_install_result(result_cp, manifest_path)
        assert result.success is False
        assert len(result.warnings) == 2

    def test_full_failure(self, apm: APMModule) -> None:
        manifest_path = apm.repo_root / MANIFEST_FILE
        manifest_path.write_text("name: test\n")
        result_cp = subprocess.CompletedProcess(
            args=["apm", "install"], returncode=2, stdout="", stderr="Fatal: network error"
        )
        result = apm._parse_install_result(result_cp, manifest_path)
        assert result.success is False
        assert "Fatal: network error" in result.warnings


# ── verify (lockfile staleness) ─────────────────────────────────────


class TestVerifyLockfileStaleness:
    """T014: Verify lockfile staleness detection in verify()."""

    def _make_apm_with_cli(self, tmp_path: Path) -> APMModule:
        """Return an APMModule with _check_apm_cli patched to always succeed."""
        module = APMModule(tmp_path)
        return module

    def test_lockfile_newer_than_manifest_is_clean(self, tmp_path: Path) -> None:
        module = self._make_apm_with_cli(tmp_path)
        manifest = tmp_path / MANIFEST_FILE
        lockfile = tmp_path / LOCKFILE
        manifest.write_text("name: test\n")
        time.sleep(0.05)
        lockfile.write_text("lockfile_version: '1.0'\n")
        with patch.object(module, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")):
            status = module.verify()
        assert status.installed is True
        assert status.healthy is True
        assert status.issue is None

    def test_lockfile_older_than_manifest_is_stale(self, tmp_path: Path) -> None:
        module = self._make_apm_with_cli(tmp_path)
        lockfile = tmp_path / LOCKFILE
        lockfile.write_text("lockfile_version: '1.0'\n")
        time.sleep(0.05)
        manifest = tmp_path / MANIFEST_FILE
        manifest.write_text("name: test\n")
        with patch.object(module, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")):
            status = module.verify()
        assert status.installed is True
        assert status.healthy is False
        assert "stale" in status.issue.lower()

    def test_lockfile_missing_warning(self, tmp_path: Path) -> None:
        module = self._make_apm_with_cli(tmp_path)
        manifest = tmp_path / MANIFEST_FILE
        manifest.write_text("name: test\n")
        with patch.object(module, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")):
            status = module.verify()
        assert status.installed is True
        assert status.healthy is False
        assert LOCKFILE in status.issue

    def test_apm_cli_missing_returns_unhealthy(self, tmp_path: Path) -> None:
        module = APMModule(tmp_path)
        with patch.object(module, "_check_apm_cli", return_value=(False, "APM CLI not found")):
            status = module.verify()
        assert status.installed is False
        assert status.healthy is False

    def test_manifest_missing_returns_not_installed(self, tmp_path: Path) -> None:
        module = APMModule(tmp_path)
        with patch.object(module, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")):
            status = module.verify()
        assert status.installed is False


# ── DEFAULT_GREENFIELD_MODULES ──────────────────────────────────────


class TestDefaultModules:
    """T019: Verify apm is in defaults and mcp_servers is not."""

    def test_apm_in_default_greenfield_modules(self) -> None:
        from dev_stack.modules import DEFAULT_GREENFIELD_MODULES
        assert "apm" in DEFAULT_GREENFIELD_MODULES

    def test_mcp_servers_not_in_default_greenfield_modules(self) -> None:
        from dev_stack.modules import DEFAULT_GREENFIELD_MODULES
        assert "mcp-servers" not in DEFAULT_GREENFIELD_MODULES
        assert "mcp_servers" not in DEFAULT_GREENFIELD_MODULES


# ── audit ───────────────────────────────────────────────────────────


class TestAudit:
    """T023: Unit tests for audit() method."""

    def test_audit_clean_scan(self, apm: APMModule) -> None:
        with patch.object(apm, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(apm, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "audit"], returncode=0, stdout="No findings\n", stderr=""
            )
            result = apm.audit()
            assert result.success is True
            assert "clean" in result.message.lower()

    def test_audit_findings_detected(self, apm: APMModule) -> None:
        with patch.object(apm, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(apm, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "audit"],
                returncode=1,
                stdout="",
                stderr="Critical: bidi override found in config file",
            )
            result = apm.audit()
            assert result.success is False
            assert len(result.warnings) > 0

    def test_audit_passes_format_option(self, apm: APMModule) -> None:
        with patch.object(apm, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(apm, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "audit", "-f", "json"], returncode=0, stdout="{}\n", stderr=""
            )
            apm.audit(fmt="json")
            mock_run.assert_called_once_with(["audit", "-f", "json"])


# ── Expanded apm.yml template (014-apm-module-swap) ─────────────────


class TestExpandedTemplate:
    """T018: Verify expanded template contains both dependencies.mcp and dependencies.apm."""

    def test_template_contains_mcp_and_apm_sections(self, apm: APMModule) -> None:
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        content = yaml.safe_load(manifest_path.read_text())
        assert "dependencies" in content
        assert "mcp" in content["dependencies"]
        assert "apm" in content["dependencies"]

    def test_template_preserves_all_mcp_servers(self, apm: APMModule) -> None:
        """All default MCP servers must be present in the template."""
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        content = yaml.safe_load(manifest_path.read_text())
        mcp_list = content["dependencies"]["mcp"]
        assert len(mcp_list) == 3
        for server in APMModule.DEFAULT_SERVERS:
            assert server in mcp_list

    def test_template_contains_agent_skills(self, apm: APMModule) -> None:
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        content = yaml.safe_load(manifest_path.read_text())
        apm_list = content["dependencies"]["apm"]
        assert len(apm_list) == 1
        # Entry is pinned to a specific SHA; check base package name only.
        assert any(
            entry.split("#")[0] == "lucasflores/agent-skills" for entry in apm_list
        )

    def test_template_apm_packages_format(self, apm: APMModule) -> None:
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        content = yaml.safe_load(manifest_path.read_text())
        for entry in content["dependencies"]["apm"]:
            assert "/" in entry, f"APM package '{entry}' should use org/repo format"


# ── Merge manifest with dependencies.apm (014-apm-module-swap) ──────


class TestMergeManifestApm:
    """T019: Verify _merge_manifest() handles dependencies.apm without duplicates."""

    def test_merge_adds_apm_section_to_existing_manifest(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {
                "mcp": ["io.github.github/github-mcp-server"],
            }
        }))
        apm._merge_manifest(existing)
        content = yaml.safe_load(existing.read_text())
        assert "apm" in content["dependencies"]
        assert len(content["dependencies"]["apm"]) == 1

    def test_merge_does_not_duplicate_existing_apm_packages(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {
                "mcp": [],
                "apm": ["lucasflores/agent-skills"],
            }
        }))
        apm._merge_manifest(existing)
        content = yaml.safe_load(existing.read_text())
        apm_list = content["dependencies"]["apm"]
        agent_skills_entries = [e for e in apm_list if "agent-skills" in e]
        assert len(agent_skills_entries) == 1
        assert len(apm_list) == 1

    def test_merge_preserves_custom_apm_packages(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {
                "mcp": [],
                "apm": ["custom/my-package#v1.0"],
            }
        }))
        apm._merge_manifest(existing)
        content = yaml.safe_load(existing.read_text())
        apm_list = content["dependencies"]["apm"]
        assert "custom/my-package#v1.0" in apm_list
        assert len(apm_list) == 2  # custom + agent-skills


# ── audit (continued) ───────────────────────────────────────────────


class TestAuditContinued:
    def test_audit_passes_output_file(self, apm: APMModule, tmp_path: Path) -> None:
        output = tmp_path / "report.sarif"
        with patch.object(apm, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(apm, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "audit", "-f", "sarif", "-o", str(output)],
                returncode=0, stdout="", stderr=""
            )
            apm.audit(fmt="sarif", output=output)
            mock_run.assert_called_once_with(["audit", "-f", "sarif", "-o", str(output)])

    def test_audit_cli_missing(self, apm: APMModule) -> None:
        with patch.object(apm, "_check_apm_cli", return_value=(False, "APM CLI not found")):
            result = apm.audit()
            assert result.success is False
            assert "not found" in result.message.lower()
