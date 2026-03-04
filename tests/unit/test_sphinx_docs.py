"""Unit tests for SphinxDocsModule."""
from __future__ import annotations

from pathlib import Path

from dev_stack.modules.sphinx_docs import (
    SphinxDocsModule,
    _detect_package_name,
    _ensure_gitignore_entry,
    _render_conf_py,
    _render_index_rst,
    _render_makefile,
)


# ---------------------------------------------------------------------------
# Template renderers
# ---------------------------------------------------------------------------


class TestRenderConfPy:
    def test_contains_pkg_name(self) -> None:
        out = _render_conf_py("mylib")
        assert 'project = "mylib"' in out

    def test_contains_deterministic_timestamp(self) -> None:
        out = _render_conf_py("mylib")
        assert "html_last_updated_fmt = None" in out

    def test_contains_sys_path_insert(self) -> None:
        out = _render_conf_py("mylib")
        assert 'sys.path.insert(0, os.path.abspath("../src"))' in out


class TestRenderIndexRst:
    def test_contains_toctree(self) -> None:
        out = _render_index_rst("mylib")
        assert ".. toctree::" in out

    def test_title_uses_pkg_name(self) -> None:
        out = _render_index_rst("coolpkg")
        assert "Welcome to coolpkg" in out


class TestRenderMakefile:
    def test_contains_w_flag(self) -> None:
        out = _render_makefile("mylib")
        assert "-W --keep-going" in out

    def test_clean_target(self) -> None:
        out = _render_makefile("mylib")
        assert "clean:" in out
        assert "rm -rf" in out


# ---------------------------------------------------------------------------
# _ensure_gitignore_entry
# ---------------------------------------------------------------------------


class TestEnsureGitignoreEntry:
    def test_creates_gitignore_if_missing(self, tmp_path: Path) -> None:
        result = _ensure_gitignore_entry(tmp_path)
        assert result is True
        content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
        assert "docs/_build/" in content

    def test_appends_to_existing(self, tmp_path: Path) -> None:
        gi = tmp_path / ".gitignore"
        gi.write_text("node_modules/\n", encoding="utf-8")
        result = _ensure_gitignore_entry(tmp_path)
        assert result is True
        content = gi.read_text(encoding="utf-8")
        assert "node_modules/" in content
        assert "docs/_build/" in content

    def test_noop_when_present(self, tmp_path: Path) -> None:
        gi = tmp_path / ".gitignore"
        gi.write_text("docs/_build/\n", encoding="utf-8")
        result = _ensure_gitignore_entry(tmp_path)
        assert result is False


# ---------------------------------------------------------------------------
# _detect_package_name
# ---------------------------------------------------------------------------


class TestDetectPackageName:
    def test_reads_from_manifest(self) -> None:
        manifest = {"modules": {"uv_project": {"config": {"package_name": "from_manifest"}}}}
        name = _detect_package_name(Path("/tmp/fake"), manifest)
        assert name == "from_manifest"

    def test_scans_src_directory(self, tmp_path: Path) -> None:
        pkg = tmp_path / "src" / "alpha_pkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()
        name = _detect_package_name(tmp_path)
        assert name == "alpha_pkg"

    def test_falls_back_to_repo_name(self, tmp_path: Path) -> None:
        # No manifest, no src packages. Uses repo dir name
        name = _detect_package_name(tmp_path)
        # tmp_path names are random but will be normalized
        assert isinstance(name, str)
        assert len(name) > 0


# ---------------------------------------------------------------------------
# SphinxDocsModule
# ---------------------------------------------------------------------------


class TestSphinxDocsModuleInstall:
    def test_install_creates_docs(self, tmp_path: Path) -> None:
        # Create src package so detect works
        pkg = tmp_path / "src" / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()

        module = SphinxDocsModule(tmp_path, {})
        result = module.install()

        assert result.success is True
        assert (tmp_path / "docs" / "conf.py").exists()
        assert (tmp_path / "docs" / "index.rst").exists()
        assert (tmp_path / "docs" / "Makefile").exists()

    def test_install_rejects_existing_file(self, tmp_path: Path) -> None:
        pkg = tmp_path / "src" / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "conf.py").write_text("# existing", encoding="utf-8")

        module = SphinxDocsModule(tmp_path, {})
        result = module.install()

        assert result.success is False
        assert "already exists" in result.message

    def test_install_force_overwrites(self, tmp_path: Path) -> None:
        pkg = tmp_path / "src" / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "conf.py").write_text("# existing", encoding="utf-8")

        module = SphinxDocsModule(tmp_path, {})
        result = module.install(force=True)

        assert result.success is True
        content = (docs / "conf.py").read_text(encoding="utf-8")
        assert "mypkg" in content


class TestSphinxDocsModuleVerify:
    def test_verify_healthy(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "conf.py").touch()
        (docs / "index.rst").touch()
        (docs / "Makefile").touch()

        module = SphinxDocsModule(tmp_path, {})
        status = module.verify()
        assert status.healthy is True

    def test_verify_unhealthy(self, tmp_path: Path) -> None:
        module = SphinxDocsModule(tmp_path, {})
        status = module.verify()
        assert status.healthy is False
        assert "conf.py" in status.issue


class TestSphinxDocsModuleUninstall:
    def test_uninstall_removes_files(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "conf.py").touch()
        (docs / "index.rst").touch()
        (docs / "Makefile").touch()

        module = SphinxDocsModule(tmp_path, {})
        result = module.uninstall()
        assert result.success is True
        assert not (docs / "conf.py").exists()


class TestSphinxDocsModulePreviewFiles:
    def test_preview_returns_three_files(self, tmp_path: Path) -> None:
        pkg = tmp_path / "src" / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()

        module = SphinxDocsModule(tmp_path, {})
        preview = module.preview_files()

        assert len(preview) == 3
        assert Path("docs/conf.py") in preview
        assert Path("docs/index.rst") in preview
        assert Path("docs/Makefile") in preview

    def test_preview_content_uses_package_name(self, tmp_path: Path) -> None:
        pkg = tmp_path / "src" / "coolpkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").touch()

        module = SphinxDocsModule(tmp_path, {})
        preview = module.preview_files()

        assert "coolpkg" in preview[Path("docs/conf.py")]
