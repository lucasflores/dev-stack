# Tasks: APM Module Swap

**Input**: Design documents from `/specs/013-apm-module-swap/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-contract.md

**Tests**: Included — TDD required per project conventions (Red-Green-Refactor cycle).

**Organization**: Tasks grouped by user story. Each story is independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create template and scaffolding files needed by all subsequent phases

- [X] T001 Create default APM manifest template with 5 default servers in src/dev_stack/templates/apm/default-apm.yml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: APMModule skeleton and registration — MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Create APMModule class skeleton with class constants (NAME, VERSION, DEPENDS_ON, MANAGED_FILES, MIN_APM_VERSION, DEFAULT_SERVERS), _check_apm_cli(), and _run_apm() helpers in src/dev_stack/modules/apm.py
- [X] T003 [P] Create apm_cmd.py Click group skeleton with install/audit placeholder subcommands and import from src/dev_stack/cli/main.py
- [X] T004 [P] Add apm module auto-import in src/dev_stack/modules/__init__.py (register via @register_module, do NOT change DEFAULT_GREENFIELD_MODULES yet)

**Checkpoint**: APMModule is registered, CLI group is wired, template exists — story implementation can begin

---

## Phase 3: User Story 1 — APM-Based MCP Server Installation (Priority: P1) 🎯 MVP

**Goal**: `dev-stack init` bootstraps an `apm.yml` manifest seeded with 5 default servers and invokes `apm install` to deploy agent-native MCP config files

**Independent Test**: Run `dev-stack init` in a fresh directory → verify `apm.yml` exists with 5 servers, `apm.lock.yaml` generated, agent config dirs populated

### Tests for User Story 1

> **Write these tests FIRST, ensure they FAIL before implementation**

- [X] T005 [P] [US1] Contract test for APMModule ModuleBase protocol compliance (install, uninstall, update, verify, preview_files return types) in tests/contract/test_apm_contract.py
- [X] T006 [P] [US1] Unit tests for APMModule install flow: _check_apm_cli (found/missing/old-version), _bootstrap_manifest (create/skip/merge/overwrite), install (success/partial-fail/cli-missing), _parse_install_result (all-pass/partial/full-fail) in tests/unit/test_apm_module.py
- [X] T007 [P] [US1] Unit tests for dev-stack apm install CLI subcommand (--force flag, JSON output, exit codes) in tests/unit/test_apm_cmd.py

### Implementation for User Story 1

- [X] T008 [US1] Implement _bootstrap_manifest() with Click prompt for skip/merge/overwrite when apm.yml exists; generate from template when missing in src/dev_stack/modules/apm.py
- [X] T009 [US1] Implement _parse_install_result() to parse apm install stdout/stderr for per-server success/failure and populate ModuleResult in src/dev_stack/modules/apm.py
- [X] T010 [US1] Implement install() method: _check_apm_cli → _bootstrap_manifest → _run_apm(["install"]) → _parse_install_result, with fail-forward on partial failure in src/dev_stack/modules/apm.py
- [X] T011 [US1] Implement preview_files(), uninstall() (remove apm.yml + apm.lock.yaml), and update() (delegates to install with force) in src/dev_stack/modules/apm.py
- [X] T012 [US1] Implement verify() checking APM CLI on PATH, version >= MIN_APM_VERSION, apm.yml exists, apm.lock.yaml exists in src/dev_stack/modules/apm.py
- [X] T013 [US1] Wire dev-stack apm install subcommand to APMModule.install() with --force option in src/dev_stack/cli/apm_cmd.py

**Checkpoint**: `dev-stack apm install` works end-to-end — bootstraps manifest, invokes APM, reports per-server status

---

## Phase 4: User Story 2 — Lockfile-Based Reproducibility (Priority: P2)

**Goal**: `apm.lock.yaml` pins exact versions; `verify()` warns when lockfile is stale relative to manifest

**Independent Test**: Initialize, modify `apm.yml` after install, run `dev-stack apm install --json` → verify staleness warning appears in verify output

### Tests for User Story 2

- [X] T014 [P] [US2] Unit tests for verify() lockfile staleness: lockfile newer than manifest (clean), lockfile older than manifest (stale warning), lockfile missing (warning) in tests/unit/test_apm_module.py

### Implementation for User Story 2

- [X] T015 [US2] Add lockfile mtime vs apm.yml mtime staleness detection to verify() with warning message in src/dev_stack/modules/apm.py

**Checkpoint**: `verify()` detects and reports lockfile drift — ensures reproducibility awareness

---

## Phase 5: User Story 3 — Custom Community Package Installation (Priority: P2)

**Goal**: Users can add community APM packages to `apm.yml` and they install alongside defaults; unknown packages produce clear errors

**Independent Test**: Add a community package to `apm.yml`, run install → community package appears in output; use a non-existent package name → clear error message

### Tests for User Story 3

- [X] T016 [P] [US3] Integration test for custom community package in apm.yml alongside defaults, and unknown-package error surfacing in tests/integration/test_apm_install.py

### Implementation for User Story 3

- [X] T017 [US3] Ensure _parse_install_result() extracts and surfaces package-not-found errors from APM stderr with actionable message in src/dev_stack/modules/apm.py

**Checkpoint**: Community packages install transparently; bad package names produce clear errors

---

## Phase 6: User Story 4 — Deprecation of Legacy mcp_servers Module (Priority: P3)

**Goal**: `mcp_servers` removed from defaults, replaced by `apm`; legacy module still works when opted in with deprecation warning

**Independent Test**: Fresh init → apm module runs (not mcp_servers); project with explicit `mcp-servers` in dev-stack.toml → legacy module runs with deprecation warning

### Tests for User Story 4

- [X] T018 [P] [US4] Unit test for DeprecationWarning in MCPServersModule.install() in tests/unit/test_mcp_servers_deprecation.py
- [X] T019 [P] [US4] Unit test that DEFAULT_GREENFIELD_MODULES contains "apm" and not "mcp_servers" in tests/unit/test_apm_module.py
- [X] T020 [P] [US4] Integration test verifying mcp-servers module runs successfully when explicitly listed in dev-stack.toml (opt-in backward compat, FR-011) in tests/integration/test_legacy_mcp_servers.py

### Implementation for User Story 4

- [X] T021 [US4] Add warnings.warn() DeprecationWarning to MCPServersModule.install() recommending migration to apm in src/dev_stack/modules/mcp_servers.py
- [X] T022 [US4] Replace "mcp_servers" with "apm" in DEFAULT_GREENFIELD_MODULES tuple in src/dev_stack/modules/__init__.py

**Checkpoint**: Default init uses `apm`; legacy `mcp-servers` opt-in still works with visible deprecation warning

---

## Phase 7: User Story 5 — Security Auditing of MCP Configurations (Priority: P3)

**Goal**: `dev-stack apm audit` invokes APM's audit capability and reports findings in text/json/sarif/markdown formats

**Independent Test**: Run `dev-stack apm audit` → clean report; run `dev-stack apm audit --format json` → parseable JSON output

### Tests for User Story 5

- [X] T023 [P] [US5] Unit tests for audit() method (clean scan, findings detected, format options, output file) and CLI subcommand (--format, --output flags, exit codes) in tests/unit/test_apm_module.py

### Implementation for User Story 5

- [X] T024 [US5] Implement audit() method in APMModule: verify CLI, run apm audit with format/output args, map APM exit codes to ModuleResult in src/dev_stack/modules/apm.py
- [X] T025 [US5] Wire dev-stack apm audit subcommand to APMModule.audit() with --format and --output options in src/dev_stack/cli/apm_cmd.py

**Checkpoint**: `dev-stack apm audit` produces security scan reports in all supported formats

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and cleanup across all user stories

- [X] T026 [P] Integration test for full dev-stack init pipeline with APM module (no legacy mcp_servers), including idempotency assertion (running init twice produces no changes on second run) and reproducibility assertion (same lockfile produces identical output) in tests/integration/test_apm_install.py
- [X] T027 Run quickstart.md verification scenarios (all 6 scenarios) to confirm end-to-end behavior
- [X] T028 [P] Code cleanup: remove any TODO placeholders, ensure consistent error messages, verify JSON output format

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (template must exist before module references it) — BLOCKS all user stories
- **User Stories (Phase 3–7)**: All depend on Foundational phase completion
  - US1 (Phase 3): No dependencies on other stories — this is the MVP
  - US2 (Phase 4): Extends verify() from US1 — depends on T012
  - US3 (Phase 5): Extends _parse_install_result() from US1 — depends on T009
  - US4 (Phase 6): Can start after Phase 2 — independent of US1/US2/US3
  - US5 (Phase 7): Depends on Phase 2 foundation (apm_cmd.py, APMModule skeleton)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — No dependencies on other stories ← **MVP**
- **US2 (P2)**: Extends US1's `verify()` — light dependency on T012
- **US3 (P2)**: Extends US1's `_parse_install_result()` — light dependency on T009
- **US4 (P3)**: Independent of US1-US3 — only modifies `mcp_servers.py` and `__init__.py`
- **US5 (P3)**: Independent of US1-US4 — only adds `audit()` and CLI wiring

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD: Red-Green-Refactor)
- Private helpers before public methods (e.g., `_bootstrap_manifest` before `install`)
- Core method before CLI wiring (e.g., `install()` before `apm_cmd.py` wiring)
- Story complete before moving to next priority

### Parallel Opportunities

- T003 and T004 can run in parallel (different files, no dependencies)
- T005, T006, T007 can all run in parallel (different test files)
- T018, T019, and T020 can run in parallel (different test files)
- US4 (Phase 6) and US5 (Phase 7) can execute in parallel once Phase 2 is complete
- US2 and US3 can execute in parallel once US1's T009 and T012 are complete

---

## Parallel Example: User Story 1

```bash
# Launch all tests for US1 together (TDD: Red phase):
Task T005: "Contract test for APMModule in tests/contract/test_apm_contract.py"
Task T006: "Unit tests for APMModule install flow in tests/unit/test_apm_module.py"
Task T007: "Unit tests for apm install CLI in tests/unit/test_apm_cmd.py"

