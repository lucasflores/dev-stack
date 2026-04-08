# Research: Universal Package Layout Detection

**Feature**: `017-package-layout-detection`  
**Date**: 2026-04-07

## R-001: pyproject.toml Setuptools Package Location Hints

**Decision**: Parse `[tool.setuptools.packages.find]` for the `where` key (list of strings) and `namespaces` key (boolean).

**Rationale**: The `where` key is a list of directory paths (e.g., `["src"]`, `["lib"]`), defaulting to `["."]`. The `namespaces` key (default `true`) controls whether PEP 420 implicit namespace packages are discovered. These two keys provide sufficient information to determine both the package root and whether namespace packages are in play.

Valid keys in `[tool.setuptools.packages.find]`:
- `where`: `list[str]` — directories to scan for packages (default: `["."]`)
- `include`: `list[str]` — glob patterns for package names to include (default: `["*"]`)
- `exclude`: `list[str]` — glob patterns for package names to exclude
- `namespaces`: `bool` — enable PEP 420 implicit namespace package discovery (default: `true`)

**Alternatives Considered**:
- Parsing `include`/`exclude` globs — rejected; not needed for locating the package root, only for filtering which packages within that root to include. Overly complex for the detection use case.
- Parsing `packages = [...]` (explicit list) — could be useful but rarely used alongside `find`; deferred.

---

## R-002: pyproject.toml Hatch Build Configuration

**Decision**: Parse `[tool.hatch.build.targets.wheel]` for the `packages` key (list of path strings).

**Rationale**: Hatch's `packages` key accepts a list of relative paths (e.g., `["src/foo"]`). From these paths, we can derive both the package root directory and the package name(s). Hatch auto-detects layouts when no explicit `packages` key is set, so the absence of this key means Hatch is using convention-based discovery (src-layout if `src/` exists, flat-layout otherwise).

Key Hatch configuration keys:
- `packages`: `list[str]` — relative paths to package directories
- `sources`: `dict[str, str]` — path prefix rewriting (advanced; deferred)

**Alternatives Considered**:
- Parsing `sources` for path rewriting — rejected for initial implementation; adds complexity for a rare edge case.
- Checking Hatch's `only-include` — rejected; used for file filtering, not package location.

---

## R-003: TOML Parsing Approach

**Decision**: Use stdlib `tomllib` (Python 3.11+) for reading `pyproject.toml`. Follow existing codebase patterns for error handling.

**Rationale**: The codebase already uses `tomllib` extensively in `uv_project.py`, `brownfield/conflict.py`, and `sphinx_docs.py`. Standard error handling pattern:

```python
try:
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
except (FileNotFoundError, tomllib.TOMLDecodeError):
    return None  # fall through to next detection strategy
```

For nested key access, use `.get()` with fallback: `data.get("tool", {}).get("setuptools", {}).get("packages", {}).get("find", {})`.

**Alternatives Considered**:
- `tomli` (backport) — rejected; Python 3.11+ is the target, `tomllib` is stdlib.
- Manual parsing — rejected; error-prone and already solved by `tomllib`.

---

## R-004: StageContext Extension Strategy

**Decision**: Add `package_layout: PackageLayout | None = None` as an optional field on the existing `StageContext` dataclass.

**Rationale**: The existing `StageContext` uses `@dataclass(slots=True)` and all instantiation sites use keyword arguments. An optional field with default `None` requires zero changes to existing call sites. The field is populated once in `runner.py` before stage execution begins.

Instantiation sites that remain unchanged (default `None`):
- `hooks_runner.py` — `StageContext(repo_root=repo_root)` (minimal context for hook execution)
- Test fixtures — mock instantiations with `repo_root` only

Instantiation site that populates the field:
- `runner.py` — computes `PackageLayout` once and sets it on the context

The existing `without_agent()` method must be updated to propagate `package_layout`.

**Alternatives Considered**:
- Separate `PackageLayoutContext` — rejected; adds ceremony, violates single-context passing pattern.
- Global module-level cache — rejected; complicates testing and breaks parallel execution.
- Environment variable — rejected; not type-safe, harder to test.

---

## R-005: Brownfield vs Greenfield Detection Integration

**Decision**: Use the existing `is_greenfield_uv_package()` function and `.dev-stack/brownfield-init` marker to determine context. Greenfield defaults to `src` layout; brownfield detects the existing layout.

