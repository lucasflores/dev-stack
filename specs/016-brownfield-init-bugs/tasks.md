# Tasks: Brownfield Init Bug Remediation

**Input**: Design documents from `/specs/016-brownfield-init-bugs/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Included — plan.md explicitly lists test files for each FR.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. User stories are ordered by priority (P1 → P2 → P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Verify working environment before making changes

- [X] T001 Verify branch `016-brownfield-init-bugs` is checked out and working tree is clean
- [X] T002 Run existing test suite (`pytest tests/`) to confirm baseline green before changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared utility that US2, US6, and US8 all depend on

**⚠️ CRITICAL**: US2, US6, and US8 require this shared scan helper

- [X] T003 Create `scan_root_python_sources(repo_root: Path)` helper in src/dev_stack/modules/uv_project.py that scans repo root at depth 1 for `.py` files and directories containing `__init__.py`, excluding `.git`, `__pycache__`, `.venv`, `node_modules`, `.tox`, and returns `tuple[bool, list[str]]` — `(has_python_sources, package_names)`

**Checkpoint**: Shared scan helper ready — user story implementation can begin

---

## Phase 3: User Story 1 — Commit-Message Hook Strips Markdown Headers (Priority: P1) 🎯 MVP

**Goal**: Fix comment stripping regex so `## Intent`, `## Reasoning`, `## Scope`, `## Narrative` markdown headers survive the commit-msg hook and UC5 validation passes on agent commits.

**Independent Test**: Create a commit message file containing `## Intent` headers and run the commit-msg hook; verify headers survive and UC5 passes.

### Implementation for User Story 1

- [X] T004 [P] [US1] Fix comment stripping regex in src/dev_stack/vcs/hooks_runner.py line 37 — replace `ln.startswith("#")` (or equivalent) with `re.match(r"^# |^#$", ln)` to strip only git comment lines, preserving `##`+ markdown headers
- [X] T005 [P] [US1] Add unit tests in tests/unit/test_hooks_runner.py — test that git comment lines (`# comment`, bare `#`) are stripped, markdown headers (`## Intent`, `### Sub`) are preserved, and mixed content is handled correctly

**Checkpoint**: Agent-generated commits with `## Intent/Reasoning/Scope/Narrative` headers pass the hook and UC5

---

## Phase 4: User Story 2 — False Greenfield Classification (Priority: P1)

**Goal**: Repos containing `.py` files or Python packages at the root are classified as brownfield, preventing incorrect greenfield scaffolding.

**Independent Test**: Run `dev-stack init` on a repo with root-level `.py` files (no `pyproject.toml` or with a `uv_build` `pyproject.toml`); verify brownfield classification.

### Implementation for User Story 2

- [X] T006 [US2] Add root-level scan to `is_greenfield_uv_package()` in src/dev_stack/brownfield/conflict.py — call `scan_root_python_sources()` from T003 before `return True`; if root Python sources are found, return `False` (brownfield)
- [X] T007 [P] [US2] Add unit tests in tests/unit/test_conflict.py — test greenfield with truly empty repo, brownfield with root `.py` files, brownfield with root `__init__.py` packages, exclusion of `.venv`/`__pycache__` directories

**Checkpoint**: Repos with root-level Python code are correctly classified as brownfield

---

## Phase 5: User Story 3 — APM Version Parse Crash (Priority: P1)

**Goal**: APM version check handles ANSI escape sequences and Rich box-drawing decoration without crashing.

**Independent Test**: Mock `apm --version` output with ANSI escapes and box-drawing characters; verify version is extracted and compared correctly.

### Implementation for User Story 3

- [X] T008 [P] [US3] Fix version parsing in src/dev_stack/modules/apm.py `_check_apm_cli()` (version parsing in try block, line ~192) — add ANSI strip via `re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)`, then extract semver via `re.search(r'\d+\.\d+\.\d+', stripped)` instead of `split()[-1]`
- [X] T009 [P] [US3] Add unit tests in tests/unit/test_apm.py — test clean version string (`apm 0.8.2`), ANSI-decorated (`\x1b[1m0.8.2\x1b[0m`), Rich box-drawing (`╭─ apm v0.8.2 ─╮`), and no-match edge case

**Checkpoint**: APM version check succeeds for all known output formats — zero parse crashes

---

## Phase 6: User Story 4 — First Commit Guarantee Broken for Brownfield (Priority: P2)

**Goal**: First commit after brownfield init auto-formats pre-existing code via `ruff format` so the lint hard-gate passes without manual intervention.

**Independent Test**: Initialize dev-stack on a repo with unformatted Python code, make first commit; verify auto-format runs and commit succeeds.

### Implementation for User Story 4

