# Tasks: Dev-Stack Update Workflow Bug Fixes

**Input**: Design documents from `/specs/021-update-workflow-bugs/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/cli-contracts.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup

**Purpose**: No new project structure required. Single `src/` layout, pre-existing test directories.

- [X] T001 Confirm branch `021-update-workflow-bugs` is checked out and clean

---

## Phase 2: Foundational (Blocking Prerequisite for US2)

**Purpose**: Add `_package_version()` helper and `version` property on `ModuleBase` — all US2 module tasks depend on these.

**⚠️ CRITICAL**: US2 module tasks (T007–T014) cannot begin until T002–T003 are complete **and T005 (`ModuleBase.version` property, Phase 4) is merged**.

- [X] T002 Add `_package_version() -> str` helper to `src/dev_stack/modules/__init__.py` using `importlib.metadata.version("dev-stack")` with fallback to `DEFAULT_MODULE_VERSION`
- [X] T003 Update `latest_module_entries()` in `src/dev_stack/modules/__init__.py` to call `_package_version()` instead of `getattr(module_cls, "VERSION", DEFAULT_MODULE_VERSION)`

**Checkpoint**: `_package_version()` and updated `latest_module_entries()` ready — US2 module tasks can now proceed.

---

## Phase 3: User Story 1 — Fresh Install Runs Without Crashing (Priority: P1) 🎯 MVP

**Goal**: Add `packaging>=24.0` to declared runtime dependencies so a clean `pip install dev-stack` is fully functional.

**Independent Test**: Create a fresh venv, `pip install dist/<wheel>`, run `dev-stack --help` — must exit 0 with no `ModuleNotFoundError`.

- [X] T004 [US1] Add `"packaging>=24.0"` to `[project].dependencies` in `pyproject.toml`

**Checkpoint**: US1 complete. Install `dev-stack` in a clean venv and run any command — no import errors.

---

## Phase 4: User Story 2 — `dev-stack update` Accurately Reports Module Update Status (Priority: P2)

**Goal**: Replace all per-module `VERSION` constants with the `self.version` property (derived via `_package_version()`) so a package version bump always surfaces outdated modules.

**Independent Test**: Build wheel at version 1.0.0, install in a project with 0.1.x module files, run `dev-stack update` — must report ≥1 outdated module.

**Depends on**: T002, T003 (Phase 2)

### Implementation for User Story 2

- [X] T005 [US2] Add `version` property to `ModuleBase` in `src/dev_stack/modules/base.py` that returns `_package_version()` from `dev_stack.modules`
- [X] T006 [P] [US2] Update `src/dev_stack/cli/status_cmd.py` — replace `getattr(instance, "VERSION", "unknown")` (~line 100) with `instance.version`
- [X] T007 [P] [US2] Remove `VERSION = "0.1.0"` class constant from `src/dev_stack/modules/apm.py`; update `verify()` to use `self.version`
- [X] T008 [P] [US2] Remove `VERSION = "0.1.0"` class constant from `src/dev_stack/modules/ci_workflows.py`; update `verify()` to use `self.version`
- [X] T009 [P] [US2] Remove `VERSION = "0.1.2"` class constant from `src/dev_stack/modules/docker.py`; update `verify()` to use `self.version`
- [X] T010 [P] [US2] Remove `VERSION = "0.1.0"` class constant from `src/dev_stack/modules/hooks.py`; update `verify()` (line 232: `version=self.VERSION`) to use `self.version`
- [X] T011 [P] [US2] Remove `VERSION = "0.1.0"` class constant from `src/dev_stack/modules/sphinx_docs.py`; update `verify()` to use `self.version`
- [X] T012 [P] [US2] Remove `VERSION = "0.1.0"` class constant from `src/dev_stack/modules/uv_project.py`; update `verify()` to use `self.version`
- [X] T013 [P] [US2] Remove `VERSION = "1.0.0"` class constant from `src/dev_stack/modules/visualization.py`; update `verify()` to use `self.version`
- [X] T014 [US2] Add unit tests to `tests/unit/test_module_version.py` (new file): `_package_version()` returns a non-empty string; `latest_module_entries()` returns the package version for every module; `ModuleBase.version` property resolves without error. **Also add end-to-end acceptance check**: build/install the wheel at current version, run `dev-stack update` in a project with 0.1.x module files, assert at least one outdated module is reported (satisfies FR-003 / US2 AC1).

**Checkpoint**: US2 complete. All `VERSION` constants removed; `dev-stack update` derives versions from installed package metadata.

---

## Phase 5: User Story 3 — Pipeline Skip Warnings Accurately Reflect Skip Reason (Priority: P3)

**Goal**: Hollow-pipeline advisory fires only when at least one core stage was skipped because a tool is genuinely absent — not when all skips are due to `--stage` filtering.

**Independent Test**: Run `uv run dev-stack run --stage docs-api` in a project with all dev tools installed — zero "missing tools" or "uv sync" advisory in the pipeline summary.

### Implementation for User Story 3

- [X] T015 [US3] In `src/dev_stack/pipeline/runner.py` lines 219–226, add inner condition: only emit the "No substantive validation" advisory if `any(r.skipped_reason != "filtered via --stage" for r in core_results)`. **Note**: per-stage skip reason text is already rendered in terminal output by `pipeline_cmd.py` lines 105-106 (`line += f" (reason: {stage['skipped_reason']})"`); FR-004 / US3 AC1 per-stage label display is already satisfied — no additional change required.
- [X] T016 [US3] Create or extend `tests/unit/test_pipeline_runner.py`: add test — all core stages with `skipped_reason="filtered via --stage"` → no advisory emitted; add test — at least one core stage with tool-missing reason → advisory emitted

**Checkpoint**: US3 complete. `--stage` runs with all tools installed produce no false "missing tools" warning.

---

## Phase 6: User Story 4 — `dev-stack status` Output Reflects Current State, Not Stale History (Priority: P3)

**Goal**: Persist `as_of` (ISO timestamp) and `stale` (bool) in `last-run.json` so consumers can assess pipeline data freshness programmatically.

**Independent Test**: Run `uv run dev-stack run --stage infra-sync`, then `uv run dev-stack --json status` — output must contain `pipeline.stale: true` and a valid `pipeline.as_of` ISO timestamp.

### Implementation for User Story 4

- [X] T017 [US4] In `src/dev_stack/pipeline/runner.py` `_record_pipeline_run()`, compute `stale = (summary.aborted_stage is not None or any(r.skipped_reason == "filtered via --stage" for r in summary.results))` and add `"as_of": now_str` and `"stale": stale` to the JSON payload written to `.dev-stack/pipeline/last-run.json`
- [X] T018 [US4] Create or extend `tests/unit/test_pipeline_runner.py`: add test — `--stage` filtered run produces `stale=True` and `as_of` present; add test — full run produces `stale=False` and `as_of` present

**Checkpoint**: US4 complete. `dev-stack --json status` includes `pipeline.as_of` and `pipeline.stale` on every run.

---

## Phase 7: Polish & Validation

**Purpose**: Cross-cutting verification that all four fixes are coherent, tests pass, coverage holds.

- [X] T019 [P] Run full test suite via `uv run pytest` and confirm `--cov-fail-under=65` passes
- [X] T020 [P] Smoke-test all four bugs end-to-end per `specs/021-update-workflow-bugs/quickstart.md` verification steps

---

## Dependencies

```
T001 (branch check)
  └─ T002 → T003 (foundational: _package_version + latest_module_entries)
       └─ T005 (ModuleBase.version property)
            └─ T006, T007, T008, T009, T010, T011, T012, T013 [all parallel, depend on T005]
                 └─ T014 (unit tests for US2)

