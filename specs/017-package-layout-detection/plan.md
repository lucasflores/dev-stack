# Implementation Plan: Universal Package Layout Detection

**Branch**: `017-package-layout-detection` | **Date**: 2026-04-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-package-layout-detection/spec.md`

## Summary

Introduce a shared `detect_package_layout()` utility that discovers the project's Python package root across `src`, flat, and namespace layouts, and rewire all 15 consumer locations that currently hardcode `src/` to call through this utility. The detection follows a strict precedence: (1) explicit manifest config, (2) `pyproject.toml` build-backend hints (setuptools, hatch), (3) `src/` directory scanning, (4) repo root scanning. The result is computed once at pipeline start and threaded to all consumers via `StageContext`.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: stdlib (`pathlib`, `tomllib`, `dataclasses`, `enum`, `logging`); existing `uv_project.scan_root_python_sources()` for repo-root scanning  
**Storage**: N/A (filesystem detection only; no new persistence)  
**Testing**: pytest (existing suite: 60+ test files across unit/, integration/, contract/)  
**Target Platform**: macOS / Linux (local-first execution per constitution)  
**Project Type**: Single project (Python CLI tool)  
**Performance Goals**: Detection completes in <100ms for typical repositories (single scan, no recursion beyond depth 1)  
**Constraints**: Must not break existing `src`-layout behavior; detection called once per pipeline run  
**Scale/Scope**: 1 new module (`layout.py`), 6 modified modules (`stages.py`, `runner.py`, `uv_project.py`, `sphinx_docs.py`, `hooks.py`, `init_cmd.py`), 15 hardcoded locations to rewire

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | ✅ PASS | No new CLI commands; detection is internal infrastructure. Pipeline output improves (real results instead of silent no-ops). |
| II. Spec-Driven Development | ✅ PASS | This plan follows the spec at `specs/017-package-layout-detection/spec.md` with 5 clarifications resolved. |
| III. Automation by Default | ✅ PASS | Detection is automatic; no manual steps introduced. Existing automation becomes correct for flat-layout projects. |
| IV. Brownfield Safety | ✅ PASS | Core motivation: respects the project's existing layout rather than forcing `src`. `preview_files()` adapted to avoid proposing conflicting structure. |
| V. AI-Native Architecture | ✅ PASS | No direct LLM API calls. Agent context updated via `update-agent-context.sh`. |
| VI. Local-First Execution | ✅ PASS | Pure filesystem detection; no network or cloud dependencies. |
| VII. Observability & Documentation | ✅ PASS | Detection logs layout style and package names. Warnings for ambiguous layouts. |
| VIII. Modularity & Composability | ✅ PASS | New `layout.py` module is independently testable. Consumer modules depend on `PackageLayout` dataclass, not implementation details. Zero coupling between detection and consumption. |

**Pre-Phase 0 gate**: ✅ All principles pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/017-package-layout-detection/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/dev_stack/
├── layout.py                    # NEW — PackageLayout dataclass + detect_package_layout()
├── modules/
│   ├── uv_project.py            # MODIFIED — delegates to layout.py, preview_files() adapted
│   ├── sphinx_docs.py           # MODIFIED — delegates to layout.py for conf.py/Makefile rendering
│   └── hooks.py                 # MODIFIED — mypy hook entry uses detected package root
├── pipeline/
│   ├── stages.py                # MODIFIED — typecheck/docs-api use PackageLayout from context
│   └── runner.py                # MODIFIED — computes PackageLayout once, adds to StageContext
└── cli/
    └── init_cmd.py              # MODIFIED — greenfield detection delegates to layout.py

tests/
├── unit/
│   ├── test_layout.py           # NEW — unit tests for detect_package_layout()
│   ├── test_uv_project.py       # MODIFIED — tests for adapted preview_files()
│   ├── test_sphinx_docs.py      # MODIFIED — tests for layout-aware rendering
│   ├── test_hooks_module.py     # MODIFIED — tests for layout-aware hook entries
│   └── test_pipeline_stages.py  # MODIFIED — tests for layout-aware stage execution
└── integration/
    ├── test_init_brownfield.py  # MODIFIED — flat-layout brownfield scenario
    └── test_layout_detection.py # NEW — end-to-end layout detection across layouts
```

**Structure Decision**: Single project layout. New `layout.py` module placed at `src/dev_stack/layout.py` (top-level, not inside `modules/`) because it is foundational infrastructure consumed by both modules and pipeline stages.

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | ✅ PASS | No new CLI commands. Existing commands produce better output for flat-layout projects. |
| II. Spec-Driven Development | ✅ PASS | Spec → Plan → Data model → Contracts → Tasks workflow followed. |
| III. Automation by Default | ✅ PASS | Detection is fully automatic. No manual steps. Idempotent (same filesystem → same result). |
| IV. Brownfield Safety | ✅ PASS | Core deliverable: `preview_files()` adapted to respect existing layout. No file overwrites. |
| V. AI-Native Architecture | ✅ PASS | Agent context updated via `update-agent-context.sh copilot`. |
| VI. Local-First Execution | ✅ PASS | Pure filesystem detection with `tomllib` (stdlib). No network dependencies. |
| VII. Observability & Documentation | ✅ PASS | Warning logging for ambiguous layouts. `quickstart.md` documents new API. |
| VIII. Modularity & Composability | ✅ PASS | `layout.py` is independently testable. `PackageLayout` dataclass provides clean contract. Consumers depend on the dataclass, not detection internals. Module can be tested without the pipeline and vice versa. |

**Post-design gate**: ✅ All principles pass. No new violations introduced by design decisions.

## Complexity Tracking

> No constitution violations. Table left empty.
