# Tasks: Replace Codeboarding With Understand-Anything

**Input**: Design documents from `/specs/019-understand-anything-swap/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Explicit test tasks are included to satisfy constitution quality gates and module-level independent test coverage requirements.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Which user story this task maps to (`US1`, `US2`, `US3`)
- Every task includes exact file paths

## Path Conventions

- Single project layout: `src/dev_stack/` and `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish Understand-Anything policy scaffolding and baseline test harness.

- [X] T001 Create Understand-Anything runner module scaffold in src/dev_stack/visualization/understand_runner.py
- [X] T002 Create graph freshness policy module scaffold in src/dev_stack/visualization/graph_policy.py
- [X] T003 [P] Update visualization package exports for new runner/policy modules in src/dev_stack/visualization/__init__.py
- [X] T004 [P] Add tooling-agnostic visualization exception scaffolding in src/dev_stack/errors.py
- [X] T005 [P] Add unit-test scaffolds for new policy modules in tests/unit/test_understand_runner.py and tests/unit/test_graph_policy.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared graph parsing, detection, and policy primitives required by all user stories.

**⚠️ CRITICAL**: No user story work starts until this phase is complete.

- [X] T006 Implement graph artifact entities and freshness state enums in src/dev_stack/visualization/graph_policy.py
- [X] T007 Implement knowledge-graph JSON loader and metadata extraction for `.understand-anything/knowledge-graph.json` in src/dev_stack/visualization/understand_runner.py
- [X] T008 Implement ordered impact-detection logic (`diff_overlay`, `graph_path_intersection`, `indeterminate`) in src/dev_stack/visualization/graph_policy.py
- [X] T009 Implement storage policy checks for 10 MB threshold and `.gitattributes` LFS rule validation in src/dev_stack/visualization/graph_policy.py
- [X] T010 Add shared `.understand-anything` constants for CLI/module consumers in src/dev_stack/modules/visualization.py and src/dev_stack/cli/visualize_cmd.py
- [X] T011 [P] Add contract tests for graph policy request/response schema mapping in tests/contract/test_graph_freshness_contract.py
- [X] T012 [P] Implement parser/metadata unit coverage in tests/unit/test_understand_runner.py
- [X] T013 Implement fail-closed transition and remediation unit coverage in tests/unit/test_graph_policy.py

**Checkpoint**: Shared graph policy infrastructure and baseline automated tests are ready.

---

## Phase 3: User Story 1 - Generate Repository Graph (Priority: P1) 🎯 MVP

**Goal**: Contributors can bootstrap and consume committed interactive repository graph artifacts with no README static diagram dependency.

**Independent Test**: In a clean clone with committed graph artifacts, run `dev-stack visualize` and confirm bootstrap verification succeeds, metadata is exposed, and no static README diagram injection occurs.

### Tests for User Story 1

- [X] T014 [P] [US1] Update bootstrap success and metadata integration assertions in tests/integration/test_visualize.py
- [X] T015 [P] [US1] Update visualization module interface contract expectations for `.understand-anything` managed paths in tests/contract/test_module_interface.py
- [X] T016 [P] [US1] Update visualize output-path unit assertions from `.codeboarding` to `.understand-anything` in tests/unit/test_output_paths.py

### Implementation for User Story 1

- [X] T017 [US1] Replace visualize bootstrap flow to require committed `.understand-anything/knowledge-graph.json` in src/dev_stack/cli/visualize_cmd.py
- [X] T018 [US1] Replace command-level runner integration from Codeboarding to Understand-Anything in src/dev_stack/cli/visualize_cmd.py and src/dev_stack/visualization/codeboarding_runner.py
- [X] T019 [US1] Update visualization module install/verify/uninstall lifecycle for `.understand-anything` assets and legacy cleanup in src/dev_stack/modules/visualization.py
- [X] T020 [US1] Update visualize stage output collection and messaging for `.understand-anything/*` artifacts in src/dev_stack/pipeline/stages.py
- [X] T021 [US1] Update visualize stage behavior unit tests for bootstrap expectations in tests/unit/test_pipeline_stages.py
- [X] T022 [US1] Add supported plugin experience matrix and required interaction checks in specs/019-understand-anything-swap/quickstart.md
- [X] T023 [US1] Add unsupported-plugin remediation messaging in src/dev_stack/cli/visualize_cmd.py

