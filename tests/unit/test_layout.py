"""Unit tests for dev_stack.layout — package layout detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from dev_stack.layout import (
    LayoutStyle,
    PackageLayout,
    detect_package_layout,
    scan_root_python_sources,
)


# ---------------------------------------------------------------------------
# PackageLayout dataclass invariants
# ---------------------------------------------------------------------------


class TestPackageLayout:
    def test_package_names_sorted(self) -> None:
        layout = PackageLayout(LayoutStyle.SRC, Path("src"), ["z_pkg", "a_pkg"])
        assert layout.package_names == ["a_pkg", "z_pkg"]

    def test_absolute_path_rejected(self) -> None:
        with pytest.raises(ValueError, match="relative"):
            PackageLayout(LayoutStyle.SRC, Path("/absolute"), ["pkg"])

    def test_frozen(self) -> None:
        layout = PackageLayout(LayoutStyle.SRC, Path("src"), ["pkg"])
        with pytest.raises(AttributeError):
            layout.layout_style = LayoutStyle.FLAT  # type: ignore[misc]


# ---------------------------------------------------------------------------
# T017 — flat-layout detection
# ---------------------------------------------------------------------------


class TestFlatLayoutDetection:
    def test_flat_layout_single_package(self, tmp_path: Path) -> None:
        """Flat-layout project with my_package/__init__.py at repo root."""
        pkg = tmp_path / "my_package"
        pkg.mkdir()
        (pkg / "__init__.py").touch()

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.FLAT
        assert layout.package_root == Path(".")
        assert layout.package_names == ["my_package"]

    def test_flat_layout_multiple_packages(self, tmp_path: Path) -> None:
        """Multiple flat-layout packages at repo root."""
        for name in ("beta", "alpha", "gamma"):
            pkg = tmp_path / name
            pkg.mkdir()
            (pkg / "__init__.py").touch()

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.FLAT
        assert layout.package_root == Path(".")
        assert layout.package_names == ["alpha", "beta", "gamma"]  # sorted

    def test_flat_layout_no_src_directory(self, tmp_path: Path) -> None:
        """No src/ directory should not prevent flat-layout detection."""
        pkg = tmp_path / "my_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").touch()
        # No src/ directory at all
        assert not (tmp_path / "src").exists()

        layout = detect_package_layout(tmp_path)
        assert layout.layout_style == LayoutStyle.FLAT


# ---------------------------------------------------------------------------
# T018 — src-layout detection
# ---------------------------------------------------------------------------


class TestSrcLayoutDetection:
    def test_src_layout_single_package(self, tmp_path: Path) -> None:
        """Standard src-layout project with src/my_pkg/__init__.py."""
        src = tmp_path / "src" / "my_pkg"
        src.mkdir(parents=True)
        (src / "__init__.py").touch()

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_root == Path("src")
        assert layout.package_names == ["my_pkg"]

    def test_src_layout_multiple_packages(self, tmp_path: Path) -> None:
        """Multiple packages under src/."""
        for name in ("zebra", "alpha"):
            pkg = tmp_path / "src" / name
            pkg.mkdir(parents=True)
            (pkg / "__init__.py").touch()

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_root == Path("src")
        assert layout.package_names == ["alpha", "zebra"]

    def test_src_preferred_over_flat(self, tmp_path: Path) -> None:
        """When both src/ and flat packages exist, src/ takes precedence."""
        # src layout
        src_pkg = tmp_path / "src" / "main_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()
        # flat layout
        flat_pkg = tmp_path / "utils"
        flat_pkg.mkdir()
        (flat_pkg / "__init__.py").touch()

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_names == ["main_pkg"]


# ---------------------------------------------------------------------------
# scan_root_python_sources
# ---------------------------------------------------------------------------


class TestScanRootPythonSources:
    def test_detects_packages_and_scripts(self, tmp_path: Path) -> None:
        pkg = tmp_path / "my_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").touch()
        (tmp_path / "script.py").touch()

        has_py, packages = scan_root_python_sources(tmp_path)

        assert has_py is True
        assert packages == ["my_pkg"]

    def test_excludes_special_dirs(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "__init__.py").touch()

        has_py, packages = scan_root_python_sources(tmp_path)

        assert has_py is False
        assert packages == []

    def test_empty_directory(self, tmp_path: Path) -> None:
        has_py, packages = scan_root_python_sources(tmp_path)

        assert has_py is False
        assert packages == []


# ---------------------------------------------------------------------------
# Default (greenfield)
# ---------------------------------------------------------------------------


class TestDefaultGreenfield:
    def test_empty_repo_returns_src_default(self, tmp_path: Path) -> None:
        """Greenfield project with no packages defaults to SRC layout."""
        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_root == Path("src")
        assert layout.package_names == []


# ---------------------------------------------------------------------------
# T021 — manifest config override (precedence level 1)
# ---------------------------------------------------------------------------


class TestManifestConfigOverride:
    def test_manifest_package_name_with_src_dir(self, tmp_path: Path) -> None:
        """Manifest config resolves to SRC when src/{name}/ exists."""
        src_pkg = tmp_path / "src" / "custom_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        manifest = {"modules": {"uv_project": {"config": {"package_name": "custom_pkg"}}}}
        layout = detect_package_layout(tmp_path, manifest)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_root == Path("src")
        assert layout.package_names == ["custom_pkg"]

    def test_manifest_package_name_with_flat_dir(self, tmp_path: Path) -> None:
        """Manifest config resolves to FLAT when {name}/ exists at root."""
        flat_pkg = tmp_path / "my_lib"
        flat_pkg.mkdir()
        (flat_pkg / "__init__.py").touch()

        manifest = {"modules": {"uv_project": {"config": {"package_name": "my_lib"}}}}
        layout = detect_package_layout(tmp_path, manifest)

        assert layout.layout_style == LayoutStyle.FLAT
        assert layout.package_root == Path(".")
        assert layout.package_names == ["my_lib"]

    def test_manifest_overrides_filesystem(self, tmp_path: Path) -> None:
        """Manifest config takes precedence even when filesystem differs."""
        # Filesystem has a different package in src/
        src_pkg = tmp_path / "src" / "other_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        # Manifest says the package is called "configured_pkg" (not on filesystem)
        manifest = {"modules": {"uv_project": {"config": {"package_name": "configured_pkg"}}}}
        layout = detect_package_layout(tmp_path, manifest)

        # Should default to SRC since dir doesn't exist
        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_names == ["configured_pkg"]

    def test_empty_manifest_falls_through(self, tmp_path: Path) -> None:
        """Empty manifest should not prevent filesystem detection."""
        src_pkg = tmp_path / "src" / "my_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        layout = detect_package_layout(tmp_path, {})

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_names == ["my_pkg"]


# ---------------------------------------------------------------------------
# T024 — pyproject.toml hint detection (precedence level 2)
# ---------------------------------------------------------------------------


class TestPyprojectHints:
    def test_setuptools_where_lib(self, tmp_path: Path) -> None:
        """setuptools where=["lib"] returns package_root=Path("lib")."""
        lib_pkg = tmp_path / "lib" / "my_lib"
        lib_pkg.mkdir(parents=True)
        (lib_pkg / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.setuptools.packages.find]\nwhere = ["lib"]\n',
            encoding="utf-8",
        )

        layout = detect_package_layout(tmp_path)

        assert layout.package_root == Path("lib")
        assert layout.package_names == ["my_lib"]
        assert layout.layout_style == LayoutStyle.FLAT  # not "src"

    def test_setuptools_where_src(self, tmp_path: Path) -> None:
        """setuptools where=["src"] returns SRC layout."""
        src_pkg = tmp_path / "src" / "my_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.setuptools.packages.find]\nwhere = ["src"]\n',
            encoding="utf-8",
        )

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_root == Path("src")
        assert layout.package_names == ["my_pkg"]

    def test_setuptools_namespaces_true(self, tmp_path: Path) -> None:
        """setuptools namespaces=true returns NAMESPACE layout."""
        src_pkg = tmp_path / "src" / "ns_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.setuptools.packages.find]\nwhere = ["src"]\nnamespaces = true\n',
            encoding="utf-8",
        )

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.NAMESPACE
        assert layout.package_root == Path("src")

    def test_hatch_packages(self, tmp_path: Path) -> None:
        """hatch packages=["src/my_pkg"] returns correct root and names."""
        src_pkg = tmp_path / "src" / "my_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.hatch.build.targets.wheel]\npackages = ["src/my_pkg"]\n',
            encoding="utf-8",
        )

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_root == Path("src")
        assert layout.package_names == ["my_pkg"]

    def test_invalid_pyproject_falls_through(self, tmp_path: Path) -> None:
        """Malformed pyproject.toml falls through to filesystem scan."""
        src_pkg = tmp_path / "src" / "my_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("this is not valid TOML {{{", encoding="utf-8")

        layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_names == ["my_pkg"]


# ---------------------------------------------------------------------------
# T030 — edge-case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_greenfield_default_src(self, tmp_path: Path) -> None:
        """No packages found → greenfield default SRC with empty names."""
        layout = detect_package_layout(tmp_path)
        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_root == Path("src")
        assert layout.package_names == []

    def test_brownfield_no_packages(self, tmp_path: Path) -> None:
        """Brownfield marker present but no Python packages discovered."""
        marker_dir = tmp_path / ".dev-stack"
        marker_dir.mkdir()
        (marker_dir / "brownfield-init").touch()

        layout = detect_package_layout(tmp_path)
        # Falls through to default SRC with empty package_names
        assert layout.layout_style == LayoutStyle.SRC
        assert layout.package_names == []

    def test_multiple_flat_packages_sorted(self, tmp_path: Path) -> None:
        """Multiple flat packages are returned sorted."""
        for name in ("zebra", "alpha", "middle"):
            pkg = tmp_path / name
            pkg.mkdir()
            (pkg / "__init__.py").touch()

        layout = detect_package_layout(tmp_path)
        assert layout.package_names == ["alpha", "middle", "zebra"]

    def test_namespace_via_setuptools(self, tmp_path: Path) -> None:
        """Namespace layout detected via setuptools namespaces=true."""
        ns_pkg = tmp_path / "src" / "ns_pkg"
        ns_pkg.mkdir(parents=True)
        (ns_pkg / "__init__.py").touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.setuptools.packages.find]\nwhere = ["src"]\nnamespaces = true\n',
            encoding="utf-8",
        )

        layout = detect_package_layout(tmp_path)
        assert layout.layout_style == LayoutStyle.NAMESPACE
        assert layout.package_root == Path("src")
        assert layout.package_names == ["ns_pkg"]

    def test_ambiguous_layout_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """When both src/ and flat packages exist, a warning is logged."""
        src_pkg = tmp_path / "src" / "main_pkg"
        src_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").touch()

        flat_pkg = tmp_path / "extra"
        flat_pkg.mkdir()
        (flat_pkg / "__init__.py").touch()

        import logging
        with caplog.at_level(logging.WARNING, logger="dev_stack.layout"):
            layout = detect_package_layout(tmp_path)

        assert layout.layout_style == LayoutStyle.SRC
        assert "Found packages in both src/ and repo root" in caplog.text

    def test_dir_without_init_not_detected(self, tmp_path: Path) -> None:
        """A directory without __init__.py is not a package."""
        (tmp_path / "not_a_package").mkdir()
        layout = detect_package_layout(tmp_path)
        assert layout.package_names == []

    def test_src_empty_falls_to_root(self, tmp_path: Path) -> None:
        """Empty src/ directory falls through to repo root scan."""
        (tmp_path / "src").mkdir()
        flat_pkg = tmp_path / "my_pkg"
        flat_pkg.mkdir()
        (flat_pkg / "__init__.py").touch()

        layout = detect_package_layout(tmp_path)
        assert layout.layout_style == LayoutStyle.FLAT
        assert layout.package_names == ["my_pkg"]
