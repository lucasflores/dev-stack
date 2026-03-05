# Tasks: CodeBoarding Visualization

**Input**: Design documents from `/specs/003-codeboarding-viz/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Unit and integration test tasks are included per Constitution Principle VIII ("Each module MUST have its own test coverage") and Quality Standards ("New code MUST include corresponding tests").

**Organization**: Tasks grouped by user story to enable independent implementation and testing. US6 (Module Lifecycle) precedes US1 (Core Visualization) because the module establishes constants and directory structure that the CLI command depends on.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Project type**: single — `src/dev_stack/` and `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Remove D2 legacy code and prepare shared error types

- [X] T001 Delete D2 legacy source files: src/dev_stack/visualization/d2_gen.py, src/dev_stack/visualization/schema_gen.py, and src/dev_stack/visualization/templates/ directory
- [X] T002 [P] Delete D2 legacy test file tests/unit/test_d2_gen.py
- [X] T003 [P] Add CodeBoardingError exception class (subclass of DevStackError) to src/dev_stack/errors.py with message and optional stderr fields for subprocess failure reporting

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the two core building blocks that ALL user stories depend on — subprocess invocation and output parsing

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement CodeBoarding subprocess runner in src/dev_stack/visualization/codeboarding_runner.py — RunResult dataclass (success, stdout, stderr, return_code); run() function that builds command list (["codeboarding", "--local", repo_root, "--depth-level", N] + optional "--incremental"), executes via subprocess.run(capture_output=True, text=True, timeout=timeout, check=False, cwd=repo_root), catches subprocess.TimeoutExpired, and returns RunResult. Include check_cli_available() using shutil.which("codeboarding")
- [X] T005 [P] Implement output parser and Mermaid extractor in src/dev_stack/visualization/output_parser.py — parse_analysis_index(path) loads .codeboarding/analysis.json into AnalysisIndex/Component/ComponentRelation dataclasses per data-model.md; extract_mermaid(md_path) reads a markdown file and returns the content of the first fenced mermaid code block; derive_markdown_filename(component_name) replaces non-alphanumeric chars with underscores and appends .md; parse_components(codeboarding_dir) orchestrates: load index, for each component derive .md filename, extract Mermaid, return list of ParsedComponent(name, component_id, mermaid, assigned_files, can_expand, sub_components). Handle missing/malformed analysis.json (raise CodeBoardingError) and missing .md files (log warning, skip component)
- [X] T005a [P] Write unit tests for codeboarding_runner in tests/unit/test_codeboarding_runner.py — Mock subprocess.run to test: successful invocation returns RunResult(success=True); non-zero exit returns RunResult(success=False, stderr=...); subprocess.TimeoutExpired is caught and returns timeout error; check_cli_available() returns True/False based on shutil.which mock; command list is correctly constructed with --depth-level and optional --incremental
- [X] T005b [P] Write unit tests for output_parser in tests/unit/test_output_parser.py — Test: parse_analysis_index with valid analysis.json returns correct dataclasses; parse_analysis_index with missing file raises CodeBoardingError; parse_analysis_index with malformed JSON raises CodeBoardingError; extract_mermaid returns first fenced mermaid block from markdown; extract_mermaid returns None for file with no mermaid block; derive_markdown_filename replaces spaces and special chars with underscores; parse_components orchestrates index+mermaid extraction end-to-end; missing component .md file logs warning and skips

**Checkpoint**: Foundation ready — runner can invoke CodeBoarding and parser can extract diagrams

---

## Phase 3: User Story 6 — Module Lifecycle (Priority: P1)

**Goal**: VisualizationModule implements the full ModuleBase contract (install/uninstall/update/verify) for CodeBoarding, replacing all D2 logic

**Independent Test**: Run `dev-stack init` with visualization enabled, verify .codeboarding/ and .dev-stack/viz/ directories are created, then run `dev-stack status` to confirm healthy status

