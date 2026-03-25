# Tasks: Remove SpecKit Module — Consolidate Under APM

**Input**: Design documents from `/specs/014-apm-module-swap/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/migration-contract.md, quickstart.md

**Tests**: Not explicitly requested in the feature specification. Test tasks are included only where existing tests must be updated or deleted to maintain a passing suite.

**Organization**: Tasks are grouped by user story. Foundational deletions and registry cleanup (US3) must complete before other stories can proceed.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Confirm branch and scope before destructive operations

- [X] T001 Verify working branch is `014-apm-module-swap` and working tree is clean

---

## Phase 2: Foundational — Delete SpecKit Files & Clean References

**Purpose**: Remove all speckit-owned code, templates, and tests from the codebase. Clean all cross-references in other modules. This MUST complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### File Deletions

- [X] T002 [P] Delete speckit module source at `src/dev_stack/modules/speckit.py`
- [X] T003 [P] Delete vendored speckit templates directory at `src/dev_stack/templates/speckit/` (12 files, ~2,117 lines)
- [X] T004 [P] Delete vendored LazySpecKit templates directory at `src/dev_stack/templates/lazyspeckit/` (3 files, ~946 lines)
- [X] T005 [P] Delete speckit unit tests at `tests/unit/test_speckit_lazyspeckit.py`
- [X] T006 [P] Delete speckit integration tests at `tests/integration/test_speckit.py`

### Cross-Reference Cleanup

- [X] T007 Remove `speckit` from the auto-import line in `src/dev_stack/modules/__init__.py` (line ~98: `from . import ... speckit ...`)
- [X] T008 Remove `"speckit"` from `DEFAULT_GREENFIELD_MODULES` tuple in `src/dev_stack/modules/__init__.py` (line ~15)
- [X] T009 Remove `"speckit"` from `DEFAULT_MODULES` tuple in `src/dev_stack/manifest.py` (line ~17: change `("hooks", "speckit")` to `("hooks",)`)
- [X] T010 Remove `\.lazyspeckit/` from detect-secrets exclude pattern in `src/dev_stack/pipeline/stages.py` (line ~341)
- [X] T011 Rename misleading `speckit_templates_dir` variable to `specify_templates_dir` in `src/dev_stack/modules/vcs_hooks.py` (lines ~384 and ~566). Do NOT remove the constitution injection logic — these references target `.specify/templates/` (created by `specify init`), not the vendored `templates/speckit/` directory being deleted

### Test Updates

- [X] T012 Update `DEFAULT_GREENFIELD_MODULES` assertion in `tests/unit/test_modules_registry.py` (line ~88: remove `"speckit"` from expected tuple, ensure `"apm"` is present)
- [X] T013 Update resolved defaults assertion in `tests/unit/test_modules_registry.py` (line ~93: remove `"speckit"` from resolved default modules check)

**Checkpoint**: All speckit references removed. `pytest tests/ -x` should pass with no import errors for speckit.

---

## Phase 3: User Story 3 — Module Registry Reflects Removal (Priority: P2)

**Goal**: The `DEPRECATED_MODULES` mapping is added so the codebase has a formal mechanism for handling removed modules. This is prerequisite infrastructure for US2's migration handler.

**Independent Test**: Import `DEPRECATED_MODULES` from `dev_stack.modules` and verify `"speckit"` is mapped to a deprecation message.

### Implementation for User Story 3

- [X] T014 [US3] Add `DEPRECATED_MODULES` dict to `src/dev_stack/modules/__init__.py` with `"speckit"` mapped to deprecation message per migration-contract.md
- [X] T015 [US3] Add unit test for `DEPRECATED_MODULES` in `tests/unit/test_modules_registry.py` — verify `"speckit"` key exists and value is a non-empty string

**Checkpoint**: Module registry is clean — `speckit` not in defaults, not importable, and formally listed as deprecated.

---

## Phase 4: User Story 4 — APM Manages All Agent Dependencies (Priority: P2)

**Goal**: Expand the `apm.yml` template to declare Agency reviewers and LazySpecKit packages alongside existing MCP servers, and update the merge logic to handle the new `dependencies.apm` section.

**Independent Test**: Render the default `apm.yml` template and verify it contains both `dependencies.mcp` (5 servers) and `dependencies.apm` (agency-agents + lazy-spec-kit pinned to git tags).

### Implementation for User Story 4

- [X] T016 [US4] Expand `src/dev_stack/templates/apm/default-apm.yml` with `dependencies.apm` section containing `msitarzewski/agency-agents#<tag>` and `Hacklone/lazy-spec-kit#<tag>` (verify latest stable tags at implementation time)
- [X] T017 [US4] Update `_merge_manifest()` in `src/dev_stack/modules/apm.py` to handle `dependencies.apm` list in addition to `dependencies.mcp` — deduplicate by package name
- [X] T018 [US4] Add unit test in `tests/unit/test_apm_module.py` verifying expanded template contains both `dependencies.mcp` and `dependencies.apm` sections with expected entries. **Must explicitly assert all 5 original MCP servers are preserved (FR-007 regression guard)**
- [X] T019 [US4] Add unit test in `tests/unit/test_apm_module.py` verifying `_merge_manifest()` merges `dependencies.apm` entries into existing manifests without duplicates

