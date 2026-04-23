# Tasks: Soften Sphinx `-W` for Brownfield Projects

**Input**: Design documents from `/specs/018-soften-sphinx-warnings/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Automated coverage is explicitly required by FR-008.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`)
- Every task includes an exact file path

## Path Conventions

- **Single project**: `src/dev_stack/` and `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create test scaffolding and shared fixtures for strictness-policy validation.

- [X] T001 Create docs strictness contract test scaffold in tests/contract/test_docs_strictness_contract.py
- [X] T002 Create docs strictness integration test scaffold in tests/integration/test_docs_strictness.py
- [X] T003 [P] Add reusable strict_docs pyproject fixture helper in tests/unit/test_pipeline_stages.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish strictness policy resolution and precedence guarantees used by all stories.

**⚠️ CRITICAL**: No user story work starts until this phase is complete.

- [X] T004 Align `_is_strict_docs` fallback and precedence behavior in src/dev_stack/pipeline/stages.py
- [X] T005 [P] Align `_read_strict_docs` fallback and precedence behavior in src/dev_stack/modules/sphinx_docs.py
- [X] T006 [P] Preserve explicit strict_docs values when setting brownfield defaults in src/dev_stack/cli/init_cmd.py
- [X] T007 Add resolver parity contract tests for pipeline/module strictness readers in tests/contract/test_docs_strictness_contract.py
- [X] T008 Add foundational unit tests for missing/unreadable pyproject strict fallback in tests/unit/test_pipeline_stages.py

**Checkpoint**: Strictness policy resolution is consistent across pipeline and module generation paths.

---

## Phase 3: User Story 1 - Unblock Brownfield Docs Validation (Priority: P1) 🎯 MVP

**Goal**: Repositories running with `strict_docs = false` can pass docs-api on warnings while still failing on real build errors.

**Independent Test**: Run docs-api with `strict_docs = false` and warnings-only output to verify pass plus execution of a subsequent stage; run with build errors to verify hard fail.

### Tests for User Story 1

- [X] T009 [P] [US1] Add contract test for non-strict docs-api command omitting `-W` and `--keep-going` in tests/contract/test_docs_strictness_contract.py
- [X] T010 [P] [US1] Add integration test for `strict_docs = false` warnings-only docs-api pass path and continuation to a subsequent stage in tests/integration/test_docs_strictness.py

### Implementation for User Story 1

- [X] T011 [US1] Update docs-api command assembly to omit warning-fatal flags when strict_docs=false in src/dev_stack/pipeline/stages.py
- [X] T012 [US1] Preserve hard-fail behavior for true Sphinx build errors in non-strict mode in src/dev_stack/pipeline/stages.py
- [X] T013 [US1] Add/adjust unit tests for non-strict warnings-pass, errors-fail, and subsequent-stage execution assertions in tests/unit/test_pipeline_stages.py

**Checkpoint**: Brownfield warning debt no longer hard-fails docs-api, but real Sphinx errors remain hard failures.

---

## Phase 4: User Story 2 - Preserve Greenfield Strictness (Priority: P2)

**Goal**: Repositories running with `strict_docs = true` keep strict docs behavior (`-W --keep-going`) and fail on warnings.

**Independent Test**: Run docs-api with `strict_docs = true` and warnings to verify fail; run with clean docs to verify pass.

### Tests for User Story 2

- [X] T014 [P] [US2] Add contract test for strict docs-api command requiring `-W --keep-going` in tests/contract/test_docs_strictness_contract.py
- [X] T015 [P] [US2] Add integration test for `strict_docs = true` warnings causing docs-api failure in tests/integration/test_docs_strictness.py

### Implementation for User Story 2

- [X] T016 [US2] Ensure strict-mode docs-api path always appends `-W --keep-going` in src/dev_stack/pipeline/stages.py
- [X] T017 [US2] Enforce strict fallback when strict_docs key is absent or unreadable in src/dev_stack/pipeline/stages.py
- [X] T018 [US2] Add/adjust unit tests for greenfield strict warnings-fail behavior in tests/unit/test_pipeline_stages.py

**Checkpoint**: Greenfield strictness remains intact and explicit strict defaults are enforced.

---

## Phase 5: User Story 3 - Mode-Aware Docs Scaffold Defaults (Priority: P3)

**Goal**: Generated docs defaults align with strictness policy and do not auto-migrate existing Makefiles during pipeline runs.

**Independent Test**: Generate Makefile in strict and non-strict modes and verify exact `SPHINXOPTS` values; verify legacy Makefile is unchanged by normal pipeline execution.

### Tests for User Story 3

- [X] T019 [P] [US3] Add contract test for strict/non-strict Makefile `SPHINXOPTS` rendering in tests/contract/test_docs_strictness_contract.py
- [X] T020 [P] [US3] Add integration test verifying legacy docs/Makefile is unchanged during normal pipeline runs in tests/integration/test_docs_strictness.py

### Implementation for User Story 3

- [X] T021 [US3] Render non-strict Makefile defaults as `SPHINXOPTS  ?= ` in src/dev_stack/modules/sphinx_docs.py
- [X] T022 [US3] Keep strict Makefile defaults as `SPHINXOPTS  ?= -W --keep-going` in src/dev_stack/modules/sphinx_docs.py
- [X] T023 [US3] Ensure install/preview paths always pass strict_docs policy into Makefile generation in src/dev_stack/modules/sphinx_docs.py
- [X] T024 [US3] Add unit tests for strict/non-strict Makefile render/install/preview outputs in tests/unit/test_sphinx_docs.py
- [X] T025 [US3] Add init-unit tests for brownfield default injection and explicit non-overwrite behavior in tests/unit/test_init_cmd.py

**Checkpoint**: Generated docs defaults are policy-aligned and migration boundaries are enforced.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation updates across all stories.

- [X] T026 [P] Update feature validation steps and expected outputs in specs/018-soften-sphinx-warnings/quickstart.md
- [X] T027 [P] Synchronize strictness contract examples with final behavior in specs/018-soften-sphinx-warnings/contracts/docs-strictness-policy.md
- [X] T028 Run targeted docs strictness regression commands and record verification notes in specs/018-soften-sphinx-warnings/quickstart.md
- [X] T029 [P] Add unit regression tests for docs-api skip behavior when `docs/` is missing and when Sphinx tooling is unavailable in tests/unit/test_pipeline_stages.py
- [X] T030 Run non-doc pipeline regression subset (lint/typecheck/test/security paths) and record unchanged-stage outcomes in specs/018-soften-sphinx-warnings/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies.
- **Phase 2 (Foundational)**: depends on Phase 1 and blocks all user stories.
- **Phase 3 (US1)**: depends on Phase 2.
- **Phase 4 (US2)**: depends on Phase 2 (recommended after US1 due shared file edits in `stages.py`).
- **Phase 5 (US3)**: depends on Phase 2.
- **Phase 6 (Polish)**: depends on completion of all selected user stories.

### User Story Dependencies

- **US1 (P1)**: starts immediately after foundational completion.
- **US2 (P2)**: independently testable after foundational completion; can run after US1 for lower merge risk.
- **US3 (P3)**: independently testable after foundational completion; primarily touches Sphinx module and init defaults.

### Within Each User Story

- Write tests first and confirm failure before implementation.
- Update runtime/build logic before finalizing unit and integration assertions.
- Complete story checkpoint before moving to next priority story.

### Parallel Opportunities

- **Setup**: T001 and T002 can run in parallel; T003 can run in parallel with either.
- **Foundational**: T005 and T006 can run in parallel while T004 is in progress.
- **US1**: T009 and T010 run in parallel before T011/T012; T013 follows implementation.
- **US2**: T014 and T015 run in parallel before T016/T017; T018 follows implementation.
- **US3**: T019 and T020 run in parallel; T024 and T025 can run in parallel after T021-T023.
- **Polish**: T026, T027, and T029 can run in parallel before T028 and T030 verification capture.

---

## Parallel Example: User Story 1

```bash
# Parallel test authoring
Task T009: tests/contract/test_docs_strictness_contract.py
Task T010: tests/integration/test_docs_strictness.py

