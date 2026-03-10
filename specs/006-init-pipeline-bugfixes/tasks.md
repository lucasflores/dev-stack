# Tasks: Init & Pipeline Bugfixes

**Input**: Design documents from `/specs/006-init-pipeline-bugfixes/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in the feature specification. Omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Verify existing environment before making changes

- [X] T001 Verify existing test suite passes with `pytest tests/ -x` and review files to be modified

---

## Phase 2: Foundational (Shared Helpers)

**Purpose**: New utility functions that multiple user stories depend on. MUST complete before user story work begins.

**⚠️ CRITICAL**: US1 depends on T002. US2 depends on T003.

- [X] T002 [P] Add `_tool_available_in_venv(tool, repo_root)` helper function using `shutil.which(tool, path=...)` in src/dev_stack/pipeline/stages.py
- [X] T003 [P] Add `is_greenfield_uv_package(pyproject_path)` fingerprint function (3-signal check: `uv_build` backend + sentinel description + no `[tool.*]`) in src/dev_stack/brownfield/conflict.py

**Checkpoint**: Foundational helpers ready — user story implementation can begin

---

## Phase 3: User Story 1 — Greenfield Bootstrap Completes Without Errors (Priority: P1) 🎯 MVP

**Goal**: A new user runs `uv init --package` → `dev-stack init` → first commit without errors or `--no-verify`.

**Independent Test**: Run the full greenfield flow in a fresh temporary directory and confirm the commit succeeds.

**FRs**: FR-001, FR-002, FR-003, FR-008

### Implementation for User Story 1

- [X] T004 [P] [US1] Update `_execute_typecheck_stage()` to use `_tool_available_in_venv("mypy", ...)` instead of bare `shutil.which("mypy")` — skip with "mypy not installed in project venv" when absent in src/dev_stack/pipeline/stages.py
- [X] T005 [US1] Update remaining stage executors (`_execute_lint_stage`, `_execute_test_stage`, `_execute_docs_api_stage`, `_execute_docs_narrative_stage`, `_execute_visualize_stage`) to use `_tool_available_in_venv()` for consistent venv-aware tool detection in src/dev_stack/pipeline/stages.py
- [X] T006 [P] [US1] Add `subprocess.run(["uv", "sync", "--all-extras"], cwd=repo_root, check=True)` call after module installation to create `.venv` with all dev dependencies in src/dev_stack/cli/init_cmd.py

**Checkpoint**: At this point, the typecheck stage skips gracefully when mypy is absent from the venv, all stages use venv Python, and init creates `.venv` with dev deps installed. The greenfield bootstrap flow should complete without blocking the first commit.

> **Edge case note**: If `.venv` is deleted mid-pipeline (e.g., user runs `rm -rf .venv` while pipeline is executing), stages should fail gracefully with a clear error ("project venv not found") rather than crash with an unhandled exception. The `_tool_available_in_venv()` helper returns `False` when `.venv/bin` doesn't exist, so stages will skip rather than crash.

---

## Phase 4: User Story 2 — Init Correctly Handles Expected Greenfield Files (Priority: P1)

**Goal**: Init recognizes `uv init --package` files as greenfield predecessors, not conflicts.

**Independent Test**: Run `uv init --package` then `dev-stack init` (without `--force`) and confirm no conflict is reported, mode is `"greenfield"`.

**FRs**: FR-004, FR-005

### Implementation for User Story 2

- [X] T007 [US2] Integrate `is_greenfield_uv_package()` into the init flow: after `build_conflict_report()`, check fingerprint and mark matching conflicts with `resolution = "greenfield_predecessor"` so `has_existing_conflicts()` returns `False` and `_determine_mode()` yields `"greenfield"` in src/dev_stack/cli/init_cmd.py. Also verify that repos with custom pyproject.toml (non-uv-generated, e.g., has `[tool.*]` sections or custom deps) are correctly treated as brownfield. The full predecessor allowlist includes: `pyproject.toml`, `src/<pkg>/__init__.py`, `.python-version`, and `README.md`.

**Checkpoint**: `dev-stack --json init` after `uv init --package` reports `"mode": "greenfield"` with zero conflicts. Truly brownfield repos still trigger conflict detection.

---

## Phase 5: User Story 3 — Pipeline Accurately Reports Stage Results (Priority: P2)

**Goal**: Pipeline reports `"completed_with_failures"` (not `"success"`) when hard-gate stages fail under `--force`, with non-zero exit code.

**Independent Test**: Run `dev-stack --json pipeline run --force` with a failing hard-gate stage and verify the JSON status and exit code.

**FRs**: FR-006

### Implementation for User Story 3

- [X] T008 [US3] Fix success calculation in `PipelineRunner.run()`: replace `success = aborted_stage is None or force` with `success = not any(r.status == StageStatus.FAIL and r.failure_mode == FailureMode.HARD for r in results)` in src/dev_stack/pipeline/runner.py
- [X] T009 [US3] Update `_serialize_run()` to return three-state status (`"success"` / `"completed_with_failures"` / `"failed"`) based on `result.success` and `force` flag in src/dev_stack/cli/pipeline_cmd.py

**Checkpoint**: `--force` with hard failures → exit 5 + `"completed_with_failures"`. All pass → exit 0 + `"success"`. Hard failure without `--force` → exit 5 + `"failed"`.

---

## Phase 6: User Story 4 — Dry-Run Init Works on Initialized Repos (Priority: P2)

**Goal**: `dev-stack --dry-run init` on an already-initialized repo shows an update preview instead of erroring.

**Independent Test**: Initialize a repo, then run `dev-stack --dry-run --json init` and confirm it returns a change preview without errors.

**FRs**: FR-007

### Implementation for User Story 4

- [X] T010 [US4] Modify the `already_initialized and not force` guard in `init_command()` to allow `ctx.dry_run` through — delegate to `_emit_dry_run_summary()` (or a new `_emit_update_preview()`) that shows files that would be added, modified, or conflicted in src/dev_stack/cli/init_cmd.py

**Checkpoint**: `dev-stack --dry-run --json init` on an initialized repo returns a preview payload without raising `SystemExit`. No files modified on disk.

---

## Phase 7: User Story 5 — CLI Version and Help Are Complete (Priority: P3)

**Goal**: `dev-stack --version` prints the semantic version. All commands have help descriptions.

**Independent Test**: Run `dev-stack --version` and `dev-stack --help`, verify version number and non-blank descriptions.

**FRs**: FR-009, FR-010

### Implementation for User Story 5

- [X] T011 [US5] Add `_get_version()` helper (using `importlib.metadata.version("dev-stack")` with `__version__` fallback) and `@click.version_option(version=_get_version(), prog_name="dev-stack")` decorator to the `cli` group in src/dev_stack/cli/main.py. Also set `__version__` in `src/dev_stack/__init__.py` as a fallback for editable installs.
- [X] T012 [US5] Update the `version` subcommand to include the actual version number in both human-readable and JSON output (add `"version"` field) in src/dev_stack/cli/main.py
- [X] T013 [P] [US5] Add `help="Update dev-stack configuration and module files in an existing repository."` to the `@cli.command("update")` decorator in src/dev_stack/cli/update_cmd.py

**Checkpoint**: `dev-stack --version` → `dev-stack 0.1.0`. `dev-stack --help` shows descriptions for all commands including `update`. `dev-stack --json version` includes `"version": "0.1.0"`.

---

## Phase 8: User Story 6 — Security Stage Properly Evaluates Findings (Priority: P3)

**Goal**: Security stage uses `.secrets.baseline` to evaluate real vs. false-positive findings.

**Independent Test**: Add a test file with a known secret pattern, run security stage, confirm FAIL. Remove it and confirm known false positives don't trigger failures.

**FRs**: FR-012

### Implementation for User Story 6

- [X] T014 [US6] Add `has_unaudited_secrets(baseline_path)` helper and update `_execute_security_stage()` to run `detect-secrets scan --baseline .secrets.baseline`, then check for unaudited/confirmed-real findings in src/dev_stack/pipeline/stages.py
- [X] T015 [US6] Add initial `.secrets.baseline` generation (`detect-secrets scan > .secrets.baseline`) during `dev-stack init` in src/dev_stack/cli/init_cmd.py

**Checkpoint**: Security stage reports FAIL for real secrets, PASS when only audited false positives remain. Init generates `.secrets.baseline` on first run.

---

## Phase 9: User Story 7 — README Validation Commands Use Correct Syntax (Priority: P3)

**Goal**: All validation commands in README use correct flag positions (global flags before subcommand).

**Independent Test**: Copy each command from the README, run it, confirm no flag-position errors.

**FRs**: FR-011

### Implementation for User Story 7

- [X] T016 [P] [US7] Fix all validation checklist flag positions — move global flags (`--json`, `--dry-run`, `--verbose`) before the subcommand (e.g., `dev-stack --json status` not `dev-stack status --json`) in README.md

**Checkpoint**: Every command in the README validation checklist runs without "unrecognized option" errors.

---

## Phase 10: User Story 8 — Rollback Tags Created for Greenfield Flow (Priority: P4)

**Goal**: `dev-stack init` creates a rollback tag even in the greenfield flow.

**Independent Test**: Run the full greenfield flow and confirm `git tag -l 'dev-stack-rollback-*'` returns at least one tag.

**FRs**: FR-013

### Implementation for User Story 8

- [X] T017 [US8] Ensure `create_rollback_tag()` is called in the greenfield flow — if no commits exist, create an initial commit before tagging in src/dev_stack/cli/init_cmd.py

**Checkpoint**: After greenfield init, `git tag -l 'dev-stack-rollback-*'` lists a tag.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories

- [X] T018 Run quickstart.md verification commands to validate all 14 fixes end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS user stories that need shared helpers
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1, US3, US5, US7 can begin in parallel (touch different files)
  - US2 should follow US1 (both modify `init_cmd.py`)
  - US4 should follow US2 (both modify `init_cmd.py`)
  - US6 should follow US1 (both modify `stages.py`)
  - US8 should follow US4 (both modify `init_cmd.py`)
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on T002 (foundational helper). No other story dependencies.
- **US2 (P1)**: Depends on T003 (foundational helper). Shares `init_cmd.py` with US1 — sequence after US1.
- **US3 (P2)**: No dependencies on other stories. Only touches `runner.py` and `pipeline_cmd.py`.
- **US4 (P2)**: Shares `init_cmd.py` with US1/US2 — sequence after US2.
- **US5 (P3)**: No dependencies on other stories. Only touches `main.py` and `update_cmd.py`.
- **US6 (P3)**: Shares `stages.py` with US1 and `init_cmd.py` with US2/US4 — sequence after both.
- **US7 (P3)**: No dependencies on other stories. Only touches `README.md`.
- **US8 (P4)**: Shares `init_cmd.py` with US1/US2/US4/US6 — sequence last among init changes.

### Within Each User Story

- Helpers before behavior changes
- Root cause fix before presentation/serialization changes
- Core implementation before integration points

### Parallel Opportunities

**After Foundational phase completes, this parallel batch is safe:**

| Stream A (stages.py) | Stream B (runner.py + pipeline_cmd.py) | Stream C (main.py + update_cmd.py) | Stream D (README.md) |
|---|---|---|---|
| US1: T004, T005 | US3: T008, T009 | US5: T011, T012, T013 | US7: T016 |

**Then sequentially on init_cmd.py:** US1 (T006) → US2 (T007) → US4 (T010) → US6 (T015) → US8 (T017)

---

## Parallel Example: After Foundational

```text
# Stream A — stages.py (US1):
T004: Update _execute_typecheck_stage() to use _tool_available_in_venv()
T005: Update remaining stage executors for venv-aware detection