**Checkpoint**: User Story 1 is independently functional and provides MVP value.

---

## Phase 4: User Story 2 - Iterative Graph Refresh (Priority: P2)

**Goal**: Contributors receive deterministic local and CI enforcement for stale graph artifacts based on graph-impact detection.

**Independent Test**: Modify graph-impacting code, run local commit flow to verify stale artifacts block commit with remediation, then push to verify required CI check fails until graph artifacts are refreshed and committed.

### Tests for User Story 2

- [X] T024 [US2] Add unit tests for `evaluateGraphImpact` detection modes in tests/unit/test_graph_policy.py
- [X] T025 [US2] Add unit tests for `validateGraphFreshness` blocked/remediation outcomes in tests/unit/test_graph_policy.py
- [X] T026 [P] [US2] Add integration tests for local hook stale-graph blocking in tests/integration/test_hooks_lifecycle.py
- [X] T027 [P] [US2] Add integration tests for iterative refresh pass/fail and indeterminate behavior in tests/integration/test_visualize.py

### Implementation for User Story 2

- [X] T028 [US2] Implement `evaluateGraphImpact` handler logic in src/dev_stack/visualization/graph_policy.py
- [X] T029 [US2] Implement `validateGraphFreshness` handler logic with fail-closed semantics in src/dev_stack/visualization/graph_policy.py
- [X] T030 [US2] Wire freshness blocking into local pre-commit execution in src/dev_stack/vcs/hooks_runner.py and src/dev_stack/templates/hooks/pre-commit.py
- [X] T031 [US2] Ensure hooks module installs freshness-aware pre-commit template flow in src/dev_stack/modules/hooks.py
- [X] T032 [US2] Add required CI graph freshness check job `dev-stack-graph-freshness` in src/dev_stack/templates/ci/dev-stack-tests.yml
- [X] T033 [US2] Update CI workflow module verify/install logic for `dev-stack-graph-freshness` presence in src/dev_stack/modules/ci_workflows.py
- [X] T034 [US2] Document and verify protected-branch required-check configuration in specs/019-understand-anything-swap/quickstart.md

**Checkpoint**: User Story 2 is independently functional with local and required CI enforcement.

---

## Phase 5: User Story 3 - Remove Codeboarding Footprint (Priority: P3)

**Goal**: All active Codeboarding references and static README diagram workflows are removed in favor of Understand-Anything-only guidance.

**Independent Test**: Search project docs/templates/source for active Codeboarding references and confirm remaining visualization guidance points exclusively to Understand-Anything interactive graph workflows.

### Tests for User Story 3

- [X] T035 [P] [US3] Replace Codeboarding runner unit coverage with Understand runner coverage in tests/unit/test_codeboarding_runner.py and tests/unit/test_understand_runner.py
- [X] T036 [P] [US3] Update parser/injector unit expectations for no static README diagram coupling in tests/unit/test_output_parser.py
- [X] T037 [P] [US3] Add integration assertion that visualize no longer injects README diagram markers in tests/integration/test_visualize.py

### Implementation for User Story 3

- [X] T038 [US3] Remove Codeboarding-specific parser execution from active visualize flow in src/dev_stack/visualization/output_parser.py and src/dev_stack/cli/visualize_cmd.py
- [X] T039 [US3] Remove static README diagram injection coupling from src/dev_stack/visualization/readme_injector.py and src/dev_stack/cli/visualize_cmd.py
- [X] T040 [US3] Rename `CodeBoardingError` to a tooling-agnostic visualization error and update imports in src/dev_stack/errors.py, src/dev_stack/cli/visualize_cmd.py, src/dev_stack/pipeline/stages.py, and src/dev_stack/modules/visualization.py
- [X] T041 [US3] Replace `.codeboarding` ignore defaults with `.understand-anything` artifact policy entries in src/dev_stack/modules/uv_project.py
- [X] T042 [US3] Update visualization policy guidance to Understand-Anything-only workflow in README.md and README.md.bak
- [X] T043 [US3] Add automated guardrail checks for Codeboarding/dual-tool reference reintroduction in src/dev_stack/visualization/graph_policy.py and src/dev_stack/pipeline/stages.py
- [X] T044 [US3] Remove legacy Codeboarding technology notes from .github/agents/copilot-instructions.md