# Sequential implementation and validation
Task T011: src/dev_stack/pipeline/stages.py
Task T012: src/dev_stack/pipeline/stages.py
Task T013: tests/unit/test_pipeline_stages.py
```

## Parallel Example: User Story 2

```bash
# Parallel test authoring
Task T014: tests/contract/test_docs_strictness_contract.py
Task T015: tests/integration/test_docs_strictness.py

# Sequential implementation and validation
Task T016: src/dev_stack/pipeline/stages.py
Task T017: src/dev_stack/pipeline/stages.py
Task T018: tests/unit/test_pipeline_stages.py
```

## Parallel Example: User Story 3

```bash
# Parallel tests
Task T019: tests/contract/test_docs_strictness_contract.py
Task T020: tests/integration/test_docs_strictness.py

# Implementation in Sphinx module
Task T021: src/dev_stack/modules/sphinx_docs.py
Task T022: src/dev_stack/modules/sphinx_docs.py
Task T023: src/dev_stack/modules/sphinx_docs.py

# Parallel validation updates
Task T024: tests/unit/test_sphinx_docs.py
Task T025: tests/unit/test_init_cmd.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1) end-to-end.
3. Validate brownfield warnings-pass/errors-fail checkpoint.
4. Demo/ship MVP value before expanding scope.

### Incremental Delivery

1. Setup + foundational policy alignment.
2. US1 for brownfield unblock (MVP).
3. US2 to preserve greenfield strictness.
4. US3 to enforce scaffold defaults and migration boundaries.
5. Polish and final regression validation.

### Parallel Team Strategy

1. Team completes Setup + Foundational together.
2. After checkpoint:
   - Developer A: US1 tasks (pipeline behavior)
   - Developer B: US2 tasks (strict regression path)
   - Developer C: US3 tasks (Makefile/render/init behavior)
3. Merge and run Phase 6 cross-cutting verification.

---

## Notes

- Every task follows required checklist format and includes a concrete path.
- Story phases remain independently testable and delivery-friendly.
- Existing Makefile auto-migration remains out of scope for this feature.
