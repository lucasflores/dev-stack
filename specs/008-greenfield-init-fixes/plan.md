# Implementation Plan: Greenfield Init Fixes

**Branch**: `008-greenfield-init-fixes` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-greenfield-init-fixes/spec.md`

## Summary

Four bugs prevent a greenfield `dev-stack init` from producing a fully functional pipeline on first commit: (1) the brownfield guard in `uv_project.install()` short-circuits when `pyproject.toml` already exists — even when `is_greenfield_uv_package()` correctly detected it as a predecessor — skipping test scaffold creation and dependency augmentation; (2) dev/docs optional-dependencies are therefore never written; (3) `uv sync --extra dev --extra docs` is never run so pipeline tools are missing from the venv; (4) the pre-commit hook's agent detection doesn't read `dev-stack.toml`, so `DEV_STACK_AGENT=none` set at init time doesn't persist. The fix is a targeted brownfield-guard refactor, auto-install of dev dependencies, improved pipeline skip messaging, a hollow-pipeline warning banner, and manifest-based agent fallback in the pipeline runner.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click (CLI framework), tomli_w/tomllib (TOML read/write), uv (package manager)
**Storage**: Filesystem — `dev-stack.toml` manifest, `pyproject.toml`, `.venv/`
**Testing**: pytest with pytest-cov; existing unit/integration/contract test directories
**Target Platform**: macOS/Linux (developer workstations)
**Project Type**: Single Python package (src layout)
**Performance Goals**: N/A — CLI tool, no latency-sensitive paths
**Constraints**: Zero breaking changes to existing brownfield/reinit flows
**Scale/Scope**: 4 files modified, 2 files with minor edits, ~150 net lines changed

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | **PASS** | Changes are to init command internals and pipeline output; all remain CLI-accessible with JSON support |
| II. Spec-Driven Development | **PASS** | This plan implements spec 008 |
| III. Automation by Default | **PASS** | FR-003 (auto-install) and FR-005 (hollow-pipeline warning) directly enforce this principle |
| IV. Brownfield Safety | **PASS** | FR-007 requires preserving existing files; the fix narrows the brownfield guard rather than removing it |
| V. AI-Native Architecture | **PASS** | FR-006 (manifest fallback) improves agent detection reliability |
| VI. Local-First Execution | **PASS** | All changes execute locally in pre-commit hooks |
| VII. Observability & Documentation | **PASS** | FR-004 (remediation hints) and FR-005 (warning banner) improve pipeline observability |
| VIII. Modularity & Composability | **PASS** | Changes are scoped to `uv_project` module and pipeline runner; no cross-module coupling introduced |

## Project Structure

### Documentation (this feature)

```text
specs/008-greenfield-init-fixes/
├── plan.md              # This file
├── research.md          # Phase 0 output — root cause analysis
├── data-model.md        # Phase 1 output — data flow diagrams
├── quickstart.md        # Phase 1 output — verification guide
├── contracts/           # Phase 1 output — internal API contracts
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (files to modify)

```text
src/dev_stack/
├── modules/
│   └── uv_project.py          # FR-001, FR-002, FR-003, FR-007, FR-008, FR-009
├── cli/
│   └── init_cmd.py             # Greenfield force-pass to uv_project
├── pipeline/
│   ├── stages.py               # FR-004 (skip message remediation hints)
│   └── runner.py               # FR-005 (hollow-pipeline warning banner)
├── agent_bridge.py             # FR-006 — leveraged (no changes needed; already accepts manifest param)
└── config.py                   # FR-006 — leveraged (no changes needed; detect_agent() already supports manifest)

tests/
├── unit/
│   ├── test_uv_project.py      # Tests for FR-001, FR-002, FR-003, FR-007, FR-008, FR-009
│   ├── test_stages.py          # Tests for FR-004
│   └── test_runner.py          # Tests for FR-005, FR-006
└── integration/
    └── test_greenfield_init.py # End-to-end greenfield verification
```

**Structure Decision**: Single project layout — all changes touch existing files in the established `src/dev_stack/` package tree. No new directories or structural changes needed.

## Complexity Tracking

No constitution violations. No complexity justifications needed.

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. CLI-First Interface | **PASS** | Pipeline warning banner surfaces via both JSON (`"warnings"` field) and human-readable CLI output |
| II. Spec-Driven Development | **PASS** | All changes traced to FR-001 through FR-009 in the spec |
| III. Automation by Default | **PASS** | Auto-install eliminates manual `uv sync` step; hollow-pipeline warning prevents silent skips |
| IV. Brownfield Safety | **PASS** | `_augment_pyproject()` uses skip-if-exists guards; `_scaffold_tests()` preserves existing files; brownfield guard still blocks non-uv pyproject.toml properly |
| V. AI-Native Architecture | **PASS** | Manifest fallback ensures agent detection works reliably across subprocess boundaries |
| VI. Local-First Execution | **PASS** | All changes are local execution; no cloud dependencies added |
| VII. Observability & Documentation | **PASS** | Remediation hints in skip messages and warning banner significantly improve pipeline observability |
| VIII. Modularity & Composability | **PASS** | Changes scoped to `uv_project` module and pipeline runner; no new cross-module dependencies introduced |

**Result**: All 8 constitutional principles satisfied. No complexity tracking entries needed.
