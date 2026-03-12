# Tasks: Proactive Agent Instruction File Creation

**Input**: Design documents from `/specs/010-proactive-agent-instructions/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in the feature specification. Tests are included because the spec's SC-004 requires "all existing tests continue to pass" and the plan identifies specific test files to modify.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Add the agent-to-file mapping constant and helper method that all user stories depend on

- [X] T001 Add `AGENT_FILE_MAP` constant to `src/dev_stack/modules/vcs_hooks.py` mapping `"claude"` → `"CLAUDE.md"`, `"copilot"` → `".github/copilot-instructions.md"`, `"cursor"` → `".cursorrules"` (FR-002)
- [X] T002 Add `_get_agent_file_path(self) -> Path | None` helper method to `VcsHooksModule` in `src/dev_stack/modules/vcs_hooks.py` that reads `self.manifest.get("agent", {}).get("cli", "none")` and returns `self.repo_root / AGENT_FILE_MAP[cli]` or `None` if cli is `"none"` or not in the map

**Checkpoint**: Mapping constant and helper available for all subsequent tasks

---

## Phase 2: Foundational

**Purpose**: No foundational/blocking prerequisites beyond Phase 1 — the existing `markers.write_managed_section()`, `detect_agent()`, and `ModuleResult` infrastructure is already in place (read-only dependencies).

**⚠️ CRITICAL**: Phase 1 must be complete before any user story work begins.

---

## Phase 3: User Story 1 — Greenfield init creates the right agent file automatically (Priority: P1) 🎯 MVP

**Goal**: When `dev-stack init` detects an agent CLI, proactively create the agent's canonical instruction file with managed section markers containing the instructions template content.

**Independent Test**: Run `DEV_STACK_AGENT=claude dev-stack init` in a fresh repo → verify `CLAUDE.md` exists and contains managed section with instructions.

### Implementation for User Story 1

- [X] T003 [US1] Add `_create_agent_file()` method to `VcsHooksModule` in `src/dev_stack/modules/vcs_hooks.py` — reads instructions template, resolves agent file via `_get_agent_file_path()`, creates parent directories with `mkdir(parents=True, exist_ok=True)`, calls `markers.write_managed_section(target, "DEV-STACK:INSTRUCTIONS", content)`, appends to `created` list (greenfield only — existing-file detection deferred to T011), wraps in `try/except OSError` appending to `warnings` on failure (FR-001, FR-003, FR-008)
- [X] T004 [US1] Call `_create_agent_file(created, modified, warnings)` from `_generate_constitutional_files()` in `src/dev_stack/modules/vcs_hooks.py` — insert the call after the existing FR-019 injection block (after line ~541) so that proactive creation runs after brownfield injection (FR-001)
- [X] T005 [US1] Add no-agent guard in `_create_agent_file()` — if `_get_agent_file_path()` returns `None`, return immediately without creating any file (FR-005)
- [X] T006 [P] [US1] Add unit test `test_init_creates_agent_file_for_claude` in `tests/unit/test_vcs_hooks_module.py` — construct `VcsHooksModule(tmp_path, {"agent": {"cli": "claude"}})`, set up required git + template fixtures, call `install()`, assert `tmp_path / "CLAUDE.md"` exists and contains `DEV-STACK:BEGIN:DEV-STACK:INSTRUCTIONS` marker
- [X] T007 [P] [US1] Add unit test `test_init_creates_copilot_instructions_with_github_dir` in `tests/unit/test_vcs_hooks_module.py` — same pattern with `{"agent": {"cli": "copilot"}}`, assert `.github/copilot-instructions.md` exists and `.github/` directory was auto-created (FR-008)
- [X] T008 [P] [US1] Add unit test `test_init_creates_cursorrules_file` in `tests/unit/test_vcs_hooks_module.py` — same pattern with `{"agent": {"cli": "cursor"}}`, assert `.cursorrules` exists with managed section
- [X] T009 [P] [US1] Add unit test `test_init_no_agent_skips_agent_file` in `tests/unit/test_vcs_hooks_module.py` — construct with `{"agent": {"cli": "none"}}`, call `install()`, assert no `CLAUDE.md`, no `.github/copilot-instructions.md`, no `.cursorrules` exist (FR-005)
- [X] T010 [US1] Add unit test `test_init_agent_file_in_files_created` in `tests/unit/test_vcs_hooks_module.py` — call `install()` with claude agent, assert `ModuleResult.files_created` contains the `CLAUDE.md` path (FR-006, FR-012)

**Checkpoint**: Greenfield init with any detected agent creates the correct file. `DEV_STACK_AGENT=none` creates no agent file. All US1 acceptance scenarios verified.

---

## Phase 4: User Story 2 — Brownfield init injects into existing agent file (Priority: P2)

**Goal**: When an agent instruction file already exists (user-created), dev-stack injects its instructions as a managed section without overwriting existing content.

**Independent Test**: Create a repo with an existing `CLAUDE.md` containing custom content, run `dev-stack init` → verify original content preserved, managed section added.

### Implementation for User Story 2

- [X] T011 [US2] Update `_create_agent_file()` in `src/dev_stack/modules/vcs_hooks.py` to detect existing file — if the target file already exists, track whether `write_managed_section()` returns `True` (changed) and append to `modified` instead of `created` (FR-004)
- [X] T012 [P] [US2] Add unit test `test_init_preserves_existing_agent_file_content` in `tests/unit/test_vcs_hooks_module.py` — pre-create `CLAUDE.md` with custom user content, call `install()` with claude agent, assert user content is preserved AND managed section markers are present (FR-004)
- [X] T013 [P] [US2] Add unit test `test_reinit_updates_managed_section_idempotently` in `tests/unit/test_vcs_hooks_module.py` — call `install()` twice with claude agent, assert `CLAUDE.md` contains exactly one set of `DEV-STACK:BEGIN` / `DEV-STACK:END` markers (SC-002)

**Checkpoint**: Brownfield injection preserves user content and is idempotent. No regressions in existing FR-019 behavior.

---

## Phase 5: User Story 3 — Update and uninstall respect the created agent file (Priority: P3)

**Goal**: `update` refreshes the managed section; `uninstall` removes it and deletes the file if empty.

**Independent Test**: Run init → update → verify refresh. Run init → uninstall → verify cleanup.

### Implementation for User Story 3

- [X] T014 [US3] Wire `_create_agent_file()` call into `update()` method in `src/dev_stack/modules/vcs_hooks.py` — add call to `_generate_constitutional_files(created, modified, warnings)` if not already present in the update path, so managed section is refreshed on update (FR-009)
- [X] T015 [US3] Update `uninstall()` in `src/dev_stack/modules/vcs_hooks.py` — add agent file cleanup: resolve agent file via `_get_agent_file_path()`, if it exists clear managed section via `markers.write_managed_section(path, "DEV-STACK:INSTRUCTIONS", "")`, if file content is empty after clearing delete the file and add to `deleted` list, otherwise add to `modified` list (FR-010)
- [X] T016 [P] [US3] Add unit test `test_update_refreshes_agent_file_managed_section` in `tests/unit/test_vcs_hooks_module.py` — install with claude agent, modify the instructions template content, call `update()`, assert `CLAUDE.md` managed section contains new template content (FR-009)
- [X] T016b [P] [US3] Add unit test `test_update_after_agent_switch_creates_new_file` in `tests/unit/test_vcs_hooks_module.py` — install with `{"agent": {"cli": "claude"}}`, then call `update()` with manifest changed to `{"agent": {"cli": "copilot"}}`, assert `.github/copilot-instructions.md` exists with managed section AND `CLAUDE.md` still exists with its managed section intact (Edge Case 1)
- [X] T017 [P] [US3] Add unit test `test_uninstall_deletes_devstack_only_agent_file` in `tests/unit/test_vcs_hooks_module.py` — install with claude agent (creates `CLAUDE.md` with only managed section), call `uninstall()`, assert `CLAUDE.md` is deleted and appears in `files_deleted` (FR-010)
- [X] T018 [P] [US3] Add unit test `test_uninstall_preserves_user_content_in_agent_file` in `tests/unit/test_vcs_hooks_module.py` — install with claude agent, append user content to `CLAUDE.md` outside managed markers, call `uninstall()`, assert file still exists with user content but managed section removed (FR-010, SC-003)

**Checkpoint**: Full lifecycle (init → update → uninstall) works correctly for the agent file.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Dry-run support, existing test validation, contract test compatibility

- [X] T019 [P] Update `preview_files()` in `src/dev_stack/modules/vcs_hooks.py` to include the agent file in the proposed files dict so dry-run and conflict detection report it (FR-011)
- [X] T020 [P] Verify existing contract test `test_modules_expose_required_metadata` in `tests/contract/test_module_interface.py` still passes — `MANAGED_FILES` class attribute must remain a sequence (the static base tuple satisfies this; the dynamic agent file is handled separately by instance methods)
- [X] T021 Run full test suite `pytest tests/` to verify no regressions (SC-004)
- [X] T022 Run quickstart.md validation — execute the verification script from `specs/010-proactive-agent-instructions/quickstart.md` in a temp repo to confirm end-to-end behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **User Stories (Phase 3–5)**: All depend on Phase 1 completion
  - US1 (Phase 3) can start after Phase 1
  - US2 (Phase 4) depends on US1 implementation (T003–T005) being complete
  - US3 (Phase 5) depends on US1 implementation (T003–T005) being complete
- **Polish (Phase 6)**: Depends on all user stories being complete

### Within Each User Story

- Implementation tasks before test tasks (tests validate the implementation)
- T003 → T004 → T005 (sequential: method → call site → guard)
- T011 depends on T003–T005 (extends `_create_agent_file()`)
- T014, T015 depend on T003–T005 (use `_create_agent_file()` and `_get_agent_file_path()`)
- Test tasks marked [P] within a story can run in parallel

### Parallel Opportunities

- T006, T007, T008, T009 can all run in parallel (independent test functions in same file)
- T012, T013 can run in parallel
- T016, T017, T018 can run in parallel
- T019, T020 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Sequential implementation:
T003: Add _create_agent_file() method
T004: Wire into _generate_constitutional_files()
T005: Add no-agent guard

# Then parallel tests:
T006: test_init_creates_agent_file_for_claude
T007: test_init_creates_copilot_instructions_with_github_dir
T008: test_init_creates_cursorrules_file
T009: test_init_no_agent_skips_agent_file
T010: test_init_agent_file_in_files_created
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 3: User Story 1 (T003–T010)
3. **STOP and VALIDATE**: Test greenfield init with each agent type
4. This alone resolves the core bug — instructions are now discoverable

### Incremental Delivery

1. Phase 1 → T001–T002 (mapping + helper)
2. Phase 3 → T003–T010 (greenfield creation) → **MVP complete**
3. Phase 4 → T011–T013 (brownfield injection preserved)
4. Phase 5 → T014–T018 (update + uninstall lifecycle)
5. Phase 6 → T019–T022 (polish, dry-run, validation)

Each phase adds value without breaking previous phases.
