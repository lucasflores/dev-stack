# Tasks: Init & Pipeline Enhancements

**Input**: Design documents from `/specs/002-init-pipeline-enhancements/`
**Prerequisites**: plan.md (✅), spec.md (✅), research.md (✅), data-model.md (✅), contracts/ (✅), quickstart.md (✅)

**Tests**: Not explicitly requested as TDD. Test updates included in Phase 8 (Polish) per FR-030.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Exact file paths included in all descriptions

## Path Conventions

- **Source**: `src/dev_stack/` (existing `src/` layout)
- **Tests**: `tests/` (unit/, integration/, contract/)
- **Templates**: `src/dev_stack/templates/`
- **Specs**: `specs/002-init-pipeline-enhancements/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Helpers and utilities needed by multiple user stories

- [x] T001 Create `_normalize_name()` helper function in `src/dev_stack/modules/uv_project.py` that converts directory names to valid Python identifiers per PEP 503/625 (hyphens→underscores, strip invalid chars, handle leading digits)
- [x] T002 Create `_detect_src_package()` helper function in `src/dev_stack/pipeline/stages.py` that scans `src/` for the first subdirectory containing `__init__.py` (sorted alphabetically for determinism), returns `str | None`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Module registration and pipeline structure changes that MUST be complete before user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Update `DEFAULT_GREENFIELD_MODULES` in `src/dev_stack/modules/__init__.py` from `("hooks", "speckit")` to `("uv_project", "sphinx_docs", "hooks", "speckit")` per FR-028
- [x] T004 Add module imports `from . import uv_project, sphinx_docs` to the bottom of `src/dev_stack/modules/__init__.py` alongside existing imports per FR-028
- [x] T005 Update `build_pipeline_stages()` in `src/dev_stack/pipeline/stages.py` to return 8 stages in order: lint(1,HARD) → typecheck(2,HARD) → test(3,HARD) → security(4,HARD) → docs-api(5,HARD) → docs-narrative(6,SOFT) → infra-sync(7,SOFT) → commit-message(8,SOFT) per FR-027 — wire placeholder executors initially

**Checkpoint**: Module registry recognizes `uv_project` and `sphinx_docs`; pipeline defines 8 stages

---

## Phase 3: User Story 1 — Greenfield Init Produces a Complete Python Project (Priority: P1) 🎯 MVP

**Goal**: `dev-stack init` in an empty directory produces a fully functional Python project via `uv init --package`, augmented `pyproject.toml`, test scaffold, and lockfile.

**Independent Test**: Run `dev-stack init` in empty dir → verify `pyproject.toml` with tool sections, `src/<pkg>/__init__.py`, `.python-version`, `uv.lock`, `tests/test_placeholder.py` exist → `uv run pytest` passes.

### Implementation for User Story 1

- [x] T006 [US1] Implement `_run_uv_init()` helper in `src/dev_stack/modules/uv_project.py` — shells out to `uv init --package <name>` with `subprocess.run()`, checks `shutil.which("uv")`, returns `tuple[bool, str]` per FR-001, FR-013
- [x] T007 [US1] Implement `_augment_pyproject()` in `src/dev_stack/modules/uv_project.py` — reads TOML with `tomllib`, adds `[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.coverage.run]`, `[tool.mypy]` sections using skip-if-exists (existing `[tool.*]` sections MUST be left untouched when already present — brownfield safety per FR-003 clarification), adds `[project.optional-dependencies]` groups (`docs`, `dev`), writes with `tomli_w` per FR-003, FR-004, FR-005
- [x] T008 [US1] Implement `_scaffold_tests()` in `src/dev_stack/modules/uv_project.py` — creates `tests/__init__.py` and `tests/test_placeholder.py` (single passing test) per FR-006
- [x] T009 [US1] Implement `_run_uv_lock()` helper in `src/dev_stack/modules/uv_project.py` — runs `uv lock` via `subprocess.run()`, returns `tuple[bool, str]` per FR-007
- [x] T010 [US1] Implement `UvProjectModule` class in `src/dev_stack/modules/uv_project.py` with `@register_module` decorator — wire `NAME="uv_project"`, `VERSION="0.1.0"`, `DEPENDS_ON=()`, `MANAGED_FILES`, `install()` method orchestrating T006→T007→T008→T009 sequence, register files in `ModuleResult.files_created` per FR-001 through FR-013. **Failure handling**: If `_run_uv_init()` fails, clean up any partial artifacts and return `ModuleResult(success=False)` to trigger rollback (edge case 3). If `_run_uv_lock()` fails, omit `uv.lock` from `ModuleResult.files_created`, add a warning, and return `ModuleResult(success=True, warnings=[...])` for partial success per module-contract.md (edge case 7)
- [x] T011 [US1] Implement `verify()` method on `UvProjectModule` in `src/dev_stack/modules/uv_project.py` — checks `pyproject.toml`, `src/{pkg}/__init__.py`, `.python-version`, `uv.lock` exist per FR-011
- [x] T012 [US1] Implement `uninstall()` and `update()` methods on `UvProjectModule` in `src/dev_stack/modules/uv_project.py` — uninstall removes test scaffold + uv.lock; update re-augments pyproject.toml with skip-if-exists per module-contract.md

**Checkpoint**: `dev-stack init` in empty dir creates complete Python project; `uv run pytest` passes

---

## Phase 4: User Story 2 — Brownfield Init With Existing Python Project (Priority: P1)

**Goal**: `dev-stack init` in a repo with existing `pyproject.toml` detects conflicts, uses `preview_files()` for conflict detection, and never silently overwrites.

**Independent Test**: Create repo with existing `pyproject.toml` → run `dev-stack init` → verify conflict report surfaces → skip-if-exists preserves existing tool sections.

### Implementation for User Story 2

- [x] T013 [US2] Implement `preview_files()` method on `UvProjectModule` in `src/dev_stack/modules/uv_project.py` — returns `dict[Path, str]` of all files the module would create with their proposed content per FR-009
- [x] T014 [US2] Add brownfield detection to `UvProjectModule.install()` in `src/dev_stack/modules/uv_project.py` — check if `pyproject.toml` exists before calling `uv init`, skip `uv init` in brownfield mode, delegate to `preview_files()` → `ConflictReport` flow per FR-008
**Note**: Skip-if-exists semantics for `_augment_pyproject()` are enforced as a constraint in T007 and validated by unit tests in T034.

**Checkpoint**: Brownfield init with existing `pyproject.toml` never overwrites without consent; existing tool sections preserved

---

## Phase 5: User Story 3 — Pre-Commit Pipeline Includes Type Checking (Priority: P2)

**Goal**: Pipeline stage 2 runs mypy; type errors block the commit; graceful skip when mypy not installed.

**Independent Test**: Create file with type error → `git commit` → pipeline rejects at typecheck stage. Remove mypy → pipeline skips with warning.

### Implementation for User Story 3

- [x] T016 [US3] Implement `_execute_typecheck_stage()` executor in `src/dev_stack/pipeline/stages.py` — check `shutil.which("mypy")` for graceful skip, run `python3 -m mypy src/` via `_run_command()`, return PASS/FAIL/SKIP `StageResult` per FR-022 through FR-025
- [x] T017 [P] [US3] Add mypy hook entry to `src/dev_stack/templates/hooks/pre-commit-config.yaml` — `repo: local`, `entry: python3 -m mypy src/`, `pass_filenames: false`, `types: [python]` per FR-026
- [x] T018 [US3] Wire `_execute_typecheck_stage` into `build_pipeline_stages()` in `src/dev_stack/pipeline/stages.py` at order=2 (replacing placeholder from T005) per FR-024

**Checkpoint**: `git commit` with type error → rejected at stage 2; mypy not installed → skip with warning

---

## Phase 6: User Story 4 — Deterministic API Documentation From Source (Priority: P2)

**Goal**: Sphinx docs module scaffolds config files; docs-api pipeline stage runs Sphinx apidoc + build as a hard gate.

**Independent Test**: Add function with docstring → commit → docs-api stage builds docs in `docs/_build/`. Malformed RST → stage fails.

### Implementation for User Story 4

- [x] T019 [P] [US4] Implement `SphinxDocsModule` class in `src/dev_stack/modules/sphinx_docs.py` with `@register_module` decorator — `NAME="sphinx_docs"`, `VERSION="0.1.0"`, `DEPENDS_ON=("uv_project",)`, `MANAGED_FILES` per FR-017, FR-018, FR-019
- [x] T020 [US4] Implement `_render_conf_py()`, `_render_index_rst()`, `_render_makefile()` template renderers in `src/dev_stack/modules/sphinx_docs.py` — `conf.py` with `sys.path.insert` for src/ layout, deterministic build config (`html_last_updated_fmt = None` to suppress timestamps, comment documenting `SOURCE_DATE_EPOCH=0` for CI reproducibility), `index.rst` with toctree, `Makefile` with `-W --keep-going` and `SPHINXOPTS += -D html_last_updated_fmt=` per module-contract.md templates and SC-006
- [x] T021 [US4] Implement `install()` on `SphinxDocsModule` in `src/dev_stack/modules/sphinx_docs.py` — create `docs/` dir, write conf.py/index.rst/Makefile, append `docs/_build/` to `.gitignore`, register in `ModuleResult.files_created` per FR-017, FR-019, FR-019a
- [x] T022 [US4] Implement `preview_files()`, `verify()`, `uninstall()`, `update()` on `SphinxDocsModule` in `src/dev_stack/modules/sphinx_docs.py` per module-contract.md
- [x] T023 [US4] Implement `_execute_docs_api_stage()` executor in `src/dev_stack/pipeline/stages.py` — check Sphinx availability via `shutil.which("sphinx-build")` or `importlib.util.find_spec("sphinx")`, use `_detect_src_package()` from T002 to locate `src/<pkg>` for apidoc, set `SOURCE_DATE_EPOCH=0` in subprocess env for deterministic output (SC-006), run `python3 -m sphinx.ext.apidoc` then `python3 -m sphinx` with `-W --keep-going`, return PASS/FAIL/SKIP per FR-015, FR-021. **Empty src**: If apidoc finds no modules, stage returns PASS (Sphinx exits 0) with output noting no modules documented (edge case 8)
- [x] T024 [US4] Wire `_execute_docs_api_stage` into `build_pipeline_stages()` in `src/dev_stack/pipeline/stages.py` at order=5 (replacing placeholder from T005) per FR-014

**Checkpoint**: `docs/conf.py` + `docs/index.rst` + `docs/Makefile` scaffolded; docs-api stage builds API docs deterministically

---

## Phase 7: User Story 5 & 6 — Agent Narrative Docs + Full 8-Stage Pipeline (Priority: P2/P3)

**Goal**: docs-narrative stage invokes agent for `docs/guides/` content; full 8-stage pipeline executes in correct order with consistent naming.

**Independent Test (US5)**: Commit with agent → docs-narrative produces `docs/guides/` content. No agent → skip with warning.
**Independent Test (US6)**: Trigger pipeline → exactly 8 stages in order with correct hard/soft assignments.

### Implementation for User Story 5

- [x] T025 [US5] Refactor `_execute_docs_stage()` into `_execute_docs_narrative_stage()` in `src/dev_stack/pipeline/stages.py` — changes: (1) rename function, (2) update stage_name to `"docs-narrative"`, (3) scope agent output exclusively to `docs/guides/` (not `docs/` root), (4) add directive to agent prompt excluding API reference generation, (5) set failure_mode to SOFT per FR-014, FR-016
- [x] T026 [US5] Update `src/dev_stack/templates/prompts/docs_update.txt` — revise prompt to narrative-only: tutorials, quickstarts, architecture walkthroughs in `docs/guides/`; add explicit directive "Do NOT generate API reference documentation" per FR-020

### Implementation for User Story 6

- [x] T027 [US6] Wire `_execute_docs_narrative_stage` into `build_pipeline_stages()` in `src/dev_stack/pipeline/stages.py` at order=6 SOFT (replacing placeholder from T005) per FR-027
- [x] T028 [US6] Verify all 8 stages in `build_pipeline_stages()` in `src/dev_stack/pipeline/stages.py` have correct order numbers (1-8), names, failure modes, and requires_agent flags per FR-027 — remove any remaining placeholders from T005
- [x] T029 [US6] Update `src/dev_stack/modules/hooks.py` to reference the 8-stage pipeline in any hardcoded stage counts or names, if any per FR-030

**Checkpoint**: Full 8-stage pipeline executes in order; docs-narrative is agent-driven soft gate for `docs/guides/`

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Test updates (FR-030), managed artifact registration (US7/FR-031), interactive update flow (FR-032), and validation

### User Story 7 — Managed Artifacts & Drift Detection (Priority: P3)

- [x] T030 [US7] Verify `UvProjectModule.install()` in `src/dev_stack/modules/uv_project.py` registers all created files in `ModuleResult.files_created` so manifest records content hashes per FR-002, FR-031. *(Verification checkpoint — implementation is in T010; test assertions in T034)*
- [x] T031 [US7] Verify `SphinxDocsModule.install()` in `src/dev_stack/modules/sphinx_docs.py` registers all created files in `ModuleResult.files_created` so manifest records content hashes per FR-019, FR-031. *(Verification checkpoint — implementation is in T021; test assertions in T035)*

### Test Updates (FR-030)

- [x] T032 [P] Update `tests/unit/test_pipeline_stages.py` — assert 8 stages (was 6), verify names, order, failure modes match FR-027 per FR-030
- [x] T033 [P] Update `tests/unit/test_modules_registry.py` — assert `DEFAULT_GREENFIELD_MODULES == ("uv_project", "sphinx_docs", "hooks", "speckit")`, verify dependency resolution order per FR-030
- [x] T034 [P] Create `tests/unit/test_uv_project.py` — unit tests for `UvProjectModule`: `_normalize_name()`, `_augment_pyproject()` skip-if-exists, `preview_files()`, `verify()`, `install()` with mocked subprocess
- [x] T035 [P] Create `tests/unit/test_sphinx_docs.py` — unit tests for `SphinxDocsModule`: template rendering, `preview_files()`, `verify()`, `install()` with mocked filesystem
- [x] T036 [P] Update `tests/contract/test_module_interface.py` — verify `uv_project` and `sphinx_docs` satisfy `ModuleBase` contract (all abstract methods implemented) per FR-030
- [x] T037 [P] Update `tests/contract/test_cli_json_output.py` — assert `total_stages: 8` in pipeline JSON output per FR-030
- [x] T038 [P] Update `tests/integration/test_init_greenfield.py` — verify UV + Sphinx artifacts present in greenfield output per FR-030
- [x] T039 [P] Update `tests/integration/test_init_brownfield.py` — verify conflict flow for new `uv_project` and `sphinx_docs` files per FR-030

### Interactive Update Flow (FR-032)

- [x] T040 Implement interactive module opt-in in `src/dev_stack/cli/update_cmd.py` — detect new available modules (`uv_project`, `sphinx_docs`) not installed in target repo, prompt user to opt in or skip each, never auto-install per FR-032

### Validation

- [x] T041 Run full test suite (`pytest tests/ -v`) and verify all existing + new tests pass with zero regressions per SC-007
- [x] T042 Run quickstart.md validation — execute greenfield scenario end-to-end per SC-001

### Constitution Amendment

- [x] T043 Draft constitution amendment (v1.1.0 MINOR) updating `.specify/memory/constitution.md` §Development Workflow pipeline definition from 6→8 stages: lint(1,HARD) → typecheck(2,HARD) → test(3,HARD) → security(4,HARD) → docs-api(5,HARD) → docs-narrative(6,SOFT) → infra-sync(7,SOFT) → commit-message(8,SOFT). Update hard-gate description from "stages 1-3" to "stages 1-5". Include rationale: typecheck and docs-api are deterministic, reproducible quality gates

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP foundation
- **User Story 2 (Phase 4)**: Depends on US1 completion (needs `UvProjectModule` to exist)
- **User Story 3 (Phase 5)**: Depends on Foundational only — can run in parallel with US1
- **User Story 4 (Phase 6)**: Depends on Foundational only — can run in parallel with US1
- **User Story 5+6 (Phase 7)**: Depends on US4 (docs-api must exist for docs-narrative split)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1, Greenfield)**: Foundation module — no story dependencies
- **US2 (P1, Brownfield)**: Depends on US1 (`UvProjectModule` must exist to add `preview_files()`)
- **US3 (P2, Typecheck)**: Independent — only needs `build_pipeline_stages()` from Foundational
- **US4 (P2, Docs-API)**: Independent — only needs `build_pipeline_stages()` from Foundational
- **US5 (P3, Docs-Narrative)**: Depends on US4 (docs split requires docs-api to exist)
- **US6 (P2, 8-Stage Pipeline)**: Depends on US3 + US4 + US5 (all stages must be wired)
- **US7 (P3, Drift Detection)**: Depends on US1 + US4 (modules must register artifacts)

### Parallel Opportunities

**After Foundational completes:**
- US1 and US3 can run in parallel (different files: `uv_project.py` vs `stages.py`)
- US1 and US4 can run in parallel (different files: `uv_project.py` vs `sphinx_docs.py` + `stages.py`)
- US3 and US4 can run in parallel (both touch `stages.py` but different executor functions)

**Within Phase 8:**
- All test tasks T032–T037 can run in parallel (different test files)

---

## Parallel Example: After Foundational

```bash
# These can execute simultaneously after Phase 2:

