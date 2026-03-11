# Tasks: Pipeline Commit Hygiene

**Input**: Design documents from `/specs/009-pipeline-commit-hygiene/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Unit tests included in Phase 8 per constitution Quality Standards ("New code MUST include corresponding tests").

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No project setup needed — this feature modifies an existing Python package. All dependencies (`detect-secrets`, `sphinx`, `codeboarding`) are already declared.

*(No tasks in this phase)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data model changes and hook infrastructure that MUST be complete before ANY user story can be implemented. These modify the shared dataclasses and hook plumbing that all stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T001 Add `output_paths: list[Path] = field(default_factory=list)` field to `StageResult` dataclass in `src/dev_stack/pipeline/stages.py`
- [X] T002 Add `hook_context: str | None = None` and `dry_run: bool = False` fields to `StageContext` dataclass in `src/dev_stack/pipeline/stages.py`
- [X] T003 [P] Add `auto_staged_paths: list[str] = field(default_factory=list)` field to `PipelineRunResult` dataclass in `src/dev_stack/pipeline/runner.py`
- [X] T004 [P] Export `DEV_STACK_HOOK_CONTEXT=pre-commit` environment variable before `dev-stack pipeline run` invocation in `src/dev_stack/templates/hooks/pre-commit`
- [X] T005 Read `os.environ.get("DEV_STACK_HOOK_CONTEXT")` in `PipelineRunner.run()` and pass value to `StageContext.hook_context` when constructing the context in `src/dev_stack/pipeline/runner.py`

**Checkpoint**: Foundational data model and hook infrastructure ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — First Commit Succeeds on First Attempt (Priority: P1) 🎯 MVP

**Goal**: Auto-stage pipeline-generated files during pre-commit hook execution so the commit lands cleanly on the first attempt — no index/working-tree mismatch, no need for a second `git add && git commit` cycle.

**Independent Test**: Run the full greenfield flow (`git init` → `uv init --package` → `dev-stack --json init` → `git add -A && git commit -m "Initial commit"`) in a fresh temporary directory. The commit must succeed on the first attempt.

### Implementation for User Story 1

- [X] T006 [US1] Implement `_auto_stage_outputs(repo_root: Path, paths: list[Path]) -> list[str]` function per Contract 3: check each path exists on disk, skip paths matched by `.gitignore` via `git check-ignore`, run `git add` for eligible files, log warnings on failure, never raise exceptions — in `src/dev_stack/pipeline/runner.py`
- [X] T007 [US1] Add post-run auto-staging step in `PipelineRunner.run()`: after all stages complete, collect `output_paths` from stage results with status pass or skip, call `_auto_stage_outputs(repo_root, collected_paths)` only when `hook_context == "pre-commit"` and `dry_run is False`, populate `PipelineRunResult.auto_staged_paths` with return value — in `src/dev_stack/pipeline/runner.py`
- [X] T008 [US1] Populate `StageResult.output_paths` with absolute path to `.secrets.baseline` in security stage executor (`_execute_security_stage`) when stage completes with status pass or skip — in `src/dev_stack/pipeline/stages.py`
- [X] T009 [US1] Populate `StageResult.output_paths` with API documentation output file paths (`docs/api/*.rst` stubs and `docs/_build/` HTML output) in docs-api stage executor (`_execute_docs_api_stage`) when stage completes with status pass or skip — in `src/dev_stack/pipeline/stages.py`
- [X] T010 [US1] Populate `StageResult.output_paths` with narrative guide output paths (`docs/guides/quickstart.md`, `docs/guides/development.md`, `docs/guides/index.md`) in docs-narrative stage executor when stage completes with status pass or skip — in `src/dev_stack/pipeline/stages.py`
- [X] T011 [US1] Populate `StageResult.output_paths` with `.codeboarding/` directory output paths in visualize stage executor when stage completes with status pass — in `src/dev_stack/pipeline/stages.py`

**Checkpoint**: Auto-staging infrastructure complete. First commit should succeed on the first attempt. Verify with greenfield flow.

> **Note on infra-sync stage (stage 7)**: No `output_paths` task is needed. The infra-sync executor (`_execute_infra_sync_stage`) is read-only — it detects drift between templates and installed files but never writes to the working tree. It produces no files to auto-stage.

---

## Phase 4: User Story 2 — Working Tree Stays Clean After Every Commit (Priority: P1)

**Goal**: Prevent unnecessary `.secrets.baseline` rewrites when only the `generated_at` timestamp changes, so `git status` shows a clean working tree after every commit.

**Independent Test**: After a successful commit in a project with an existing `.secrets.baseline`, run `git status --porcelain`. The output must be empty.

### Implementation for User Story 2

- [X] T012 [US2] Implement `_baseline_findings_changed(old_content: str, new_content: str) -> bool` function per Contract 4: parse both JSON strings, compare only the `results` key (ignoring `generated_at`, `version`, `plugins_used`, `filters_used`), return `True` if results differ or if either string is invalid JSON — in `src/dev_stack/pipeline/stages.py`
- [X] T013 [US2] Refactor security stage executor (`_execute_security_stage`) to: (a) read existing `.secrets.baseline` content before running `detect-secrets scan --baseline`, (b) run the scan (which overwrites the file with new timestamp), (c) read the updated file content, (d) call `_baseline_findings_changed(old, new)`, (e) if findings are unchanged restore the original file content (preserving old timestamp), (f) only add `.secrets.baseline` to `output_paths` when findings actually differ — in `src/dev_stack/pipeline/stages.py`

**Checkpoint**: Security baseline no longer causes dirty working tree from timestamp-only rewrites. Combined with US1 auto-staging, `git status --porcelain` is empty after every commit.

---

## Phase 5: User Story 3 — Visualize Stage Skips Gracefully Without LLM API Key (Priority: P2)

**Goal**: When CodeBoarding is installed but no LLM API key is configured, the visualize stage reports a clear "skip" message listing the five supported keys instead of a raw error traceback.

**Independent Test**: Install CodeBoarding, unset all LLM API key environment variables, run the pipeline. Verify stage 8 reports "skip" with a human-readable message listing the five API key names.

### Implementation for User Story 3

- [X] T014 [US3] Add `LLM_API_KEY_VARS: tuple[str, ...] = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "MISTRAL_API_KEY", "COHERE_API_KEY")` module-level constant and implement `_has_llm_api_key() -> bool` function per Contract 5 — in `src/dev_stack/pipeline/stages.py`
- [X] T015 [US3] Add LLM API key pre-check in visualize stage executor (`_execute_visualize_stage`): after the existing CLI availability check, call `_has_llm_api_key()` and if `False` return `StageResult` with status skip and message listing all five supported environment variable names (e.g., "No LLM API key found. Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, MISTRAL_API_KEY, COHERE_API_KEY") — in `src/dev_stack/pipeline/stages.py`

**Checkpoint**: Visualize stage skips gracefully with an actionable message. No raw tracebacks when LLM API key is missing.

---

## Phase 6: User Story 4 — Commit-Message Stage Reports Honestly When Inactive (Priority: P2)

**Goal**: When the user commits with `-m`, the commit-message stage reports "skip" with an explanatory message instead of falsely claiming "pass".

**Independent Test**: Run `git commit -m "test message"` and inspect pipeline output. Stage 9 must report "skip" (not "pass") with a message explaining that `-m` overrides generated messages.

### Implementation for User Story 4

- [X] T016 [US4] Implement `_user_message_provided(repo_root: Path) -> bool` function per Contract 6: check if `.git/COMMIT_EDITMSG` exists and contains non-empty non-comment lines (comment lines start with `#`), return `True` if user-supplied content is found — in `src/dev_stack/pipeline/stages.py`
- [X] T017 [US4] Add `-m` detection in commit-message stage executor (`_execute_commit_stage`): before agent invocation, call `_user_message_provided(repo_root)` and if `True` return `StageResult` with status skip and message "User-supplied commit message detected (-m flag); skipping generated message" — in `src/dev_stack/pipeline/stages.py`

**Checkpoint**: Commit-message stage accurately reports its status. No false "pass" when `-m` flag is used.

---

## Phase 7: User Story 5 — README Documents Soft-Gate Prerequisites (Priority: P3)

**Goal**: Document the LLM API key requirement for the visualize stage and the `-m` flag behavior for the commit-message stage so developers understand prerequisites before encountering unexpected behavior.

**Independent Test**: Review the README: visualize section mentions the five LLM API key names; commit-message section explains `-m` flag behavior.

### Implementation for User Story 5

- [X] T018 [US5] Add LLM API key requirement documentation to the visualize/CodeBoarding stage section: list all five supported environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`) and explain the stage skips gracefully when none are set — in `README.md`
- [X] T019 [US5] Add `-m` flag behavior documentation to the commit-message stage section: explain that user-supplied messages via `-m` take precedence and the stage only generates structured messages in interactive commit mode — in `README.md`

**Checkpoint**: README documents all soft-gate prerequisites. Developers can discover requirements before encountering unexpected behavior.

---

## Phase 8: Unit Tests (Constitution §Quality Standards)

**Purpose**: Satisfy constitution mandate: "New code MUST include corresponding tests." Each new helper function and behavioral change requires unit test coverage.

**⚠️ NOTE**: Write tests FIRST (before or alongside implementation); ensure they FAIL before the corresponding implementation task is complete.

- [X] T020 [P] Unit test for `_auto_stage_outputs()`: verify it stages existing files, skips nonexistent paths, skips gitignored paths, logs warnings on `git add` failure, and never raises exceptions — in `tests/unit/test_auto_stage.py`
- [X] T021 [P] Unit test for `_baseline_findings_changed()`: verify identical results return `False`, differing results return `True`, and invalid JSON returns `True` — in `tests/unit/test_baseline_comparison.py`
- [X] T022 [P] Unit test for `_has_llm_api_key()`: verify returns `True` when any of the 5 keys is set, `False` when none are set, and `False` when keys are empty strings — in `tests/unit/test_llm_key_check.py`
- [X] T023 [P] Unit test for `_user_message_provided()`: verify returns `True` when `COMMIT_EDITMSG` has user content, `False` when file is missing, `False` when file has only comments/whitespace — in `tests/unit/test_user_message.py`
- [X] T024 [P] Unit test for `StageResult.output_paths` population: verify security, docs-api, docs-narrative, and visualize executors populate `output_paths` on pass/skip and leave it empty on fail — in `tests/unit/test_output_paths.py`
- [X] T025 Unit test for auto-staging integration in `PipelineRunner.run()`: verify auto-staging is called when `hook_context == "pre-commit"` and skipped when `hook_context is None` or `dry_run is True` — in `tests/unit/test_runner_auto_stage.py`

**Checkpoint**: All new helper functions and behavioral changes have unit test coverage. Constitution Quality Standards satisfied.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and verification across all user stories.

- [X] T026 [P] Run `quickstart.md` manual verification checklist against all implemented changes
- [X] T027 Verify greenfield flow end-to-end per SC-001 and SC-002: `git init` → `uv init --package` → `dev-stack --json init` → `git add -A && git commit -m "Initial commit"` succeeds on first attempt and `git status --porcelain` is empty

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks — existing project
- **Foundational (Phase 2)**: No external dependencies — can start immediately. BLOCKS all user stories.
- **US1 (Phase 3)**: Depends on Phase 2 completion (StageResult.output_paths, StageContext.hook_context, PipelineRunResult.auto_staged_paths)
- **US2 (Phase 4)**: Depends on Phase 2 completion. Can run in parallel with US1 (different functions in stages.py). Full verification requires US1 auto-staging to be complete.
- **US3 (Phase 5)**: Depends on Phase 2 completion (StageResult.output_paths from T001). Independent of US1/US2.
- **US4 (Phase 6)**: Depends on Phase 2 completion (StageResult dataclass). Independent of US1/US2/US3.
- **US5 (Phase 7)**: No code dependencies — can start after US3 and US4 are complete (so docs match behavior).
- **Tests (Phase 8)**: Test tasks (T020-T025) can start in parallel with implementation (write tests first per TDD). T025 depends on T006-T007 implementation.
- **Polish (Phase 9)**: Depends on all user stories and tests being complete.

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P1)**: Can start after Phase 2 — no dependencies on other stories (shares stages.py with US1 but modifies different functions)
- **US3 (P2)**: Can start after Phase 2 — independent of US1/US2
- **US4 (P2)**: Can start after Phase 2 — independent of US1/US2/US3
- **US5 (P3)**: Should follow US3 and US4 so documentation reflects implemented behavior

### Within Each User Story

- Helper functions before executor modifications (e.g., T012 before T013, T014 before T015)
- Runner infrastructure before stage output_paths population (T006-T007 before T008-T011 for full integration)
- Core implementation before integration/validation

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T003 (runner.py) and T004 (pre-commit template) can run in parallel with T001-T002 (stages.py)

**Phase 3-6 (User Stories)**:
- After Phase 2, US1/US2/US3/US4 can all start in parallel (different functions, minimal overlap):
  - US1: runner.py (T006-T007) + stages.py stage executors (T008-T011)
  - US2: stages.py security executor (T012-T013)
  - US3: stages.py visualize executor (T014-T015)
  - US4: stages.py commit-message executor (T016-T017)
- Within US1: T006-T007 (runner.py) can run in parallel with T008-T011 (stages.py)

**Phase 7 (Documentation)**:
- T018 and T019 modify different sections of README.md — sequential but low-conflict

**Phase 8 (Tests)**:
- T020-T024 can all run in parallel (different test files, no dependencies)
- T025 depends on T006-T007 (runner.py) being at least stubbed
- Test tasks can start in parallel with implementation tasks (TDD: write tests first)

---

## Parallel Example: User Story 1

```text
# Worker A (runner.py):
T006: Implement _auto_stage_outputs() function
T007: Add post-run auto-staging in PipelineRunner.run()

# Worker B (stages.py — can run simultaneously with Worker A):
T008: Populate output_paths in security stage
T009: Populate output_paths in docs-api stage
T010: Populate output_paths in docs-narrative stage
T011: Populate output_paths in visualize stage
```

## Parallel Example: All P2 User Stories

```text
# Worker A (stages.py — visualize section):
T014: Add LLM_API_KEY_VARS constant and _has_llm_api_key()
T015: Add key check in visualize executor

# Worker B (stages.py — commit-message section):
T016: Implement _user_message_provided()
T017: Add -m detection in commit-message executor
```

---

## Implementation Strategy

### MVP Scope (P1 Stories Only)

**Phase 2 + Phase 3 (US1) + Phase 4 (US2) + relevant Phase 8 tests** = 17 tasks

This delivers the two highest-priority fixes:
1. First commit succeeds on first attempt (auto-staging)
2. Working tree stays clean after every commit (baseline comparison)

These resolve the commit-blocking issues that break the greenfield onboarding experience.

### Incremental Delivery

1. **Increment 1 (MVP)**: Phase 2 → Phase 3 → Phase 4 + Phase 8 tests (T020-T021, T024-T025) — Commit flow works correctly with test coverage
2. **Increment 2**: Phase 5 → Phase 6 + Phase 8 tests (T022-T023) — Soft-gate stages behave and report correctly
3. **Increment 3**: Phase 7 → Phase 9 — Documentation and validation

### File Change Summary

| File | Tasks | Changes |
|------|-------|---------|
| `src/dev_stack/pipeline/stages.py` | T001, T002, T008-T015, T016-T017 | StageResult + StageContext fields, output_paths in 4 executors, baseline comparison, LLM key check, -m detection |
| `src/dev_stack/pipeline/runner.py` | T003, T005-T007 | PipelineRunResult field, hook_context wiring, auto-staging function + post-run step |
| `src/dev_stack/templates/hooks/pre-commit` | T004 | Export DEV_STACK_HOOK_CONTEXT env var |
| `README.md` | T018-T019 | LLM API key docs + commit-message -m behavior docs || `tests/unit/pipeline/test_auto_stage.py` | T020 | Unit tests for `_auto_stage_outputs()` |
| `tests/unit/pipeline/test_baseline_comparison.py` | T021 | Unit tests for `_baseline_findings_changed()` |
| `tests/unit/pipeline/test_llm_key_check.py` | T022 | Unit tests for `_has_llm_api_key()` |
| `tests/unit/pipeline/test_user_message.py` | T023 | Unit tests for `_user_message_provided()` |
| `tests/unit/pipeline/test_output_paths.py` | T024 | Unit tests for output_paths population |
| `tests/unit/pipeline/test_runner_auto_stage.py` | T025 | Unit tests for runner auto-staging integration |