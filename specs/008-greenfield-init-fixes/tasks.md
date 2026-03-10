# Tasks: Greenfield Init Fixes

**Input**: Design documents from `/specs/008-greenfield-init-fixes/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Required by Constitution (Quality Standards: "New code MUST include corresponding tests."). Test tasks are included per plan.md test file inventory.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. US1 and US2 share the same root cause fix (brownfield guard + force propagation), which is placed in the Foundational phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Not applicable — this is a bugfix feature on an existing codebase. No new project initialization or structure changes needed. Branch `008-greenfield-init-fixes` already exists.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the root cause that blocks US1, US2, and the primary path for US3. Both changes are needed together — T001 makes `force=True` do the right thing inside the module, T002 ensures `force=True` is actually passed for greenfield repos.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T001 [P] Refine brownfield guard in src/dev_stack/modules/uv_project.py — when `force=True` and `pyproject.toml` already exists, skip `uv init` (Step 1) but execute `_augment_pyproject()` (Step 2), `_scaffold_tests()` (Step 3), `_run_uv_lock()` (Step 4), and `_ensure_standard_gitignore()` (Step 5). See Contract 1 in contracts/internal-api.md. **Implicitly covers FR-003** (unblocks existing `uv sync --all-extras` in init_cmd.py by making deps available) **and FR-008** (unblocks `_run_uv_lock()` — Step 4).
- [X] T002 [P] Fix greenfield force propagation in src/dev_stack/cli/init_cmd.py — add `is_greenfield` to `effective_force` calculation so greenfield predecessor repos pass `force=True` to modules. Change `effective_force = force or existing_conflicts` to `effective_force = force or existing_conflicts or is_greenfield`. See Contract 2 in contracts/internal-api.md. **Implicitly covers FR-003** (the existing `uv sync --all-extras` call at line ~151 now runs after deps are in pyproject.toml).

**Checkpoint**: Foundation ready — `dev-stack init` now invokes `_augment_pyproject()`, `_scaffold_tests()`, `_run_uv_lock()`, and `_ensure_standard_gitignore()` for greenfield repos. User story implementation can begin.

---

## Phase 3: User Story 1 — Tests Scaffold Created on Greenfield Init (Priority: P1) 🎯 MVP

**Goal**: `dev-stack init` creates `tests/__init__.py` and `tests/test_placeholder.py` in greenfield repos, and these files appear in the "created" list in the init report.

**Independent Test**: Run `dev-stack --json init` in a fresh `uv init --package` repo and verify `tests/__init__.py` and `tests/test_placeholder.py` exist on disk with correct content.

**Note**: The primary fix is delivered by the Foundational phase (T001 + T002). `_scaffold_tests()` already contains correct logic — it just wasn't being called. This phase ensures brownfield safety edge cases are handled.

### Implementation for User Story 1

- [X] T003 [US1] Ensure `_scaffold_tests()` in src/dev_stack/modules/uv_project.py has skip-if-exists guards for `tests/__init__.py` and `tests/test_placeholder.py` — if the file already exists on disk, skip creating it but do NOT error. This preserves user-created test files during `--force` reinit (FR-007).

**Checkpoint**: After T001 + T002 + T003, a greenfield init creates the test scaffold, and a reinit preserves existing test files.

---

## Phase 4: User Story 2 — Dev Dependencies Pre-configured in pyproject.toml (Priority: P1)

**Goal**: `dev-stack init` adds `[project.optional-dependencies.dev]` (ruff, mypy, pytest, pytest-cov) and `[project.optional-dependencies.docs]` (sphinx, sphinx-autodoc-typehints, myst-parser) to `pyproject.toml`, then auto-installs them via `uv sync`.

**Independent Test**: Run `dev-stack --json init` in a fresh repo and verify `pyproject.toml` contains both optional-dependency groups and `.venv/bin/ruff`, `.venv/bin/mypy`, `.venv/bin/pytest` exist.

**Note**: The primary fix is delivered by the Foundational phase (T001 + T002). `_augment_pyproject()` already contains correct logic. This phase handles edge cases and the `uv sync` failure path.

### Implementation for User Story 2

- [X] T004 [P] [US2] Ensure `_augment_pyproject()` in src/dev_stack/modules/uv_project.py has skip-if-exists guards for existing optional-dependency groups — if `dev` or `docs` group already exists in `[project.optional-dependencies]`, preserve the existing entries rather than overwriting (FR-007). Also handle edge case of existing but empty `[project.optional-dependencies]` section.
- [X] T005 [P] [US2] Add `uv sync` failure handling in src/dev_stack/cli/init_cmd.py — wrap the `uv sync --all-extras` subprocess call with error handling. On failure (non-zero exit code), emit a warning containing the failure reason and the exact retry command (`uv sync --extra dev --extra docs`), then continue init without aborting (FR-009).

**Checkpoint**: After T001 + T002 + T004 + T005, greenfield init adds dev/docs dependencies to `pyproject.toml`, auto-installs them, and gracefully handles install failures.

---

## Phase 5: User Story 3 — Pipeline Runs Substantively on First Commit (Priority: P1)

**Goal**: After `dev-stack init` (which now auto-installs dev tools), the first `git commit` executes lint, typecheck, and test stages with real results. When tools ARE missing (edge case), the pipeline provides clear remediation guidance and a hollow-pipeline warning banner.

**Independent Test**: After `dev-stack init` in a fresh repo, run `git add -A && git commit` and verify lint, typecheck, test stages show pass/fail (not skip). For the fallback path, simulate missing tools and verify the warning banner appears.

### Implementation for User Story 3

- [X] T006 [P] [US3] Add remediation hints to pipeline skip messages in src/dev_stack/pipeline/stages.py — change each skip reason to include the install command. `"ruff not installed in project venv"` → `"ruff not installed in project venv — run 'uv sync --extra dev' to install"`. Apply to ruff, mypy, pytest (extra dev) and sphinx (extra docs). See Contract 3 in contracts/internal-api.md (FR-004).
- [X] T007 [P] [US3] Add `warnings` field to `PipelineRunResult` dataclass in src/dev_stack/pipeline/runner.py — add `warnings: list[str] = field(default_factory=list)` to the dataclass. See Contract 4 in contracts/internal-api.md (FR-005).
- [X] T008 [US3] Add hollow-pipeline detection logic in src/dev_stack/pipeline/runner.py — after the stage execution loop, check if all three core stages (lint, typecheck, test) have `StageStatus.SKIP` status. If so, append a warning message to `PipelineRunResult.warnings`: `"⚠ No substantive validation: lint, typecheck, test all skipped due to missing tools. Run 'uv sync --extra dev' to install."` (FR-005). Depends on T007.
- [X] T009 [US3] Add warnings serialization to pipeline JSON output in src/dev_stack/cli/pipeline_cmd.py — include `"warnings"` key in the serialized output payload from `_serialize_run()` or equivalent function. When warnings are present in human-readable output, print each warning to stderr. See Contract 4 in contracts/internal-api.md (FR-005). Depends on T007.

**Checkpoint**: After Phase 5, the pipeline provides remediation hints for individual skipped stages and a warning banner when all core stages skip. The primary path (tools installed) runs substantively.

---

## Phase 6: User Story 4 — DEV_STACK_AGENT Persists Across Subprocesses (Priority: P2)

**Goal**: The pre-commit hook reads agent config from `dev-stack.toml` as fallback when `DEV_STACK_AGENT` env var is not set, so the user's init-time agent choice persists into hook subprocesses without requiring `export`.

**Independent Test**: Set `DEV_STACK_AGENT=none` (not exported) during `dev-stack init`, then `git commit`, and verify agent-dependent stages skip with reason `"coding agent unavailable"`.

### Implementation for User Story 4

- [X] T010 [US4] Add `_try_load_manifest()` helper function in src/dev_stack/cli/pipeline_cmd.py — read `dev-stack.toml` from `repo_root` using the existing manifest reader. Return `None` (not raise) if the file is missing or malformed, so the pipeline still works in repos that haven't run `dev-stack init`. See Contract 5 in contracts/internal-api.md (FR-006).
- [X] T011 [US4] Wire manifest into `AgentBridge` in src/dev_stack/cli/pipeline_cmd.py — call `_try_load_manifest(repo_root)` before constructing `AgentBridge`, then change `AgentBridge(repo_root)` to `AgentBridge(repo_root, manifest=manifest)`. This enables `detect_agent(manifest)` to use `manifest.agent.cli` as priority #2 fallback when `DEV_STACK_AGENT` env var is absent (FR-006). Depends on T010.

**Checkpoint**: After Phase 6, agent config set at init time persists via `dev-stack.toml` and is read by the pipeline hook without requiring the user to `export` the env var.

---

## Phase 7: Tests

**Purpose**: Satisfy Constitution Quality Standards ("New code MUST include corresponding tests"). Test files listed in plan.md Project Structure.

- [X] T012 [P] Unit tests for uv_project in tests/unit/test_uv_project.py — test brownfield guard refinement (T001), skip-if-exists guards for `_scaffold_tests()` (T003) and `_augment_pyproject()` (T004), `uv lock` execution path (FR-008), and file preservation in force/brownfield mode (FR-007). Covers FR-001, FR-002, FR-003, FR-007, FR-008, FR-009.
- [X] T013 [P] Unit tests for pipeline stages in tests/unit/test_stages.py — test that each skip reason string includes the remediation hint with the correct `uv sync --extra` command (FR-004).
- [X] T014 [P] Unit tests for pipeline runner in tests/unit/test_runner.py — test `PipelineRunResult.warnings` field population, hollow-pipeline detection when all core stages skip (FR-005), and manifest-based agent fallback (FR-006).
- [X] T015 Integration test for greenfield init in tests/integration/test_greenfield_init.py — end-to-end: `uv init --package` → `dev-stack init` → verify tests exist, deps in pyproject.toml, tools in venv, pipeline runs substantively on first commit.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end verification and safety checks across all user stories.

- [X] T016 Run quickstart.md verification steps end-to-end in a fresh test repo — follow all 8 steps in specs/008-greenfield-init-fixes/quickstart.md and confirm each expected outcome matches
- [X] T017 Verify brownfield safety — run `dev-stack init --force` in a repo with existing custom `pyproject.toml` (with user-defined optional-deps) and existing `tests/` directory (with user-written tests), confirm no data loss and existing content preserved per FR-007

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A — existing codebase
- **Foundational (Phase 2)**: No dependencies — can start immediately. BLOCKS all user stories.
- **US1 (Phase 3)**: Depends on Foundational (T001). Modifies same file as T001 (uv_project.py).
- **US2 (Phase 4)**: Depends on Foundational (T001 for uv_project.py, T002 for init_cmd.py).
- **US3 (Phase 5)**: Depends on Foundational phase completion. No file overlap with Phases 3–4.
- **US4 (Phase 6)**: Depends on Foundational phase completion. Shares pipeline_cmd.py with T009 (US3).
- **Tests (Phase 7)**: Depends on all implementation phases (2–6). T012–T015 can run in parallel (different files).
- **Polish (Phase 8)**: Depends on all user stories and tests being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependencies on other stories.
- **User Story 2 (P1)**: Can start after Foundational (Phase 2). No dependencies on other stories. US2 tasks can run in parallel with US1 (different files).
- **User Story 3 (P1)**: Can start after Foundational (Phase 2). No dependencies on US1/US2. Different files (stages.py, runner.py, pipeline_cmd.py).
- **User Story 4 (P2)**: Can start after Foundational (Phase 2). Should run after US3 Phase 5 since T009 and T010 both modify pipeline_cmd.py.
- **Tests**: Depend on all implementation phases. T012–T015 can run in parallel (different files).

### Within Each User Story

- Foundational changes before story-specific changes
- Core implementation before edge case handling
- Data model changes (runner.py warnings field) before consumers (pipeline_cmd.py serialization)
- Story complete before moving to next priority

### Parallel Opportunities

- **Foundational**: T001 and T002 can run in parallel (different files: uv_project.py vs init_cmd.py)
- **US1 + US2**: T003 (uv_project.py) and T005 (init_cmd.py) can run in parallel (different files)
- **US2**: T004 (uv_project.py) and T005 (init_cmd.py) can run in parallel (different files)
- **US3**: T006 (stages.py) and T007 (runner.py) can run in parallel (different files)
- **Across stories**: US3 (stages.py, runner.py) can overlap with US1/US2 (uv_project.py, init_cmd.py) since all target different files

---

## Parallel Example: Foundational Phase

```text
# Batch 1 — Both foundational tasks in parallel (different files):
T001: Refine brownfield guard in src/dev_stack/modules/uv_project.py
T002: Fix greenfield force propagation in src/dev_stack/cli/init_cmd.py
```

## Parallel Example: User Stories 1–3

```text
# After Foundational phase completes:

# Batch 2 — US1 + US2 + US3 tasks across different files:
T003: [US1] _scaffold_tests() guards in src/dev_stack/modules/uv_project.py
T005: [US2] uv sync failure handling in src/dev_stack/cli/init_cmd.py
T006: [US3] Skip message remediation hints in src/dev_stack/pipeline/stages.py
T007: [US3] PipelineRunResult.warnings field in src/dev_stack/pipeline/runner.py

# Batch 3 — Depends on Batch 2:
T004: [US2] _augment_pyproject() guards in src/dev_stack/modules/uv_project.py (after T003)
T008: [US3] Hollow-pipeline detection in src/dev_stack/pipeline/runner.py (after T007)
T009: [US3] Warnings serialization in src/dev_stack/cli/pipeline_cmd.py (after T007)

# Batch 4 — US4 (after pipeline_cmd.py batch 3 edits):
T010: [US4] _try_load_manifest() in src/dev_stack/cli/pipeline_cmd.py
T011: [US4] Wire manifest into AgentBridge in src/dev_stack/cli/pipeline_cmd.py

# Batch 5 — Tests (after all implementation, all in parallel):
T012: Unit tests in tests/unit/test_uv_project.py
T013: Unit tests in tests/unit/test_stages.py
T014: Unit tests in tests/unit/test_runner.py
T015: Integration test in tests/integration/test_greenfield_init.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001, T002)
2. Complete Phase 3: User Story 1 (T003)
3. **STOP and VALIDATE**: Run `dev-stack --json init` in a fresh `uv init --package` repo → verify `tests/` scaffold exists
4. This single checkpoint validates the root cause fix

