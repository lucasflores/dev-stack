"""Integration test for legacy mcp-servers opt-in via dev-stack.toml (FR-011)."""
from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from dev_stack.modules import resolve_module_names
from dev_stack.modules.mcp_servers import MCPServersModule


class TestLegacyMcpServersOptIn:
    """T020: mcp-servers module runs when explicitly listed in dev-stack.toml."""

    def test_mcp_servers_resolves_when_explicitly_requested(self) -> None:
        """When a user explicitly requests mcp-servers, it resolves."""
        resolved = resolve_module_names(["mcp-servers"], include_defaults=False)
        assert "mcp-servers" in resolved

    def test_mcp_servers_not_in_defaults(self) -> None:
        """Without explicit request, mcp-servers is not included."""
        resolved = resolve_module_names(include_defaults=True)
        assert "mcp-servers" not in resolved

    def test_apm_in_defaults(self) -> None:
        """Default resolution includes apm."""
        resolved = resolve_module_names(include_defaults=True)
        assert "apm" in resolved

    def test_mcp_servers_install_emits_deprecation(self, tmp_path: Path) -> None:
        """Opt-in mcp-servers module emits deprecation warning on install."""
        module = MCPServersModule(tmp_path)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                module.install()
            except Exception:
                pass
            deprecation_warnings = [
                w for w in caught if issubclass(w.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) >= 1
            msg = str(deprecation_warnings[0].message)
            assert "apm" in msg.lower()
