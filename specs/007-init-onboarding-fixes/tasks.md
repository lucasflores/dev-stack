# Tasks: Init Onboarding Fixes

**Input**: Design documents from `/specs/007-init-onboarding-fixes/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No test tasks generated — tests were not explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: No project initialization needed — all changes target existing files in an existing codebase. This phase handles the one structural prerequisite.

- [X] T001 Reorder `DEFAULT_GREENFIELD_MODULES` tuple to put `speckit` before `vcs_hooks` in `src/dev_stack/modules/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: There are no shared foundational tasks that block all user stories. Each user story's changes are independent and target different functions/files. User story implementation can begin immediately after Phase 1.

**Checkpoint**: Setup complete — user story implementation can now begin.

---

## Phase 3: User Story 1 — Security Stage Handles Dev-Stack Files Without Circular Detection (Priority: P1) 🎯 MVP

**Goal**: `detect-secrets scan` excludes `.dev-stack/` and `.secrets.baseline` so the security stage never reports false positives from dev-stack's own managed files. First commit succeeds without `--no-verify`.

**Independent Test**: Run `dev-stack init` in a fresh repo, then `dev-stack pipeline run`. Verify the security stage passes. Inspect `.secrets.baseline` and confirm no entries from `.dev-stack/` paths and no self-referential entries.

### Implementation for User Story 1

- [X] T002 [P] [US1] Add `--exclude-files '\.\.dev-stack/|\.secrets\.baseline'` to the `detect-secrets scan` command in `_generate_secrets_baseline()` in `src/dev_stack/cli/init_cmd.py`
- [X] T003 [P] [US1] Add `--exclude-files '\.dev-stack/|\.secrets\.baseline'` to the `detect-secrets scan --baseline` command in `_execute_security_stage()` in `src/dev_stack/pipeline/stages.py`

**Checkpoint**: Security stage passes on freshly initialized repos. `.secrets.baseline` contains zero `.dev-stack/` entries. Real secrets still detected.

---

## Phase 4: User Story 2 — Greenfield Init After uv init --package Succeeds Without --force (Priority: P1)

**Goal**: `has_existing_conflicts()` only counts `pending` conflicts, so `uv init --package` predecessor files don't block greenfield init.

**Independent Test**: `uv init --package myproject && dev-stack --json init` → exit code 0, no pending conflicts in JSON output.

### Implementation for User Story 2

- [X] T004 [US2] Add `if conflict.resolution == "pending"` filter to the `any()` generator in `has_existing_conflicts()` in `src/dev_stack/cli/_shared.py`

**Checkpoint**: `uv init --package` → `dev-stack init` completes without `--force`. `dev-stack.toml` records `mode = "greenfield"`.

---

## Phase 5: User Story 3 — DEV_STACK_AGENT=none Skips Agent Detection (Priority: P2)

**Goal**: `DEV_STACK_AGENT=none` immediately returns `AgentInfo(cli="none", path=None)` without attempting binary resolution.

**Independent Test**: `DEV_STACK_AGENT=none dev-stack --json init --force` → JSON shows `"cli": "none"`, `"path": null`.

### Implementation for User Story 3

- [X] T005 [US3] Add early return for `cli == "none"` before `_resolve_cli()` call in `detect_agent()` in `src/dev_stack/config.py`

**Checkpoint**: `DEV_STACK_AGENT=none` records `agent.cli = "none"` regardless of installed agents.

---

## Phase 6: User Story 4 — README Documents Initial Commit Workflow (Priority: P2)

**Goal**: README greenfield instructions show clean `git commit` flow (no `--no-verify`); troubleshooting section mentions `--no-verify` as fallback only.

**Independent Test**: Follow the README greenfield instructions verbatim in a fresh repo — every step succeeds.

### Implementation for User Story 4

- [X] T006 [US4] Update the greenfield quickstart section in `README.md` to document clean initial commit (no `--no-verify` required) and remove `--force` from the primary greenfield path
- [X] T007 [US4] Add a troubleshooting section in `README.md` explaining `--no-verify` as a fallback for edge cases only

**Checkpoint**: README instructions match actual behavior after US1/US2 fixes are applied.

---

## Phase 7: User Story 5 — Baseline Practices Merge Into SpecKit Constitution (Priority: P2)

**Goal**: `vcs_hooks` injects baseline practices into `.specify/templates/constitution-template.md` instead of creating a root-level file. Skips entirely if speckit is not installed.

**Independent Test**: `dev-stack init` → no `constitution-template.md` at repo root; content present in `.specify/templates/constitution-template.md`.

### Implementation for User Story 5

