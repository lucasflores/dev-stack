"""Tests for module registry utilities."""
from __future__ import annotations

import pytest

import dev_stack.modules as modules
from dev_stack.manifest import create_default
from dev_stack.modules.base import ModuleBase, ModuleResult, ModuleStatus


@pytest.fixture()
def registry(monkeypatch):
    original = modules._MODULE_REGISTRY.copy()
    monkeypatch.setattr(modules, "_MODULE_REGISTRY", dict(original))
    try:
        yield modules._MODULE_REGISTRY
    finally:
        modules._MODULE_REGISTRY.clear()
        modules._MODULE_REGISTRY.update(original)


class DummyModule(ModuleBase):
    NAME = "dummy"
    VERSION = "0.1.0"
    DEPENDS_ON = ("hooks",)

    def install(self, *, force: bool = False) -> ModuleResult:
        return ModuleResult(True, "installed")

    def uninstall(self) -> ModuleResult:
        return ModuleResult(True, "removed")

    def update(self) -> ModuleResult:
        return ModuleResult(True, "updated")

    def verify(self) -> ModuleStatus:
        return ModuleStatus(name=self.NAME, installed=True, version=self.VERSION, healthy=True)


class CycleModule(ModuleBase):
    NAME = "cycle"
    VERSION = "0.1.0"
    DEPENDS_ON = ("cycle",)

    def install(self, *, force: bool = False) -> ModuleResult:
        return ModuleResult(True, "installed")

    def uninstall(self) -> ModuleResult:
        return ModuleResult(True, "removed")

    def update(self) -> ModuleResult:
        return ModuleResult(True, "updated")

    def verify(self) -> ModuleStatus:
        return ModuleStatus(name=self.NAME, installed=True, version=self.VERSION, healthy=True)


def test_available_and_resolve_modules(registry, tmp_path) -> None:
    modules.register_module(DummyModule)

    resolved = modules.resolve_module_names(["dummy"], include_defaults=False)
    assert resolved == ["hooks", "dummy"]
    assert "dummy" in modules.available_modules()

    manifest = create_default(["hooks", "dummy"])
    instances = modules.instantiate_modules(tmp_path, manifest, resolved)
    assert [instance.NAME for instance in instances] == ["hooks", "dummy"]


def test_resolve_unknown_module_raises(registry) -> None:
    with pytest.raises(KeyError):
        modules.resolve_module_names(["missing"], include_defaults=False)


def test_cyclical_dependency_detection(registry) -> None:
    modules.register_module(CycleModule)

    with pytest.raises(modules.DependencyError):
        modules.resolve_module_names(["cycle"], include_defaults=False)


def test_default_greenfield_modules_include_new_modules() -> None:
    assert modules.DEFAULT_GREENFIELD_MODULES == ("uv_project", "sphinx_docs", "hooks", "apm", "vcs_hooks")


def test_resolve_default_modules_respect_dependency_order() -> None:
    resolved = modules.resolve_module_names()
    # uv_project must come before sphinx_docs (dependency)
    assert resolved.index("uv_project") < resolved.index("sphinx_docs")
    # All defaults present
    for name in ("uv_project", "sphinx_docs", "hooks", "apm"):
        assert name in resolved
    # speckit is no longer a default
    assert "speckit" not in resolved


def test_deprecated_modules_contains_speckit() -> None:
    assert "speckit" in modules.DEPRECATED_MODULES
    assert isinstance(modules.DEPRECATED_MODULES["speckit"], str)
    assert len(modules.DEPRECATED_MODULES["speckit"]) > 0
