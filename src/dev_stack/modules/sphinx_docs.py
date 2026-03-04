"""Sphinx Docs module — Sphinx documentation scaffolding."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from .base import ModuleBase, ModuleResult, ModuleStatus


# ---------------------------------------------------------------------------
# Template renderers (T020)
# ---------------------------------------------------------------------------


def _render_conf_py(pkg_name: str) -> str:
    """Generate ``docs/conf.py`` content with ``sys.path.insert`` for src/ layout."""
    return f'''\
"""Sphinx configuration for {pkg_name}."""
import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "{pkg_name}"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
html_theme = "alabaster"

# Deterministic build: suppress dynamic timestamps.
# For full CI reproducibility also set SOURCE_DATE_EPOCH=0 in the
# build environment.
html_last_updated_fmt = None
'''


def _render_index_rst(pkg_name: str) -> str:
    """Generate ``docs/index.rst`` with toctree."""
    title = f"Welcome to {pkg_name}"
    underline = "=" * len(title)
    return f"""\
{title}
{underline}

.. toctree::
   :maxdepth: 2

   api/modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
"""


def _render_makefile(pkg_name: str) -> str:
    """Generate ``docs/Makefile`` with ``-W --keep-going`` flags."""
    return f"""\
SPHINXOPTS  ?= -W --keep-going
SOURCEDIR   = .
BUILDDIR    = _build

html:
\tpython3 -m sphinx -b html $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)

apidoc:
\tpython3 -m sphinx.ext.apidoc -o api ../src/{pkg_name} -f --module-first -e

clean:
\trm -rf $(BUILDDIR) api/

.PHONY: html apidoc clean
"""


def _ensure_gitignore_entry(repo_root: Path) -> bool:
    """Append ``docs/_build/`` to ``.gitignore`` if not already present.

    Returns True if the file was modified.
    """
    gitignore = repo_root / ".gitignore"
    entry = "docs/_build/"

    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if entry in content:
            return False
        if not content.endswith("\n"):
            content += "\n"
        content += f"{entry}\n"
        gitignore.write_text(content, encoding="utf-8")
        return True
    else:
        gitignore.write_text(f"{entry}\n", encoding="utf-8")
        return True


def _detect_package_name(repo_root: Path, manifest: dict[str, Any] | None = None) -> str:
    """Resolve the package name from manifest or ``src/`` directory scan."""
    if manifest:
        modules = manifest.get("modules", {})
        uv_entry = modules.get("uv_project", {})
        config = uv_entry.get("config", {})
        if "package_name" in config:
            return config["package_name"]

    src_dir = repo_root / "src"
    if src_dir.is_dir():
        candidates = sorted(
            d.name for d in src_dir.iterdir() if d.is_dir() and (d / "__init__.py").is_file()
        )
        if candidates:
            return candidates[0]

    # Last resort: normalize the repo directory name
    from .uv_project import _normalize_name

    return _normalize_name(repo_root.resolve().name)


# ---------------------------------------------------------------------------
# Module class (T019)
# ---------------------------------------------------------------------------


class SphinxDocsModule(ModuleBase):
    """Scaffold Sphinx documentation configuration files."""

    NAME = "sphinx_docs"
    VERSION = "0.1.0"
    DEPENDS_ON: Sequence[str] = ("uv_project",)
    MANAGED_FILES: Sequence[str] = (
        "docs/conf.py",
        "docs/index.rst",
        "docs/Makefile",
    )

    # ------------------------------------------------------------------
    # install (T021)
    # ------------------------------------------------------------------

    def install(self, *, force: bool = False) -> ModuleResult:
        pkg_name = _detect_package_name(self.repo_root, self.manifest)
        created: list[Path] = []
        modified: list[Path] = []

        docs_dir = self.repo_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Write templates
        targets = {
            docs_dir / "conf.py": _render_conf_py(pkg_name),
            docs_dir / "index.rst": _render_index_rst(pkg_name),
            docs_dir / "Makefile": _render_makefile(pkg_name),
        }

        for dest, content in targets.items():
            if dest.exists() and not force:
                return ModuleResult(
                    success=False,
                    message=f"File already exists: {dest.relative_to(self.repo_root)} — use force=True to overwrite",
                )
            dest.write_text(content, encoding="utf-8")
            created.append(dest)

        # Append docs/_build/ to .gitignore
        if _ensure_gitignore_entry(self.repo_root):
            modified.append(self.repo_root / ".gitignore")

        return ModuleResult(
            success=True,
            message=f"Sphinx docs scaffolded for: {pkg_name}",
            files_created=created,
            files_modified=modified,
        )

    # ------------------------------------------------------------------
    # verify (T022)
    # ------------------------------------------------------------------

    def verify(self) -> ModuleStatus:
        missing: list[str] = []
        for rel in self.MANAGED_FILES:
            if not (self.repo_root / rel).exists():
                missing.append(rel)
        healthy = len(missing) == 0
        issue = f"Missing: {', '.join(missing)}" if missing else None
        return ModuleStatus(
            name=self.NAME,
            installed=True,
            version=self.VERSION,
            healthy=healthy,
            issue=issue,
        )

    # ------------------------------------------------------------------
    # uninstall (T022)
    # ------------------------------------------------------------------

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []
        for rel in self.MANAGED_FILES:
            p = self.repo_root / rel
            if p.exists():
                p.unlink()
                deleted.append(p)
        return ModuleResult(True, "Sphinx docs files removed", files_deleted=deleted)

    # ------------------------------------------------------------------
    # update (T022)
    # ------------------------------------------------------------------

    def update(self) -> ModuleResult:
        # Regenerate templates (force mode)
        return self.install(force=True)

    # ------------------------------------------------------------------
    # preview_files (T022)
    # ------------------------------------------------------------------

    def preview_files(self) -> dict[Path, str]:
        pkg_name = _detect_package_name(self.repo_root, self.manifest)
        return {
            Path("docs/conf.py"): _render_conf_py(pkg_name),
            Path("docs/index.rst"): _render_index_rst(pkg_name),
            Path("docs/Makefile"): _render_makefile(pkg_name),
        }


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(SphinxDocsModule)
