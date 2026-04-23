# Implementation Plan: Replace Codeboarding With Understand-Anything

**Branch**: `019-understand-anything-swap` | **Date**: 2026-04-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/019-understand-anything-swap/spec.md`

## Summary

Replace Codeboarding-based visualization with Understand-Anything graph workflows by migrating managed artifacts from `.codeboarding/` to `.understand-anything/`, removing README diagram injection, and enforcing graph freshness in both local pre-commit and required CI checks. The implementation keeps existing `dev-stack visualize` command/module surfaces for compatibility while swapping internals to Understand-Anything-compatible artifact validation, incremental impact detection based on graph metadata, and strict policy checks (including Git LFS threshold enforcement for large graph JSON files).

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: existing CLI/runtime stack (`click`, `rich`, `pathspec`, `PyYAML`, `gitlint-core`), stdlib (`json`, `pathlib`, `subprocess`, `hashlib`, `dataclasses`)  
**Storage**: Repository-tracked JSON artifacts under `.understand-anything/` plus internal state under `.dev-stack/viz/` and `.gitattributes` for LFS policy  
**Testing**: `pytest` (unit/integration/contract suites using `CliRunner` and patch-based subprocess mocking)  
**Target Platform**: Local macOS/Linux developer environments + GitHub Actions workflows generated from templates  
**Project Type**: Single Python CLI project  
**Performance Goals**: Graph freshness validation completes in <=5s for typical commits (<200 changed files) and <=15s for larger commits (<2k changed files) without invoking heavyweight full regeneration by default  
**Constraints**: Must remove Codeboarding references and README diagram injection entirely; must fail closed when graph impact detection is indeterminate; must enforce in both local hooks and required CI checks; must require Git LFS when committed graph JSON exceeds 10 MB  
**Scale/Scope**: Core changes across visualization command/module internals, pipeline stage behavior, CI templates, project README guidance, module verification, and all visualization-related test suites

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | ✅ PASS | Existing `dev-stack visualize` command remains user-facing entry point; behavior changes are exposed through CLI/JSON output only. |
| II. Spec-Driven Development | ✅ PASS | Plan implements accepted clarifications from `spec.md`, including local+CI enforcement and storage policy. |
| III. Automation by Default | ✅ PASS | Graph freshness becomes enforced in hooks and CI; no manual-only compliance path. |
| IV. Brownfield Safety | ✅ PASS | Migration strategy removes Codeboarding assets via managed paths and avoids overwriting unrelated user files. |
| V. AI-Native Architecture | ✅ PASS | No direct LLM API integration added; workflow remains agent/plugin-driven for graph generation. |
| VI. Local-First Execution | ✅ PASS | Primary enforcement runs locally in pre-commit with CI as required safety net. |
| VII. Observability & Documentation | ✅ PASS | Visualization remains mandatory via interactive graph artifacts; docs pivot from static README diagrams to reproducible graph workflow guidance. |
| VIII. Modularity & Composability | ✅ PASS | Visualization module boundary stays intact; internals swap tooling without coupling to unrelated modules. |

**Pre-Phase 0 gate**: ✅ All principles pass. No violations requiring complexity exceptions.

## Project Structure

### Documentation (this feature)

```text
specs/019-understand-anything-swap/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI contract)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/dev_stack/
├── cli/
│   └── visualize_cmd.py                 # MODIFIED — Understand-Anything graph policy flow
├── modules/
│   ├── visualization.py                 # MODIFIED — managed paths/constants/verify for .understand-anything
│   ├── hooks.py                         # MODIFIED — ensure hook behavior aligns with graph freshness gating
│   ├── ci_workflows.py                  # MODIFIED — required CI graph validation workflow content
│   └── uv_project.py                    # MODIFIED — ignore/scaffold defaults updated for .understand-anything
├── pipeline/
│   └── stages.py                        # MODIFIED — visualize stage outputs/fail behavior aligned to new policy
├── visualization/
│   ├── codeboarding_runner.py           # REMOVED/REPLACED — Codeboarding subprocess adapter
│   ├── output_parser.py                 # MODIFIED OR REMOVED — no README-mermaid parsing path
│   ├── readme_injector.py               # MODIFIED OR REMOVED — static README injection removed
│   ├── incremental.py                   # MODIFIED — freshness state persisted for .understand-anything policy
│   ├── scanner.py                       # MODIFIED — graph-impact path detection support
│   ├── understand_runner.py             # NEW — Understand-Anything artifact/check adapter
│   └── graph_policy.py                  # NEW — freshness, impact, and LFS enforcement logic
└── templates/
    ├── ci/dev-stack-tests.yml           # MODIFIED — required CI graph freshness check
    └── hooks/pre-commit                 # MODIFIED (if needed) — ensure graph check is part of local gate path