**Checkpoint**: `apm.yml` template contains all agent dependencies. `apm install` would resolve Agency reviewers, LazySpecKit, and MCP servers from a single manifest.

---

## Phase 5: User Story 1 — New Project Initialization (Priority: P1) 🎯 MVP

**Goal**: `dev-stack init` on a fresh directory produces a project with an expanded `apm.yml` containing all previously speckit-managed dependencies, and no speckit-related files are created.

**Independent Test**: Run `dev-stack init` on a clean directory and verify `apm.yml` has `dependencies.apm` section, no `[modules.speckit]` in `dev-stack.toml`, and no vendored speckit templates.

### Implementation for User Story 1

- [X] T020 [US1] Verify `dev-stack init` on a temp directory produces `apm.yml` with `dependencies.mcp` and `dependencies.apm` sections — no code changes expected (foundational + US4 enable this), add integration test if missing in `tests/integration/`. **Verify completes in under 60 seconds (SC-001)**
- [X] T021 [US1] Verify `dev-stack.toml` from fresh init does NOT contain `[modules.speckit]` — add assertion to existing init integration test

**Checkpoint**: Greenfield initialization works end-to-end without speckit. New projects get all agent dependencies from APM.

---

## Phase 6: User Story 2 — Existing Project Update with speckit Module (Priority: P1)

**Goal**: `dev-stack update` on existing projects with `[modules.speckit]` in `dev-stack.toml` completes gracefully, emits an informational message, and marks the section `deprecated = true`.

**Independent Test**: Create a `dev-stack.toml` with `[modules.speckit]` installed, run `dev-stack update`, verify exit code 0, deprecation message emitted, and `deprecated = true` added to TOML.

### Implementation for User Story 2

- [X] T022 [US2] Implement deprecated module detection in `src/dev_stack/cli/update_cmd.py` — when module name from manifest is not in `_MODULE_REGISTRY`, check `DEPRECATED_MODULES` mapping, emit info message per migration-contract.md, skip instantiation
- [X] T023 [US2] Implement `deprecated = true` TOML mutation in `src/dev_stack/cli/update_cmd.py` — add `deprecated = true` to the `[modules.speckit]` section in `dev-stack.toml` (idempotent: skip if already present)
- [X] T024 [US2] Add unit test in `tests/unit/test_update_cmd.py` (or appropriate test file) verifying deprecated module detection emits info message and does not raise error
- [X] T025 [US2] Add unit test verifying `deprecated = true` is written to `dev-stack.toml` for `[modules.speckit]` after update
- [X] T026 [US2] Add edge case test: project with `[modules.speckit]` and `installed = false` — update should still mark deprecated without error
- [X] T027 [US2] Add edge case test: project with NO `[modules.speckit]` entry — update should proceed normally with no deprecation message
- [X] T028 [US2] Add integration test verifying downstream project update with `[modules.speckit]` completes cleanly (FR-009)

**Checkpoint**: Existing downstream projects can run `dev-stack update` cleanly after the speckit module removal.

---

## Phase 7: User Story 5 — README Documents Post-Init Step (Priority: P3)

**Goal**: README includes clear post-init instructions for running `specify init --here --ai copilot` to scaffold the `.specify/` directory.

**Independent Test**: Read the README and verify the post-init step is documented in the setup/quickstart section.

### Implementation for User Story 5

- [X] T029 [US5] Update `README.md` quickstart/setup section to include post-init step: `specify init --here --ai copilot` with explanation of why this step is separate from `dev-stack init`
- [X] T030 [US5] Update `README.md` to mention `uv tool install specify-cli` as a prerequisite for the `specify` command

**Checkpoint**: A new developer can follow the README from zero to fully functional project with `.specify/` directory.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup across all stories

