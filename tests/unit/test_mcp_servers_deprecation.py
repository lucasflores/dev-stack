"""Unit tests for MCPServersModule deprecation warning."""
from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from dev_stack.modules.mcp_servers import MCPServersModule


class TestMCPServersDeprecation:
    """T018: Verify DeprecationWarning in MCPServersModule.install()."""

    def test_install_emits_deprecation_warning(self, tmp_path: Path) -> None:
        module = MCPServersModule(tmp_path)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # install() will fail (no agent detected) but should still emit warning first
            try:
                module.install()
            except Exception:
                pass
            deprecation_warnings = [
                w for w in caught if issubclass(w.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) >= 1
            assert "apm" in str(deprecation_warnings[0].message).lower()