# Developer A: User Story 1 (UV Project Module)
Task T006: Implement _run_uv_init() in src/dev_stack/modules/uv_project.py
Task T007: Implement _augment_pyproject() in src/dev_stack/modules/uv_project.py
Task T008: Implement _scaffold_tests() in src/dev_stack/modules/uv_project.py
Task T009: Implement _run_uv_lock() in src/dev_stack/modules/uv_project.py
Task T010: Wire UvProjectModule class in src/dev_stack/modules/uv_project.py

# Developer B: User Story 3 (Typecheck Stage) — in parallel
Task T016: Implement _execute_typecheck_stage() in src/dev_stack/pipeline/stages.py
Task T017: Add mypy hook to pre-commit-config.yaml template
Task T018: Wire typecheck into build_pipeline_stages()

# Developer C: User Story 4 (Sphinx Docs) — in parallel
Task T019: Implement SphinxDocsModule in src/dev_stack/modules/sphinx_docs.py
Task T020: Implement template renderers in src/dev_stack/modules/sphinx_docs.py
Task T021: Implement install() on SphinxDocsModule
Task T023: Implement _execute_docs_api_stage() in src/dev_stack/pipeline/stages.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T005)
3. Complete Phase 3: User Story 1 (T006–T012)
4. **STOP and VALIDATE**: `dev-stack init` in empty dir → `uv run pytest` passes
5. This alone delivers the highest-value feature (greenfield scaffolding)

### Incremental Delivery

1. Setup + Foundational → Framework ready
2. Add US1 → `dev-stack init` creates complete Python project (MVP!)
3. Add US2 → Brownfield safety verified
4. Add US3 → Type checking in pipeline
5. Add US4 → Deterministic API docs
6. Add US5+US6 → Full 8-stage pipeline
7. Add US7 + Polish → Drift detection, test updates, validation

### Suggested MVP Scope

**US1 alone** is the MVP — it delivers the single most impactful feature (eliminates manual Python project bootstrapping). All other stories build on top incrementally.