- [X] T010 [US4] Write `.dev-stack/brownfield-init` marker file at end of brownfield init path in src/dev_stack/cli/init_cmd.py — empty file, existence-only check, follows established `.dev-stack/` pattern
- [X] T011 [US4] Add auto-format logic in src/dev_stack/pipeline/stages.py `_execute_lint_stage()` — before `--check` invocations, check for `.dev-stack/brownfield-init` marker; if present, run `ruff format .` (auto-fix mode), delete marker, then proceed with normal lint checks
- [X] T012 [P] [US4] Update README.md to document that brownfield first-commits include an automatic `ruff format` pass and that subsequent commits are hard-gated normally
- [X] T013 [P] [US4] Add unit tests in tests/unit/test_stages.py — test auto-format runs when marker present, marker is deleted after formatting, no auto-format on subsequent commits (marker absent)

**Checkpoint**: First commit after brownfield init succeeds without manual reformatting; marker is consumed

---

## Phase 7: User Story 5 — requirements.txt Not Migrated (Priority: P2)

**Goal**: Brownfield init detects `requirements.txt`, previews dependencies, and merges into `pyproject.toml` with user confirmation (or warns in CI).

**Independent Test**: Place `requirements.txt` with dependencies in a repo, run `dev-stack init`, verify dependencies appear in `pyproject.toml` or a warning is displayed.

### Implementation for User Story 5

- [X] T014 [US5] Implement `_detect_and_migrate_requirements(repo_root: Path, interactive: bool)` in src/dev_stack/cli/init_cmd.py — parse `requirements.txt` line-by-line using `packaging.requirements.Requirement`, skip comments/blanks/`-e` editable installs/URL deps, display preview table via Rich, prompt for confirmation (interactive) or warn and skip (CI), merge confirmed deps into `[project.dependencies]` in pyproject.toml via `tomli_w`
- [X] T015 [US5] Wire `_detect_and_migrate_requirements()` into the brownfield init path in src/dev_stack/cli/init_cmd.py — call after greenfield/brownfield classification, before module installation
- [X] T016 [P] [US5] Add unit tests in tests/unit/test_init_cmd.py — test parsing valid requirements with pinned versions, skipping comments/blanks/editable installs, merge into pyproject.toml `[project.dependencies]`, CI warn-only mode

**Checkpoint**: requirements.txt dependencies are either merged with confirmation or warned about — no silent data loss

---

## Phase 8: User Story 6 — Existing Packages Invisible to uv_project (Priority: P2)

**Goal**: Brownfield init detects root-level Python packages and recommends `src/` layout migration.

**Independent Test**: Create a repo with top-level packages (dirs with `__init__.py`), run init, verify detection and guidance output.

### Implementation for User Story 6

- [X] T017 [US6] Implement `_detect_root_packages(repo_root: Path)` in src/dev_stack/cli/init_cmd.py — call `scan_root_python_sources()` from T003, display detected package names via Rich console, recommend `src/` layout migration (e.g., `mv eval/ src/eval/`)
- [X] T018 [US6] Wire `_detect_root_packages()` into the brownfield init path in src/dev_stack/cli/init_cmd.py — call after module installation, before final summary output
- [X] T019 [P] [US6] Add unit tests in tests/unit/test_init_cmd.py — test detection of root packages, migration guidance in output, no false positives when packages are only in `src/`

**Checkpoint**: All root-level Python packages are listed with migration guidance during brownfield init

---

## Phase 9: User Story 7 — --json Pipeline Run Broken (Priority: P3)

**Goal**: All commands that accept `--json` produce valid, parseable JSON output — no human-readable text leaks.

**Independent Test**: Run `dev-stack --json init` and `dev-stack --json pipeline run`; verify all output parses as valid JSON.

### Implementation for User Story 7

