# Tasks: Update APM Default Packages and Manifest Version

**Branch**: `020-update-apm-defaults`
**Input**: [plan.md](plan.md), [spec.md](spec.md), [data-model.md](data-model.md), [research.md](research.md)
**Source files modified**: 3 (`default-apm.yml`, `apm.py`, test files)
**New files**: 0

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (independent files, no incomplete-task dependencies)
- **[US1/US2/US3]**: Maps to user story in spec.md
- Each task includes exact file path

---

## Phase 1: Setup

**Purpose**: No external dependencies or scaffolding needed — all changes are in existing files. This phase is intentionally minimal.

- [X] T001 Confirm branch is `020-update-apm-defaults` and working tree is clean

**Checkpoint**: Ready to implement. All three user stories can proceed — they touch different code paths.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Update the template file and module constants that ALL three user stories depend on for correctness.

- [X] T002 Update `src/dev_stack/templates/apm/default-apm.yml`: set `version: "2.0.0"`, remove `mcp` key entirely, replace `apm` list with the four path-specific entries
- [X] T003 Update `DEFAULT_SERVERS = ()` in `src/dev_stack/modules/apm.py`
- [X] T004 [P] Update `DEFAULT_APM_PACKAGES` to the four path-specific entries in `src/dev_stack/modules/apm.py`
- [X] T005 [P] Update `APMModule` class docstring to `"Manage APM packages and agent skills via the APM CLI."` in `src/dev_stack/modules/apm.py`
- [X] T006 [P] Update `_parse_install_result` success message to `"All APM dependencies installed successfully"` in `src/dev_stack/modules/apm.py`

**Checkpoint**: Foundation ready — template and constants are correct. User story implementation and test updates can proceed.

---

## Phase 3: User Story 1 - Fresh Init Produces Correct Default Manifest (Priority: P1) 🎯 MVP

**Goal**: A fresh `dev-stack init` generates an `apm.yml` with version `2.0.0`, no `mcp` key, and exactly the four approved path-specific `apm` entries. `apm install` exits 0.

**Independent Test**: `python -m pytest tests/unit/test_apm_module.py::TestBootstrapManifest tests/unit/test_apm_module.py::TestExpandedTemplate -v -o addopts=''`

### Implementation for User Story 1

- [X] T007 [P] [US1] Update `TestBootstrapManifest::test_create_when_missing` in `tests/unit/test_apm_module.py`: remove `len(mcp) == 3` assertion; assert `"mcp" not in content["dependencies"]` and `len(content["dependencies"]["apm"]) == 4`
- [X] T008 [P] [US1] Update `TestBootstrapManifest::test_overwrite_when_exists` in `tests/unit/test_apm_module.py`: same assertion change as T007
- [X] T009 [P] [US1] Update `TestBootstrapManifest::test_force_overwrites_existing` in `tests/unit/test_apm_module.py`: same assertion change as T007
- [X] T010 [US1] Replace `TestExpandedTemplate::test_template_contains_mcp_and_apm_sections` in `tests/unit/test_apm_module.py`: assert `"mcp" not in content["dependencies"]`, `"apm" in content["dependencies"]`, and `content["version"] == "2.0.0"` (covers SC-003)
- [X] T011 [US1] Replace `TestExpandedTemplate::test_template_preserves_all_mcp_servers` with `test_template_has_no_mcp_servers` in `tests/unit/test_apm_module.py`: assert `"mcp" not in content["dependencies"]`
- [X] T012 [US1] Update `TestExpandedTemplate::test_template_contains_agent_skills` in `tests/unit/test_apm_module.py`: assert `len(apm_list) == 4`; assert all four path-specific entries are present
- [X] T013 [US1] Update `TestExpandedTemplate::test_template_apm_packages_format` in `tests/unit/test_apm_module.py`: update format assertion to expect `owner/repo/path` (three slash-separated segments minimum)

**Checkpoint**: US1 fully testable. Run `python -m pytest tests/unit/test_apm_module.py::TestBootstrapManifest tests/unit/test_apm_module.py::TestExpandedTemplate -v -o addopts=''` — all pass.

---

## Phase 4: User Story 2 - Merge Strategy Preserves No MCP Entries (Priority: P2)

**Goal**: The merge strategy does not add MCP servers to any manifest. Empty merged `mcp` list → key omitted entirely. Path-specific entries deduplicate by full path.

**Independent Test**: `python -m pytest tests/unit/test_apm_module.py::TestMergeManifestApm tests/integration/test_apm_install.py::TestCommunityPackages::test_merge_preserves_community_packages -v -o addopts=''`

### Implementation for User Story 2

- [X] T014 [US2] Fix `_merge_manifest` in `src/dev_stack/modules/apm.py`: replace `deps["mcp"] = mcp_list` with conditional — only write `deps["mcp"]` if `mcp_list` is non-empty; delete the key if it exists and result is empty
- [X] T015 [US2] Add `test_merge_empty_mcp_key_omitted` to `TestMergeManifestApm` in `tests/unit/test_apm_module.py`: given manifest with no `mcp` section, after merge, assert `"mcp" not in content["dependencies"]`
- [X] T016 [P] [US2] Add `test_merge_no_mcp_added_from_empty_defaults` to `TestMergeManifestApm` in `tests/unit/test_apm_module.py`: assert `APMModule.DEFAULT_SERVERS == ()` and that `_merge_manifest` on a blank manifest produces no `mcp` key
- [X] T017 [US2] Update `TestMergeManifestApm::test_merge_adds_apm_section_to_existing_manifest` in `tests/unit/test_apm_module.py`: assert `len(content["dependencies"]["apm"]) == 4` (four path entries added, not 1)
- [X] T018 [US2] Update `TestMergeManifestApm::test_merge_does_not_duplicate_existing_apm_packages` in `tests/unit/test_apm_module.py`: use a path-specific entry (e.g., `lucasflores/agent-skills/skills/commit-pipeline`) as the pre-existing entry; assert that entry appears exactly once and total `apm` count is 4 (not 1)
- [X] T019 [US2] Update `TestMergeManifestApm::test_merge_preserves_custom_apm_packages` in `tests/unit/test_apm_module.py`: assert `len(apm_list) == 5` (1 custom + 4 path defaults)
- [X] T020 [US2] Update `TestBootstrapManifest::test_merge_adds_missing_defaults` in `tests/unit/test_apm_module.py`: remove MCP count assertion; assert 4 `apm` entries added to manifest with no prior `apm` section; assert no `mcp` key in result
- [X] T021 [US2] Update `TestCommunityPackages::test_merge_preserves_community_packages` in `tests/integration/test_apm_install.py`: assert `len(mcp_list) == 1` (community server only; no defaults added since `DEFAULT_SERVERS` is now empty)

