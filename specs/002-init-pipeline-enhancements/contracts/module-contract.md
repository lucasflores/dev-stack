# Module Contract: UV Project & Sphinx Docs Modules

**Branch**: `002-init-pipeline-enhancements` | **Date**: 2026-02-28

---

## Overview

This contract defines the interface and behavioral guarantees for two new modules: `uv_project` and `sphinx_docs`. Both extend the existing `ModuleBase` ABC and follow all conventions established in the [001-dev-stack-ecosystem module contract](../../001-dev-stack-ecosystem/contracts/module-contract.md).

---

## UvProjectModule

### Registration

```python
@register_module
class UvProjectModule(ModuleBase):
    NAME = "uv_project"
    VERSION = "0.1.0"
    DEPENDS_ON: Sequence[str] = ()
    MANAGED_FILES: Sequence[str] = (
        "pyproject.toml",
        ".python-version",
        ".gitignore",
        "README.md",
        "uv.lock",
        "tests/__init__.py",
        "tests/test_placeholder.py",
        # src/{pkg}/__init__.py is dynamic — registered at install time
    )
```

### install(*, force: bool = False) -> ModuleResult

**Preconditions**:
- `shutil.which("uv")` returns a valid path, **OR** abort with `ModuleResult(success=False, message="uv CLI not found ...")`
- `repo_root` is a valid directory

**Sequence**:
1. Normalize repo directory name to valid Python identifier via `_normalize_name()`
2. Check if `pyproject.toml` already exists at `repo_root`:
   - If **yes** and `force=False`: delegate to `preview_files()` → return `ModuleResult(success=False)` with conflict info
   - If **yes** and `force=True`: proceed (overwrite)
   - If **no**: run `uv init --package` in `repo_root`
3. Run `uv init --package <normalized_name>` (no path arg — avoids subdirectory trap)
4. Augment `pyproject.toml`:
   - Read with `tomllib.load()`
   - For each tool section (`[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.coverage.run]`, `[tool.mypy]`): add ONLY if not present (skip-if-exists)
   - Add `[project.optional-dependencies]` groups (`docs`, `dev`): add ONLY if group not present
   - Write back with `tomli_w.dump()`
5. Scaffold `tests/__init__.py` and `tests/test_placeholder.py`
6. Run `uv lock` — capture exit code and stderr
   - If exit code != 0: report failure but do NOT rollback pyproject.toml (leave for manual fix)
7. Register all created files in `ModuleResult.files_created`

**Postconditions**:
- `pyproject.toml` exists with `[build-system]`, all tool sections, and optional-dep groups
- `src/{pkg}/__init__.py` exists
- `.python-version` exists
- `uv.lock` exists (unless `uv lock` failed)
- `tests/test_placeholder.py` exists and passes `pytest`

**Return**:
```python
ModuleResult(
    success=True,
    message="UV project initialized: {pkg_name}",
    files_created=[
        Path("pyproject.toml"),
        Path(f"src/{pkg_name}/__init__.py"),
        Path(".python-version"),
        Path(".gitignore"),
        Path("README.md"),
        Path("uv.lock"),
        Path("tests/__init__.py"),
        Path("tests/test_placeholder.py"),
    ],
    files_modified=[],
    files_deleted=[],
    warnings=[],  # or ["uv lock failed: <reason>"] if lock failed
)
```

### uninstall() -> ModuleResult

**Behavior**: Removes `tests/test_placeholder.py`, `tests/__init__.py` (if empty), `uv.lock`. Does NOT remove `pyproject.toml`, `src/`, `.python-version`, `.gitignore`, or `README.md` — these are foundational and may have user modifications.

### update() -> ModuleResult

**Behavior**: Re-reads `pyproject.toml` and adds any missing tool sections using skip-if-exists. Runs `uv lock` if `pyproject.toml` was modified. Does NOT re-run `uv init`.

### verify() -> ModuleStatus

**Checks**:
1. `pyproject.toml` exists
2. `src/{pkg}/__init__.py` exists (pkg name from manifest or directory scan)
3. `.python-version` exists
4. `uv.lock` exists

**Returns**: `ModuleStatus(healthy=True)` if all checks pass; `healthy=False` with `issue` describing what's missing.

### preview_files() -> dict[Path, str]

**Returns**: Dictionary mapping relative paths to their proposed content. For `pyproject.toml`, generates the fully-augmented content. For other files, returns the template content. Used by brownfield conflict detection.

---

## SphinxDocsModule

### Registration

