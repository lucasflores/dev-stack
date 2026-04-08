# Tasks: Universal Package Layout Detection

**Input**: Design documents from `/specs/017-package-layout-detection/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — plan.md explicitly specifies test files and success criteria require verified behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/dev_stack/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new layout module and establish imports

- [X] T001 Create src/dev_stack/layout.py with module docstring, `from __future__ import annotations`, and imports (`pathlib.Path`, `enum.Enum`, `dataclasses.dataclass`, `logging`, `tomllib`, `typing.Any`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types, detection function skeleton, and StageContext extension. MUST be complete before any user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Implement LayoutStyle enum with values SRC, FLAT, NAMESPACE in src/dev_stack/layout.py
- [X] T003 Implement PackageLayout frozen dataclass with fields layout_style (LayoutStyle), package_root (Path), and package_names (list[str]) — package_names always sorted, package_root always relative — in src/dev_stack/layout.py
- [X] T004 Move scan_root_python_sources() and _SCAN_EXCLUDE_DIRS from src/dev_stack/modules/uv_project.py to src/dev_stack/layout.py and re-export from uv_project.py to preserve backward compatibility
- [X] T005 Implement detect_package_layout(repo_root: Path, manifest: dict[str, Any] | None = None) -> PackageLayout with precedence levels 3–5: (3) src/ directory scan for subdirs with __init__.py, (4) repo root scan via scan_root_python_sources(), (5) default SRC layout with empty package_names. Include warning log when both src/ and flat packages are found (FR-014). In src/dev_stack/layout.py
- [X] T006 [P] Add `package_layout: PackageLayout | None = None` field to StageContext dataclass in src/dev_stack/pipeline/stages.py (must work with slots=True)
- [X] T007 Update StageContext.without_agent() to propagate package_layout in src/dev_stack/pipeline/stages.py
- [X] T008 Compute PackageLayout via detect_package_layout(repo_root, manifest) and assign to StageContext before stage execution begins in src/dev_stack/pipeline/runner.py

**Checkpoint**: Core detection infrastructure ready — all types defined, detection works for src/ and flat layouts, StageContext carries PackageLayout.

---

## Phase 3: User Story 1 — Brownfield Flat-Layout Project Runs Full Pipeline (Priority: P1) 🎯 MVP

**Goal**: A brownfield flat-layout project (`my_package/` at repo root, no `src/`) gets correct mypy, sphinx-apidoc, hooks, and conf.py behavior after running the dev-stack pipeline.

**Independent Test**: Create a temporary flat-layout Python project with `my_package/__init__.py` at repo root, run the dev-stack pipeline, and verify mypy scans `my_package/`, sphinx-apidoc documents `my_package/`, and hooks target `my_package/`.

### Implementation for User Story 1

- [X] T009 [P] [US1] Rewire _execute_typecheck_stage() to use context.package_layout (with fallback to detect_package_layout when None) — replace hardcoded `"src/"` mypy target with `layout.package_root / pkg` for each package_name in src/dev_stack/pipeline/stages.py
- [X] T010 [US1] Rewire _execute_docs_api_stage() to use context.package_layout — replace hardcoded `f"src/{pkg_name}"` sphinx-apidoc target with `layout.package_root / pkg` for each package_name in src/dev_stack/pipeline/stages.py
- [X] T011 [P] [US1] Rewire _build_hook_list() to accept PackageLayout parameter (or detect layout internally when not provided) — replace hardcoded `entry="python3 -m mypy src/"` with dynamic entry using layout.package_root and all package_names in src/dev_stack/modules/hooks.py
- [X] T012 [P] [US1] Rewire _render_conf_py() to accept PackageLayout — replace hardcoded `sys.path.insert(0, os.path.abspath("../src"))` with relative path computed from layout (e.g., `"../{layout.package_root}"` for SRC, `".."` for FLAT) in src/dev_stack/modules/sphinx_docs.py
- [X] T013 [US1] Rewire _render_makefile() to accept PackageLayout — replace hardcoded `../src/{pkg_name}` apidoc target with path derived from layout.package_root and package_names in src/dev_stack/modules/sphinx_docs.py
- [X] T014 [P] [US1] Rewire install() and verify() — replace hardcoded `self.repo_root / "src" / pkg_name` and `self.repo_root / "src" / pkg_name / "__init__.py"` with paths from detected layout in src/dev_stack/modules/uv_project.py
- [X] T015 [US1] Rewire _augment_pyproject() and _scaffold_pyproject_defaults() — replace hardcoded `"mypy_path": "src"` with `str(layout.package_root)` and replace `"source": [f"src/{pkg_name}"]` with layout-derived source path in src/dev_stack/modules/uv_project.py
- [X] T016 [P] [US1] Rewire greenfield detection — replace hardcoded `repo_root / "src"` reference with detect_package_layout() result in src/dev_stack/cli/init_cmd.py
- [X] T017 [US1] Add unit tests for flat-layout detection: verify detect_package_layout returns LayoutStyle.FLAT with package_root=Path(".") for a tmp_path with `my_package/__init__.py` at root (no src/) in tests/unit/test_layout.py

**Checkpoint**: Brownfield flat-layout projects run the full pipeline correctly. All consumer locations use PackageLayout instead of hardcoded `src/`.

---

## Phase 4: User Story 2 — Src-Layout Projects Continue Working Unchanged (Priority: P1)

**Goal**: Existing projects with `src/<pkg>/` layout experience zero behavioral change after the refactor — full regression safety.

**Independent Test**: Run the dev-stack pipeline on the dev-stack project itself (which uses src layout) and verify all stages produce identical results to before the refactor.

### Implementation for User Story 2

- [X] T018 [US2] Add unit tests verifying src-layout detection: detect_package_layout on a tmp_path with `src/my_pkg/__init__.py` returns LayoutStyle.SRC, package_root=Path("src"), package_names=["my_pkg"] in tests/unit/test_layout.py
- [X] T019 [US2] Run full existing test suite (`uv run pytest`) and verify all tests pass without modification — fix any regressions introduced by consumer rewiring

**Checkpoint**: All existing src-layout tests pass. Backward compatibility confirmed.

---

## Phase 5: User Story 3 — Explicit Config Override Takes Precedence (Priority: P2)

**Goal**: When `modules.uv_project.config.package_name` is set in the manifest, the detection utility uses it directly without filesystem scanning.

**Independent Test**: Create a manifest with explicit `package_name`, run detection, and verify the configured value is returned regardless of directory structure.

### Implementation for User Story 3

- [X] T020 [US3] Add manifest config precedence check (level 1) to detect_package_layout() — before any filesystem scan, check `manifest["modules"]["uv_project"]["config"]["package_name"]`. If present, resolve layout style by checking: (a) if `src/{name}/` exists → SRC with `package_root=Path("src")`, (b) elif `{name}/` exists at repo root → FLAT with `package_root=Path(".")`, (c) else → default SRC with `package_root=Path("src")`. Return early with the resolved PackageLayout. In src/dev_stack/layout.py
- [X] T021 [US3] Add unit tests for manifest config override: verify detect_package_layout returns the manifest-configured package name even when filesystem has a different layout in tests/unit/test_layout.py

**Checkpoint**: Manifest config override works correctly and takes highest precedence.

---

## Phase 6: User Story 4 — pyproject.toml Build-Backend Hints Are Used (Priority: P2)

**Goal**: Projects with `[tool.setuptools.packages.find.where]` or `[tool.hatch.build.targets.wheel.packages]` in pyproject.toml get accurate detection from build-backend hints before falling back to directory scanning.

**Independent Test**: Create projects with setuptools and hatch pyproject.toml configs pointing to non-standard locations and verify detection uses those hints.

### Implementation for User Story 4

- [X] T022 [P] [US4] Implement setuptools hint parsing (precedence level 2a) — parse `[tool.setuptools.packages.find]` for `where` key (list, use first entry as package root) and `namespaces` key (bool, set NAMESPACE style when true). Use tomllib to read pyproject.toml in src/dev_stack/layout.py
- [X] T023 [US4] Implement hatch hint parsing (precedence level 2b) — parse `[tool.hatch.build.targets.wheel]` for `packages` key (list of relative paths), derive package_root and package_names from path entries in src/dev_stack/layout.py
- [X] T024 [US4] Add unit tests for pyproject.toml hint detection: setuptools where=["lib"] returns package_root=Path("lib"); hatch packages=["src/my_pkg"] returns correct root and names; conflicting hints with filesystem log warning and fall through in tests/unit/test_layout.py

**Checkpoint**: pyproject.toml build-backend hints are correctly parsed for setuptools and hatch.

---

## Phase 7: User Story 5 — preview_files() Respects Detected Layout in Brownfield Mode (Priority: P2)

**Goal**: `preview_files()` proposes file paths consistent with the project's actual layout — flat-layout projects see `my_package/` paths, not `src/my_package/` paths.

**Independent Test**: Call `preview_files()` on a flat-layout brownfield project and verify no `src/` paths appear in the proposed file list.

### Implementation for User Story 5

- [X] T025 [US5] Adapt preview_files() to call detect_package_layout() and use the result to compute proposed file paths — for FLAT layout propose `{pkg}/__init__.py`, for SRC layout propose `src/{pkg}/__init__.py` — in src/dev_stack/modules/uv_project.py
- [X] T026 [US5] Add unit tests verifying preview_files() produces flat-layout paths for brownfield flat projects and src-layout paths for src-layout projects in tests/unit/test_uv_project.py

**Checkpoint**: preview_files() produces layout-consistent paths. Brownfield conflict detection works correctly for flat-layout projects.

---

## Phase 8: User Story 6 — Duplicate Detection Logic Is Eliminated (Priority: P3)

**Goal**: The three independent package-detection implementations are removed. Only `detect_package_layout()` in `layout.py` remains as the authoritative source.

**Independent Test**: Search the codebase for `_detect_package_name` and `_detect_src_package` — neither should exist as standalone implementations.

### Implementation for User Story 6

- [X] T027 [P] [US6] Remove _detect_src_package() function from src/dev_stack/pipeline/stages.py (dead code after T009/T010 rewiring)
- [X] T028 [P] [US6] Remove _detect_package_name() function from src/dev_stack/modules/sphinx_docs.py (dead code after T012/T013 rewiring)
- [X] T029 [P] [US6] Remove _detect_package_name() method from UvProjectModule in src/dev_stack/modules/uv_project.py (dead code after T014/T015/T025 rewiring)

**Checkpoint**: Exactly one package-detection implementation exists in the codebase. All consumers delegate to `detect_package_layout()`.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Edge-case coverage, integration tests, and final validation

- [X] T030 [P] Add edge-case unit tests: no packages found (greenfield default SRC), brownfield with no discoverable packages (create `.dev-stack/brownfield-init` marker but no Python packages — verify consumers skip the stage with a warning per FR-013), multiple flat packages discovered (all returned sorted), namespace layout via setuptools `namespaces=true`, ambiguous layout warning logged in tests/unit/test_layout.py
- [X] T031 Add integration test for end-to-end layout detection across src, flat, and namespace layouts using tmp_path fixtures in tests/integration/test_layout_detection.py
- [X] T032 Run quickstart.md validation — verify code examples in specs/017-package-layout-detection/quickstart.md match the final API

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — core consumer rewiring
- **US2 (Phase 4)**: Depends on US1 (Phase 3) — regression verification after rewiring
- **US3 (Phase 5)**: Depends on Foundational (Phase 2) — adds manifest precedence to detection
- **US4 (Phase 6)**: Depends on Foundational (Phase 2) — adds pyproject.toml parsing to detection
- **US5 (Phase 7)**: Depends on Foundational (Phase 2) — adapts preview_files()
- **US6 (Phase 8)**: Depends on US1 (Phase 3) + US5 (Phase 7) — removes dead code after all rewiring is complete
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — no dependencies on other stories
- **US2 (P1)**: Depends on US1 — runs regression tests after consumer rewiring
- **US3 (P2)**: Can start after Foundational (Phase 2) — independent of US1 (adds to layout.py only)
- **US4 (P2)**: Can start after Foundational (Phase 2) — independent of US1 (adds to layout.py only)
- **US5 (P2)**: Can start after Foundational (Phase 2) — independent of US1 (modifies uv_project.py preview_files only)
- **US6 (P3)**: Depends on US1 + US5 — dead code removal requires all consumers to be rewired first

### Within Each User Story

- Models / types before service logic
- Core implementation before integration tests
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 2**: T006 can run in parallel with T002–T005 (different file: stages.py vs layout.py)
- **Phase 3**: T009, T011, T012, T014, T016 can all start in parallel (different files). T010 after T009 (same file), T013 after T012 (same file), T015 after T014 (same file)
- **Phase 5–7**: US3, US4, US5 can start in parallel after Phase 2 (US3 and US4 both modify layout.py but different sections; US5 modifies uv_project.py)
- **Phase 8**: T027, T028, T029 can all run in parallel (different files)

---

## Parallel Example: User Story 1

```
# Launch first tasks for each consumer file in parallel:
T009: Rewire _execute_typecheck_stage() in stages.py
T011: Rewire _build_hook_list() in hooks.py
T012: Rewire _render_conf_py() in sphinx_docs.py
T014: Rewire install()/verify() in uv_project.py
T016: Rewire greenfield detection in init_cmd.py