### Incremental Delivery

1. Foundational (T001 + T002) → Root cause fixed
2. US1 (T003) → Test scaffold works → **MVP validated**
3. US2 (T004 + T005) → Dev deps pre-configured, auto-installed, failure-safe
4. US3 (T006–T009) → Pipeline gives actionable feedback when tools missing
5. US4 (T010 + T011) → Agent scoping persists across subprocesses
6. Tests (T012–T015) → Constitution compliance ("New code MUST include corresponding tests")
7. Polish (T016 + T017) → Full end-to-end verification

### Optimal Single-Developer Sequence

1. T001 → T002 (foundational — same session)
2. T003 → T004 (uv_project.py — same file, one session)
3. T005 (init_cmd.py — same file as T002, one session)
4. T006 (stages.py — standalone)
5. T007 → T008 (runner.py — same file, one session)
6. T009 → T010 → T011 (pipeline_cmd.py — same file, one session)
7. T012 → T013 → T014 → T015 (tests — one per file)
8. T016 → T017 (verification)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps tasks to specific user story for traceability
- US1 and US2 share the same root cause — the Foundational phase fix unblocks both
- `_scaffold_tests()` and `_augment_pyproject()` already contain correct logic; the bug was that they weren't being invoked
- T001 + T002 implicitly cover FR-003 (auto-install) and FR-008 (uv lock) — see task descriptions
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
