# Implementation Plan: Init Onboarding Fixes

**Branch**: `007-init-onboarding-fixes` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-init-onboarding-fixes/spec.md`

## Summary

Fix six issues blocking or degrading the new-user onboarding experience: (1) `detect-secrets` circular self-detection in the security stage (BLOCKING), (2) greenfield init requiring `--force` after `uv init --package`, (3) `DEV_STACK_AGENT=none` env var ignored, (4) README missing initial commit guidance, (5) constitution template placed as floating root file instead of merging into speckit, (6) mode mislabeled as "brownfield" for greenfield flows. All fixes target existing functions in `init_cmd.py`, `config.py`, `stages.py`, and `vcs_hooks.py`, plus a README update.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: click ≥8.1, detect-secrets ≥1.5, tomli-w ≥1.0, rich ≥13.7, pathspec ≥0.12, gitlint-core ≥0.19  
**Storage**: Filesystem — `.secrets.baseline` (JSON), `dev-stack.toml` (TOML), `.dev-stack/hooks-manifest.json` (JSON)  
**Testing**: pytest ≥7.4 with pytest-cov ≥4.1 (cov target: 65% on `dev_stack.pipeline`)  
**Target Platform**: macOS / Linux (local dev machines)  
**Project Type**: Single Python package (`src/dev_stack/`)  
**Performance Goals**: N/A — all changes are to init-time or pre-commit pipeline logic, not hot paths  
**Constraints**: No new runtime dependencies; backward-compatible with existing initialized repos  
**Scale/Scope**: 6 bug fixes + 1 documentation update across 5 source files and 1 README

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | ✅ PASS | All changes affect existing CLI commands (`init`, `pipeline run`). No new commands introduced. |
| II. Spec-Driven Development | ✅ PASS | Spec exists at `specs/007-init-onboarding-fixes/spec.md` with user stories, FRs, and acceptance criteria. |
| III. Automation by Default | ✅ PASS | Fixes ensure automation works correctly (security stage, greenfield auto-resolution). No manual steps added. |
| IV. Brownfield Safety | ✅ PASS | FR-004/FR-005 enhance brownfield safety by recognizing `uv init --package` predecessors. FR-011 handles reinit migration of root constitution file. |
| V. AI-Native Architecture | ✅ PASS | No changes to agent interfaces. FR-006 fixes the agent override so `DEV_STACK_AGENT=none` works as documented. |
| VI. Local-First Execution | ✅ PASS | All changes are local — no cloud CI modifications. |
| VII. Observability & Documentation | ✅ PASS | FR-007 updates README to document clean first-commit flow. |
| VIII. Modularity & Composability | ✅ PASS | FR-009/FR-010 improve modularity: `vcs_hooks` checks for speckit presence before injecting content, skips if absent. No implicit coupling introduced. |
| Security & Quality Gates | ✅ PASS | FR-001/FR-002/FR-003 fix the security gate to correctly exclude false positives while detecting real secrets. |

**Gate result**: PASS — no violations. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/007-init-onboarding-fixes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/dev_stack/
├── cli/
│   ├── init_cmd.py          # FR-001/FR-002: _generate_secrets_baseline() exclusions
│   └── _shared.py           # FR-004/FR-005: has_existing_conflicts() predecessor filter
├── config.py                # FR-006: DEV_STACK_AGENT=none early return
├── pipeline/
│   └── stages.py            # FR-001/FR-002: security stage --exclude-files args
├── modules/
│   └── vcs_hooks.py         # FR-009/FR-010/FR-011: constitution template placement
├── templates/
│   └── constitution-template.md  # Baseline practices content (source for injection)
└── brownfield/
    └── conflict.py          # FR-012: mode determination considers predecessor resolution

tests/
├── unit/
│   ├── test_config.py       # FR-006 tests
│   ├── test_init_cmd.py     # FR-004/FR-005/FR-012 tests
│   └── test_stages.py       # FR-001/FR-002/FR-003 tests
├── contract/                # Contract tests for module interfaces
└── integration/             # End-to-end greenfield flow test

README.md                    # FR-007/FR-008: documentation updates
```

**Structure Decision**: Single project layout. All changes target existing files. No new directories or structural changes.

## Complexity Tracking

No constitution violations — table empty.

## Post-Design Constitution Re-Check

*Re-evaluation after Phase 1 design artifacts (data-model.md, contracts/, quickstart.md, research.md).*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. CLI-First Interface | ✅ PASS | No new commands. All changes are internal to existing `init` and `pipeline run` CLI commands. |
| II. Spec-Driven Development | ✅ PASS | Full spec → plan → research → data-model → contracts pipeline followed. |
| III. Automation by Default | ✅ PASS | Security stage fix is idempotent (`--exclude-files` stored in baseline `filters_used`). Module reorder preserves additive behavior. |
| IV. Brownfield Safety | ✅ PASS | `has_existing_conflicts()` filter to `pending` only preserves explicit consent semantics. Reinit migration preserves user content below `## User-Defined Requirements`. |
| V. AI-Native Architecture | ✅ PASS | `DEV_STACK_AGENT=none` early return is a sentinel, not a new agent interface. No changes to MCP or agent detection beyond the fix. |
| VI. Local-First Execution | ✅ PASS | All changes remain local. No cloud CI impact. |
| VII. Observability & Documentation | ✅ PASS | README update documents clean-commit workflow. Contracts document pre/post conditions for all modified functions. |
| VIII. Modularity & Composability | ✅ PASS | Module reorder (`speckit` before `vcs_hooks`) respects explicit dependency declaration. Guard in `_generate_constitutional_files()` checks for speckit presence, skips gracefully if absent — no implicit coupling. |
| Security & Quality Gates | ✅ PASS | Defense-in-depth: `--exclude-files` applied to both initial baseline and security stage scan. Real secrets still detected. Contract 2 explicitly requires FAIL on unaudited real secrets. |

**Post-design gate result**: PASS — no violations or regressions from design decisions.

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Feature Spec | [spec.md](spec.md) | Complete |
| Implementation Plan | [plan.md](plan.md) | Complete |
| Research | [research.md](research.md) | Complete (6 topics) |
| Data Model | [data-model.md](data-model.md) | Complete (6 entities) |
| Function Contracts | [contracts/function-contracts.md](contracts/function-contracts.md) | Complete (7 contracts) |
| Quickstart | [quickstart.md](quickstart.md) | Complete |
| Tasks | [tasks.md](tasks.md) | Complete (16 tasks) |