- [X] T008 [US5] Update `MANAGED_FILES` in `src/dev_stack/modules/vcs_hooks.py` to replace `"constitution-template.md"` with `".specify/templates/constitution-template.md"`
- [X] T009 [US5] Rewrite `_generate_constitutional_files()` in `src/dev_stack/modules/vcs_hooks.py` to check if `.specify/templates/` exists, inject into speckit template if yes, skip entirely if no
- [X] T010 [US5] Add reinit migration logic in `_generate_constitutional_files()` in `src/dev_stack/modules/vcs_hooks.py` to detect root `constitution-template.md` with `# Dev-Stack Baseline Practices` signature, extract user content below `## User-Defined Requirements`, append to speckit template, and delete root file
- [X] T011 [US5] Update `verify()` in `src/dev_stack/modules/vcs_hooks.py` to check the new `.specify/templates/constitution-template.md` path instead of repo root

**Checkpoint**: No `constitution-template.md` at repo root. Baseline practices in speckit template. Reinit migrates existing root files.

---

## Phase 8: User Story 6 — Greenfield Mode Correctly Labeled in Manifest (Priority: P3)

**Goal**: `dev-stack.toml` records `mode = "greenfield"` when all conflicts are resolved as `greenfield_predecessor`.

**Independent Test**: `uv init --package foo && dev-stack init` → `dev-stack.toml` shows `mode = "greenfield"`.

### Implementation for User Story 6

No dedicated tasks — this is automatically fixed by T004 (US2). When `has_existing_conflicts()` returns `False` for predecessor-only conflicts, `_determine_mode(False, False)` correctly returns `"greenfield"`.

**Checkpoint**: Verify `dev-stack.toml` records `mode = "greenfield"` after the US2 fix.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validation and cleanup across all user stories

- [X] T012 [P] Run quickstart.md validation — execute the full greenfield flow (`uv init --package` → `dev-stack init` → first commit) in a fresh temp directory
- [X] T013 [P] Run `DEV_STACK_AGENT=none dev-stack --json init --force` validation in the same temp directory
- [X] T014 Verify `.secrets.baseline` contains no `.dev-stack/` entries and no self-referential findings, AND verify a test secret planted in user code IS detected by the security stage (FR-003)
- [X] T015 Verify `dev-stack.toml` records `mode = "greenfield"` and `agent.cli = "none"`
- [X] T016 Verify no `constitution-template.md` at repo root; baseline practices present in `.specify/templates/constitution-template.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 can start immediately
- **User Stories (Phases 3–8)**: All can start after Phase 1 (module reorder)
  - US1 (Phase 3): Independent — targets init_cmd.py + stages.py
  - US2 (Phase 4): Independent — targets _shared.py
  - US3 (Phase 5): Independent — targets config.py
  - US4 (Phase 6): Depends on US1 + US2 being complete (README documents post-fix behavior)
  - US5 (Phase 7): Depends on Phase 1 (module reorder ensures speckit runs before vcs_hooks)
  - US6 (Phase 8): Automatically resolved by US2 (no dedicated tasks)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1 (Setup: T001)
├── US1 (T002, T003) — independent
├── US2 (T004) — independent
├── US3 (T005) — independent
├── US5 (T008–T011) — depends on Phase 1 reorder
│
├── US4 (T006, T007) — depends on US1 + US2
├── US6 — no tasks (fixed by T004)
│
└── Polish (T012–T016) — depends on all above
```

### Within Each User Story

- Core fix before verification
- Single-function changes within each story — no intra-story dependencies except US5 (MANAGED_FILES → rewrite → migration → verify)

### Parallel Opportunities

- **After Phase 1**: T002, T003, T004, T005 can all run in parallel (different files)
- **US5 internal**: T008 must precede T009–T011 (MANAGED_FILES update before function rewrite)
- **US4**: T006 and T007 target the same file (README.md) — sequential
- **Polish phase**: T012 and T013 can run in parallel; T014–T016 are sequential verification steps

---

## Parallel Example: After Phase 1

```
# All four can run simultaneously (different files, no dependencies):
T002: Add --exclude-files to _generate_secrets_baseline() in src/dev_stack/cli/init_cmd.py
T003: Add --exclude-files to _execute_security_stage() in src/dev_stack/pipeline/stages.py
T004: Filter has_existing_conflicts() to pending only in src/dev_stack/cli/_shared.py
T005: Add early return for "none" in detect_agent() in src/dev_stack/config.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001 — module reorder)
2. Complete Phase 3: User Story 1 (T002, T003 — detect-secrets exclusions)
3. **STOP and VALIDATE**: `dev-stack init` → `dev-stack pipeline run` passes; `.secrets.baseline` clean
4. This alone unblocks the BLOCKING issue — users can commit

### Incremental Delivery

1. T001 → Module reorder ready
2. T002 + T003 → Security stage fixed (MVP! Unblocks all users)
3. T004 → Greenfield flow works without `--force`; mode label fixed (US2 + US6)
4. T005 → `DEV_STACK_AGENT=none` honored (US3)
5. T008–T011 → Constitution template placement fixed (US5)
6. T006 + T007 → README updated to match new behavior (US4)
7. T012–T016 → Full validation pass (Polish)

### Notes

- Each story adds value without breaking previous stories
- US4 (README) should be done last since it documents the post-fix behavior
- US6 has no dedicated tasks — it's automatically resolved by the US2 fix (T004)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
