# Implementation Plan: Brownfield Init Bug Remediation

**Branch**: `016-brownfield-init-bugs` | **Date**: 2026-04-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/016-brownfield-init-bugs/spec.md`

## Summary

Fix 8 bugs discovered during brownfield `dev-stack init`: false greenfield classification, requirements.txt silently ignored, existing packages invisible, APM version parse crash on ANSI output, broken --json pipeline output, first-commit lint gate fails on pre-existing code, mypy blind to non-`src/` packages, and commit-msg hook stripping markdown headers needed by UC5. All fixes are surgical patches to existing modules — no new modules or architectural changes required.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click, rich, packaging, tomli-w, yaml, gitlint-core, ruff
**Storage**: File-based (pyproject.toml, apm.yml, .dev-stack/ marker files)
**Testing**: pytest (unit + integration + contract)
**Target Platform**: macOS/Linux CLI
**Project Type**: Single project (Python package)
**Performance Goals**: N/A (CLI tool, sub-second operations)
**Constraints**: All changes must be backward-compatible with existing greenfield init paths
**Scale/Scope**: 8 bug fixes across 6 source files + README update

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | ✅ PASS | All fixes maintain CLI accessibility; --json gaps are being closed |
| II. Spec-Driven Development | ✅ PASS | This spec exists with 8 user stories, FRs, and acceptance criteria |
| III. Automation by Default | ✅ PASS | Auto-format on first brownfield commit extends automation; no manual steps added |
| IV. Brownfield Safety | ✅ PASS | Core theme — these fixes improve brownfield safety (conflict detection, requirements migration, package visibility) |
| V. AI-Native Architecture | ✅ PASS | Commit-msg hook fix (FR-001) restores agent commit workflow compatibility |
| VI. Local-First Execution | ✅ PASS | All fixes are local operations, no cloud dependencies added |
| VII. Observability & Documentation | ✅ PASS | Adding warnings for uncovered packages + requirements.txt improves observability; README update for first-commit behavior |
| VIII. Modularity & Composability | ✅ PASS | Changes are isolated to individual modules; no cross-module coupling introduced |

**Gate result**: PASS — no violations. All 8 fixes align with existing constitutional principles.

### Post-Design Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| IV. Brownfield Safety | ✅ PASS | requirements.txt merge uses confirmation prompt, not silent overwrite |
| III. Automation by Default | ✅ PASS | Auto-format is idempotent; marker file ensures single execution |
| VIII. Modularity & Composability | ✅ PASS | No new module dependencies; marker file follows established `.dev-stack/` pattern |

## Project Structure

### Documentation (this feature)

```text
specs/016-brownfield-init-bugs/
├── plan.md              # This file
├── research.md          # Phase 0 output — 8 research items resolved
├── data-model.md        # Phase 1 output — entity changes
├── quickstart.md        # Phase 1 output — verification guide
├── contracts/           # Phase 1 output — N/A (no new APIs)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (changes to existing files)

```text
src/dev_stack/
├── brownfield/
│   └── conflict.py              # FR-002: Add root-level .py scan
├── cli/
│   └── init_cmd.py              # FR-002, FR-004, FR-005, FR-007: Init pipeline fixes
│   └── visualize_cmd.py         # FR-006: JSON output gap fix
├── modules/
│   └── apm.py                   # FR-003: ANSI stripping in version parser
│   └── uv_project.py            # FR-005: Package detection scan helper
├── pipeline/
│   └── stages.py                # FR-007, FR-008: Auto-format + mypy warning
├── vcs/
│   └── hooks_runner.py          # FR-001: Comment stripping regex fix
└── README.md                    # FR-007: First-commit brownfield documentation

tests/
├── unit/
│   ├── test_hooks_runner.py     # FR-001: Comment stripping tests
│   ├── test_conflict.py         # FR-002: Greenfield classification tests
│   ├── test_apm.py              # FR-003: ANSI version parse tests
│   ├── test_init_cmd.py         # FR-004, FR-005: requirements + package detection
│   └── test_stages.py           # FR-007, FR-008: Auto-format + mypy warning
└── integration/
    └── test_brownfield_init.py  # End-to-end brownfield init test
```

**Structure Decision**: Single project — all changes are patches to existing source files within the established `src/dev_stack/` layout. No new modules or directories needed.

## Complexity Tracking

No constitution violations. Table intentionally left empty.
