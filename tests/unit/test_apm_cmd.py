"""Unit tests for dev-stack apm CLI subcommands."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dev_stack.cli.main import cli
from dev_stack.modules.apm import APMModule
from dev_stack.modules.base import ModuleResult


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def mock_install_success() -> ModuleResult:
    return ModuleResult(
        success=True,
        message="All MCP servers installed successfully",
        files_created=[Path("/tmp/test/apm.yml"), Path("/tmp/test/apm.lock.yaml")],
    )


@pytest.fixture()
def mock_install_failure() -> ModuleResult:
    return ModuleResult(
        success=False,
        message="APM install failed (exit 1)",
        files_created=[Path("/tmp/test/apm.yml")],
        warnings=["Error: notebooklm-mcp not found"],
    )


class TestApmInstallCommand:
    def test_install_success_human_output(
        self, runner: CliRunner, mock_install_success: ModuleResult
    ) -> None:
        with patch.object(APMModule, "install", return_value=mock_install_success):
            result = runner.invoke(cli, ["apm", "install"])
            assert result.exit_code == 0
            assert "All MCP servers installed" in result.output

    def test_install_success_json_output(
        self, runner: CliRunner, mock_install_success: ModuleResult
    ) -> None:
        with patch.object(APMModule, "install", return_value=mock_install_success):
            result = runner.invoke(cli, ["--json", "apm", "install"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["success"] is True

    def test_install_failure_exit_code(
        self, runner: CliRunner, mock_install_failure: ModuleResult
    ) -> None:
        with patch.object(APMModule, "install", return_value=mock_install_failure):
            result = runner.invoke(cli, ["apm", "install"])
            assert result.exit_code != 0

    def test_install_with_force_flag(
        self, runner: CliRunner, mock_install_success: ModuleResult
    ) -> None:
        with patch.object(APMModule, "install", return_value=mock_install_success) as mock:
            result = runner.invoke(cli, ["apm", "install", "--force"])
            assert result.exit_code == 0
            mock.assert_called_once_with(force=True)

    def test_install_cli_missing_exit_code(self, runner: CliRunner) -> None:
        no_cli = ModuleResult(
            success=False,
            message="APM CLI not found on PATH",
            warnings=["APM CLI not found on PATH"],
        )
        with patch.object(APMModule, "install", return_value=no_cli):
            result = runner.invoke(cli, ["apm", "install"])
            assert result.exit_code == 4  # AGENT_UNAVAILABLE


class TestApmAuditCommand:
    def test_audit_clean(self, runner: CliRunner) -> None:
        clean = ModuleResult(success=True, message="Audit clean — no findings")
        with patch.object(APMModule, "audit", return_value=clean):
            result = runner.invoke(cli, ["apm", "audit"])
            assert result.exit_code == 0
            assert "clean" in result.output.lower()

    def test_audit_with_format_flag(self, runner: CliRunner) -> None:
        clean = ModuleResult(success=True, message="Audit clean — no findings")
        with patch.object(APMModule, "audit", return_value=clean) as mock:
            result = runner.invoke(cli, ["apm", "audit", "--format", "json"])
            assert result.exit_code == 0
            mock.assert_called_once_with(fmt="json", output=None)

    def test_audit_with_output_flag(self, runner: CliRunner) -> None:
        clean = ModuleResult(success=True, message="Audit clean — no findings")
        with patch.object(APMModule, "audit", return_value=clean) as mock:
            result = runner.invoke(cli, ["apm", "audit", "--output", "/tmp/report.txt"])
            assert result.exit_code == 0
            mock.assert_called_once_with(fmt="text", output=Path("/tmp/report.txt"))

    def test_audit_findings_json_output(self, runner: CliRunner) -> None:
        findings = ModuleResult(
            success=False,
            message="Audit found issues (exit 1)",
            warnings=["Critical: bidi override in config"],
        )
        with patch.object(APMModule, "audit", return_value=findings):
            result = runner.invoke(cli, ["--json", "apm", "audit"])
            assert result.exit_code != 0
            payload = json.loads(result.output)
            assert payload["success"] is False
            assert payload["findings_count"] == 1

    def test_audit_format_choices(self, runner: CliRunner) -> None:
        """Invalid format is rejected by Click."""
        result = runner.invoke(cli, ["apm", "audit", "--format", "invalid"])
        assert result.exit_code != 0
