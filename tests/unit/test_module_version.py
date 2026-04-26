"""Unit tests for runtime-derived module version (Bug 2)."""
from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Any, Sequence
from unittest.mock import patch

import pytest

import dev_stack.modules as modules
from dev_stack.modules import _package_version, latest_module_entries
from dev_stack.modules.base import ModuleBase, ModuleResult, ModuleStatus


# ---------------------------------------------------------------------------
# _package_version()
# ---------------------------------------------------------------------------

class TestPackageVersion:
    def test_returns_nonempty_string(self):
        result = _package_version()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_installed_package_version(self):
        expected = importlib.metadata.version("dev-stack")
        assert _package_version() == expected

    def test_falls_back_on_metadata_error(self):
        from dev_stack.manifest import DEFAULT_MODULE_VERSION
        with patch("importlib.metadata.version", side_effect=Exception("not found")):
            result = _package_version()
        assert result == DEFAULT_MODULE_VERSION

    def test_never_raises(self):
        with patch("importlib.metadata.version", side_effect=RuntimeError("boom")):
            # Should not raise regardless of the exception type
            result = _package_version()
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# latest_module_entries()
# ---------------------------------------------------------------------------

class TestLatestModuleEntries:
    def test_all_entries_use_package_version(self):
        pkg_version = _package_version()
        entries = latest_module_entries()
        for name, entry in entries.items():
            assert entry.version == pkg_version, (
                f"Module '{name}' has version '{entry.version}', expected '{pkg_version}'"
            )

    def test_returns_entry_for_every_registered_module(self):
        registered = set(modules.available_modules())
        entries = latest_module_entries()
        assert registered == set(entries.keys())

    def test_subset_request_works(self):
        pkg_version = _package_version()
        entries = latest_module_entries(["hooks", "apm"])
        assert set(entries.keys()) == {"hooks", "apm"}
        for entry in entries.values():
            assert entry.version == pkg_version

    def test_no_module_returns_stale_constant(self):
        """No module should ever return a hardcoded VERSION constant string."""
        entries = latest_module_entries()
        stale_versions = {"0.1.0", "0.1.2", "0.1.1"}
        for name, entry in entries.items():
            assert entry.version not in stale_versions, (
                f"Module '{name}' is returning a stale hardcoded version: '{entry.version}'"
            )


# ---------------------------------------------------------------------------
# ModuleBase.version property
# ---------------------------------------------------------------------------

class _MinimalModule(ModuleBase):
    """Concrete subclass for testing the base version property."""

    NAME = "test-minimal"
    DEPENDS_ON: Sequence[str] = ()
    MANAGED_FILES: Sequence[str] = ()

    def install(self, *, force: bool = False) -> ModuleResult:
        return ModuleResult(True, "ok")

    def uninstall(self) -> ModuleResult:
        return ModuleResult(True, "ok")

    def update(self) -> ModuleResult:
        return ModuleResult(True, "ok")

    def verify(self) -> ModuleStatus:
        return ModuleStatus(name=self.NAME, installed=True, version=self.version, healthy=True)


class TestModuleBaseVersionProperty:
    def test_version_property_resolves(self, tmp_path: Path):
        mod = _MinimalModule(tmp_path)
        result = mod.version
        assert isinstance(result, str)
        assert len(result) > 0

    def test_version_property_matches_package_version(self, tmp_path: Path):
        mod = _MinimalModule(tmp_path)
        assert mod.version == _package_version()

    def test_version_property_consistent_across_calls(self, tmp_path: Path):
        mod = _MinimalModule(tmp_path)
        assert mod.version == mod.version

    def test_verify_uses_version_property(self, tmp_path: Path):
        mod = _MinimalModule(tmp_path)
        status = mod.verify()
        assert status.version == _package_version()