### Implementation for User Story 6

- [X] T006 [US6] Rewrite VisualizationModule in src/dev_stack/modules/visualization.py — Remove all D2 logic (_ensure_d2_installed, _d2_version, D2_MIN_VERSION). Define constants per module-contract.md: CODEBOARDING_OUTPUT_DIR=Path(".codeboarding"), VIZ_STATE_DIR=Path(".dev-stack/viz"), LEGACY_DOCS_DIR=Path("docs/diagrams"), ANALYSIS_INDEX="analysis.json", INJECTION_LEDGER="injected-readmes.json", ROOT_MARKER_ID="architecture", COMPONENT_MARKER_ID="component-architecture", DEFAULT_DEPTH_LEVEL=2, DEFAULT_TIMEOUT_SECONDS=300. Implement install(force): create both dirs, check CLI via codeboarding_runner.check_cli_available(), warn if missing. Implement uninstall(): load injection ledger from .codeboarding/injected-readmes.json, iterate entries and call readme_injector.remove_diagram(readme_path, marker_id) for each (removal implemented in readme_injector.py, not markers.py), delete .codeboarding/ tree, delete .dev-stack/viz/ tree, delete legacy docs/diagrams/ if present. Implement update(): delegate to install(force=True). Implement verify(): check dirs exist + CLI on PATH, return ModuleStatus with health matrix per contract
- [X] T007 [US6] Register visualization module in src/dev_stack/modules/__init__.py — Add "visualization" to the default modules tuple so it is discovered by dev-stack init and dev-stack status

**Checkpoint**: Module lifecycle is functional — install creates dirs, verify reports health, uninstall cleans up

---

## Phase 4: User Story 1 — Core Visualization (Priority: P1) 🎯 MVP

**Goal**: `dev-stack visualize` invokes CodeBoarding, parses output, and injects a top-level Mermaid architecture diagram into root README.md

**Independent Test**: Run `dev-stack visualize` in a repo with Python source files, confirm CodeBoarding runs, .codeboarding/ output exists, and root README.md contains a Mermaid block between DEV-STACK:BEGIN:architecture / DEV-STACK:END:architecture markers

### Implementation for User Story 1

- [X] T008 [US1] Implement README injector and injection ledger in src/dev_stack/visualization/readme_injector.py — inject_diagram(readme_path, marker_id, mermaid_content) wraps Mermaid in a fenced code block and calls markers.write_managed_section(); creates README.md if it does not exist. remove_diagram(readme_path, marker_id) removes managed section by writing empty content then stripping the leftover empty markers (markers.py has no dedicated remove function; implement removal as write_managed_section with empty string followed by marker cleanup). InjectionLedger class: load(path) reads .codeboarding/injected-readmes.json (returns empty ledger if missing), save(path) writes JSON with version=1 + generated_at + entries list, add_entry(readme_path, marker_id, component_name) appends a LedgerEntry, clear() resets entries. inject_root_diagram(repo_root, mermaid_content, ledger) injects into repo_root/README.md with marker_id="architecture" and adds entry to ledger. Handle write permission errors by logging warning and continuing (per cli-contract.md error table)
- [X] T008a [P] [US1] Write unit tests for readme_injector in tests/unit/test_readme_injector.py — Test: inject_diagram creates managed section in existing README; inject_diagram creates new README if file does not exist; inject_diagram is idempotent (second call produces identical file content); remove_diagram removes managed section and leaves surrounding content intact; InjectionLedger.load returns empty ledger when file missing; InjectionLedger.save+load roundtrip preserves entries; inject_root_diagram injects with correct marker_id and updates ledger; write permission error logs warning and continues without raising
- [X] T009 [US1] Rewrite dev-stack visualize CLI command in src/dev_stack/cli/visualize_cmd.py — Remove all D2 imports (SourceScanner, SchemaGenerator, D2Generator, AgentBridge, _render_d2). Define click command with options: --incremental (flag, default False), --depth-level (int, default 2), --no-readme (flag, default False), --timeout (int, default 300), --json (flag), --verbose (flag). Core flow: (1) check_cli_available() or exit code 4 with installation guidance; (2) build and invoke codeboarding_runner.run(repo_root, depth_level, incremental=False, timeout=timeout); (3) on non-zero exit or timeout: display stderr, exit 1, no README changes; (4) parse_components(codeboarding_dir) to get overview + components; (5) extract overview Mermaid from .codeboarding/overview.md; (6) call inject_root_diagram(); (7) save ledger; (8) report results in human format or JSON per cli-contract.md schemas. Wire --json for structured output and --verbose for debug logging via rich console

