"""Integration tests for APM install with community packages."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from dev_stack.modules.apm import APMModule, LOCKFILE, MANIFEST_FILE


@pytest.fixture()
def apm(tmp_path: Path) -> APMModule:
    return APMModule(tmp_path)


class TestCommunityPackages:
    """T016: Community packages install alongside defaults; unknown packages produce clear errors."""

    def test_community_package_in_manifest_passes_to_apm(self, apm: APMModule) -> None:
        """A user-added community package in apm.yml is passed to apm install."""
        manifest = apm.repo_root / MANIFEST_FILE
        manifest.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {
                "mcp": [
                    "io.github.upstash/context7",
                    "ghcr.io/community/custom-mcp-server",
                ]
            }
        }))
        (apm.repo_root / LOCKFILE).write_text("lockfile_version: '1.0'\n")

        with patch.object(apm, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(apm, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "install"], returncode=0, stdout="Installed 2 packages\n", stderr=""
            )
            # install with force to skip prompt for existing manifest
            result = apm.install(force=True)
            assert result.success is True
            mock_run.assert_called_once_with(["install"])

    def test_unknown_package_produces_clear_error(self, apm: APMModule) -> None:
        """APM returns a non-zero exit with package-not-found; _parse_install_result surfaces it."""
        manifest = apm.repo_root / MANIFEST_FILE
        manifest.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {
                "mcp": ["ghcr.io/nonexistent/fake-mcp-server"]
            }
        }))

        with patch.object(apm, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(apm, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "install"],
                returncode=1,
                stdout="",
                stderr="Error: package 'ghcr.io/nonexistent/fake-mcp-server' not found in registry\n",
            )
            result = apm.install(force=True)
            assert result.success is False
            assert any("fake-mcp-server" in w for w in result.warnings)

    def test_merge_preserves_community_packages(self, apm: APMModule) -> None:
        """Merge strategy preserves user-added community packages while adding defaults."""
        manifest = apm.repo_root / MANIFEST_FILE
        manifest.write_text(yaml.dump({
            "name": "myproject",
            "version": "1.0.0",
            "dependencies": {
                "mcp": ["ghcr.io/community/my-mcp-server"]
            }
        }))

        with patch.object(apm, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(apm, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "install"], returncode=0, stdout="Installed\n", stderr=""
            )
            (apm.repo_root / LOCKFILE).write_text("lockfile_version: '1.0'\n")
            apm._bootstrap_manifest(force=False, strategy="merge")
            content = yaml.safe_load(manifest.read_text())
            mcp_list = content["dependencies"]["mcp"]
            # Community + 3 defaults = 4
            assert len(mcp_list) == 4
            assert "ghcr.io/community/my-mcp-server" in mcp_list


class TestFullPipelineIntegration:
    """T026: Full init pipeline with APM module — idempotency and reproducibility."""

    def _make_successful_apm(self, tmp_path: Path) -> APMModule:
        module = APMModule(tmp_path)
        return module

    def _mock_apm_install_success(self, module: APMModule) -> None:
        """Side-effect helper: simulate APM creating a lockfile."""
        lockfile = module.repo_root / LOCKFILE
        lockfile.write_text("lockfile_version: '1.0'\ngenerated_at: '2026-03-24T10:00:00Z'\n")

    def test_idempotency_second_install_produces_no_changes(self, tmp_path: Path) -> None:
        """Running install twice — second run produces same result (no changes)."""
        module = self._make_successful_apm(tmp_path)

        with patch.object(module, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(module, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "install"], returncode=0, stdout="All installed\n", stderr=""
            )
            # First install
            self._mock_apm_install_success(module)
            result1 = module.install()
            assert result1.success is True
            manifest_after_first = (tmp_path / MANIFEST_FILE).read_text()

            # Second install (force to simulate re-run)
            self._mock_apm_install_success(module)
            result2 = module.install(force=True)
            assert result2.success is True
            manifest_after_second = (tmp_path / MANIFEST_FILE).read_text()

            # Idempotency: same manifest content
            assert manifest_after_first == manifest_after_second

    def test_reproducibility_same_lockfile_same_output(self, tmp_path: Path) -> None:
        """Same lockfile content produces identical ModuleResult."""
        module = self._make_successful_apm(tmp_path)
        lockfile_content = "lockfile_version: '1.0'\ngenerated_at: '2026-03-24T10:00:00Z'\n"

        with patch.object(module, "_check_apm_cli", return_value=(True, "APM CLI v0.9.0")), \
             patch.object(module, "_run_apm") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["apm", "install"], returncode=0, stdout="All installed\n", stderr=""
            )
            (tmp_path / LOCKFILE).write_text(lockfile_content)
            result1 = module.install()

            (tmp_path / LOCKFILE).write_text(lockfile_content)
            result2 = module.install(force=True)

            # Reproducibility: same success status, same file count
            assert result1.success == result2.success
            assert len(result1.files_created) == len(result2.files_created)