**Rationale**: The brownfield detection flow already exists:
1. `is_greenfield_uv_package()` checks `pyproject.toml` heuristics (build-backend is `uv_build`, description is default, no `[tool]` section, no root-level Python sources).
2. `.dev-stack/brownfield-init` marker is written by `init_cmd.py` after brownfield initialization.
3. `preview_files()` generates proposed files for conflict detection.

The layout detection utility integrates as follows:
- **Greenfield** (no existing packages): Detection returns empty; consumers use `src` layout as the default (FR-013).
- **Brownfield** (existing packages): Detection runs the full precedence chain and returns the detected layout.
- `preview_files()` uses the detected layout to propose files matching the existing structure (FR-010).

**Alternatives Considered**:
- Duplicating brownfield detection logic — rejected; reuse existing mechanisms.
- Making brownfield detection a prerequisite for layout detection — rejected; layout detection works independently and should not be coupled to brownfield-specific logic.

---

## R-006: Hardcoded `src/` Location Inventory

**Decision**: 15+ hardcoded `src/` references identified across 6 files. All must be rewired to use `PackageLayout`.

**Inventory**:

| # | File | Location | Hardcoded Reference | Consumer Rewire Strategy |
|---|------|----------|---------------------|--------------------------|
| 1 | `stages.py` | `_execute_typecheck_stage()` | `context.repo_root / "src"`, `"mypy", "src/"` | Use `layout.package_root` |
| 2 | `stages.py` | `_execute_docs_api_stage()` | `f"src/{pkg_name}"` in apidoc cmd | Use `layout.package_root / pkg` |
| 3 | `stages.py` | `_detect_src_package()` | `repo_root / "src"` | Replace with shared utility |
| 4 | `hooks.py` | `_build_hook_list()` | `entry="python3 -m mypy src/"` | Use `layout.package_root` |
| 5 | `sphinx_docs.py` | `_render_conf_py()` | `sys.path.insert(0, os.path.abspath("../src"))` | Use relative package root |
| 6 | `sphinx_docs.py` | `_render_makefile()` | `../src/{pkg_name}` in apidoc target | Use relative package root |
| 7 | `sphinx_docs.py` | `_detect_package_name()` | `repo_root / "src"` | Replace with shared utility |
| 8 | `uv_project.py` | `_detect_package_name()` | `self.repo_root / "src"` | Replace with shared utility |
| 9 | `uv_project.py` | `preview_files()` | `f"src/{pkg_name}/__init__.py"`, `"mypy_path": "src"`, `"source": [f"src/{pkg_name}"]` | Use detected layout |
| 10 | `uv_project.py` | `_augment_pyproject()` | `"mypy_path": "src"` | Use detected package root |
| 11 | `uv_project.py` | `install()` cleanup | `self.repo_root / "src" / pkg_name` | Use detected layout |
| 12 | `uv_project.py` | `install()` tracking | `self.repo_root / "src" / pkg_name / "__init__.py"` | Use detected layout |
| 13 | `uv_project.py` | `verify()` | `self.repo_root / "src" / pkg_name / "__init__.py"` | Use detected layout |
| 14 | `uv_project.py` | `_scaffold_pyproject_defaults()` | `"mypy_path": "src"` | Use detected package root |
| 15 | `init_cmd.py` | greenfield detection | `repo_root / "src"` | Use detected layout |

---

## R-007: `scan_root_python_sources()` Reuse

**Decision**: Reuse the existing `scan_root_python_sources()` function from `uv_project.py` for the flat-layout fallback path in the detection utility. The `_SCAN_EXCLUDE_DIRS` set is stable and correctly curated.

**Rationale**: The function already scans repo root at depth 1, excludes `.git`, `__pycache__`, `.venv`, `node_modules`, `.tox`, and returns `(has_python_sources, package_names)`. This is exactly what the flat-layout fallback needs. Moving it to `layout.py` (or importing from `uv_project.py`) avoids duplication.

**`_SCAN_EXCLUDE_DIRS`**: `frozenset({".git", "__pycache__", ".venv", "node_modules", ".tox"})`

**Alternatives Considered**:
- Duplicating the function — rejected; violates DRY.
- Adding more exclusions — deferred; current set handles standard Python projects. `build/`, `dist/`, `.eggs` could be added later if needed.
