# Implementation Plan: Soften Sphinx `-W` for Brownfield Projects

**Branch**: `018-soften-sphinx-warnings` | **Date**: 2026-04-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/018-soften-sphinx-warnings/spec.md`

## Summary

Enforce a single docs strictness policy source (`[tool.dev-stack.pipeline] strict_docs`) across both pipeline execution and Sphinx Makefile scaffolding, with brownfield defaults remaining non-strict and greenfield defaults strict. The implementation preserves hard-fail behavior for true Sphinx build errors, keeps docs skip semantics unchanged when Sphinx/docs are missing, and explicitly avoids auto-migrating existing `docs/Makefile` files during normal pipeline runs.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: stdlib (`pathlib`, `tomllib`, `subprocess`), `tomli_w` (init-time config write), existing pipeline/module infrastructure in `dev_stack`  
**Storage**: Filesystem only (`pyproject.toml`, generated `docs/Makefile`)  
**Testing**: pytest (unit, contract, and integration coverage via `tests/unit/test_pipeline_stages.py`, `tests/unit/test_sphinx_docs.py`, `tests/unit/test_init_cmd.py`, `tests/contract/test_docs_strictness_contract.py`, and `tests/integration/test_docs_strictness.py`)  
**Target Platform**: macOS/Linux local-first CLI workflows  
**Project Type**: Single Python CLI project  
**Performance Goals**: No measurable regression in docs-api stage runtime; strictness resolution remains lightweight TOML read + command-flag branching  
**Constraints**: Default to strict behavior when config is missing/unreadable; no new CLI flags in this feature; no automatic rewrite of pre-existing Makefiles during pipeline runs  
**Scale/Scope**: Tight scope across existing docs-related surfaces (pipeline stage, Sphinx template renderer, init defaults, and unit/contract/integration regression coverage)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | ✅ PASS | No new CLI command required; behavior is controlled by existing `pyproject.toml` config. |
| II. Spec-Driven Development | ✅ PASS | Plan is derived from `spec.md` with all clarification answers integrated. |
| III. Automation by Default | ✅ PASS | Docs strictness behavior remains automatic in pipeline and scaffolding generation paths. |
| IV. Brownfield Safety | ✅ PASS | Core objective is brownfield-safe docs behavior; no forced rewrite of existing `docs/Makefile`. |
| V. AI-Native Architecture | ✅ PASS | No LLM/API architecture changes are required for this feature. |
| VI. Local-First Execution | ✅ PASS | Entire behavior runs locally via existing pipeline/module execution. |
| VII. Observability & Documentation | ✅ PASS | Existing stage outputs continue to expose exact Sphinx commands, including strictness flags. |
| VIII. Modularity & Composability | ✅ PASS | Changes remain confined to existing docs/pipeline modules and associated tests. |

**Pre-Phase 0 gate**: ✅ All principles pass. No justified violations required.

## Project Structure

### Documentation (this feature)

```text
specs/018-soften-sphinx-warnings/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── docs-strictness-policy.md
└── tasks.md              # created later by /speckit.tasks
```

### Source Code (repository root)

```text
src/dev_stack/
├── pipeline/
│   └── stages.py                 # docs-api strictness command assembly + strict_docs read fallback
├── modules/
│   └── sphinx_docs.py            # Makefile rendering strictness defaults
└── cli/
    └── init_cmd.py               # brownfield default strict_docs=false injection

tests/unit/
├── test_pipeline_stages.py       # docs-api strict/non-strict behavior and strict_docs parsing
├── test_sphinx_docs.py           # Makefile rendering/install/preview strictness behavior
└── test_init_cmd.py              # brownfield strict_docs default injection safeguards

tests/contract/
└── test_docs_strictness_contract.py

tests/integration/
└── test_docs_strictness.py
```

**Structure Decision**: Single-project structure retained. The feature intentionally limits changes to existing docs and pipeline modules, plus regression tests in existing unit test files.

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | ✅ PASS | Design keeps behavior behind existing CLI + config contract; no command surface growth. |
| II. Spec-Driven Development | ✅ PASS | Research, data model, contracts, and quickstart directly map to FR-001..FR-013. |
| III. Automation by Default | ✅ PASS | Strictness policy remains fully automatic for docs-api and scaffold generation. |
| IV. Brownfield Safety | ✅ PASS | Non-strict brownfield defaults persist via config; legacy Makefiles are not silently rewritten. |
| V. AI-Native Architecture | ✅ PASS | Design remains within existing AI-native architecture boundaries without new agent dependencies. |
| VI. Local-First Execution | ✅ PASS | No network or cloud services introduced. |
| VII. Observability & Documentation | ✅ PASS | Contracts and quickstart document strict/non-strict behavior and expected command output. |
| VIII. Modularity & Composability | ✅ PASS | No new module coupling; behavior expressed through existing helper boundaries (`_is_strict_docs`, `_read_strict_docs`, `_render_makefile`). |

**Post-design gate**: ✅ All principles pass. No violations introduced by design.

## Complexity Tracking

> No constitution violations. Table intentionally left empty.
