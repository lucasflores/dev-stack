"""Unit tests for UvProjectModule."""
from __future__ import annotations

import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from dev_stack.modules.uv_project import (
    UvProjectModule,
    _augment_pyproject,
    _normalize_name,
    _scaffold_tests,
)


# ---------------------------------------------------------------------------
# _normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_hyphens_to_underscores(self) -> None:
        assert _normalize_name("my-cool-project") == "my_cool_project"

    def test_dots_to_underscores(self) -> None:
        assert _normalize_name("my.cool.project") == "my_cool_project"

    def test_leading_digit_prepends_underscore(self) -> None:
        assert _normalize_name("123abc") == "_123abc"

    def test_empty_string_fallback(self) -> None:
        assert _normalize_name("") == "package"

    def test_all_invalid_chars_fallback(self) -> None:
        assert _normalize_name("---") == "package"

    def test_mixed_case_lowered(self) -> None:
        assert _normalize_name("MyProject") == "myproject"

    def test_consecutive_separators_collapsed(self) -> None:
        assert _normalize_name("foo--bar__baz") == "foo_bar_baz"


# ---------------------------------------------------------------------------
# _augment_pyproject — skip-if-exists
# ---------------------------------------------------------------------------


class TestAugmentPyproject:
    def test_adds_all_sections_to_bare_toml(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\n', encoding="utf-8")

        added = _augment_pyproject(pyproject, "test")

        assert "tool.ruff" in added
        assert "tool.pytest.ini_options" in added
        assert "tool.mypy" in added
        assert "tool.coverage.run" in added
        assert "project.optional-dependencies.docs" in added
        assert "project.optional-dependencies.dev" in added

        with open(pyproject, "rb") as fh:
            data = tomllib.load(fh)
        assert "ruff" in data["tool"]
        assert "mypy" in data["tool"]
        assert "docs" in data["project"]["optional-dependencies"]

    def test_skips_existing_tool_sections(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n[tool.ruff]\nline-length = 120\n',
            encoding="utf-8",
        )

        added = _augment_pyproject(pyproject, "test")

        assert "tool.ruff" not in added
        with open(pyproject, "rb") as fh:
            data = tomllib.load(fh)
        # Existing value preserved
        assert data["tool"]["ruff"]["line-length"] == 120

    def test_no_write_when_nothing_added(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n'
            "[tool.ruff]\n[tool.pytest]\n[tool.coverage]\n[tool.mypy]\n"
            "[project.optional-dependencies]\ndocs = []\ndev = []\n",
            encoding="utf-8",
        )
        mtime_before = pyproject.stat().st_mtime_ns

        added = _augment_pyproject(pyproject, "test")

        assert added == []
        # File should not be rewritten
        assert pyproject.stat().st_mtime_ns == mtime_before


# ---------------------------------------------------------------------------
# _scaffold_tests
# ---------------------------------------------------------------------------


class TestScaffoldTests:
    def test_creates_test_files(self, tmp_path: Path) -> None:
        created = _scaffold_tests(tmp_path, "mypkg")

        assert (tmp_path / "tests" / "__init__.py").exists()
        assert (tmp_path / "tests" / "test_placeholder.py").exists()
        content = (tmp_path / "tests" / "test_placeholder.py").read_text(encoding="utf-8")
        assert "import mypkg" in content
        assert len(created) == 2

    def test_idempotent(self, tmp_path: Path) -> None:
        _scaffold_tests(tmp_path, "mypkg")
        second = _scaffold_tests(tmp_path, "mypkg")

        assert second == []  # Nothing new created


# ---------------------------------------------------------------------------
# UvProjectModule
# ---------------------------------------------------------------------------


class TestUvProjectModuleVerify:
    def test_verify_healthy(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / ".python-version").touch()
        (tmp_path / "uv.lock").touch()
        pkg_dir = tmp_path / "src" / "mypkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").touch()

        module = UvProjectModule(tmp_path, {})
        status = module.verify()
        assert status.healthy is True

    def test_verify_unhealthy(self, tmp_path: Path) -> None:
        module = UvProjectModule(tmp_path, {})
        status = module.verify()
        assert status.healthy is False
        assert "pyproject.toml" in status.issue


