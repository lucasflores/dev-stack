# Tasks: Universal Init Pipeline

**Input**: Design documents from `/specs/012-universal-init-pipeline/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅  
**Tests**: Included (TDD — Red-Green-Refactor per `.github/copilot-instructions.md`)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/dev_stack/` source, `tests/unit/` tests (existing structure per plan.md)

---

## Phase 1: Setup

**Purpose**: Verify branch and project readiness for implementation

- [X] T001 Verify checkout on `012-universal-init-pipeline` branch and `uv sync --all-extras` succeeds
- [X] T002 Verify existing test suite passes with `pytest tests/ -v` before any changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure that multiple user stories depend on — StackProfile entity and detection function

**⚠️ CRITICAL**: US1 and US2 both depend on StackProfile. Must complete before those stories.

### Tests for Foundation ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Red phase)**

- [X] T003 [P] Write failing tests for `StackProfile` dataclass and `detect_stack_profile()` in `tests/unit/test_stack_profile.py` — cover: pure markdown repo → `has_python=False`; repo with `.py` file → `has_python=True`; `.py` only in `.venv/` → `has_python=False`; `.py` only in `__pycache__/` → `has_python=False`; mixed repo → `has_python=True`; empty repo → `has_python=False` (per contract `contracts/stack-profile.md`)

### Implementation for Foundation

- [X] T004 Implement `StackProfile` frozen dataclass in `src/dev_stack/config.py` with `has_python: bool` field
- [X] T005 Implement `detect_stack_profile(repo_root: Path) -> StackProfile` in `src/dev_stack/config.py` — rglob `*.py` with exclusions for `.git/`, `.venv/`, `venv/`, `node_modules/`, `.dev-stack/`, `__pycache__/` using short-circuit `next()` evaluation (per research R1)
- [X] T006 Verify all `test_stack_profile.py` tests pass (Green phase), then refactor if needed

**Checkpoint**: StackProfile detection is working and tested. User story implementation can begin.

---

## Phase 3: User Story 1 — Non-Python Repo Init Produces a Clean Working Tree (Priority: P1) 🎯 MVP

**Goal**: `dev-stack init` on a non-Python repo completes with zero errors, no `uv sync` failures, and a clean `git status`.

**Independent Test**: Run `dev-stack init --modules hooks,speckit,vcs_hooks` in a repo with no Python files. Verify `git status` shows a clean tree, no error output, and exit code 0.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Red phase)**

- [X] T007 [P] [US1] Write failing test in `tests/unit/test_init_nonpython.py` for uv sync gating: init with `uv_project` NOT in module list → assert `subprocess.run` for `uv sync` is never called
- [X] T008 [P] [US1] Write failing test in `tests/unit/test_init_nonpython.py` for uv sync inclusion: init WITH `uv_project` in module list → assert `uv sync` IS called (regression guard)

### Implementation for User Story 1

- [X] T009 [US1] Gate `uv sync` call in `src/dev_stack/cli/init_cmd.py` — wrap existing `subprocess.run(["uv", "sync", ...])` with `if "uv_project" in module_names:` guard (per contract `contracts/init-pipeline.md` Change 1)
- [X] T010 [US1] Verify all `test_init_nonpython.py` US1 tests pass (Green phase), then refactor if needed

**Checkpoint**: User Story 1 core behavior (uv sync gating) is functional. Full clean-tree validation requires US4, US5, US6 also complete.

---

## Phase 4: User Story 2 — Pre-Commit Hooks Adapt to Project Stack (Priority: P2)

**Goal**: Generated `.pre-commit-config.yaml` includes Python hooks only when Python source files exist in the repo.

**Independent Test**: Initialize a non-Python repo with the hooks module. Confirm `.pre-commit-config.yaml` has no Python-specific hook entries (ruff, pytest, mypy). Then init a Python repo and confirm Python hooks are present.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Red phase)**

