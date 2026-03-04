# Research: Init & Pipeline Enhancements

**Feature Branch**: `002-init-pipeline-enhancements` | **Date**: 2026-02-28

## Overview

Five research tasks were dispatched to resolve NEEDS CLARIFICATION items from the Technical Context and to gather best-practice patterns for each integration point.

---

## R-1: `uv init --package` Output and Behavior

**Context**: The `uv_project` module delegates scaffolding to `uv init --package`. We need to know the exact file tree, name normalization, conflict behavior, and available flags.

**Decision**: `uv init --package <name>` (uv ≥ 0.9.24) produces:

```text
<name>/
├── .git/
├── .gitignore
├── .python-version
├── README.md
├── pyproject.toml
└── src/<normalized_name>/__init__.py
```

| Aspect | Finding |
|--------|---------|
| Name normalization | Hyphens → underscores for the package directory (PEP 503/625). `[project] name` retains hyphens. |
| Build system (default) | `uv_build` (uv's own backend). Override with `--build-backend setuptools\|hatch\|flit\|...`. |
| Key flags | `--python <VER>`, `--no-readme`, `--bare`, `--name <NAME>`, `--vcs none`, `--no-pin-python`, `--author-from none`. |
| `__init__.py` content | Contains a `main()` stub and a `[project.scripts]` entry point. |
| Conflict behavior | `uv init` (no path arg) in a directory with existing `pyproject.toml` **fails with exit code 2** ("Project is already initialized"). `uv init <path>` creates a subdirectory. |

**Rationale**: `uv_build` is the default since late 2025, but `--build-backend` allows overriding for projects that prefer setuptools/hatch. Name normalization follows the same PEP standards the spec already assumes.

**Alternatives considered**:
- `hatchling` — previous default, still available via `--build-backend hatch`.
- `setuptools` — what dev-stack itself uses. Available via flag.

**Impact on spec**: FR-001 is confirmed. The module must use `uv init --package` (no path arg) to avoid the subdirectory trap. Brownfield detection (FR-008) should check for existing `pyproject.toml` *before* calling `uv init` and skip the call entirely in brownfield mode, delegating conflict resolution to `preview_files()` → `ConflictReport`.

---

## R-2: Programmatic TOML Augmentation

**Context**: After `uv init`, the module augments `pyproject.toml` with tool configuration sections. We need a strategy for reading, modifying, and writing TOML without introducing new dependencies.

**Decision**: Use `tomllib` (stdlib read) + `tomli_w` (existing dep, write) for the read→modify→write pattern.

| Aspect | Finding |
|--------|---------|
| Roundtrip fidelity | Data integrity preserved. Formatting normalized (trailing commas added). **Comments are lost**. |
| Section existence check | `data.setdefault('tool', {})` then `if 'mypy' not in data['tool']`. |
| Optional-dependencies | `data['project'].setdefault('optional-dependencies', {})['docs'] = [...]` works correctly. |
| Comment-preserving alt | `tomlkit` preserves comments/formatting but is **not** a current dependency. |

**Rationale**: `tomllib` + `tomli_w` is the pragmatic choice:
1. Already in the dependency tree (`tomli_w>=1.0`).
2. `tomllib` is stdlib since Python 3.11 (project minimum).
3. `uv init` generates TOML with no comments, so comment loss is irrelevant for greenfield.
4. The existing `manifest.py` already uses this exact pattern.

**Alternatives considered**:
- `tomlkit` — comment-preserving, but requires a new dependency. Worth reconsidering only if brownfield augmentation must preserve user comments (the skip-if-exists strategy avoids this).
- String/regex manipulation — fragile, rejected.

**Impact on spec**: FR-003 brownfield skip-if-exists is the right strategy. Since we only *add* missing sections and never *modify* existing ones, comment loss in existing `[tool.*]` sections is irrelevant (those sections are skipped entirely).

---

## R-3: Sphinx apidoc + build Invocation

**Context**: The `docs-api` stage and `sphinx_docs` module need to invoke Sphinx programmatically. We need the correct invocation, `src/` layout configuration, and CI-friendly flags.

**Decision**: Two-step command sequence using `python3 -m` invocation:

```bash
# Step 1: Generate .rst stubs from source
python3 -m sphinx.ext.apidoc -o docs/api src/<pkg_name> -f --module-first -e

# Step 2: Build HTML docs
python3 -m sphinx docs docs/_build -W --keep-going -b html
```

| Aspect | Finding |
|--------|---------|
| Module invocation | Use `python3 -m sphinx.ext.apidoc` / `python3 -m sphinx` — CLI binaries may not be on PATH in venvs. |
| Deterministic output | `-f` (force overwrite) ensures reproducibility. |
| Warnings as errors | `-W` flag on `sphinx-build`. `--keep-going` reports all errors. |
| Empty package handling | `sphinx-apidoc` on empty packages still generates valid stubs. Does **not** fail. |

**Minimal `conf.py` for `src/` layout:**
```python
import os, sys
sys.path.insert(0, os.path.abspath("../src"))

project = "<pkg-name>"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx.ext.viewcode"]
html_theme = "alabaster"
```

**Minimal `index.rst`:**
```rst
Welcome to <pkg-name>
======================

.. toctree::
   :maxdepth: 2

   api/modules
```

**Minimal `Makefile`:**
```makefile
SPHINXOPTS  ?= -W --keep-going
SOURCEDIR   = .
BUILDDIR    = _build

html:
	python3 -m sphinx -b html $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)

clean:
	rm -rf $(BUILDDIR)
```

**Rationale**: `python3 -m` invocation avoids PATH issues, matching the existing pattern in `stages.py` (`_run_command()`). The `-f -e --module-first` flags produce clean output. `sys.path.insert` in `conf.py` is required for `src/` layout autodoc.

**Alternatives considered**:
- `sphinx-quickstart` — generates excessive boilerplate (batch files, unused Makefiles). Overkill.
- `pdoc` / `mkdocstrings` — MkDocs ecosystem, different from Sphinx standard.
- `myst-parser` — Markdown in Sphinx. Nice optional add-on but not needed for initial API docs scaffolding.

**Impact on spec**: FR-015, FR-017, FR-019a confirmed. The `docs/_build/` output directory and `.gitignore` entry are correct. The `conf.py` template must include `sys.path.insert` for `src/` layout.

---

## R-4: mypy Invocation and Pre-commit Integration

**Context**: The typecheck stage and pre-commit hook need to invoke mypy correctly for a `src/` layout project.

**Decision**: Use `python3 -m mypy src/<pkg_name>` with `pyproject.toml` configuration.

**`pyproject.toml` config (FR-003 curated defaults):**
```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_incomplete_defs = true
check_untyped_defs = true
mypy_path = "src"
```

| Aspect | Finding |
|--------|---------|
| Detection / graceful skip | `shutil.which("mypy")` for PATH check. Use existing `_run_command()` pattern. |
| `src/` layout | Set `mypy_path = "src"` in `[tool.mypy]` or point mypy at `src/<pkg>` directly. |
| Exit codes | 0 = clean, 1 = type errors found, 2 = fatal error (missing config, etc.). |

**Pre-commit hook (local, matching existing pattern):**
```yaml
- repo: local
  hooks:
    - id: mypy
      name: mypy type check
      entry: python3 -m mypy src/
      language: system
      pass_filenames: false
      types: [python]
```

**Rationale**: Local hook matches the existing `pre-commit-config.yaml` pattern (all hooks use `repo: local`). Avoids version drift issues with `mirrors-mypy`. `python3 -m mypy` is consistent with Sphinx invocation pattern.

**Alternatives considered**:
- `mirrors-mypy` pre-commit repo — requires `additional_dependencies` for type stubs, brittle.
- `pyright` — faster but different error semantics.
- `pytype` — less adoption.

**Impact on spec**: FR-022–FR-026 confirmed. The executor should use `_run_command()` → `shutil.which("mypy")` for detection, matching the existing lint/test/security stage patterns. The curated defaults from FR-003 are validated as sensible for an incremental strict path.

---

## R-5: `uv lock` Behavior

**Context**: After augmenting `pyproject.toml` with optional-dependencies, the module runs `uv lock`. We need to verify this works without special flags.

**Decision**: `uv lock` (no special flags) correctly re-resolves after optional-dependency augmentation.

| Aspect | Finding |
|--------|---------|
| After adding optional-deps | `uv lock` re-resolves correctly. Exit code 0. ~1 second. |
| Output file | Always `uv.lock` at project root (same dir as `pyproject.toml`). |
| Idempotency | Running twice produces the same result. |
| Key flags | `--check` (verify only), `--dry-run`, `-U` (upgrade). None needed for initial lock. |

**Rationale**: No special flags needed. `uv lock` detects `pyproject.toml` changes and re-resolves automatically. The lockfile path is fixed at `uv.lock` in the project root.

**Alternatives considered**:
- `uv lock --upgrade` — only for re-resolving pinned versions to latest. Not needed for initial lock.
- `uv sync` — locks *and* installs. Has side effects. `uv lock` is minimal/safe for scaffolding.
- `uv pip compile` — lower-level, produces `requirements.txt`. Irrelevant for project-mode.

**Impact on spec**: FR-007 confirmed. The module runs `uv lock` after all augmentations and registers `uv.lock` as a managed artifact. No special error handling beyond checking the exit code and capturing stderr on failure (edge case: unresolvable dependencies).