class TestUvProjectModulePreviewFiles:
    def test_preview_returns_expected_keys(self, tmp_path: Path) -> None:
        module = UvProjectModule(tmp_path, {})
        preview = module.preview_files()

        assert Path("pyproject.toml") in preview
        assert Path("tests/__init__.py") in preview
        assert Path("tests/test_placeholder.py") in preview


class TestUvProjectModuleInstall:
    def test_install_fails_when_uv_not_found(self, tmp_path: Path) -> None:
        with patch("dev_stack.modules.uv_project.shutil.which", return_value=None):
            module = UvProjectModule(tmp_path, {})
            result = module.install()
            assert result.success is False
            assert "uv CLI not found" in result.message

    def test_install_brownfield_guard(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "existing"\n', encoding="utf-8")
        module = UvProjectModule(tmp_path, {})
        result = module.install()
        assert result.success is False
        assert "already exists" in result.message

    def test_install_brownfield_force_skips_uv_init_runs_steps_2_to_5(self, tmp_path: Path) -> None:
        """T001: When force=True and pyproject exists, skip uv init but run Steps 2-5."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "existing"\n', encoding="utf-8")
        (tmp_path / "src" / "existing").mkdir(parents=True)
        (tmp_path / "src" / "existing" / "__init__.py").touch()

        with patch("dev_stack.modules.uv_project.shutil.which", return_value="/usr/bin/uv"), \
             patch("dev_stack.modules.uv_project._run_uv_lock", return_value=(True, "")):
            module = UvProjectModule(tmp_path, {})
            result = module.install(force=True)

        assert result.success is True
        # Step 2: augment pyproject
        with open(pyproject, "rb") as fh:
            data = tomllib.load(fh)
        assert "ruff" in data.get("tool", {})
        assert "dev" in data.get("project", {}).get("optional-dependencies", {})
        # Step 3: scaffold tests
        assert (tmp_path / "tests" / "__init__.py").exists()
        assert (tmp_path / "tests" / "test_placeholder.py").exists()

    def test_install_brownfield_force_preserves_existing_tests(self, tmp_path: Path) -> None:
        """T003/FR-007: Existing test files are preserved during force reinstall."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "existing"\n', encoding="utf-8")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("# custom", encoding="utf-8")
        (tests_dir / "test_placeholder.py").write_text("# my tests", encoding="utf-8")

        with patch("dev_stack.modules.uv_project.shutil.which", return_value="/usr/bin/uv"), \
             patch("dev_stack.modules.uv_project._run_uv_lock", return_value=(True, "")):
            module = UvProjectModule(tmp_path, {})
            result = module.install(force=True)

        assert result.success is True
        # Files preserved
        assert (tests_dir / "__init__.py").read_text(encoding="utf-8") == "# custom"
        assert (tests_dir / "test_placeholder.py").read_text(encoding="utf-8") == "# my tests"

    def test_install_brownfield_force_preserves_existing_opt_deps(self, tmp_path: Path) -> None:
        """T004/FR-007: Existing optional-dependency groups are preserved."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "existing"\n'
            '[project.optional-dependencies]\ndev = ["black>=23.0"]\n',
            encoding="utf-8",
        )

        with patch("dev_stack.modules.uv_project.shutil.which", return_value="/usr/bin/uv"), \
             patch("dev_stack.modules.uv_project._run_uv_lock", return_value=(True, "")):
            module = UvProjectModule(tmp_path, {})
            result = module.install(force=True)

        assert result.success is True
        with open(pyproject, "rb") as fh:
            data = tomllib.load(fh)
        # Existing dev group preserved — not overwritten
        assert "black>=23.0" in data["project"]["optional-dependencies"]["dev"]
        # docs group added
        assert "docs" in data["project"]["optional-dependencies"]

    def test_install_brownfield_force_runs_uv_lock(self, tmp_path: Path) -> None:
        """FR-008: uv lock is executed during force install."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "existing"\n', encoding="utf-8")
        lock_called = []

        def mock_uv_lock(repo_root):
            lock_called.append(True)
            return (True, "")

        with patch("dev_stack.modules.uv_project.shutil.which", return_value="/usr/bin/uv"), \
             patch("dev_stack.modules.uv_project._run_uv_lock", side_effect=mock_uv_lock):
            module = UvProjectModule(tmp_path, {})
            result = module.install(force=True)

        assert result.success is True
        assert lock_called
