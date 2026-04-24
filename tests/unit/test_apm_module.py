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
        assert "mcp" not in content["dependencies"]
        assert len(content["dependencies"]["apm"]) == 4

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
        assert "mcp" not in content["dependencies"]
        assert len(content["dependencies"]["apm"]) == 4

    def test_merge_adds_missing_defaults(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {}
        }))
        manifest_path = apm._bootstrap_manifest(force=False, strategy="merge")
        content = yaml.safe_load(manifest_path.read_text())
        # DEFAULT_SERVERS is empty — no mcp key should appear
        assert "mcp" not in content["dependencies"]
        # All 4 default apm entries added
        assert len(content["dependencies"]["apm"]) == 4

    def test_force_overwrites_existing(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text("name: existing\n")
        manifest_path = apm._bootstrap_manifest(force=True)
        content = yaml.safe_load(manifest_path.read_text())
        assert "mcp" not in content["dependencies"]
        assert len(content["dependencies"]["apm"]) == 4

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
    """T018: Verify expanded template contains dependencies.apm and no dependencies.mcp."""

    def test_template_contains_mcp_and_apm_sections(self, apm: APMModule) -> None:
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        content = yaml.safe_load(manifest_path.read_text())
        assert "dependencies" in content
        assert "mcp" not in content["dependencies"]
        assert "apm" in content["dependencies"]
        assert content["version"] == "2.0.0"  # SC-003

    def test_template_has_no_mcp_servers(self, apm: APMModule) -> None:
        """Template must contain no MCP server entries (DEFAULT_SERVERS is empty)."""
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        content = yaml.safe_load(manifest_path.read_text())
        assert "mcp" not in content["dependencies"]
        assert APMModule.DEFAULT_SERVERS == ()

    def test_template_contains_agent_skills(self, apm: APMModule) -> None:
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        content = yaml.safe_load(manifest_path.read_text())
        apm_list = content["dependencies"]["apm"]
        assert len(apm_list) == 4
        expected = [
            "lucasflores/agent-skills/agents/idea-to-speckit.agent.md",
            "lucasflores/agent-skills/prompts/AutoSpecKit.prompt.md",
            "lucasflores/agent-skills/skills/commit-pipeline",
            "lucasflores/agent-skills/skills/dev-stack-update",
        ]
        for entry in expected:
            assert entry in apm_list

    def test_template_apm_packages_format(self, apm: APMModule) -> None:
        manifest_path = apm._bootstrap_manifest(force=False, strategy="overwrite")
        content = yaml.safe_load(manifest_path.read_text())
        for entry in content["dependencies"]["apm"]:
            # Each entry must use owner/repo/path format (at least 3 slash-separated segments)
            parts = entry.split("/")
            assert len(parts) >= 3, f"APM package '{entry}' should use owner/repo/path format"


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
        # User's existing mcp entry is preserved; no defaults added (DEFAULT_SERVERS is empty)
        assert len(content["dependencies"]["mcp"]) == 1
        # All 4 default apm path entries added
        assert len(content["dependencies"]["apm"]) == 4

    def test_merge_does_not_duplicate_existing_apm_packages(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        # Pre-populate with one of the four default path entries
        existing.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {
                "apm": ["lucasflores/agent-skills/skills/commit-pipeline"],
            }
        }))
        apm._merge_manifest(existing)
        content = yaml.safe_load(existing.read_text())
        apm_list = content["dependencies"]["apm"]
        commit_pipeline_entries = [e for e in apm_list if "commit-pipeline" in e]
        assert len(commit_pipeline_entries) == 1
        # 1 pre-existing + 3 new = 4 total
        assert len(apm_list) == 4

    def test_merge_preserves_custom_apm_packages(self, apm: APMModule) -> None:
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {
                "apm": ["custom/my-package#v1.0"],
            }
        }))
        apm._merge_manifest(existing)
        content = yaml.safe_load(existing.read_text())
        apm_list = content["dependencies"]["apm"]
        assert "custom/my-package#v1.0" in apm_list
        assert len(apm_list) == 5  # 1 custom + 4 path defaults

    def test_merge_empty_mcp_key_omitted(self, apm: APMModule) -> None:
        """When manifest has no mcp section and DEFAULT_SERVERS is empty, mcp key is not written."""
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {}
        }))
        apm._merge_manifest(existing)
        content = yaml.safe_load(existing.read_text())
        assert "mcp" not in content["dependencies"]

    def test_merge_no_mcp_added_from_empty_defaults(self, apm: APMModule) -> None:
        """DEFAULT_SERVERS is empty: merge on a blank manifest produces no mcp key."""
        assert APMModule.DEFAULT_SERVERS == ()
        existing = apm.repo_root / MANIFEST_FILE
        existing.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {}
        }))
        apm._merge_manifest(existing)
        content = yaml.safe_load(existing.read_text())
        assert "mcp" not in content["dependencies"]


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