T004 (US1 — independent, no deps)

T015 (US3 — independent, no deps)
  └─ T016 (US3 tests)

T017 (US4 — independent, no deps)
  └─ T018 (US4 tests)

T019, T020 (final validation — depend on T004, T014, T016, T018)
```

### Parallel Execution Within US2 (after T005)

```
# Once T005 (ModuleBase.version) is done, launch all module constant-removal tasks together:
T006 — status_cmd.py VERSION reference
T007 — apm.py
T008 — ci_workflows.py
T009 — docker.py
T010 — hooks.py
T011 — sphinx_docs.py
T012 — uv_project.py
T013 — visualization.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 — confirm branch
2. T004 — add `packaging` dep to `pyproject.toml`
3. **STOP and VALIDATE**: rebuild wheel, install in clean venv, run `dev-stack --help`

### Incremental Delivery

1. T001 → T004 → validate US1 (MVP: crash on fresh install is fixed)
2. T002 → T003 → T005 → T006–T013 (parallel) → T014 → validate US2
3. T015 → T016 → validate US3
4. T017 → T018 → validate US4
5. T019 + T020 → final suite + smoke test

### Independent Stories

- **US1** (T004): Zero dependencies. Can be shipped alone as a patch.
- **US2** (T002, T003, T005–T014): Depends only on Phase 2 foundation. Independent of US3/US4.
- **US3** (T015–T016): Fully independent. Touches only `pipeline/runner.py` lines 219–226.
- **US4** (T017–T018): Fully independent. Touches only `_record_pipeline_run()`.

---

## Summary

| Phase | Tasks | Story | Parallel |
|---|---|---|---|
| 1: Setup | T001 | — | — |
| 2: Foundational | T002–T003 | — | — |
| 3: US1 | T004 | US1 (P1) | — |
| 4: US2 | T005–T014 | US2 (P2) | T006–T013 |
| 5: US3 | T015–T016 | US3 (P3) | — |
| 6: US4 | T017–T018 | US4 (P3) | — |
| 7: Polish | T019–T020 | — | T019, T020 |
| **Total** | **20 tasks** | | **8 parallel** |

**Suggested MVP scope**: T001 + T004 (2 tasks, US1 only — eliminates the hard blocker crash on fresh install)
