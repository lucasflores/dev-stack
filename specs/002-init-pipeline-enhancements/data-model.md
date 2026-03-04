# Data Model: Init & Pipeline Enhancements

**Branch**: `002-init-pipeline-enhancements` | **Date**: 2026-02-28

---

## Entity Relationship Overview

```
StackManifest 1──* Module
UvProjectModule ──|> ModuleBase
SphinxDocsModule ──|> ModuleBase
SphinxDocsModule *──1 UvProjectModule  (DEPENDS_ON)
PipelineStage 1──1 StageExecutor
build_pipeline_stages() ──> [8 PipelineStage]
PyprojectAugmentation 1──* ToolSection
PyprojectAugmentation 1──* OptionalDepGroup
```

---

## New Entities

### UvProjectModule

Subclass of `ModuleBase`. Delegates Python project scaffolding to `uv init --package` and augments the generated `pyproject.toml` with opinionated tool configuration.

| Field / Attr | Type | Value | Description |
|-------------|------|-------|-------------|
| NAME | str | `"uv_project"` | Module identifier in registry |
| VERSION | str | `"0.1.0"` | Initial version |
| DEPENDS_ON | Sequence[str] | `()` | Foundation module — no dependencies |
| MANAGED_FILES | Sequence[str] | `("pyproject.toml", "src/{pkg}/__init__.py", ".python-version", ".gitignore", "README.md", "uv.lock", "tests/__init__.py", "tests/test_placeholder.py")` | Files created or augmented |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `install` | `(*, force: bool = False) -> ModuleResult` | Runs `uv init --package`, augments pyproject.toml, scaffolds tests, runs `uv lock` |
| `uninstall` | `() -> ModuleResult` | Removes managed files (except user-modified pyproject.toml) |
| `update` | `() -> ModuleResult` | Re-augments pyproject.toml if new tool sections are needed |
| `verify` | `() -> ModuleStatus` | Checks pyproject.toml, src/{pkg}/__init__.py, .python-version, uv.lock exist |
| `preview_files` | `() -> dict[Path, str]` | Returns all files the module would create, for brownfield conflict detection |

**Internal helpers**:

| Helper | Purpose |
|--------|---------|
| `_normalize_name(name: str) -> str` | Converts directory name to valid Python identifier (PEP 503/625) |
| `_run_uv_init(repo_root: Path, pkg_name: str) -> tuple[bool, str]` | Shells out to `uv init --package` |
| `_augment_pyproject(path: Path, pkg_name: str) -> None` | Reads TOML, adds tool sections (skip-if-exists), writes back |
| `_scaffold_tests(repo_root: Path, pkg_name: str) -> list[Path]` | Creates tests/__init__.py and tests/test_placeholder.py |
| `_run_uv_lock(repo_root: Path) -> tuple[bool, str]` | Runs `uv lock`, returns success + output |

**Validation rules**:
- `uv` must be found on PATH (`shutil.which("uv")`) or install aborts with `ModuleResult(success=False)`
- Package name must start with a letter or underscore after normalization
- `uv init` exit code must be 0; any non-zero triggers rollback

**State transitions**:
- `not-installed` → `installed` (via `install()`)
- `installed` → `not-installed` (via `uninstall()`)
- `installed` → `installed` (via `update()` — re-augments)

---

### SphinxDocsModule

Subclass of `ModuleBase`. Scaffolds Sphinx configuration files and `.gitignore` entry for `docs/_build/`.

| Field / Attr | Type | Value | Description |
|-------------|------|-------|-------------|
| NAME | str | `"sphinx_docs"` | Module identifier in registry |
| VERSION | str | `"0.1.0"` | Initial version |
| DEPENDS_ON | Sequence[str] | `("uv_project",)` | Requires `uv_project` for `src/` layout |
| MANAGED_FILES | Sequence[str] | `("docs/conf.py", "docs/index.rst", "docs/Makefile")` | Template-generated files |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `install` | `(*, force: bool = False) -> ModuleResult` | Creates docs/conf.py, docs/index.rst, docs/Makefile; appends docs/_build/ to .gitignore |
| `uninstall` | `() -> ModuleResult` | Removes managed Sphinx config files |
| `update` | `() -> ModuleResult` | Re-scaffolds if templates are newer |
| `verify` | `() -> ModuleStatus` | Checks docs/conf.py, docs/index.rst, docs/Makefile exist |
| `preview_files` | `() -> dict[Path, str]` | Returns all Sphinx config files for conflict detection |

