"""Contract tests for docs strictness policy behavior."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import tomli_w

from dev_stack.modules.sphinx_docs import _read_strict_docs, _render_makefile
from dev_stack.pipeline.stages import StageContext, StageStatus, _execute_docs_api_stage, _is_strict_docs


def _write_pipeline_pyproject(repo_root: Path, *, strict_docs: bool | None = None) -> None:
    data: dict[str, object] = {"project": {"name": "demo"}}
    if strict_docs is not None:
        data = {
            "tool": {"dev-stack": {"pipeline": {"strict_docs": strict_docs}}},
            "project": {"name": "demo"},
        }
    (repo_root / "pyproject.toml").write_text(tomli_w.dumps(data), encoding="utf-8")


def _create_docs_pkg(repo_root: Path) -> None:
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    src_pkg = repo_root / "src" / "mypkg"
    src_pkg.mkdir(parents=True, exist_ok=True)
    (src_pkg / "__init__.py").write_text("", encoding="utf-8")


class TestStrictnessResolverContract:
    def test_pipeline_and_module_default_true_without_pyproject(self, tmp_path: Path) -> None:
        context = StageContext(repo_root=tmp_path)
        assert _is_strict_docs(context) is True
        assert _read_strict_docs(tmp_path) is True

    def test_pipeline_and_module_read_explicit_false(self, tmp_path: Path) -> None:
        _write_pipeline_pyproject(tmp_path, strict_docs=False)
        context = StageContext(repo_root=tmp_path)
        assert _is_strict_docs(context) is False
        assert _read_strict_docs(tmp_path) is False

    def test_pipeline_and_module_read_explicit_true(self, tmp_path: Path) -> None:
        _write_pipeline_pyproject(tmp_path, strict_docs=True)
        context = StageContext(repo_root=tmp_path)
        assert _is_strict_docs(context) is True
        assert _read_strict_docs(tmp_path) is True

    def test_pipeline_and_module_fallback_on_unreadable_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.dev-stack.pipeline\nstrict_docs = false", encoding="utf-8")
        context = StageContext(repo_root=tmp_path)
        assert _is_strict_docs(context) is True
        assert _read_strict_docs(tmp_path) is True


class TestDocsApiCommandContract:
    @pytest.fixture(autouse=True)
    def _has_sphinx(self, monkeypatch):
        monkeypatch.setattr(
            "dev_stack.pipeline.stages._tool_available_in_venv",
            lambda tool, root: True,
        )

    def test_non_strict_omits_warning_fatal_flags(self, tmp_path: Path, monkeypatch) -> None:
        _write_pipeline_pyproject(tmp_path, strict_docs=False)
        _create_docs_pkg(tmp_path)

        captured: list[tuple[str, ...]] = []

        def fake_run(cmd, **kwargs):
            captured.append(tuple(cmd))
            return subprocess.CompletedProcess(cmd, 0, "warning: harmless", "")

        monkeypatch.setattr("subprocess.run", fake_run)

        result = _execute_docs_api_stage(StageContext(repo_root=tmp_path))

        assert result.status == StageStatus.PASS
        build_cmd = [c for c in captured if c[:5] == ("python3", "-m", "sphinx", "-b", "html")][0]
        assert "-W" not in build_cmd
        assert "--keep-going" not in build_cmd

    def test_strict_requires_warning_fatal_flags(self, tmp_path: Path, monkeypatch) -> None:
        _write_pipeline_pyproject(tmp_path, strict_docs=True)
        _create_docs_pkg(tmp_path)

        captured: list[tuple[str, ...]] = []

        def fake_run(cmd, **kwargs):
            captured.append(tuple(cmd))
            return subprocess.CompletedProcess(cmd, 0, "ok", "")

        monkeypatch.setattr("subprocess.run", fake_run)

        result = _execute_docs_api_stage(StageContext(repo_root=tmp_path))

        assert result.status == StageStatus.PASS
        build_cmd = [c for c in captured if c[:5] == ("python3", "-m", "sphinx", "-b", "html")][0]
        assert "-W" in build_cmd
        assert "--keep-going" in build_cmd


class TestMakefileStrictnessContract:
    def test_makefile_line_non_strict_is_empty_sphinxopts(self) -> None:
        rendered = _render_makefile("mylib", strict_docs=False)
        assert "SPHINXOPTS  ?= \n" in rendered

    def test_makefile_line_strict_has_warning_fatal_opts(self) -> None:
        rendered = _render_makefile("mylib", strict_docs=True)
        assert "SPHINXOPTS  ?= -W --keep-going\n" in rendered