- [X] T011 [P] [US2] Write failing test in `tests/unit/test_hooks_stack_aware.py` for `_build_hook_list()`: given `StackProfile(has_python=False)` → returns only `dev-stack-pipeline` hook
- [X] T012 [P] [US2] Write failing test in `tests/unit/test_hooks_stack_aware.py` for `_build_hook_list()`: given `StackProfile(has_python=True)` → returns `dev-stack-pipeline` + ruff + pytest + mypy hooks
- [X] T013 [P] [US2] Write failing test in `tests/unit/test_hooks_stack_aware.py` for `_render_pre_commit_config()`: output YAML string contains managed section markers `DEV-STACK:BEGIN:HOOKS` / `DEV-STACK:END:HOOKS`
- [X] T014 [P] [US2] Write failing test in `tests/unit/test_hooks_stack_aware.py` for user hook preservation: existing hooks outside managed section markers survive re-init (FR-012)

### Implementation for User Story 2

- [X] T015 [US2] Define `HookEntry` frozen dataclass in `src/dev_stack/modules/hooks.py` with fields: `id`, `name`, `entry`, `language`, `pass_filenames`, `types`, `stages` (per data-model.md)
- [X] T016 [US2] Implement `_build_hook_list(profile: StackProfile) -> list[HookEntry]` in `src/dev_stack/modules/hooks.py` — always include `dev-stack-pipeline`; conditionally include ruff, pytest, mypy when `profile.has_python` is True (per contract `contracts/hooks-generation.md`)
- [X] T017 [US2] Implement `_render_pre_commit_config(hooks: list[HookEntry]) -> str` in `src/dev_stack/modules/hooks.py` — render hooks as YAML string wrapped in managed section markers
- [X] T018 [US2] Modify `HooksModule.install()` in `src/dev_stack/modules/hooks.py` — replace the existing static template copy of `templates/hooks/pre-commit-config.yaml` with programmatic generation: call `detect_stack_profile()`, then `_build_hook_list()`, then `_render_pre_commit_config()`, then write output via managed section markers preserving user hooks (FR-012, per research R2 and R7)
- [X] T018a [US2] Remove or stub the static `src/dev_stack/templates/hooks/pre-commit-config.yaml` template with a comment indicating it is superseded by programmatic generation in `HooksModule.install()`. Verify no other code path references it
- [X] T019 [US2] Verify all `test_hooks_stack_aware.py` tests pass (Green phase), then refactor if needed

**Checkpoint**: Hook generation is stack-aware. Python hooks appear only for Python repos; non-Python repos get only the pipeline hook.

---

## Phase 5: User Story 3 — Commit-Msg Hook Validates Agent Commit Body Sections (Priority: P3)

**Goal**: Agent commits (with `Agent:` trailer) are rejected if they lack `## Intent`, `## Reasoning`, `## Scope`, `## Narrative` body sections. Human commits are unaffected.

**Independent Test**: Create a commit message with agent trailers but no body sections. Run the commit-msg hook. Verify rejection with clear error listing missing sections.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Red phase)**

- [X] T020 [P] [US3] Write failing test in `tests/unit/test_body_section_rule.py` for agent commit with all 4 sections → PASS (no violations)
- [X] T021 [P] [US3] Write failing test in `tests/unit/test_body_section_rule.py` for agent commit with no body sections → FAIL listing all 4 missing sections
- [X] T022 [P] [US3] Write failing test in `tests/unit/test_body_section_rule.py` for agent commit with partial sections (e.g., Intent + Scope only) → FAIL listing Reasoning, Narrative as missing
- [X] T023 [P] [US3] Write failing test in `tests/unit/test_body_section_rule.py` for human commit (no `Agent:` trailer) with no body sections → PASS (no enforcement per FR-004)
- [X] T024 [P] [US3] Write failing test in `tests/unit/test_body_section_rule.py` for agent commit with `### Intent` (h3 instead of h2) → FAIL (must be `##` not `###`)

### Implementation for User Story 3

