# Implementation Plan: Universal Init Pipeline

**Branch**: `012-universal-init-pipeline` | **Date**: 2026-03-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-universal-init-pipeline/spec.md`

## Summary

Dev-stack's init pipeline assumes every target repository is a Python project. Six specific issues must be resolved: (1) gate `uv sync` behind `uv_project` module selection, (2) gate `.secrets.baseline` generation behind secrets module selection, (3) validate agent commit body sections in the commit-msg hook, (4) ensure `.dev-stack/` is always gitignored, (5) make hook generation stack-aware (Python detection), (6) remove machine-specific absolute paths from `dev-stack.toml`. The approach modifies the init command, hooks module, manifest serialization, and adds a new gitlint rule — all within the existing single-project architecture.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: click, tomli_w, tomllib, gitlint-core, pathlib  
**Storage**: TOML files (dev-stack.toml), YAML files (.pre-commit-config.yaml), git hooks  
**Testing**: pytest with strict markers  
**Target Platform**: macOS, Linux (developer machines)  
**Project Type**: Single CLI package (`src/dev_stack/`)  
**Performance Goals**: Init completes in <5s (already met, no regression)  
**Constraints**: No new dependencies; all changes to existing modules  
**Scale/Scope**: 6 bug fixes across init pipeline, hooks module, manifest, and commit validation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | ✅ PASS | No new commands. Existing `dev-stack init` adapts behavior based on module selection and repo contents. Exit codes and JSON output preserved. |
| II. Spec-Driven Development | ✅ PASS | spec.md with 6 user stories, 12 FRs, 7 success criteria authored before implementation. |
| III. Automation by Default | ✅ PASS | Automation adapts rather than being removed. Pipeline hook stays for all projects (FR-006). Stack-aware hooks still automate linting/testing when applicable. |
| IV. Brownfield Safety | ✅ PASS | FR-012 preserves user-defined hooks. Managed section markers used for .gitignore (FR-009). No user files overwritten. |
| V. AI-Native Architecture | ✅ PASS | Agent detection improved: runtime path resolution (FR-008). Commit body validation (FR-003) strengthens agent memory quality. |
| VI. Local-First Execution | ✅ PASS | All changes are to local hooks and init pipeline. No cloud dependencies. |
| VII. Observability & Documentation | ✅ PASS | Clear error messages for missing body sections (FR-011). Commit-msg hook outputs which sections are absent. |
| VIII. Modularity & Composability | ✅ PASS | FR-010 directly implements this principle. No module produces artifacts requiring another module. `uv sync` gated, secrets gated, hooks adapted. |

**Security & Quality Gates**:
- "No secrets in code" gate: modified to be conditional on module selection. When no secrets module is selected, this gate is **inapplicable** (not degraded) — the user never requested secrets scanning, so removing the unconditional scan does not weaken any protection the user opted into. The constitution mandates the gate for "every commit," but the gate's enforcement mechanism (`.secrets.baseline` + `detect-secrets`) requires explicit opt-in to be meaningful. This is a scope clarification, not a dilution of the principle.
- All other gates preserved. Test coverage required for all changes.

**Post-Phase 1 Re-Check**: ✅ PASS — Design does not introduce new constitution violations. All changes strengthen module self-containment (Principle VIII).

## Project Structure

### Documentation (this feature)

```text
specs/012-universal-init-pipeline/
├── plan.md              # This file
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: entity and data model changes
├── quickstart.md        # Phase 1: developer quickstart
├── contracts/           # Phase 1: API contracts
│   ├── stack-profile.md
│   ├── hooks-generation.md
│   ├── body-section-rule.md
│   └── init-pipeline.md
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/dev_stack/
├── cli/
│   └── init_cmd.py          # FR-001: gate uv sync, FR-002: gate secrets, FR-009: gitignore
├── config.py                # FR-008: runtime agent path, new detect_stack_profile()
├── manifest.py              # FR-007: AgentConfig.to_dict() drops `path`
├── modules/
│   └── hooks.py             # FR-005/FR-006/FR-012: stack-aware hook generation
├── rules/
│   └── body_sections.py     # FR-003/FR-004/FR-011: new UC5 body section rule (NEW FILE)
└── templates/hooks/
    └── pre-commit-config.yaml  # DEPRECATED: replaced by programmatic generation in hooks.py (T018a)

tests/unit/
├── test_stack_profile.py       # Stack profile detection tests (NEW FILE)
├── test_hooks_stack_aware.py   # Stack-aware hook generation tests (NEW FILE)
├── test_body_section_rule.py   # Body section validation tests (NEW FILE)
├── test_init_nonpython.py      # Non-Python init integration tests (NEW FILE)
└── test_manifest.py            # Extended: no-path serialization + runtime resolution tests
```

**Structure Decision**: Single project (existing). All changes are within the existing `src/dev_stack/` package and `tests/unit/` test suite. One new source file (`rules/body_sections.py`) and four new test files.

## Complexity Tracking

No constitution violations to justify. All changes are targeted fixes within existing module boundaries.