**Checkpoint**: `dev-stack visualize` produces a Mermaid architecture diagram in root README.md — MVP is functional

---

## Phase 5: User Story 2 — Per-Folder Sub-Diagrams (Priority: P2)

**Goal**: Each CodeBoarding-identified component folder receives a README.md with an inline Mermaid sub-diagram

**Independent Test**: Run `dev-stack visualize` on a multi-package repo, verify at least one component folder has a README.md with a Mermaid block between DEV-STACK:BEGIN:component-architecture / DEV-STACK:END:component-architecture markers

### Implementation for User Story 2

- [X] T010 [P] [US2] Add component-to-folder mapping in src/dev_stack/visualization/output_parser.py — compute_target_folder(assigned_files) returns the longest common directory prefix of a component's assigned_files list (e.g., ["agents/agent.py", "agents/constants.py"] → "agents/"); handle empty assigned_files (return None, skip injection); add target_folder field to ParsedComponent dataclass
- [X] T011 [US2] Extend README injector for per-folder sub-diagram injection in src/dev_stack/visualization/readme_injector.py — inject_component_diagrams(repo_root, components, ledger) iterates parsed components, for each with a target_folder and mermaid content: compute readme_path as target_folder/README.md, call inject_diagram(readme_path, "component-architecture", mermaid), add ledger entry with component_name. Create README.md in folder if it does not exist. Skip components with no target_folder or no Mermaid (log warning). Update ledger with all injected entries
- [X] T012 [US2] Wire sub-diagram injection into CLI flow in src/dev_stack/cli/visualize_cmd.py — After root diagram injection (T009 step 6), call inject_component_diagrams() with parsed components and ledger. Update JSON output schema to include per-component injection counts (components_found, diagrams_injected, readmes_modified list). Update human output to list modified READMEs

**Checkpoint**: Component folders have README.md files with sub-diagrams — User Stories 1 and 2 are both independently functional

---

## Phase 6: User Story 3 — Incremental Mode (Priority: P3)

**Goal**: `dev-stack visualize --incremental` uses ManifestStore to skip unchanged repos and passes --incremental to CodeBoarding

**Independent Test**: Run initial visualization, then re-run with --incremental and no file changes — verify CodeBoarding is NOT invoked and "up to date" is reported. Modify a file and re-run — verify CodeBoarding IS invoked with --incremental flag

### Implementation for User Story 3

- [X] T013 [US3] Integrate ManifestStore change detection gate and --incremental passthrough in src/dev_stack/cli/visualize_cmd.py — Import ManifestStore from visualization/incremental.py (RETAIN). When --incremental is set: (1) load manifest via ManifestStore.load(); (2) build current file snapshot via ManifestStore.build() using SourceScanner; (3) compute changed_paths = manifest.changed_paths(current); (4) if no changes: report "All diagrams up to date" (or JSON with skipped=true, reason="No files changed since last run"), exit 0 without invoking CodeBoarding; (5) if changes exist: pass incremental=True to codeboarding_runner.run(); (6) after successful run: save updated manifest via ManifestStore.save(). Ensure non-incremental runs also save manifest for future incremental comparisons