- [X] T025 [US3] Create `src/dev_stack/rules/body_sections.py` with `BodySectionRule(CommitRule)` class — rule ID `UC5`, name `dev-stack-body-sections`, require `## Intent`, `## Reasoning`, `## Scope`, `## Narrative` headings for agent commits only (per contract `contracts/body-section-rule.md`)
- [X] T026 [US3] Implement agent detection in `BodySectionRule.validate()` — check for `Agent:` trailer presence; skip validation for human commits (FR-004)
- [X] T027 [US3] Implement section validation in `BodySectionRule.validate()` — scan body for required headings, return `RuleViolation` listing missing sections with clear error message (FR-011)
- [X] T028 [US3] Add `from dev_stack.rules.body_sections import BodySectionRule` to `src/dev_stack/rules/__init__.py` and append `"BodySectionRule"` to the `__all__` list, matching the existing UC1-UC4 explicit registration pattern
- [X] T029 [US3] Verify all `test_body_section_rule.py` tests pass (Green phase), then refactor if needed

**Checkpoint**: Agent commits with missing body sections are rejected. Human commits pass freely.

---

## Phase 6: User Story 4 — Pipeline Skip Marker Is Always Gitignored (Priority: P4)

**Goal**: `.dev-stack/` directory is always in `.gitignore` via managed section, regardless of module selection.

**Independent Test**: Initialize a repo without `uv_project`. Trigger pipeline skip marker. Verify `git status` does not show it as untracked.

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Red phase)**

- [X] T030 [P] [US4] Write failing test in `tests/unit/test_init_nonpython.py` for gitignore managed section: after init, `.gitignore` contains `DEV-STACK:BEGIN:GITIGNORE` marker and `.dev-stack/` entry
- [X] T031 [P] [US4] Write failing test in `tests/unit/test_init_nonpython.py` for gitignore creation: init on repo with no `.gitignore` → file is created with managed section
- [X] T032 [P] [US4] Write failing test in `tests/unit/test_init_nonpython.py` for gitignore preservation: init on repo with existing `.gitignore` content → user content preserved, managed section added

### Implementation for User Story 4

- [X] T033 [US4] Implement `_ensure_gitignore_managed_section(repo_root: Path)` in `src/dev_stack/cli/init_cmd.py` — use `brownfield.markers.write_managed_section()` with section ID `GITIGNORE` and content `.dev-stack/` (per research R4 and contract `contracts/init-pipeline.md` Change 4)
- [X] T034 [US4] Call `_ensure_gitignore_managed_section(repo_root)` in init command flow after module install, before manifest write — runs regardless of module selection (FR-009)
- [X] T035 [US4] Verify all US4 tests pass (Green phase), then refactor if needed

**Checkpoint**: `.dev-stack/` is always gitignored. Skip marker never pollutes `git status`.

---

## Phase 7: User Story 5 — Secrets Scanning Only Runs When Requested (Priority: P5)

**Goal**: `.secrets.baseline` is never created during init unless a secrets scanning module is explicitly selected.

**Independent Test**: Run init without any secrets-related module. Verify `.secrets.baseline` does not exist.

### Tests for User Story 5 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Red phase)**

- [X] T036 [P] [US5] Write failing test in `tests/unit/test_init_nonpython.py` for secrets gating: init without secrets module → `_generate_secrets_baseline()` is not called and `.secrets.baseline` does not exist
- [X] T037 [P] [US5] Write failing test in `tests/unit/test_init_nonpython.py` for secrets inclusion: init with secrets module explicitly selected → `_generate_secrets_baseline()` IS called (regression guard)

### Implementation for User Story 5

- [X] T038 [US5] Remove the unconditional `_generate_secrets_baseline(repo_root)` call from the init flow in `src/dev_stack/cli/init_cmd.py`. No secrets module currently exists in `_MODULE_REGISTRY`, so the call is unreachable dead code. Add a `# TODO(012): Re-enable when a dedicated secrets module is added to _MODULE_REGISTRY` comment at the deletion site (per research R6 alternative)
- [X] T039 [US5] Verify `_generate_secrets_baseline()` function definition is retained (not deleted) in `src/dev_stack/cli/init_cmd.py` for future use — only the *call* is removed
- [X] T040 [US5] Verify all US5 tests pass (Green phase), then refactor if needed