# Then complete same-file follow-ups:
T010: Rewire _execute_docs_api_stage() in stages.py (after T009)
T013: Rewire _render_makefile() in sphinx_docs.py (after T012)
T015: Rewire _augment_pyproject()/_scaffold_pyproject_defaults() in uv_project.py (after T014)

# Finally:
T017: Unit tests (after all rewiring)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T008)
3. Complete Phase 3: User Story 1 (T009–T017)
4. Complete Phase 4: User Story 2 (T018–T019) — regression verification
5. **STOP and VALIDATE**: All pipeline consumers work for both src and flat layouts

### Incremental Delivery

1. Setup + Foundational → Core detection infra ready
2. US1 + US2 → Pipeline works for flat-layout brownfield projects (MVP!)
3. US3 → Manifest config override supported
4. US4 → pyproject.toml hints supported (more accurate detection)
5. US5 → preview_files() layout-aware (brownfield safety improved)
6. US6 → Dead code eliminated (single source of truth)
7. Polish → Edge cases, integration tests, quickstart validation

### Suggested MVP Scope

**US1 + US2 (Phases 1–4)**: This delivers the core value — brownfield flat-layout projects work correctly — while guaranteeing no regressions for existing src-layout projects. Total: 19 tasks.

---

## Notes

- [P] tasks = different files, no dependencies on other [P] tasks in the same phase
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- When rewiring consumers (Phase 3), always include a `None` fallback: `layout = context.package_layout or detect_package_layout(context.repo_root)`
- The 15 hardcoded `src/` references (R-006) are covered by T009–T016 (rewiring) and T027–T029 (dead code removal)