**Checkpoint**: Incremental mode gates on file changes and passes --incremental to CodeBoarding

---

## Phase 7: User Story 4 + User Story 5 — Depth Control + Analysis-Only (Priority: P3)

**Goal**: --depth-level controls decomposition depth; --no-readme runs analysis without README injection

**Independent Test (US4)**: Run `dev-stack visualize --depth-level 1` — verify only top-level diagram, no sub-diagrams. Run with `--depth-level 3` — verify deeper sub-diagrams appear

**Independent Test (US5)**: Run `dev-stack visualize --no-readme` — verify .codeboarding/ output exists but no README files are created or modified

### Implementation for User Story 4

- [X] T014 [P] [US4] Verify --depth-level flag end-to-end passthrough in src/dev_stack/cli/visualize_cmd.py — Ensure the --depth-level option value (default 2, per research.md R-005 correction) is passed from the click option through to codeboarding_runner.run() as the depth_level parameter, which constructs ["--depth-level", str(depth_level)] in the subprocess command. When depth_level is 1, only overview.md is produced (no sub-component .md files), so inject_component_diagrams() should gracefully handle empty component lists

### Implementation for User Story 5

- [X] T015 [P] [US5] Implement --no-readme conditional guard in src/dev_stack/cli/visualize_cmd.py — When --no-readme flag is set: skip inject_root_diagram(), skip inject_component_diagrams(), skip ledger save. Still invoke CodeBoarding runner and parse output so .codeboarding/ is populated. Report results with diagrams_injected=0 and empty readmes_modified list. JSON output should still include components_found count

**Checkpoint**: All six user stories are independently functional

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Clean up remaining D2 references, update tests, validate end-to-end

- [X] T016 [P] Sweep codebase for remaining D2 references and remove them — Check imports in src/dev_stack/cli/__init__.py, src/dev_stack/visualization/__init__.py, and any references to d2_gen, schema_gen, D2Generator, SchemaGenerator, D2_MIN_VERSION, _render_d2, AgentBridge in non-deleted files
- [X] T017 [P] Update contract test assertions for visualization module in tests/contract/test_module_interface.py — Add or update assertions that VisualizationModule exposes NAME="visualization", implements install/uninstall/update/verify, and returns correct ModuleResult/ModuleStatus types
- [X] T018 [P] Write integration test for end-to-end visualize command in tests/integration/test_visualize.py — Test: `dev-stack visualize` invokes CodeBoarding (mock subprocess), parses output, and injects Mermaid into root README.md; `dev-stack visualize --no-readme` produces .codeboarding/ but no README changes; `dev-stack visualize --incremental` with no changes reports "up to date"; `dev-stack visualize` with CLI missing exits with code 4 and guidance message; JSON output matches cli-contract.md schema
- [X] T019 Run quickstart.md end-to-end validation — Follow the steps in specs/003-codeboarding-viz/quickstart.md from prerequisites through each command invocation and verify expected outputs match actual behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T003 CodeBoardingError used by T004, T005) — BLOCKS all user stories
- **US6 (Phase 3)**: Depends on Foundational (T004 codeboarding_runner.check_cli_available used by T006)
- **US1 (Phase 4)**: Depends on Foundational (T004 runner, T005 parser) and US6 (T006 constants)
- **US2 (Phase 5)**: Depends on US1 (T008 injector, T009 CLI) — extends existing injection flow
- **US3 (Phase 6)**: Depends on US1 (T009 CLI) — adds ManifestStore gate to existing flow
- **US4 + US5 (Phase 7)**: Depends on US1 (T009 CLI) — adds flag-specific behavior
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US6 (P1)**: Can start after Foundational — no dependencies on other stories
- **US1 (P1)**: Can start after Foundational + US6 — depends on US6 for constants and directory contract
- **US2 (P2)**: Depends on US1 — extends the injection pipeline with per-folder logic
- **US3 (P3)**: Depends on US1 — adds incremental gate to the CLI flow
- **US4 (P3)**: Depends on US1 — validates depth-level passthrough (implementation done in Phase 2 + 4)
- **US5 (P3)**: Depends on US1 — adds --no-readme conditional (implementation done in Phase 4)

