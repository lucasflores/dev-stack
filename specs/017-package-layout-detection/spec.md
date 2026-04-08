# Feature Specification: Universal Package Layout Detection

**Feature Branch**: `017-package-layout-detection`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "Universal Package Layout Detection — introduce a shared `detect_package_layout()` utility that discovers the project's Python package root regardless of layout style, and rewire every consumer that currently hardcodes `src` to call through this utility instead."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Brownfield Flat-Layout Project Runs Full Pipeline (Priority: P1)

A developer uses dev-stack's `init` command on an existing Python project that uses a flat layout (`my_package/` at the repository root with no `src/` directory). After initialization, they run the pipeline. Type-checking, documentation generation, and pre-push hooks all operate against the correct package directory instead of a nonexistent `src/` folder.

**Why this priority**: This is the core broken path today. Every brownfield project that does not follow `src` layout gets meaningless pipeline results — mypy scans nothing, sphinx-apidoc documents nothing, and hooks point at a nonexistent directory. Fixing this delivers immediate value to the largest class of affected users.

**Independent Test**: Can be fully tested by creating a temporary flat-layout Python project, running the dev-stack pipeline, and verifying that mypy, sphinx-apidoc, and hooks all target the correct package directory.

**Acceptance Scenarios**:

1. **Given** a brownfield project with a flat layout (`my_package/` at repo root, no `src/` directory), **When** the dev-stack pipeline runs the type-check stage, **Then** mypy targets `my_package/` and reports real type-check results (not "no files found").
2. **Given** a brownfield project with a flat layout, **When** the pipeline runs the docs-api stage, **Then** sphinx-apidoc receives the correct package path and generates API documentation for the discovered package.
3. **Given** a brownfield project with a flat layout, **When** pre-push hooks are installed, **Then** the mypy hook entry points at the correct package root (not `src/`).
4. **Given** a brownfield project with a flat layout, **When** Sphinx `conf.py` is rendered, **Then** `sys.path.insert` targets the actual package root directory.

---

### User Story 2 — Src-Layout Projects Continue Working Unchanged (Priority: P1)

A developer uses dev-stack on a project that follows the standard `src/<pkg>/` layout. After the refactor to the shared detection utility, everything works exactly as it does today — no behavioral change.

**Why this priority**: Regression prevention is equally critical. The existing `src` layout is the most common path and must remain unbroken.

**Independent Test**: Can be fully tested by running the dev-stack pipeline on an existing `src`-layout project and verifying all stages produce identical results to the current behavior.

**Acceptance Scenarios**:

1. **Given** a project with `src/my_package/__init__.py`, **When** the detection utility runs, **Then** it returns layout style `src`, package root pointing to `src/`, and `["my_package"]` as the discovered packages.
2. **Given** a `src`-layout project, **When** the full pipeline runs, **Then** mypy, sphinx-apidoc, hooks, and `conf.py` all target `src/` exactly as they do today.

---

### User Story 3 — Explicit Config Override Takes Precedence (Priority: P2)

A developer has manually specified a `package_name` in their dev-stack module configuration (`modules.uv_project.config.package_name`). The detection utility respects this explicit setting and does not override it with auto-detected values.

**Why this priority**: Explicit configuration should always win over auto-detection. This ensures power users retain full control and prevents surprises when auto-detection guesses incorrectly.

**Independent Test**: Can be fully tested by setting `package_name` in configuration, running the pipeline, and verifying the configured value is used regardless of the project's actual directory structure.

**Acceptance Scenarios**:

1. **Given** a project where `modules.uv_project.config.package_name` is set to `custom_pkg`, **When** the detection utility runs, **Then** it returns `custom_pkg` as the package name without scanning the filesystem.
2. **Given** a project where the explicit config points to a flat-layout package, **When** the pipeline runs, **Then** all consumers use the configured package path.

---

### User Story 4 — pyproject.toml Build-Backend Hints Are Used (Priority: P2)

A developer's project has build-backend configuration in `pyproject.toml` (e.g., `[tool.hatch.build.targets.wheel.packages]` or `[tool.setuptools.packages.find.where]`) that specifies where packages live. The detection utility reads these hints and uses them to locate packages without relying on directory scanning.

**Why this priority**: Many modern Python projects declare their package layout in `pyproject.toml`. Using these hints provides more accurate detection than filesystem scanning alone.

**Independent Test**: Can be fully tested by creating a project with `pyproject.toml` build-backend hints pointing to a non-standard location and verifying the utility detects the correct package root.

**Acceptance Scenarios**:

1. **Given** a project with `[tool.setuptools.packages.find] where = ["lib"]`, **When** the detection utility runs, **Then** it returns `lib` as the package root.
2. **Given** a project with `[tool.hatch.build.targets.wheel.packages]` listing `["src/my_pkg"]`, **When** the detection utility runs, **Then** it returns the correct package root and package name derived from the Hatch configuration.