- [X] T020 [US7] Fix JSON output gaps in src/dev_stack/cli/visualize_cmd.py lines 60-92 — add JSON payloads to early-exit pre-flight validation paths that currently only emit human-readable text; ensure `CLIContext.json_output` flag is checked in all branches
- [X] T021 [US7] Spot-check all other CLI commands for missing JSON branches — audit src/dev_stack/cli/*.py for paths that emit text output without checking `json_output` flag; fix any gaps found
- [X] T022 [P] [US7] Add integration test in tests/integration/test_brownfield_init.py (or tests/integration/test_json_output.py) — run key commands with `--json`, validate output parses as JSON via `json.loads()`

**Checkpoint**: Every `--json` command produces valid JSON — CI can consume output reliably

---

## Phase 10: User Story 8 — Typecheck Blind to Existing Code (Priority: P3)

**Goal**: mypy pipeline stage warns about root-level Python packages outside `src/` that are not type-checked, with migration guidance.

**Independent Test**: Place typed Python code with errors outside `src/`, run typecheck stage, verify warning is emitted listing uncovered packages.

### Implementation for User Story 8

- [X] T023 [US8] Add root-package warning to `run_mypy_type_checking()` in src/dev_stack/pipeline/stages.py — call `scan_root_python_sources()` from T003, if non-src packages found emit warning listing uncovered package names with `src/` migration guidance; keep `mypy_path = "src"` unchanged
- [X] T024 [P] [US8] Add unit test in tests/unit/test_stages.py — test warning emitted when packages exist outside `src/`, test no warning when all packages are in `src/`

**Checkpoint**: Developers are informed about uncovered packages — no false sense of type safety

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all fixes

- [X] T025 Run full quickstart.md verification steps (all 8 scenarios) to validate end-to-end behavior
- [X] T026 Run complete test suite (`pytest tests/ -v`) to confirm all new and existing tests pass
- [X] T027 Code review pass for consistency — verify `import re` is added where needed, Rich console output matches project style, error messages are clear

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS US2, US6, US8
- **US1 (Phase 3)**: Depends on Setup only — can start in parallel with Phase 2
- **US2 (Phase 4)**: Depends on Phase 2 (shared scan helper)
- **US3 (Phase 5)**: Depends on Setup only — can start in parallel with Phase 2
- **US4 (Phase 6)**: Depends on Setup only — no shared dependencies
- **US5 (Phase 7)**: Depends on Setup only — no shared dependencies
- **US6 (Phase 8)**: Depends on Phase 2 (shared scan helper)
- **US7 (Phase 9)**: Depends on Setup only — no shared dependencies
- **US8 (Phase 10)**: Depends on Phase 2 (shared scan helper)
- **Polish (Phase 11)**: Depends on all user story phases being complete

### User Story Independence

| Story | Depends On | Independent? |
|-------|-----------|-------------|
| US1 (Hook fix) | Setup only | ✅ Fully independent |
| US2 (Greenfield) | Phase 2 (scan helper) | ✅ Independent of other stories |
| US3 (APM parse) | Setup only | ✅ Fully independent |
| US4 (Auto-format) | Setup only | ✅ Fully independent |
| US5 (requirements.txt) | Setup only | ✅ Fully independent |
| US6 (Package detection) | Phase 2 (scan helper) | ✅ Independent of other stories |
| US7 (--json) | Setup only | ✅ Fully independent |
| US8 (mypy warning) | Phase 2 (scan helper) | ✅ Independent of other stories |

### Parallel Opportunities

After Phase 2 completes, ALL 8 user stories can proceed in parallel since they modify different files:

```
Phase 2 (Foundational) ──┬──▶ US1: hooks_runner.py
                         ├──▶ US2: conflict.py
                         ├──▶ US3: apm.py
                         ├──▶ US4: init_cmd.py (marker) + stages.py (format)
                         ├──▶ US5: init_cmd.py (requirements)
                         ├──▶ US6: init_cmd.py (packages)
                         ├──▶ US7: visualize_cmd.py + cli/*.py
                         └──▶ US8: stages.py (mypy warning)
```

**Note**: US4, US5, US6 all modify `init_cmd.py` — they add separate functions but wire into the same brownfield init path. Execute sequentially or coordinate merge points.

**Note**: US4 and US8 both modify `stages.py` — US4 touches `_execute_lint_stage()` and US8 touches `run_mypy_type_checking()`. These are separate functions and can be parallelized.

**Note**: T016 (US5) and T019 (US6) both add unit tests to `tests/unit/test_init_cmd.py`. They test different functions but share the same file — execute sequentially to avoid merge conflicts.

### Within Each User Story

- Implementation before tests (tests validate the fix)
- Core fix before wiring into calling code
- Commit after each task or logical group

---

## Parallel Example: P1 Stories (US1 + US2 + US3)

```bash
# After Phase 2 completes, launch all P1 fixes in parallel:
Task: T004 — Fix hooks_runner.py regex (US1)
Task: T006 — Add root scan to conflict.py (US2)
Task: T008 — Fix apm.py version parse (US3)

# Then launch all P1 tests in parallel:
Task: T005 — tests/unit/test_hooks_runner.py
Task: T007 — tests/unit/test_conflict.py
Task: T009 — tests/unit/test_apm.py
```

---

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (shared scan helper)
3. Complete Phase 3: US1 — Hook fix
4. Complete Phase 4: US2 — Greenfield classification fix
5. Complete Phase 5: US3 — APM version parse fix
6. **STOP and VALIDATE**: All three P1 bugs are fixed — agent commits work, classification is correct, APM doesn't crash

### Incremental Delivery

1. Setup + Foundational → Shared infrastructure ready
2. US1 + US2 + US3 (P1) → Critical bugs fixed (MVP!)
3. US4 + US5 + US6 (P2) → Onboarding experience fixed
4. US7 + US8 (P3) → CI integration and observability improved
5. Polish → Full validation pass

---

## Notes

- All changes are surgical patches to existing modules — no new modules or architecture changes
- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable per its "Independent Test" criteria
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