### Within Each User Story

- Models/dataclasses before services/functions
- Core implementation before integration wiring
- Each story independently testable at its checkpoint

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel (different files)
- **Phase 2**: T004 and T005 can run in parallel (different files, no cross-dependency). T005a, T005b can run in parallel with each other and with T004/T005 (test files, no production code dependency)
- **Phase 3**: T006 and T007 are sequential (T007 depends on T006 module class)
- **Phase 4**: T008 and T009 are sequential (T009 depends on T008 injector). T008a can run in parallel with T009 (test file for T008)
- **Phase 5**: T010 is parallel with other work (only modifies output_parser.py); T011 and T012 are sequential
- **Phase 7**: T014 and T015 can run in parallel (independent flag handlers)
- **Phase 8**: T016, T017, and T018 can run in parallel (different files)

---

## Parallel Example: Phase 2 (Foundational)

```text
# Launch both foundational tasks together (different files, no cross-dependency):
T004: "Implement CodeBoarding subprocess runner in src/dev_stack/visualization/codeboarding_runner.py"
T005: "Implement output parser and Mermaid extractor in src/dev_stack/visualization/output_parser.py"
T005a: "Write unit tests for codeboarding_runner in tests/unit/test_codeboarding_runner.py"
T005b: "Write unit tests for output_parser in tests/unit/test_output_parser.py"
```

## Parallel Example: Phase 7 (US4 + US5)

```text
# Both flag tasks touch visualize_cmd.py but different code paths — can parallelize:
T014: "Verify --depth-level flag end-to-end passthrough in src/dev_stack/cli/visualize_cmd.py"
T015: "Implement --no-readme conditional guard in src/dev_stack/cli/visualize_cmd.py"
```

## Parallel Example: Phase 4 (US1)

```text
# Launch injector test alongside CLI rewrite (different files):
T008a: "Write unit tests for readme_injector in tests/unit/test_readme_injector.py"
T009: "Rewrite dev-stack visualize CLI command in src/dev_stack/cli/visualize_cmd.py"
```

---

## Implementation Strategy

### MVP First (US6 + US1 Only)

1. Complete Phase 1: Setup — delete D2, add error class
2. Complete Phase 2: Foundational — runner + parser
3. Complete Phase 3: US6 — module lifecycle
4. Complete Phase 4: US1 — core visualization
5. **STOP and VALIDATE**: Test `dev-stack visualize` end-to-end — Mermaid diagram appears in root README.md
6. This is the minimum viable replacement for D2

### Incremental Delivery

1. Setup + Foundational → building blocks ready
2. US6 → Module lifecycle functional → `dev-stack init` / `dev-stack status` work
3. US1 → Core visualization → root README diagram (MVP!)
4. US2 → Per-folder sub-diagrams → full documentation coverage
5. US3 → Incremental mode → efficiency for large repos
6. US4 + US5 → Depth control + analysis-only → power user flags
7. Each story adds value without breaking previous stories

### Single Developer Strategy

Work sequentially through phases 1 → 8. Each phase builds on the previous. Commit after each task or logical group (e.g., after each phase checkpoint).

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Constants (CODEBOARDING_OUTPUT_DIR, etc.) are defined in T006 (visualization.py) and imported by later tasks
- The --depth-level default is 2 (not CodeBoarding's default of 1) per research.md R-005 correction
- The index file is analysis.json (not output.json) per research.md R-002 correction
- Component .md filename derivation: replace non-alphanumeric chars with underscores + .md
- Existing ManifestStore and SourceScanner in visualization/ are RETAINED as-is
- Existing markers.py in brownfield/ is UNCHANGED — used by readme_injector.py