---

### User Story 5 — preview_files() Respects Detected Layout in Brownfield Mode (Priority: P2)

A developer runs `preview_files()` on a brownfield flat-layout project. Instead of always proposing `src/<pkg>/__init__.py` paths (which would create a parallel src tree), the preview shows files consistent with the project's actual layout.

**Why this priority**: Incorrect preview output causes the brownfield conflict detector to miss real conflicts or propose creating a conflicting directory structure. This undermines the safety guarantees of brownfield initialization.

**Independent Test**: Can be fully tested by calling `preview_files()` on a flat-layout project and verifying the proposed file list does not include `src/` paths.

**Acceptance Scenarios**:

1. **Given** a brownfield project with flat layout `my_package/`, **When** `preview_files()` is called, **Then** the proposed paths reference `my_package/` (not `src/my_package/`).
2. **Given** a brownfield project with `src` layout, **When** `preview_files()` is called, **Then** the proposed paths reference `src/<pkg>/` as they do today.

---

### User Story 6 — Duplicate Detection Logic Is Eliminated (Priority: P3)

A maintainer fixes a bug in the package-detection logic. Because there is now a single shared utility, the fix applies everywhere — type-checking, documentation, hooks, and Sphinx configuration all benefit from the same correction.

**Why this priority**: This is a code-quality and maintainability concern. While it does not directly affect end users, it prevents the class of bug where a fix in one detection implementation is missed in another.

**Independent Test**: Can be verified by confirming that `uv_project._detect_package_name()`, `sphinx_docs._detect_package_name()`, and `stages._detect_src_package()` all delegate to or are replaced by the single shared utility.

**Acceptance Scenarios**:

1. **Given** the codebase after this feature is implemented, **When** a developer searches for package-detection logic, **Then** there is exactly one authoritative implementation that all consumers call.
2. **Given** the shared utility is updated, **When** any consumer invokes package detection, **Then** it receives results from the updated logic without requiring changes in the consumer.

---

### Edge Cases

- What happens when the repository root contains no Python packages at all (no `__init__.py` anywhere)? The utility should return an empty result and consumers should handle this gracefully (e.g., skip the stage with a warning).
- What happens when multiple top-level packages exist in a flat layout (e.g., `pkg_a/` and `pkg_b/` both at repo root)? The utility should discover all of them and return them in the `package_names` list.
- What happens when both `src/<pkg>/` and a flat `<pkg>/` exist simultaneously? The utility should prefer the `src` layout (standard convention) and log a warning about the ambiguity.
- What happens when `pyproject.toml` build-backend hints conflict with the actual filesystem structure (e.g., config says `src` but no `src/` directory exists)? The utility should fall through to filesystem scanning and log a warning.
- What happens when the project uses namespace packages (directories without `__init__.py`)? The detection should identify this as a namespace layout when the `pyproject.toml` declares implicit namespaces or when directories contain only sub-packages with `__init__.py`.
- What happens when `scan_root_python_sources()` exclusion list filters out a directory the user intended as a package? The explicit config override (User Story 3) provides an escape hatch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single shared utility function that detects the project's Python package layout and returns the layout style, package root path, and discovered package names.
- **FR-002**: The detection utility MUST follow a defined precedence order: (1) explicit user configuration, (2) `pyproject.toml` build-backend hints, (3) `src/` directory scanning, (4) repository root scanning.
- **FR-003**: The detection utility MUST support at least three layout styles: `src` layout (`src/<pkg>/`), flat layout (`<pkg>/` at repo root), and namespace layout. Namespace layout detection MUST only activate when `pyproject.toml` explicitly declares implicit namespace packages (e.g., via build-backend configuration) or when the explicit config override is set; heuristic filesystem detection of namespace packages is not performed.
- **FR-004**: The detection utility MUST parse `pyproject.toml` for build-backend package location hints. The initial implementation MUST support `[tool.setuptools.packages.find.where]` and `[tool.hatch.build.targets.wheel.packages]`. Other backends (PDM, Flit, Maturin, etc.) are deferred to future work but the parsing infrastructure should be extensible.
- **FR-005**: The type-check stage MUST use the detected package root path instead of a hardcoded `src/` reference when invoking mypy.
- **FR-006**: The docs-api stage MUST use the detected package root and package names when invoking sphinx-apidoc.
- **FR-007**: The pre-push hook configuration MUST use the detected package root in the mypy hook entry.
- **FR-008**: The Sphinx `conf.py` renderer MUST insert the detected package root into `sys.path` instead of hardcoding `../src`.
- **FR-009**: The Sphinx Makefile renderer MUST use the detected package root and package name in the apidoc target.
- **FR-010**: The `preview_files()` function MUST use the detected layout to propose file paths consistent with the project's actual structure (not always `src/<pkg>/`).
- **FR-011**: The detection utility MUST reuse the existing `scan_root_python_sources()` exclusion list when scanning the repository root for packages in the flat-layout fallback path.
- **FR-012**: All three existing duplicate detection implementations (`uv_project._detect_package_name()`, `sphinx_docs._detect_package_name()`, `stages._detect_src_package()`) MUST be replaced by or delegate to the single shared utility.
- **FR-013**: When detection finds no packages in a greenfield context, the utility MUST default to `src` layout (preserving current greenfield behavior). In a brownfield context where packages are expected but not found, consumers MUST handle this gracefully (skip the stage with a warning rather than crash).
- **FR-014**: When ambiguous layouts are detected (e.g., both `src/<pkg>/` and flat `<pkg>/` exist), the utility MUST prefer `src` layout and log a warning.
- **FR-015**: The detection result MUST be computed once at pipeline start and the resulting `PackageLayout` MUST be passed to all consumers within that run. Consumers MUST NOT independently re-run detection.
- **FR-016**: When multiple packages are discovered, consumers MUST operate on all of them — mypy MUST scan all package directories, sphinx-apidoc MUST document all packages, and hooks MUST cover all package directories.