**Internal helpers**:

| Helper | Purpose |
|--------|---------|
| `_detect_package_name(repo_root: Path) -> str` | Resolves the package name from manifest or `src/` directory |
| `_render_conf_py(pkg_name: str) -> str` | Generates conf.py content with `sys.path.insert` for src/ layout |
| `_render_index_rst(pkg_name: str) -> str` | Generates index.rst with toctree pointing at apidoc output |
| `_render_makefile() -> str` | Generates Makefile with sphinx -W --keep-going flags |
| `_ensure_gitignore_entry(repo_root: Path) -> None` | Appends `docs/_build/` to .gitignore if not already present |

**Validation rules**:
- `uv_project` must be installed first (enforced by dependency resolution)
- The `src/` directory must exist

---

### PyprojectAugmentation

Schema for the TOML augmentation applied by `UvProjectModule._augment_pyproject()`. Not a runtime class — describes the structure of TOML sections added.

**Tool sections added (skip-if-exists)**:

| Section | Key Fields | Source |
|---------|-----------|--------|
| `[tool.ruff]` | `target-version`, `line-length`, `select`, `ignore` | Dev-stack opinionated defaults |
| `[tool.pytest.ini_options]` | `testpaths`, `addopts` | `["tests"]`, `--strict-markers -v` |
| `[tool.coverage.run]` | `source`, `omit` | `["src/{pkg}"]`, `["tests/*"]` |
| `[tool.mypy]` | See below | FR-003 curated defaults |

**`[tool.mypy]` schema (FR-003)**:

```toml
[tool.mypy]
python_version = "<from .python-version>"
strict = false
warn_return_any = true
warn_unused_configs = true
disallow_incomplete_defs = true
check_untyped_defs = true
mypy_path = "src"
```

**Optional-dependency groups added**:

| Group | Dependencies | Notes |
|-------|-------------|-------|
| `docs` | `sphinx>=7.0`, `sphinx-autodoc-typehints>=2.0`, `myst-parser>=3.0` | FR-004 |
| `dev` | `mypy>=1.10`, `pytest>=7.4`, `pytest-cov>=4.1`, `ruff>=0.3` | FR-005 |

**Skip-if-exists semantics** (FR-003, brownfield):
1. Read existing `pyproject.toml` with `tomllib`.
2. For each `[tool.*]` section: check `if key not in data.get('tool', {})`. Skip if present.
3. For each optional-dep group: check `if group not in data.get('project', {}).get('optional-dependencies', {})`. Skip if present.
4. Write back with `tomli_w` only if any sections were added.

---

## Modified Entities

### PipelineStage (updated)

The pipeline expands from 6 to 8 stages. The `PipelineStage` dataclass itself is unchanged; only the `build_pipeline_stages()` output changes.

**New 8-stage pipeline**:

| Order | Name | Failure Mode | Requires Agent | Executor | Change |
|-------|------|-------------|----------------|----------|--------|
| 1 | lint | HARD | no | `_execute_lint_stage` | unchanged |
| 2 | typecheck | HARD | no | `_execute_typecheck_stage` | **NEW** |
| 3 | test | HARD | no | `_execute_test_stage` | order 2→3 |
| 4 | security | HARD | no | `_execute_security_stage` | order 3→4 |
| 5 | docs-api | HARD | no | `_execute_docs_api_stage` | **NEW** (replaces old docs) |
| 6 | docs-narrative | SOFT | yes | `_execute_docs_narrative_stage` | **NEW** (split from old docs) |
| 7 | infra-sync | SOFT | no | `_execute_infra_sync_stage` | order 5→7 |
| 8 | commit-message | SOFT | yes | `_execute_commit_stage` | order 6→8 |

**New executor: `_execute_typecheck_stage`**:

```python
def _execute_typecheck_stage(context: StageContext) -> StageResult:
    """Run mypy type checking against project source."""
    start = time.perf_counter()
    
    # Graceful skip if mypy not installed
    if not shutil.which("mypy"):
        return StageResult(
            stage_name="typecheck",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.HARD,
            duration_ms=_elapsed_ms(start),
            skipped_reason="mypy not found, skipping type check",
        )
    
    # Detect src package directory
    src_dir = context.repo_root / "src"
    # Run mypy against src/
    success, output = _run_command(
        ("python3", "-m", "mypy", "src/"),
        context.repo_root,
    )
    
    return StageResult(
        stage_name="typecheck",
        status=StageStatus.PASS if success else StageStatus.FAIL,
        failure_mode=FailureMode.HARD,
        duration_ms=_elapsed_ms(start),
        output=output,
    )
```

