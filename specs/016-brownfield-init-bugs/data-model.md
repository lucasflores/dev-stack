# Data Model: Brownfield Init Bug Remediation

**Feature**: 016-brownfield-init-bugs | **Date**: 2026-04-07

## Overview

This feature introduces no new entities or data structures. All changes are behavioral patches to existing code. This document captures the existing entities that are **modified** and the new marker file added.

## Modified Entities

### Init Mode (existing)

**Location**: `src/dev_stack/brownfield/conflict.py` → `is_greenfield_uv_package()`

**Current fields**:
- `pyproject.toml` structure (build-backend, description, tool sections)

**Added check**:
- Root-level `.py` files or directories containing `__init__.py` at depth 1
- Excluded directories: `.git`, `__pycache__`, `.venv`, `node_modules`, `.tox`

**State transition**: If any root-level Python source is detected, the function returns `False` (brownfield) even if `pyproject.toml` passes all existing heuristics.

---

### Commit Message (existing)

**Location**: `src/dev_stack/vcs/hooks_runner.py` → `run_commit_msg_hook()`

**Current behavior**: Strips all lines where `ln.startswith("#")`
**New behavior**: Strips only lines matching `re.match(r"^# |^#$", ln)` (git comment lines)

**Preserved lines**: `## Intent`, `## Reasoning`, `## Scope`, `## Narrative` (and any other markdown headers)

---

### APM Version String (existing)

**Location**: `src/dev_stack/modules/apm.py` → `_check_apm_cli()`

**Current parsing**: `result.stdout.strip().split()[-1]`
**New parsing**: 
1. Strip ANSI escape sequences via `re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)`
2. Extract semver via `re.search(r'\d+\.\d+\.\d+', stripped)`

---

### Pipeline Stage Context (existing)

**Location**: `src/dev_stack/pipeline/stages.py`

**New behavior in lint stage**: Check for `.dev-stack/brownfield-init` marker. If present, run `ruff format .` (auto-fix) before the `--check` pass, then delete the marker.

**New behavior in typecheck stage**: Scan for root-level Python packages outside `src/`. If found, emit a warning listing uncovered packages.

## New Artifacts

### Brownfield Init Marker File

**Path**: `.dev-stack/brownfield-init`
**Lifecycle**: Created at end of brownfield init path in `init_cmd.py`. Consumed and deleted by the lint stage in `stages.py` on first pipeline run.
**Content**: Empty file (existence-only check)
**Purpose**: Signals that the next pipeline run should auto-format before lint-gating.

## Relationships

```
init_cmd.py ──creates──▶ .dev-stack/brownfield-init
     │
     ├──calls──▶ conflict.py::is_greenfield_uv_package() ──reads──▶ repo root files
     │
     ├──calls──▶ _detect_and_migrate_requirements() ──reads──▶ requirements.txt
     │                                                ──writes──▶ pyproject.toml
     │
     └──calls──▶ _detect_root_packages() ──reads──▶ repo root dirs
                                          ──emits──▶ console warning

stages.py::_execute_lint_stage()
     └──reads + deletes──▶ .dev-stack/brownfield-init
     └──runs──▶ ruff format . (if marker exists)

stages.py::run_mypy_type_checking()
     └──scans──▶ repo root dirs
     └──emits──▶ console warning (if non-src packages found)

hooks_runner.py::run_commit_msg_hook()
     └──strips──▶ git comment lines only (not markdown headers)
     └──passes to──▶ gitlint (UC5 body_sections.py)
```
