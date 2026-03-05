"""Unit tests for codeboarding_runner."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dev_stack.errors import CodeBoardingError
from dev_stack.visualization.codeboarding_runner import RunResult, check_cli_available, run


class TestCheckCliAvailable:
    def test_returns_true_when_found(self) -> None:
        with patch("dev_stack.visualization.codeboarding_runner.shutil.which", return_value="/usr/bin/codeboarding"):
            assert check_cli_available() is True

    def test_returns_false_when_missing(self) -> None:
        with patch("dev_stack.visualization.codeboarding_runner.shutil.which", return_value=None):
            assert check_cli_available() is False


class TestRun:
    def test_successful_invocation(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Analysis complete"
        mock_result.stderr = ""

        with patch("dev_stack.visualization.codeboarding_runner.subprocess.run", return_value=mock_result) as mock_run:
            result = run(tmp_path, depth_level=2)

        assert result == RunResult(success=True, stdout="Analysis complete", stderr="", return_code=0)
        mock_run.assert_called_once()
        args = mock_run.call_args
        cmd = args[0][0]
        assert cmd == ["codeboarding", "--local", str(tmp_path), "--depth-level", "2"]
        assert args[1]["timeout"] == 300
        assert args[1]["cwd"] == tmp_path

    def test_nonzero_exit(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "API key missing"

        with patch("dev_stack.visualization.codeboarding_runner.subprocess.run", return_value=mock_result):
            result = run(tmp_path)

        assert result.success is False
        assert result.stderr == "API key missing"
        assert result.return_code == 1

    def test_timeout_raises_codeboarding_error(self, tmp_path: Path) -> None:
        with patch(
            "dev_stack.visualization.codeboarding_runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="codeboarding", timeout=300, stderr="partial"),
        ):
            with pytest.raises(CodeBoardingError, match="timed out"):
                run(tmp_path, timeout=300)

    def test_incremental_flag_appended(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("dev_stack.visualization.codeboarding_runner.subprocess.run", return_value=mock_result) as mock_run:
            run(tmp_path, incremental=True)

        cmd = mock_run.call_args[0][0]
        assert "--incremental" in cmd

    def test_custom_depth_level(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("dev_stack.visualization.codeboarding_runner.subprocess.run", return_value=mock_result) as mock_run:
            run(tmp_path, depth_level=3)

        cmd = mock_run.call_args[0][0]
        assert "--depth-level" in cmd
        idx = cmd.index("--depth-level")
        assert cmd[idx + 1] == "3"

    def test_custom_timeout(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("dev_stack.visualization.codeboarding_runner.subprocess.run", return_value=mock_result) as mock_run:
            run(tmp_path, timeout=600)

        assert mock_run.call_args[1]["timeout"] == 600