**New executor: `_execute_docs_api_stage`**:

```python
def _execute_docs_api_stage(context: StageContext) -> StageResult:
    """Run Sphinx apidoc + build for deterministic API docs."""
    start = time.perf_counter()
    
    # Graceful skip if sphinx not installed
    if not shutil.which("sphinx-build"):
        # Also try module invocation detection
        try:
            import sphinx  # noqa: F401
        except ImportError:
            return StageResult(
                stage_name="docs-api",
                status=StageStatus.SKIP,
                failure_mode=FailureMode.HARD,
                duration_ms=_elapsed_ms(start),
                skipped_reason="sphinx not found, skipping API docs",
            )
    
    # Step 1: Generate .rst stubs
    pkg_name = _detect_src_package(context.repo_root)
    _run_command(
        ("python3", "-m", "sphinx.ext.apidoc", "-o", "docs/api",
         f"src/{pkg_name}", "-f", "--module-first", "-e"),
        context.repo_root,
    )
    
    # Step 2: Build HTML
    success, output = _run_command(
        ("python3", "-m", "sphinx", "docs", "docs/_build",
         "-W", "--keep-going", "-b", "html"),
        context.repo_root,
    )
    
    return StageResult(
        stage_name="docs-api",
        status=StageStatus.PASS if success else StageStatus.FAIL,
        failure_mode=FailureMode.HARD,
        duration_ms=_elapsed_ms(start),
        output=output,
    )
```

**Modified executor: `_execute_docs_narrative_stage`** (renamed from `_execute_docs_stage`):
- Retains agent invocation via `AgentBridge`
- Writes to `docs/guides/` instead of generic docs path
- Uses updated prompt template (narrative-only)

---

### DEFAULT_GREENFIELD_MODULES (updated)

```python
# Before
DEFAULT_GREENFIELD_MODULES: Sequence[str] = ("hooks", "speckit")

# After
DEFAULT_GREENFIELD_MODULES: Sequence[str] = ("uv_project", "sphinx_docs", "hooks", "speckit")
```

**Dependency resolution order** (via `resolve_module_names()`):
1. `uv_project` (no deps)
2. `sphinx_docs` (depends on `uv_project`)
3. `hooks` (no deps)
4. `speckit` (no deps)

---

### Module Registry Imports (updated)

```python
# Before
from . import ci_workflows, docker, hooks, mcp_servers, speckit, visualization

# After  
from . import ci_workflows, docker, hooks, mcp_servers, speckit, uv_project, sphinx_docs, visualization
```

---

### Pre-commit Hook Template (updated)

The `pre-commit-config.yaml` template adds a mypy hook entry:

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

---

### Docs Prompt Template (updated)

`templates/prompts/docs_update.txt` is revised to instruct narrative-only content:

- **Scope**: Tutorials, quickstarts, architecture walkthroughs, capability guides in `docs/guides/`
- **Exclusion**: "Do NOT generate API reference documentation. API docs are handled by the deterministic docs-api stage via Sphinx."
- **Output directory**: `docs/guides/`

---

## Managed Artifacts Registry

All new managed files tracked in `dev-stack.toml` manifest:

### UvProjectModule artifacts

| Path | Type | Hash Tracked | Rollback |
|------|------|-------------|----------|
| `pyproject.toml` | generated + augmented | yes | yes |
| `src/{pkg}/__init__.py` | generated | yes | yes |
| `.python-version` | generated | yes | yes |
| `.gitignore` | generated (augmented) | yes | yes |
| `README.md` | generated | yes | yes |
| `uv.lock` | generated | yes | yes |
| `tests/__init__.py` | generated | yes | yes |
| `tests/test_placeholder.py` | generated | yes | yes |

### SphinxDocsModule artifacts

| Path | Type | Hash Tracked | Rollback |
|------|------|-------------|----------|
| `docs/conf.py` | template-rendered | yes | yes |
| `docs/index.rst` | template-rendered | yes | yes |
| `docs/Makefile` | template-rendered | yes | yes |

### Infra-sync coverage

The `_execute_infra_sync_stage` already performs hash comparison for all managed files registered in the manifest. No changes needed to its core logic — the new files are automatically covered once registered via `ModuleResult.files_created`.