- [X] T031 [P] Run full test suite: `pytest tests/ -x -q` — verify all tests pass with no speckit-related failures
- [X] T032 [P] Run linter: `ruff check src/ tests/` — verify no lint errors from removed imports or stale references
- [X] T033 Run quickstart.md verification steps 1-8 against the implemented changes. **This covers SC-006 (apm install resolves all deps end-to-end)**
- [X] T034 Verify net line deletion is approximately 3,600+ lines (SC-003)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **US3 — Registry (Phase 3)**: Depends on Foundational — provides `DEPRECATED_MODULES` for US2
- **US4 — APM Template (Phase 4)**: Depends on Foundational — can run in parallel with Phase 3
- **US1 — Greenfield Init (Phase 5)**: Depends on Foundational + US4 (expanded template)
- **US2 — Update Migration (Phase 6)**: Depends on Foundational + US3 (`DEPRECATED_MODULES`)
- **US5 — README (Phase 7)**: Depends on Foundational — can run in parallel with Phase 3-6
- **Polish (Phase 8)**: Depends on ALL user stories being complete

### User Story Dependencies

- **US3 (P2 — Registry)**: No inter-story dependency. Foundational phase only.
- **US4 (P2 — APM Template)**: No inter-story dependency. Can run in parallel with US3.
- **US1 (P1 — Greenfield Init)**: Depends on US4 (expanded apm.yml needed for init).
- **US2 (P1 — Update Migration)**: Depends on US3 (`DEPRECATED_MODULES` mapping needed).
- **US5 (P3 — README)**: No inter-story dependency. Can run any time after Foundational.

### Within Each User Story

- Implementation before integration tests
- Core logic before edge case tests
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 2**: T002-T006 (file deletions) can ALL run in parallel
- **Phase 2**: T007-T011 (cross-reference cleanup) are sequential (same files)
- **Phase 3 + Phase 4**: Can run in parallel (different files, no dependencies between them)
- **Phase 5 + Phase 6 + Phase 7**: Can run in parallel once their dependencies are met
- **Phase 8**: T030 and T031 can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all file deletions in parallel (T002-T006):
Task: "Delete src/dev_stack/modules/speckit.py"
Task: "Delete src/dev_stack/templates/speckit/"
Task: "Delete src/dev_stack/templates/lazyspeckit/"
Task: "Delete tests/unit/test_speckit_lazyspeckit.py"
Task: "Delete tests/integration/test_speckit.py"

# Then sequential cross-reference cleanup (T007-T011):
Task: "Remove speckit from __init__.py imports"
Task: "Remove speckit from DEFAULT_GREENFIELD_MODULES"
Task: "Remove speckit from DEFAULT_MODULES"
Task: "Remove .lazyspeckit from stages.py"
Task: "Remove speckit refs from vcs_hooks.py"
```

## Parallel Example: US3 + US4 Together

```bash
# These two phases have no dependencies on each other:
# Developer A (US3):
Task: "Add DEPRECATED_MODULES to modules/__init__.py"
Task: "Add test for DEPRECATED_MODULES"

# Developer B (US4):
Task: "Expand default-apm.yml with dependencies.apm"
Task: "Update _merge_manifest() for apm deps"
Task: "Add template expansion test"
Task: "Add merge manifest test"
```

---

## Implementation Strategy

### MVP First (Foundational + US4 + US1)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational deletions + cleanup (T002-T013)
3. Complete Phase 4: Expand apm.yml template (T016-T019)
4. Complete Phase 5: Verify greenfield init works (T020-T021)
5. **STOP and VALIDATE**: `dev-stack init` on fresh directory produces complete `apm.yml`

### Incremental Delivery

1. Foundational → All speckit files deleted, references cleaned
2. Add US3 + US4 → Registry has `DEPRECATED_MODULES`, apm.yml expanded
3. Add US1 → Greenfield init verified end-to-end (MVP!)
4. Add US2 → Migration handler for existing projects
5. Add US5 → README documentation
6. Polish → Full test suite, lint, quickstart validation

### Single Developer Strategy

Execute phases sequentially in order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. This is a deletion-heavy feature where the foundational phase does most of the work, and subsequent phases are small targeted additions.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Total tasks: 34 (T001-T034)
- Estimated net deletion: ~3,639 lines across 18 files
- Reference edits: ~14 lines across 4 files + variable renames in vcs_hooks.py
- New code additions: ~50-80 lines (DEPRECATED_MODULES, migration handler, merge update, tests)
- The exact git tags for `agency-agents` and `lazy-spec-kit` must be verified against live repos at implementation time (T016)