README.md                                 # MODIFIED — replace Codeboarding docs with Understand-Anything workflow
README.md.bak                             # MODIFIED — keep backup documentation in sync

tests/
├── contract/
│   └── test_module_interface.py          # MODIFIED — visualization managed files and module contract
├── integration/
│   ├── test_visualize.py                 # MODIFIED — end-to-end command behavior for .understand-anything
│   └── test_hooks_lifecycle.py           # MODIFIED — local hook blocking behavior for stale graph state
└── unit/
    ├── test_codeboarding_runner.py       # REMOVED/REPLACED — Understand runner tests
    ├── test_output_parser.py             # MODIFIED OR REMOVED — parser no longer tied to Codeboarding markdown
    ├── test_output_paths.py              # MODIFIED — output paths now under .understand-anything
    └── test_pipeline_stages.py           # MODIFIED — visualize stage enforcement semantics
```

**Structure Decision**: Keep the existing single-project structure and preserve the `visualization` module/CLI entrypoint names for compatibility, while replacing Codeboarding-specific internals with Understand-Anything-aware policy and artifact handling.

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | ✅ PASS | CLI remains stable (`dev-stack visualize`) and emits deterministic JSON status for automation. |
| II. Spec-Driven Development | ✅ PASS | Clarified requirements are mapped into research, data model, contract, and quickstart artifacts. |
| III. Automation by Default | ✅ PASS | Both local hook and CI enforcement are explicit design outputs. |
| IV. Brownfield Safety | ✅ PASS | Migration removes only managed Codeboarding assets and stale references; no destructive blanket rewrites. |
| V. AI-Native Architecture | ✅ PASS | Graph generation remains agent/plugin based; enforcement code remains tool-agnostic and local. |
| VI. Local-First Execution | ✅ PASS | Local pre-commit is first gate; CI is mandatory backstop for bypass cases. |
| VII. Observability & Documentation | ✅ PASS | Interactive graph artifacts become the canonical visualization medium; quickstart documents repeatable validation and remediation. |
| VIII. Modularity & Composability | ✅ PASS | New graph policy logic is isolated in dedicated visualization-layer components, preserving module boundaries. |

**Post-design gate**: ✅ All principles pass. No violations introduced by Phase 1 design.

## Complexity Tracking

> No constitution violations. Table intentionally empty.

## Implementation/Test Scope Alignment

- Contract coverage: `tests/contract/test_graph_freshness_contract.py` and `tests/contract/test_module_interface.py` validate API/schema and module interface commitments.
- Unit coverage: `tests/unit/test_understand_runner.py`, `tests/unit/test_graph_policy.py`, and updated visualization/hook unit suites validate detection order, fail-closed behavior, and policy helpers.
- Integration coverage: `tests/integration/test_visualize.py` and `tests/integration/test_hooks_lifecycle.py` validate bootstrap pass/fail, stale-graph blocking, and incremental refresh semantics.
- Task mapping: these checks correspond to tasks T011-T013, T014-T016, T021, T024-T027, T035-T037 and are required before marking implementation complete.

## Quickstart Validation Outcomes

| Scenario | Validation Command | Outcome |
|----------|--------------------|---------|
| Bootstrap artifact verification | `pytest -o addopts='' tests/unit/test_understand_runner.py tests/integration/test_visualize.py` | PASS |
| Local stale-graph blocking | `pytest -o addopts='' tests/integration/test_hooks_lifecycle.py::TestPreCommitGraphFreshness` | PASS |
| CI required-check wiring | `pytest -o addopts='' tests/contract/test_graph_freshness_contract.py tests/contract/test_module_interface.py` | PASS |
| Detection-mode and fail-closed policy | `pytest -o addopts='' tests/unit/test_graph_policy.py tests/unit/test_pipeline_stages.py::TestVisualizeStage` | PASS |
