# Implementation Plan: Init & Pipeline Bugfixes

**Branch**: `006-init-pipeline-bugfixes` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-init-pipeline-bugfixes/spec.md`

## Summary

Fix 14 bugs (critical through low severity) in the init flow, pipeline execution, and CLI UX that prevent new users from completing the README-documented bootstrap workflow. The changes span 7 source files across `cli/`, `pipeline/`, and `brownfield/` packages, plus the README itself. The approach is surgical: each fix targets a specific function or code path without architectural changes. Key changes: venv-aware tool detection in pipeline stages, `uv sync --all-extras` during init, pyproject.toml structural fingerprinting for greenfield detection, `completed_with_failures` pipeline status with non-zero exit codes, `.secrets.baseline` integration, dry-run delegation to update preview, and CLI `--version` flag.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click (CLI), tomllib (pyproject parsing), subprocess (stage execution), uv (package management)
**Storage**: `dev-stack.toml` (TOML manifest), `.secrets.baseline` (JSON), `.dev-stack/pipeline/last-run.json`
**Testing**: pytest (unit + integration + contract suites under `tests/`)
**Target Platform**: macOS / Linux (CLI tool, local execution)
**Project Type**: Single Python package (`src/dev_stack/`)
**Performance Goals**: N/A (CLI tool, sub-second operations)
**Constraints**: All changes must be backward-compatible with existing `dev-stack.toml` manifests; no new dependencies
**Scale/Scope**: 14 targeted bugfixes touching ~7 source files, ~1 doc file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. CLI-First Interface** | PASS | All fixes maintain CLI invocations. FR-009 adds `--version`. Exit codes follow POSIX (FR-006). |
| **II. Spec-Driven Development** | PASS | This plan follows the spec at `specs/006-init-pipeline-bugfixes/spec.md`. |
| **III. Automation by Default** | PASS | Fixes to the pipeline (FR-001, FR-006, FR-008, FR-012) restore automation reliability. Init runs `uv sync --all-extras` so pipeline works immediately. |
| **IV. Brownfield Safety** | PASS | FR-004/FR-005 improve conflict detection via structural fingerprinting. FR-007 enables dry-run preview on initialized repos. No files overwritten without consent. |
| **V. AI-Native Architecture** | N/A | No AI/agent changes in this feature. |
| **VI. Local-First Execution** | PASS | All fixes target local execution (git hooks, local pipeline). No cloud CI changes. |
| **VII. Observability & Documentation** | PASS | FR-011 fixes README validation commands. FR-009/FR-010 improve CLI discoverability. Pipeline status reporting becomes accurate (FR-006). |
| **VIII. Modularity & Composability** | PASS | No new modules. Existing module boundaries preserved. Changes are isolated to specific functions. |

**Gate Result**: PASS — no violations. All 14 fixes align with constitutional principles.

## Project Structure

### Documentation (this feature)

```text
specs/006-init-pipeline-bugfixes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/dev_stack/
├── cli/
│   ├── main.py              # FR-009: --version flag, FR-010: update help text
│   ├── init_cmd.py          # FR-002/003: uv sync --all-extras, FR-004/005: greenfield fingerprint,
│   │                        #   FR-007: dry-run delegation, FR-013: rollback tag in greenfield
│   ├── pipeline_cmd.py      # FR-006: completed_with_failures status + exit code
│   └── update_cmd.py        # FR-010: help description
├── pipeline/
│   ├── stages.py            # FR-001: venv-aware mypy detection, FR-008: venv Python for all stages,
│   │                        #   FR-012: .secrets.baseline integration
│   └── runner.py            # FR-006: success field accounts for hard-gate failures under --force
├── brownfield/
│   └── conflict.py          # FR-004: greenfield predecessor file allowlist
└── __init__.py              # FR-009: __version__ attribute

tests/
├── unit/                    # New/updated tests for each fix
├── integration/             # Greenfield flow end-to-end test
└── contract/                # CLI schema contract updates

README.md                    # FR-011: Fix validation checklist flag positions
```

**Structure Decision**: Single project layout. All changes are modifications to existing files — no new packages or modules.

## Complexity Tracking

| Principle | Tension | Resolution |
|-----------|---------|------------|
| III. Automation by Default | `--force` runs all stages but `ExitCode.PIPELINE_FAILURE` means the overall outcome can still be non-zero — tension with expectation that automation "just works" | `--force` means "don't abort mid-pipeline," not "suppress failure signals." The non-zero exit code is correct per FR-006. Documented in spec and data model. |
