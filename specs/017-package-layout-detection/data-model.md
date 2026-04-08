# Data Model: Universal Package Layout Detection

**Feature**: `017-package-layout-detection`  
**Date**: 2026-04-07

## Entities

### LayoutStyle (Enum)

Classification of how a Python project organizes its packages.

| Value | Description |
|-------|-------------|
| `SRC` | Packages under a `src/` directory (e.g., `src/my_package/`) |
| `FLAT` | Packages at the repository root (e.g., `my_package/` at repo root) |
| `NAMESPACE` | Implicit namespace packages (PEP 420) declared via `pyproject.toml` |

**Rules**:
- `SRC` is the default for greenfield projects (no existing packages detected).
- `NAMESPACE` is only assigned when `pyproject.toml` explicitly declares implicit namespaces (e.g., `namespaces = true` in setuptools config) or when the explicit config override is set. Heuristic filesystem detection is not performed.

---

### PackageLayout (Dataclass)

Represents the detected layout of a Python project. Immutable after creation.

| Field | Type | Description |
|-------|------|-------------|
| `layout_style` | `LayoutStyle` | The detected layout classification |
| `package_root` | `Path` | Directory containing top-level package(s), relative to repo root. For `SRC`: `Path("src")`. For `FLAT`: `Path(".")`. |
| `package_names` | `list[str]` | Sorted list of discovered package names (e.g., `["my_package"]`). May be empty for greenfield projects. |

**Relationships**:
- Created by `detect_package_layout()` (one per pipeline run).
- Consumed by `StageContext` (threading to all pipeline stages).
- Consumed by `preview_files()` (proposing layout-consistent paths).
- Consumed by `_render_conf_py()` and `_render_makefile()` (Sphinx configuration).
- Consumed by `_build_hook_list()` (mypy hook entry).

**Validation Rules**:
- `package_root` must be a relative `Path` (not absolute).
- `package_names` is always sorted alphabetically for determinism.
- When `layout_style` is `SRC`, `package_root` must be `Path("src")`.
- When `layout_style` is `FLAT`, `package_root` must be `Path(".")`.
- When `layout_style` is `NAMESPACE`, `package_root` is determined by the `where` value from the build-backend config (e.g., `Path("src")` for `where = ["src"]`, or `Path(".")` when `where` is `["."]` or absent). Consumers treat NAMESPACE the same as FLAT when `package_root == Path(".")` and the same as SRC when `package_root == Path("src")`.

**State Transitions**: None — `PackageLayout` is immutable. It is computed once and does not change during a pipeline run.

---

### StageContext (Extended Dataclass — existing)

Existing execution context shared by all pipeline stages. Extended with one new field.

| Field | Type | Default | Status |
|-------|------|---------|--------|
| `repo_root` | `Path` | (required) | Existing |
| `manifest` | `StackManifest \| None` | `None` | Existing |
| `force` | `bool` | `False` | Existing |
| `agent_bridge` | `AgentBridge \| None` | `None` | Existing |
| `completed_results` | `list[StageResult] \| None` | `None` | Existing |
| `hook_context` | `str \| None` | `None` | Existing |
| `dry_run` | `bool` | `False` | Existing |
| `package_layout` | `PackageLayout \| None` | `None` | **NEW** |

**Rules**:
- `package_layout` is set once in `runner.py` before stage execution begins.
- The existing `without_agent()` method must propagate `package_layout`.
- When `package_layout` is `None` (e.g., in minimal hook contexts), consumers fall back to `_detect_src_package()`-style behavior for backward compatibility.

---

## Detection Precedence

The `detect_package_layout()` function follows this strict precedence:

```
1. Explicit config: manifest → modules.uv_project.config.package_name
   ↓ (not found)
2. pyproject.toml hints:
   a. [tool.setuptools.packages.find] → where + namespaces
   b. [tool.hatch.build.targets.wheel] → packages
   ↓ (not found)
3. src/ directory scan: repo_root/src/ → subdirs with __init__.py
   ↓ (not found)
4. Repo root scan: scan_root_python_sources() → packages at repo root
   ↓ (not found)
5. Default: SRC layout with empty package_names (greenfield)
```

At each level, if a result is found, detection stops. If the result conflicts with the filesystem (e.g., config says `src` but `src/` doesn't exist), a warning is logged and detection falls through to the next level.