```python
@register_module
class SphinxDocsModule(ModuleBase):
    NAME = "sphinx_docs"
    VERSION = "0.1.0"
    DEPENDS_ON: Sequence[str] = ("uv_project",)
    MANAGED_FILES: Sequence[str] = (
        "docs/conf.py",
        "docs/index.rst",
        "docs/Makefile",
    )
```

### install(*, force: bool = False) -> ModuleResult

**Preconditions**:
- `uv_project` module is already installed (enforced by dependency resolution)
- `repo_root / "src"` exists

**Sequence**:
1. Detect package name from `src/` directory or manifest
2. Create `docs/` directory if not exists
3. Render and write `docs/conf.py` (with `sys.path.insert` for src/ layout)
4. Render and write `docs/index.rst` (with toctree pointing to `api/modules`)
5. Render and write `docs/Makefile` (with `-W --keep-going` flags)
6. Append `docs/_build/` to `.gitignore` if not already present
7. Register files in `ModuleResult.files_created`

**Postconditions**:
- `docs/conf.py` exists with correct `sys.path.insert` and extensions
- `docs/index.rst` exists with toctree
- `docs/Makefile` exists
- `docs/_build/` is in `.gitignore`

**Return**:
```python
ModuleResult(
    success=True,
    message="Sphinx docs scaffolded for: {pkg_name}",
    files_created=[
        Path("docs/conf.py"),
        Path("docs/index.rst"),
        Path("docs/Makefile"),
    ],
    files_modified=[Path(".gitignore")],  # if docs/_build/ was appended
    files_deleted=[],
    warnings=[],
)
```

### Template: docs/conf.py

```python
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
```

### Template: docs/index.rst

```rst
Welcome to {pkg_name}
{'=' * (len("Welcome to ") + len(pkg_name))}

.. toctree::
   :maxdepth: 2

   api/modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
```

### Template: docs/Makefile

```makefile
SPHINXOPTS  ?= -W --keep-going
SOURCEDIR   = .
BUILDDIR    = _build

html:
	python3 -m sphinx -b html $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)

apidoc:
	python3 -m sphinx.ext.apidoc -o api ../src/{pkg_name} -f --module-first -e

clean:
	rm -rf $(BUILDDIR) api/

.PHONY: html apidoc clean
```

### uninstall() -> ModuleResult

**Behavior**: Removes `docs/conf.py`, `docs/index.rst`, `docs/Makefile`. Does NOT remove `docs/` directory (may contain user content). Does NOT modify `.gitignore`.

### update() -> ModuleResult

**Behavior**: Regenerates templates if module version has increased. Does NOT overwrite if files are user-modified (checks hash against manifest).

### verify() -> ModuleStatus

**Checks**:
1. `docs/conf.py` exists
2. `docs/index.rst` exists
3. `docs/Makefile` exists

### preview_files() -> dict[Path, str]

**Returns**: Dictionary with rendered `docs/conf.py`, `docs/index.rst`, `docs/Makefile` content.

---

## Module Resolution Order (updated)

```
1. uv_project      (no deps)           — NEW
2. sphinx_docs     (depends: uv_project) — NEW
3. hooks           (no deps)
4. speckit         (no deps)
5. ci-workflows    (no deps)
6. docker          (no deps)
7. mcp-servers     (no deps)
8. visualization   (depends: hooks)
```

## Module File Ownership (additions)

| Module | Managed Files |
|--------|---------------|
| uv_project | `pyproject.toml`, `src/{pkg}/__init__.py`, `.python-version`, `.gitignore`, `README.md`, `uv.lock`, `tests/__init__.py`, `tests/test_placeholder.py` |
| sphinx_docs | `docs/conf.py`, `docs/index.rst`, `docs/Makefile` |

---

## Error Handling

Both modules use the existing error types from `src/dev_stack/errors.py`:

| Scenario | Error / Behavior |
|----------|-----------------|
| `uv` not on PATH | `ModuleResult(success=False, message="uv CLI not found ...")` — does NOT raise |
| `uv init` exits non-zero | `ModuleResult(success=False, message=<stderr>)` — triggers rollback |
| `uv lock` exits non-zero | `ModuleResult(success=True, warnings=["uv lock failed: ..."])` — partial success |
| Brownfield conflict (no force) | `preview_files()` returns conflicts → `ConflictReport` → interactive resolution |
| Dependency not met (sphinx_docs without uv_project) | `DependencyError` raised by `resolve_module_names()` before install |
| Disk full / permission error | Let OS exception propagate — caught by CLI error handler |
