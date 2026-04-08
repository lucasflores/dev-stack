"""Unit tests for init_cmd helper functions (FR-005, FR-006, 018)."""
from __future__ import annotations

from pathlib import Path

import click
import pytest

from dev_stack.cli.init_cmd import (
    _detect_and_migrate_requirements,
    _detect_root_packages,
    _set_brownfield_pipeline_defaults,
)


# ── FR-005: _detect_and_migrate_requirements ──────────────────────────

_MINIMAL_PYPROJECT = """\
[project]
name = "myproject"
version = "0.1.0"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""


class TestDetectAndMigrateRequirements:
    """Tests for requirements.txt detection and migration."""

    def test_no_requirements_file_is_noop(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(_MINIMAL_PYPROJECT)
        # Should not raise or output anything
        _detect_and_migrate_requirements(tmp_path, interactive=False, json_output=False)

    def test_parses_valid_pinned_requirements(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(_MINIMAL_PYPROJECT)
        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.31.0\nflask>=3.0\n")

        _detect_and_migrate_requirements(tmp_path, interactive=False, json_output=False)

        # Non-interactive should warn but not merge
        import tomllib
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        assert "dependencies" not in data.get("project", {})

    def test_skips_comments_blanks_editables(self, tmp_path: Path, monkeypatch) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(_MINIMAL_PYPROJECT)
        req = tmp_path / "requirements.txt"
        req.write_text("# a comment\n\n-e ./local-pkg\nhttps://example.com/pkg.tar.gz\nvalid-pkg\n")

        # Simulate user confirming merge
        monkeypatch.setattr(click, "confirm", lambda *a, **kw: True)
        _detect_and_migrate_requirements(tmp_path, interactive=True, json_output=False)

        import tomllib
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        deps = data["project"]["dependencies"]
        assert "valid-pkg" in deps
        assert len(deps) == 1  # only valid-pkg, not editable or URL

    def test_merge_into_pyproject_dependencies(self, tmp_path: Path, monkeypatch) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(_MINIMAL_PYPROJECT)
        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.31.0\nclick>=8.0\n")

        monkeypatch.setattr(click, "confirm", lambda *a, **kw: True)
        _detect_and_migrate_requirements(tmp_path, interactive=True, json_output=False)

        import tomllib
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        deps = data["project"]["dependencies"]
        assert "requests==2.31.0" in deps
        assert "click>=8.0" in deps

    def test_ci_warns_only_in_noninteractive(self, tmp_path: Path, capsys) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(_MINIMAL_PYPROJECT)
        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.31.0\n")

        _detect_and_migrate_requirements(tmp_path, interactive=False, json_output=False)

        captured = capsys.readouterr()
        assert "skipping" in captured.err.lower() or "warning" in captured.err.lower()

    def test_no_duplicates_on_merge(self, tmp_path: Path, monkeypatch) -> None:
        pyproject_text = """\
[project]
name = "myproject"
version = "0.1.0"
dependencies = ["requests>=2.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(pyproject_text)
        req = tmp_path / "requirements.txt"
        req.write_text("requests==2.31.0\nnew-dep\n")

        monkeypatch.setattr(click, "confirm", lambda *a, **kw: True)
        _detect_and_migrate_requirements(tmp_path, interactive=True, json_output=False)

        import tomllib
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        deps = data["project"]["dependencies"]
        # "requests" already existed — should NOT be duplicated
        req_count = sum(1 for d in deps if d.lower().startswith("requests"))
        assert req_count == 1
        assert "new-dep" in deps


# ── FR-006: _detect_root_packages ─────────────────────────────────────


class TestDetectRootPackages:
    """Tests for root-level package detection and migration guidance."""

    def test_detects_root_packages(self, tmp_path: Path, capsys) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        _detect_root_packages(tmp_path, json_output=False)
        captured = capsys.readouterr()
        assert "mypkg" in captured.out
        assert "src/" in captured.out

    def test_no_output_when_no_packages(self, tmp_path: Path, capsys) -> None:
        _detect_root_packages(tmp_path, json_output=False)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_ignores_src_layout_packages(self, tmp_path: Path, capsys) -> None:
        # Packages inside src/ should not trigger guidance
        src = tmp_path / "src" / "mypkg"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("")
        _detect_root_packages(tmp_path, json_output=False)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_json_output_for_detected_packages(self, tmp_path: Path, capsys) -> None:
        import json as _json

        pkg = tmp_path / "eval"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        _detect_root_packages(tmp_path, json_output=True)
        captured = capsys.readouterr()
        data = _json.loads(captured.out)
        assert data["info"] == "root_packages_detected"
        assert "eval" in data["packages"]


# ── 018: _set_brownfield_pipeline_defaults ─────────────────────────────


class TestSetBrownfieldPipelineDefaults:
    """Tests for strict_docs=false injection into pyproject.toml."""

    def test_sets_strict_docs_false(self, tmp_path: Path) -> None:
        import tomllib

        import tomli_w

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(tomli_w.dumps({"project": {"name": "test"}}))

        _set_brownfield_pipeline_defaults(tmp_path)

        with open(pyproject, "rb") as fh:
            data = tomllib.load(fh)
        assert data["tool"]["dev-stack"]["pipeline"]["strict_docs"] is False

    def test_preserves_existing_pipeline_config(self, tmp_path: Path) -> None:
        import tomllib

        import tomli_w

        existing = {
            "tool": {"dev-stack": {"pipeline": {"visualize": False}}},
            "project": {"name": "test"},
        }
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(tomli_w.dumps(existing))

        _set_brownfield_pipeline_defaults(tmp_path)

        with open(pyproject, "rb") as fh:
            data = tomllib.load(fh)
        assert data["tool"]["dev-stack"]["pipeline"]["visualize"] is False
        assert data["tool"]["dev-stack"]["pipeline"]["strict_docs"] is False

    def test_does_not_overwrite_explicit_true(self, tmp_path: Path) -> None:
        import tomllib

        import tomli_w

        existing = {"tool": {"dev-stack": {"pipeline": {"strict_docs": True}}}}
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(tomli_w.dumps(existing))

        _set_brownfield_pipeline_defaults(tmp_path)

        with open(pyproject, "rb") as fh:
            data = tomllib.load(fh)
        assert data["tool"]["dev-stack"]["pipeline"]["strict_docs"] is True

    def test_noop_when_no_pyproject(self, tmp_path: Path) -> None:
        # Should not raise
        _set_brownfield_pipeline_defaults(tmp_path)