# Stream B — runner.py + pipeline_cmd.py (US3):
T008: Fix success calculation in PipelineRunner.run()
T009: Add completed_with_failures status to _serialize_run()

# Stream C — main.py + update_cmd.py (US5):
T011: Add --version flag to CLI group
T012: Update version subcommand with actual version
T013: Add help text to update command

# Stream D — README.md (US7):
T016: Fix validation checklist flag positions
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup (verify environment)
2. Complete Phase 2: Foundational (T002, T003)
3. Complete Phase 3: US1 — Greenfield bootstrap works (T004, T005, T006)
4. Complete Phase 4: US2 — Greenfield files handled correctly (T007)
5. **STOP and VALIDATE**: Test the full greenfield flow end-to-end
6. The primary README-documented workflow now works

### Incremental Delivery

1. Setup + Foundational → Helpers ready
2. US1 + US2 → Greenfield flow works → **MVP!** (SC-001, SC-002, SC-003)
3. US3 → Pipeline reporting is honest → (SC-004)
4. US4 → Dry-run works on initialized repos → (SC-008)
5. US5 → CLI version and help complete → (SC-006)
6. US6 → Security stage evaluates findings → (SC-007)
7. US7 → README commands are correct → (SC-005)
8. US8 → Rollback tags in greenfield → Safety net

### Parallel Strategy (Multiple Developers)

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (stages.py) → US6 (stages.py + init_cmd.py)
   - Developer B: US3 (runner.py + pipeline_cmd.py) → US4 (init_cmd.py)
   - Developer C: US5 (main.py + update_cmd.py) → US7 (README.md) → US8 (init_cmd.py)
3. US2 integrates after US1 completes (init_cmd.py coordination)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- No test tasks included — tests not explicitly requested in the specification
- All changes are modifications to existing files — no new packages or modules
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
