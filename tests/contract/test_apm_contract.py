"""Contract tests for APMModule — ModuleBase protocol compliance."""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from dev_stack.modules.apm import APMModule
from dev_stack.modules.base import ModuleBase, ModuleResult, ModuleStatus


@pytest.fixture()
def apm_module(tmp_path: Path) -> APMModule:
    return APMModule(tmp_path)


class TestAPMModuleProtocol:
    """Verify APMModule satisfies the ModuleBase abstract interface."""

    def test_is_subclass_of_module_base(self) -> None:
        assert issubclass(APMModule, ModuleBase)

    def test_not_abstract(self) -> None:
        assert not inspect.isabstract(APMModule)

    def test_has_required_class_constants(self) -> None:
        assert isinstance(APMModule.NAME, str) and APMModule.NAME == "apm"
        assert isinstance(APMModule.VERSION, str) and APMModule.VERSION
        assert isinstance(APMModule.DEPENDS_ON, (list, tuple))
        assert isinstance(APMModule.MANAGED_FILES, (list, tuple))
        for path in APMModule.MANAGED_FILES:
            assert isinstance(path, str)

    def test_install_returns_module_result(self, apm_module: APMModule) -> None:
        result = apm_module.install()
        assert isinstance(result, ModuleResult)

    def test_uninstall_returns_module_result(self, apm_module: APMModule) -> None:
        result = apm_module.uninstall()
        assert isinstance(result, ModuleResult)

    def test_update_returns_module_result(self, apm_module: APMModule) -> None:
        result = apm_module.update()
        assert isinstance(result, ModuleResult)

    def test_verify_returns_module_status(self, apm_module: APMModule) -> None:
        status = apm_module.verify()
        assert isinstance(status, ModuleStatus)

    def test_preview_files_returns_dict(self, apm_module: APMModule) -> None:
        preview = apm_module.preview_files()
        assert isinstance(preview, dict)
        for key, value in preview.items():
            assert isinstance(key, Path)
            assert isinstance(value, str)

    def test_install_signature_has_force_kwarg(self) -> None:
        sig = inspect.signature(APMModule.install)
        params = list(sig.parameters.values())
        assert len(params) == 2  # self + force
        force_param = params[1]
        assert force_param.name == "force"
        assert force_param.kind == inspect.Parameter.KEYWORD_ONLY
        assert force_param.default is False