# Then implement sequentially (TDD: Green phase):
Task T008: "_bootstrap_manifest() in src/dev_stack/modules/apm.py"
Task T009: "_parse_install_result() in src/dev_stack/modules/apm.py"
Task T010: "install() in src/dev_stack/modules/apm.py"
Task T011: "preview_files, uninstall, update in src/dev_stack/modules/apm.py"
Task T012: "verify() in src/dev_stack/modules/apm.py"
Task T013: "Wire apm install CLI in src/dev_stack/cli/apm_cmd.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T004)
3. Complete Phase 3: User Story 1 (T005–T013)
4. **STOP and VALIDATE**: Run `dev-stack apm install` in a test directory
5. Deploy/demo if ready — core APM-based install works

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Full APM install flow → **MVP!**
3. Add US2 → Lockfile staleness detection
4. Add US3 → Community package error surfacing
5. Add US4 → Legacy deprecation + default swap
6. Add US5 → Security audit capability
7. Polish → Integration tests + quickstart validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (core install — MVP)
   - Developer B: US4 (deprecation — independent)
   - Developer C: US5 (audit — independent)
3. After US1 completes:
   - Developer A: US2 + US3 (extend US1)
4. Final: All converge on Phase 8 polish

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- APM CLI registry URIs in default-apm.yml need verification at implementation time (R2 in research.md)
- Use `subprocess.run(capture_output=True)` for all APM invocations (R1)
- `packaging.version.Version` for semver comparison in `_check_apm_cli()` (R6)
- Click `click.prompt(type=click.Choice(...))` for skip/merge/overwrite (R4)
- Non-interactive mode (CI) defaults to "skip" for brownfield safety (R4)
- Commit after each task or logical group per atomic commit conventions