**Checkpoint**: No stray `.secrets.baseline` files from init unless explicitly requested.

---

## Phase 8: User Story 6 — No Machine-Specific Paths in Committed Config (Priority: P6)

**Goal**: `dev-stack.toml` does not contain absolute filesystem paths. Agent CLI path resolved at runtime.

**Independent Test**: Run init and inspect `dev-stack.toml`. Verify no absolute paths appear.

### Tests for User Story 6 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (Red phase)**

- [X] T041 [P] [US6] Write failing test in `tests/unit/test_manifest.py` for `AgentConfig.to_dict()`: serialized dict contains `cli` key but NOT `path` key
- [X] T042 [P] [US6] Write failing test in `tests/unit/test_manifest.py` for `AgentConfig.from_dict()` backward compat: dict with `path` key → `path` field is `None` (ignored)
- [X] T043 [P] [US6] Write failing test in `tests/unit/test_manifest.py` for full manifest round-trip: serialize → deserialize → no absolute paths in output

### Implementation for User Story 6

- [X] T044 [US6] Modify `AgentConfig.to_dict()` in `src/dev_stack/manifest.py` — remove `path` from serialized output; keep only `cli` and `detected_at` (per research R5)
- [X] T045 [US6] Modify `AgentConfig.from_dict()` in `src/dev_stack/manifest.py` — silently ignore `path` key if present in old manifests for backward compatibility; always set `path=None`
- [X] T046 [US6] Update init command in `src/dev_stack/cli/init_cmd.py` — change `AgentConfig(cli=agent_info.cli, path=agent_info.path)` to `AgentConfig(cli=agent_info.cli)` (per contract `contracts/init-pipeline.md` Change 3)
- [X] T046a [P] [US6] Write failing test in `tests/unit/test_manifest.py` for runtime agent resolution: given `AgentConfig(cli="claude", path=None)`, verify that `detect_agent()` or equivalent resolves the path via `shutil.which("claude")` at runtime rather than reading a stored path (FR-008)
- [X] T046b [US6] Remove `"path": agent.path` from the JSON payload in `_emit_init_result()` in `src/dev_stack/cli/init_cmd.py` — the init result JSON should not emit machine-specific absolute paths (consistent with FR-007 intent)
- [X] T047 [US6] Verify all US6 tests pass (Green phase), then refactor if needed

**Checkpoint**: `dev-stack.toml` is fully portable across machines. No absolute paths persisted.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Integration validation, edge cases, and cross-story verification

- [X] T048 [P] Write integration test in `tests/unit/test_init_nonpython.py` for full non-Python init flow: init with `--modules hooks,speckit,vcs_hooks` on a non-Python repo → verify clean `git status`, no `.secrets.baseline`, no Python hooks, `.dev-stack/` gitignored, no absolute paths in `dev-stack.toml`, and any pre-existing user-defined hooks in `.pre-commit-config.yaml` are preserved (SC-001 through SC-007, FR-012, edge case: pre-existing detect-secrets hook)
- [X] T049 [P] Write integration test in `tests/unit/test_init_nonpython.py` for Python repo init regression: init on a Python project → verify Python hooks present, `uv sync` called, all existing behavior preserved (SC-005)
- [X] T050 [P] Write edge case test for polyglot repo: repo with some `.py` files but `uv_project` not selected → hooks detect Python presence, but `uv sync` does not run
- [X] T051 Run full test suite `pytest tests/ -v` and verify all tests pass with no regressions
- [X] T052 Run quickstart.md validation scenarios manually per `specs/012-universal-init-pipeline/quickstart.md`
- [X] T053 Verify commit-msg hook end-to-end: create agent commit with all sections → accepted; create agent commit missing sections → rejected with clear error

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** US1 and US2
- **US1 (Phase 3)**: Depends on Foundational (uses StackProfile indirectly via init flow)
- **US2 (Phase 4)**: Depends on Foundational (directly uses StackProfile + detect_stack_profile)
- **US3 (Phase 5)**: Independent — can start after Setup (new file, no shared entities)
- **US4 (Phase 6)**: Independent — can start after Setup (uses existing brownfield.markers)
- **US5 (Phase 7)**: Independent — can start after Setup (simple guard clause)
- **US6 (Phase 8)**: Independent — can start after Setup (manifest change only)
- **Polish (Phase 9)**: Depends on ALL user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    │
    ▼