**Checkpoint**: US2 fully testable. Run `python -m pytest tests/unit/test_apm_module.py::TestMergeManifestApm tests/unit/test_apm_module.py::TestBootstrapManifest::test_merge_adds_missing_defaults tests/integration/test_apm_install.py::TestCommunityPackages::test_merge_preserves_community_packages -v -o addopts=''` — all pass.

---

## Phase 5: User Story 3 - Preview Reflects Updated Defaults (Priority: P3)

**Goal**: `preview_files()` returns the updated manifest content — version `2.0.0`, no `mcp`, four path-specific `apm` entries.

**Independent Test**: `python -m pytest tests/contract/test_apm_contract.py::TestAPMModuleProtocol::test_preview_files_returns_dict -v -o addopts=''` (contract test unchanged — no new test needed; correctness is verified by the template change in T002 which `preview_files` reads directly)

### Implementation for User Story 3

*No additional implementation tasks — `preview_files()` calls `_render_template()` which reads `default-apm.yml` directly. Template updated in T002 covers this story entirely.*

**Checkpoint**: US3 verified by running the quickstart Step 3 scenario (`preview_files()` returns content matching new template).

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T022 [P] Run full APM test suite and confirm all pass: `python -m pytest tests/unit/test_apm_module.py tests/unit/test_apm_cmd.py tests/contract/test_apm_contract.py tests/integration/test_apm_install.py -v -o addopts=''`
- [X] T023 Run quickstart.md verification steps 1–5 in `specs/020-update-apm-defaults/quickstart.md` to confirm live end-to-end correctness

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user story work**
- **Phase 3 (US1)**: Depends on Phase 2 (T002–T006 complete)
- **Phase 4 (US2)**: Depends on Phase 2 (T002–T006 complete); T014 (`_merge_manifest` fix) must complete before T015–T021
- **Phase 5 (US3)**: Depends on Phase 2 (T002 complete) — no additional tasks
- **Phase 6 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US1** and **US2** can proceed in parallel after Phase 2 completes (they touch different test classes)
- **US3** is satisfied by T002 alone; no blocking dependency on US1 or US2

### Within Each User Story

- **US1**: T007–T009 can run in parallel (three independent test methods); T010–T013 are sequential (same test class, thematically ordered)
- **US2**: T014 (`_merge_manifest` logic fix) MUST complete before T015–T021 (tests verify the fix); T015–T016 can run in parallel after T014; T017–T021 can run in parallel with each other after T014

### Parallel Opportunities

- T003, T004, T005, T006 (Phase 2) can all run in parallel — they touch different lines of `apm.py`
- T007, T008, T009 (US1) can run in parallel — different test method bodies
- T015, T016 (US2 new tests) can run in parallel
- T017, T018, T019, T020 (US2 test updates) can run in parallel after T014

---

## Parallel Example: Phase 2 (Foundational)

```
T002 (template file)      ──┐
T003 (DEFAULT_SERVERS)    ──┤
T004 (DEFAULT_APM_PKGS)   ──┼──▶ Phase 2 done ──▶ Phase 3 + Phase 4 start
T005 (docstring)          ──┤
T006 (success message)    ──┘
```

## Parallel Example: User Story 1

```
T007 (test_create_when_missing)     ──┐
T008 (test_overwrite_when_exists)   ──┼──▶ T010 ──▶ T011 ──▶ T012 ──▶ T013
T009 (test_force_overwrites)        ──┘
```

## Parallel Example: User Story 2

```
T014 (_merge_manifest fix)
       │
       ├──▶ T015 (new test: empty mcp omitted)  ──┐
       ├──▶ T016 (new test: no mcp from empty)  ──┤
       ├──▶ T017 (update: apm section count)    ──┤──▶ T022 (full suite)
       ├──▶ T018 (update: dedup path entry)     ──┤
       ├──▶ T019 (update: custom + 4 defaults)  ──┤
       ├──▶ T020 (update: bootstrap merge)      ──┤
       └──▶ T021 (integration: community merge) ──┘
```

---

## Implementation Strategy

**MVP scope**: Phase 2 + Phase 3 (T001–T013) — delivers US1 (fresh init correctness), which is the primary observable outcome and the safest first increment.

**Full delivery**: Phase 2 + Phase 3 + Phase 4 (adds merge correctness for US2) — recommended single PR since the changeset is small and self-contained.

**Phase 5 (US3)**: Zero additional implementation effort; covered by T002.

**Total tasks**: 23 (T001–T023)  
**Parallelizable**: T003–T006, T007–T009, T015–T021  
**Sequential blockers**: T002 (template) and T014 (`_merge_manifest` fix)
