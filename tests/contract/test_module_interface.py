"""Contract tests that enforce ModuleBase interface guarantees."""
from __future__ import annotations

import inspect
from typing import Iterable, Type

import dev_stack.modules  # noqa: F401  -- ensure module registry side effects run
from dev_stack.modules.base import ModuleBase, ModuleResult, ModuleStatus


def _annotation_matches(annotation: object, expected: type) -> bool:

    if annotation is expected:
        return True
    if isinstance(annotation, str):
        return annotation == expected.__name__
    return False


def _all_module_classes() -> Iterable[Type[ModuleBase]]:
    seen: set[type[ModuleBase]] = set()
    stack: list[type[ModuleBase]] = list(ModuleBase.__subclasses__())
    while stack:
        cls = stack.pop()
        if cls in seen:
            continue
        seen.add(cls)
        stack.extend(cls.__subclasses__())
        yield cls


def test_modules_expose_required_metadata() -> None:
    for cls in _all_module_classes():
        assert not inspect.isabstract(cls), f"{cls.__name__} is still abstract"
        assert isinstance(getattr(cls, "NAME", None), str) and cls.NAME, "Missing NAME"
        assert isinstance(getattr(cls, "VERSION", None), str) and cls.VERSION, "Missing VERSION"
        managed = getattr(cls, "MANAGED_FILES", ())
        assert isinstance(managed, (list, tuple)), "MANAGED_FILES must be a sequence"
        for path in managed:
            assert isinstance(path, str), "MANAGED_FILES entries must be strings"


def test_install_signature_matches_contract() -> None:
    for cls in _all_module_classes():
        sig = inspect.signature(cls.install)
        params = list(sig.parameters.values())
        assert len(params) == 2, f"install signature mismatch for {cls.NAME}"
        self_param, force_param = params
        assert self_param.name == "self" and self_param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.POSITIONAL_ONLY,
        )
        assert force_param.name == "force" and force_param.kind is inspect.Parameter.KEYWORD_ONLY
        assert force_param.default is False
        assert _annotation_matches(sig.return_annotation, ModuleResult)


def test_update_and_verify_signatures_match_contract() -> None:
    for cls in _all_module_classes():
        uninstall_sig = inspect.signature(cls.uninstall)
        update_sig = inspect.signature(cls.update)
        verify_sig = inspect.signature(cls.verify)

        for sig in (uninstall_sig, update_sig):
            params = list(sig.parameters.values())
            assert len(params) == 1 and params[0].name == "self", f"signature mismatch for {cls.NAME}"
            assert _annotation_matches(sig.return_annotation, ModuleResult)

        params = list(verify_sig.parameters.values())
        assert len(params) == 1 and params[0].name == "self"
        assert _annotation_matches(verify_sig.return_annotation, ModuleStatus)


def test_visualization_module_identity() -> None:
    """Verify VisualizationModule exposes correct NAME, VERSION, and MANAGED_FILES."""

    from dev_stack.modules.visualization import VisualizationModule

    assert VisualizationModule.NAME == "visualization"
    assert VisualizationModule.VERSION == "1.0.0"
    assert ".codeboarding" in VisualizationModule.MANAGED_FILES[0]
    assert ".dev-stack/viz" in VisualizationModule.MANAGED_FILES[1]


def test_visualization_module_is_registered() -> None:
    """Confirm the visualization module is in the module registry."""

    from dev_stack.modules import _MODULE_REGISTRY

    assert "visualization" in _MODULE_REGISTRY