Phase 2: Foundational (StackProfile)
    │
    ├──────────────────────┐
    ▼                      ▼
Phase 3: US1 (P1)    Phase 4: US2 (P2)
    │                      │
    │   ┌──────────────────┤     (US3, US4, US5, US6 can
    │   │                  │      start in parallel after
    │   │                  │      Phase 1 — no dependency
    │   │                  │      on Phase 2)
    ▼   ▼                  ▼
Phase 9: Polish (after ALL stories complete)
```

**Independent stories** (can run in parallel with each other and with Phase 2):
- US3 (Body Section Rule) — completely new file, no shared code
- US4 (Gitignore) — uses existing markers module
- US5 (Secrets Gating) — simple guard clause in init_cmd.py
- US6 (Manifest Paths) — isolated manifest.py change

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (Red)
2. Implement minimal code to make tests pass (Green)
3. Refactor while keeping tests green (Refactor)
4. Commit test + implementation together (atomic)

### Parallel Opportunities

- **Phase 2**: T003 (tests) can be written in parallel with Phase 1 validation
- **After Phase 2**: US3, US4, US5, US6 can ALL start in parallel (different files, no deps)
- **Within each US**: All test tasks marked [P] within a story can be written in parallel
- **US1 + US2**: Can start once Phase 2 completes; can run in parallel with US3-US6

---

## Parallel Example: After Phase 2 Completes

```
# Stream A: US1 + US2 (depend on Phase 2)
T007, T008 → T009, T010                    # US1: gate uv sync
T011, T012, T013, T014 → T015-T019         # US2: stack-aware hooks

# Stream B: US3 (independent)
T020-T024 → T025-T029                      # US3: body section rule

# Stream C: US4 + US5 + US6 (independent, small)
T030-T032 → T033-T035                      # US4: gitignore
T036-T037 → T038-T040                      # US5: secrets gating
T041-T043 → T044-T047                      # US6: manifest paths
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (StackProfile)
3. Complete Phase 3: User Story 1 (gate uv sync)
4. **STOP and VALIDATE**: Test `dev-stack init` on non-Python repo — uv sync does not run
5. This alone unblocks the primary use case

### Incremental Delivery

1. Setup + Foundational → StackProfile ready
2. US1 (uv sync gating) → MVP: non-Python init doesn't fail ✅
3. US2 (stack-aware hooks) → Python hooks omitted on non-Python repos ✅
4. US3 (body section rule) → Agent commit hygiene enforced ✅
5. US4 (gitignore) → Clean working tree (no skip marker) ✅
6. US5 (secrets gating) → No stray .secrets.baseline ✅
7. US6 (manifest paths) → Portable config ✅
8. Polish → Full integration validation ✅

### Recommended Execution Order (Solo Developer)

1. Phase 1 → Phase 2 (setup + foundation)
2. US6 → US5 → US4 (quick wins, 1-2 tasks each, independent)
3. US1 (builds on foundation, small change)
4. US2 (largest story, depends on foundation)
5. US3 (independent, medium complexity)
6. Phase 9 (polish + integration)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- TDD enforced: write tests first → see them fail → implement → see them pass
- Commit test + implementation together per `.github/copilot-instructions.md`
- All new test files: `test_stack_profile.py`, `test_hooks_stack_aware.py`, `test_body_section_rule.py`, `test_init_nonpython.py`
- All modified files: `init_cmd.py`, `config.py`, `manifest.py`, `modules/hooks.py`
- One new source file: `rules/body_sections.py`