### Key Entities

- **PackageLayout**: Represents the detected layout of a Python project. Key attributes: layout style (src, flat, namespace), package root path (the directory containing top-level packages), and a list of discovered package names.
- **Layout Style**: A classification of how the project organizes its Python packages — `src` (packages under a `src/` directory), `flat` (packages at the repository root), or `namespace` (implicit namespace packages without `__init__.py`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The dev-stack pipeline produces correct type-checking results for flat-layout projects (mypy reports real findings, not "no files found") — verified by running the pipeline end-to-end on a flat-layout test project.
- **SC-002**: Sphinx API documentation is successfully generated for flat-layout projects — verified by confirming sphinx-apidoc produces `.rst` files for the discovered package.
- **SC-003**: Pre-push hooks point at the correct package directory for all three supported layout styles — verified by inspecting the generated hook configuration.
- **SC-004**: `preview_files()` proposes layout-consistent paths for brownfield projects — verified by confirming no `src/` paths appear in the preview output for flat-layout projects.
- **SC-005**: There is exactly one package-detection implementation in the codebase — verified by confirming the three previously independent implementations delegate to the shared utility.
- **SC-006**: All existing tests for `src`-layout projects continue to pass without modification — verified by running the full test suite.
- **SC-007**: Detection correctly uses `pyproject.toml` build-backend hints when present — verified by tests with `[tool.setuptools]` and `[tool.hatch]` configurations.

## Assumptions

- Python 3.11+ is the minimum supported version for the detection utility.
- The project uses `uv` as its package manager; no changes to package manager integration are required.
- The existing `scan_root_python_sources()` function and its `_SCAN_EXCLUDE_DIRS` exclusion set are stable and correctly curated.
- The `.dev-stack/brownfield-init` marker mechanism is unchanged; this feature references it but does not modify it.
- Namespace package detection covers the common case of PEP 420 implicit namespace packages. Exotic namespace package configurations may require the explicit config override.
- When multiple packages exist in a flat layout, all of them are returned; consumers operate on all discovered packages (mypy scans all, sphinx-apidoc documents all, hooks cover all).

## Scope Boundaries

- **In scope**: Detection utility, consumer rewiring, tests for all layout styles, `preview_files()` adaptation.
- **Out of scope**: Migrating existing flat-layout projects to `src` layout — that is a user choice, not an automation decision. This spec is about *detecting and respecting* the layout, not changing it.
- **Out of scope**: The `-W` (warnings-as-errors) flag behavior in Sphinx — that is a separate concern.
- **Out of scope**: Changes to the brownfield-init marker mechanism (`.dev-stack/brownfield-init`).

## Clarifications

### Session 2026-04-07

- Q: What should the default layout be when the detection utility finds no existing packages (greenfield initialization)? → A: Default to `src` layout (current greenfield behavior preserved).
- Q: Which build-backend pyproject.toml hints should the utility support in the initial implementation? → A: Setuptools + Hatch only (the two most common pure-Python backends); other backends deferred to follow-up work.
- Q: Should namespace package detection require a pyproject.toml declaration, or also attempt heuristic filesystem detection? → A: Require pyproject.toml declaration or explicit config override only; no heuristic filesystem detection of namespace packages.
- Q: Should the detection result be computed once per pipeline run and shared, or should each consumer call independently? → A: Compute once at pipeline start and pass the PackageLayout result to all consumers (avoids redundant I/O and guarantees consistency).
- Q: How should consumers handle multiple discovered packages? → A: Operate on all discovered packages (mypy scans all, sphinx documents all, hooks cover all).