**Checkpoint**: User Story 3 is independently complete with single-tool visualization policy enforcement.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, measurable-outcome instrumentation, and rollout hardening across all stories.

- [X] T045 [P] Run final reference audit for `codeboarding|.codeboarding` and patch remaining active paths in src/dev_stack/** and README.md
- [X] T046 [P] Update graph freshness contract examples for required-check naming and diagnostics in specs/019-understand-anything-swap/contracts/graph-freshness.openapi.yaml
- [X] T047 Reconcile plan/task test-scope consistency notes in specs/019-understand-anything-swap/plan.md and specs/019-understand-anything-swap/tasks.md
- [X] T048 Finalize SC-004 sampling template and reporting table in specs/019-understand-anything-swap/quickstart.md
- [X] T049 Validate quickstart end-to-end bootstrap/refresh/CI scenarios and record outcomes in specs/019-understand-anything-swap/plan.md
- [X] T050 Produce final migration compliance checklist for existing repositories in specs/019-understand-anything-swap/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; can start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2 and builds on US1 bootstrap behavior.
- **Phase 5 (US3)**: Depends on Phase 2 and should finalize after US1/US2 integration points stabilize.
- **Phase 6 (Polish)**: Depends on completion of all selected user stories.

### User Story Dependencies

- **US1 (P1)**: Starts after foundational completion; no dependency on other stories.
- **US2 (P2)**: Requires foundational policy primitives and US1 bootstrap behavior.
- **US3 (P3)**: Requires foundational primitives; complete final cleanup after US1/US2 are integrated.

### Within Each User Story

- Test tasks execute before or alongside implementation tasks and must validate changed behavior.
- Shared policy handlers must be implemented before hook/CI wiring.
- Command/module behavior updates precede documentation finalization.

### Parallel Opportunities

- Setup: T003, T004, and T005 can run in parallel.
- Foundational: T011 and T012 can run in parallel once T006-T010 foundations exist.
- US1: T014, T015, and T016 can run in parallel.
- US2: T026 and T027 can run in parallel; T032 and T033 can run in parallel after policy handlers exist.
- US3: T035, T036, and T037 can run in parallel; T042 and T044 can run in parallel.
- Polish: T045 and T046 can run in parallel.

---

## Parallel Example: User Story 1

```text
Parallel block:
- T014 [US1] Update visualize integration bootstrap assertions in tests/integration/test_visualize.py
- T015 [US1] Update module interface contract assertions in tests/contract/test_module_interface.py
- T016 [US1] Update visualize output-path unit assertions in tests/unit/test_output_paths.py
```

## Parallel Example: User Story 2

```text
Parallel block:
- T026 [US2] Add stale-graph blocking hook integration tests in tests/integration/test_hooks_lifecycle.py
- T027 [US2] Add iterative refresh integration tests in tests/integration/test_visualize.py
```

## Parallel Example: User Story 3

```text
Parallel block:
- T042 [US3] Update README.md and README.md.bak guidance to Understand-Anything-only workflow
- T044 [US3] Remove legacy Codeboarding notes in .github/agents/copilot-instructions.md
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational).
3. Complete Phase 3 (US1).
4. Validate US1 checkpoint in a clean clone.
5. Demo/deploy MVP graph bootstrap behavior.

### Incremental Delivery

1. Deliver US1 (bootstrap graph workflow).
2. Deliver US2 (iterative refresh + local/CI enforcement).
3. Deliver US3 (full Codeboarding removal + guardrails).
4. Execute Phase 6 polish and rollout hardening.

### Parallel Team Strategy

1. Team completes Setup + Foundational together.
2. After foundational checkpoint:
   - Engineer A: US1 command/module integration and bootstrap behavior.
   - Engineer B: US2 policy, hook, and CI enforcement.
   - Engineer C: US3 cleanup, documentation migration, and guardrails.
3. Rejoin for Phase 6 verification and release readiness.

---

## Notes

- `[P]` markers are only applied to tasks touching separate files with no direct dependency conflicts.
- Every user story includes explicit validation tasks and independent test criteria.
- Task IDs are sequential and implementation-ready for immediate `/speckit.implement` execution.
