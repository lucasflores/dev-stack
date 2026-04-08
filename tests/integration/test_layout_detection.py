"""Integration test: end-to-end layout detection across src, flat, and namespace layouts."""

from __future__ import annotations

from pathlib import Path

import pytest

from dev_stack.layout import LayoutStyle, detect_package_layout


class TestEndToEndLayoutDetection:
    """Integration tests exercising the full detection precedence chain."""

    def test_src_layout_full_project(self, tmp_path: Path) -> None:
        """Realistic src-layout project with pyproject.toml."""
        # Set up a proper src-layout project
        src_pkg = tmp_path / "src" / "my_app"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").write_text('"""My app."""\n')
        (src_pkg / "main.py").write_text("def main(): pass\n")

        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "my-app"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_root == Path("src")
        assert layout.package_names == ["my_app"]

    def test_flat_layout_full_project(self, tmp_path: Path) -> None:
        """Realistic flat-layout project — package at repo root."""
        flat_pkg = tmp_path / "my_lib"
        flat_pkg.mkdir()
        (flat_pkg / "__init__.py").write_text('"""My library."""\n')
        (flat_pkg / "core.py").write_text("class Core: pass\n")

        # tests/ without __init__.py (modern pytest doesn't need it)
        (tmp_path / "tests").mkdir()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "my-lib"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.FLAT
        assert layout.package_root == Path(".")
        assert layout.package_names == ["my_lib"]

    def test_namespace_layout_via_setuptools(self, tmp_path: Path) -> None:
        """Namespace layout declared via setuptools config."""
        ns_pkg = tmp_path / "src" / "company" / "product"
        ns_pkg.mkdir(parents=True)
        (tmp_path / "src" / "company" / "__init__.py").touch()
        (ns_pkg / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "company-product"\nversion = "0.1.0"\n\n'
            '[tool.setuptools.packages.find]\nwhere = ["src"]\nnamespaces = true\n',
            encoding="utf-8",
        )

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.NAMESPACE
        assert layout.package_root == Path("src")

    def test_manifest_overrides_everything(self, tmp_path: Path) -> None:
        """Manifest config takes precedence over filesystem and pyproject.toml."""
        # Set up a src-layout project
        src_pkg = tmp_path / "src" / "actual_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        # But manifest says the package is different
        manifest = {"modules": {"uv_project": {"config": {"package_name": "actual_pkg"}}}}
        layout = detect_package_layout(tmp_path, manifest)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_names == ["actual_pkg"]

    def test_hatch_layout_with_packages(self, tmp_path: Path) -> None:
        """Hatch build config specifies explicit package paths."""
        src_pkg = tmp_path / "src" / "hatch_app"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "hatch-app"\nversion = "0.1.0"\n\n'
            '[tool.hatch.build.targets.wheel]\npackages = ["src/hatch_app"]\n',
            encoding="utf-8",
        )

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_root == Path("src")
        assert layout.package_names == ["hatch_app"]

    def test_precedence_manifest_over_pyproject(self, tmp_path: Path) -> None:
        """Manifest config (level 1) beats pyproject.toml hints (level 2)."""
        # Set up conflicting signals
        (tmp_path / "src" / "manifest_pkg").mkdir(parents=True)
        (tmp_path / "src" / "manifest_pkg" / "__init__.py").touch()
        (tmp_path / "src" / "setuptools_pkg").mkdir(parents=True)
        (tmp_path / "src" / "setuptools_pkg" / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.setuptools.packages.find]\nwhere = ["src"]\n',
            encoding="utf-8",
        )

        manifest = {"modules": {"uv_project": {"config": {"package_name": "manifest_pkg"}}}}
        layout = detect_package_layout(tmp_path, manifest)

        # Level 1 (manifest) should win: only manifest_pkg, not both
        assert layout.package_names == ["manifest_pkg"]

    def test_detection_is_deterministic(self, tmp_path: Path) -> None:
        """Same filesystem state always produces the same result."""
        src_pkg = tmp_path / "src" / "my_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        results = [detect_package_layout(tmp_path) for _ in range(5)]
        assert all(r == results[0] for r in results)
