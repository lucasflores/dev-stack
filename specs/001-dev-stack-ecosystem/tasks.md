# Tasks: Dev-Stack Ecosystem

**Input**: Design documents from `/specs/001-dev-stack-ecosystem/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included — plan.md defines explicit test files (unit/, integration/, contract/) and contract tests for CLI JSON output.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in every description

## Path Conventions

- **Single project**: `src/dev_stack/` for source, `tests/` at repository root, `templates/` for scaffolding
- Per plan.md project structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — pyproject.toml, package skeleton, dev tooling

- [X] T001 Create project skeleton: `pyproject.toml`, `src/dev_stack/__init__.py`, `tests/__init__.py`, `README.md`
- [X] T002 Configure pyproject.toml with dependencies (click, tomli-w, rich, pytest, pytest-cov with `--cov-fail-under=80`, ruff) and `[project.scripts]` entry point `dev-stack = "dev_stack.cli.main:cli"`
- [X] T003 [P] Configure ruff settings in pyproject.toml `[tool.ruff]` section (target Python 3.11, line-length 100)
- [X] T004 [P] Create templates/ directory structure: `templates/hooks/`, `templates/ci/`, `templates/docker/`, `templates/mcp/`, `templates/speckit/`, `templates/prompts/`
- [X] T005 [P] Create package `__init__.py` files for all subpackages: `src/dev_stack/cli/__init__.py`, `src/dev_stack/modules/__init__.py`, `src/dev_stack/pipeline/__init__.py`, `src/dev_stack/visualization/__init__.py`, `src/dev_stack/brownfield/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Implement StackManifest reader/writer (read_manifest, write_manifest, create_default) using tomllib/tomli-w per R-003 schema in `src/dev_stack/manifest.py`
- [X] T007 [P] Implement global config: agent detection algorithm (R-002 order: $DEV_STACK_AGENT → claude → gh copilot → cursor → none), env var validation in `src/dev_stack/config.py`
- [X] T008 [P] Implement ModuleBase ABC with ModuleResult, ModuleStatus dataclasses per module-contract.md in `src/dev_stack/modules/base.py`
- [X] T009 [P] Implement error hierarchy (DevStackError, ConflictError, DependencyError, AgentUnavailableError, RollbackError) per module-contract.md in `src/dev_stack/errors.py`
- [X] T010 Implement AgentBridge with detect(), invoke(), is_available() — subprocess-based, per agent-invocation-contract.md with _executor testing seam in `src/dev_stack/pipeline/agent_bridge.py`
- [X] T011 [P] Implement marker read/write (read_managed_section, write_managed_section) with comment-prefix adaptation per R-004 in `src/dev_stack/brownfield/markers.py`
- [X] T012 [P] Implement conflict detection: file-hash comparison, ConflictReport/FileConflict generation per data-model.md in `src/dev_stack/brownfield/conflict.py`
- [X] T013 Implement git-based rollback: tag creation (dev-stack/rollback/<timestamp>), restore (git checkout <ref> -- .), tag cleanup per R-005 in `src/dev_stack/brownfield/rollback.py`
- [X] T014 Implement Click CLI group with global flags (--json, --verbose, --dry-run), TTY color detection, exit code constants per cli-contract.md in `src/dev_stack/cli/main.py`
- [X] T015 [P] Unit test for manifest reader/writer (read, write, create_default, invalid TOML) in `tests/unit/test_manifest.py`
- [X] T016 [P] Unit test for marker operations (read, write, append, multi-section, comment-prefix variants) in `tests/unit/test_markers.py`
- [X] T017 [P] Unit test for conflict detection (new file, modified file, hash match, hash mismatch) in `tests/unit/test_conflict.py`

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Initialize a New Repository (Priority: P1) 🎯 MVP

**Goal**: A developer runs `dev-stack init` in an empty directory and gets a fully scaffolded, automation-ready repository

**Independent Test**: Run `dev-stack init` in an empty git repo and verify all expected files exist, `dev-stack.toml` is valid, and `git commit` triggers the pre-commit hook

### Implementation for User Story 1

- [X] T018 [P] [US1] Implement HooksModule (install: copy pre-commit hook + config, uninstall, update, verify) in `src/dev_stack/modules/hooks.py`
- [X] T019 [P] [US1] Create pre-commit hook shell script template (invokes `dev-stack pipeline run`) in `templates/hooks/pre-commit`
- [X] T020 [P] [US1] Create .pre-commit-config.yaml template (ruff, pytest, security stages) in `templates/hooks/pre-commit-config.yaml`
- [X] T021 [US1] Implement module resolver: dependency ordering, auto-include missing deps, default module set (hooks, speckit for greenfield) in `src/dev_stack/modules/__init__.py`
- [X] T022 [US1] Implement init command — greenfield path: detect empty repo, resolve modules, call module.install(), create manifest, create rollback tag, detect agent in `src/dev_stack/cli/init_cmd.py`
- [X] T023 [US1] Register init command with main CLI group, wire --modules, --force, --json, --dry-run flags in `src/dev_stack/cli/main.py`
- [X] T024 [US1] Contract test: validate init --json output matches cli-contract.md schema (status, mode, manifest_path, modules_installed, agent) in `tests/contract/test_cli_json_output.py`
- [X] T025 [US1] Integration test: greenfield init in temp dir → verify files created, manifest valid, hook executable; verify idempotency (running init twice produces identical results) in `tests/integration/test_init_greenfield.py`
- [X] T079 [US1] Handle re-init detection in init command: if `dev-stack.toml` already exists, offer to re-initialize (with confirmation) or switch to `update` mode per Edge Case 1, in `src/dev_stack/cli/init_cmd.py`

**Checkpoint**: `dev-stack init` works end-to-end in greenfield repos — this is MVP

---

## Phase 4: User Story 2 — Initialize an Existing Repository (Brownfield) (Priority: P1)

**Goal**: A developer adds dev-stack to an existing project with conflict detection, per-file approval, and safe rollback

**Independent Test**: Run `dev-stack init` in a repo with existing Dockerfile and CI workflows, verify every conflict is surfaced, nothing is overwritten without consent, and rollback restores pre-init state

### Implementation for User Story 2

- [X] T026 [US2] Implement brownfield detection in init command: scan for overlapping files, generate ConflictReport, present per-file diffs in `src/dev_stack/cli/init_cmd.py`
- [X] T027 [US2] Implement interactive conflict resolution prompts (accept/skip/merge) with rich formatting in `src/dev_stack/brownfield/conflict.py`
- [X] T028 [US2] Implement rollback command: read rollback_ref from manifest, git checkout restore, tag cleanup per cli-contract.md in `src/dev_stack/cli/rollback_cmd.py`
- [X] T029 [US2] Register rollback command in CLI group in `src/dev_stack/cli/main.py`
- [X] T030 [US2] Implement --dry-run (show ConflictReport without writing) and --force (skip prompts, overwrite) flags for brownfield init in `src/dev_stack/cli/init_cmd.py`
- [X] T031 [US2] Integration test: brownfield init with existing Dockerfile + CI → verify conflicts surfaced, markers applied, user content preserved in `tests/integration/test_init_brownfield.py`
- [X] T032 [US2] Integration test: rollback after init → verify all files restored to pre-init state in `tests/integration/test_rollback.py`

**Checkpoint**: Both greenfield and brownfield init work with full conflict safety

---

## Phase 5: User Story 4 — Pre-Commit Automation Pipeline (Priority: P2)

**Goal**: Every `git commit` triggers a 6-stage pipeline — lint, test, security (hard gates) + docs, infra-sync, commit-message (soft gates)

**Independent Test**: Stage files, run `git commit`, verify each stage executes in order, hard failures block commit, soft failures warn but allow with --force

### Implementation for User Story 4

- [X] T033 [US4] Implement PipelineStage and StageResult dataclasses with failure_mode enum (hard/soft) per data-model.md in `src/dev_stack/pipeline/stages.py`
- [X] T034 [P] [US4] Implement lint stage: invoke ruff check + ruff format --check via subprocess in `src/dev_stack/pipeline/stages.py`
- [X] T035 [P] [US4] Implement test stage: invoke pytest (if tests/ exists) via subprocess in `src/dev_stack/pipeline/stages.py`
- [X] T036 [P] [US4] Implement security stage: invoke pip-audit + detect-secrets via subprocess in `src/dev_stack/pipeline/stages.py`
- [X] T042 [P] [US4] Create documentation update prompt template in `templates/prompts/docs_update.txt`
- [X] T037 [US4] Implement docs agent stage: construct docs-update prompt, invoke via AgentBridge, apply updates — MUST preserve user-written documentation sections per FR-028 in `src/dev_stack/pipeline/stages.py`
- [X] T038 [US4] Implement infra-sync stage: compare templates/ against generated files (including Dockerfile dependency comparison per FR-020), flag drift in `src/dev_stack/pipeline/stages.py`
- [X] T039 [US4] Implement PipelineRunner orchestrator: sequential execution, hard/soft gate logic, --force override, coverage enforcement (`--cov-fail-under` in test stage), parallel mode for >500 files (stages 1-3 via ProcessPoolExecutor) per R-006 in `src/dev_stack/pipeline/runner.py`
- [X] T040 [US4] Unit test for PipelineRunner: stage ordering, hard-fail halts pipeline, soft-fail warns, --force bypass, skip-when-no-agent, idempotency (running pipeline twice produces identical results) in `tests/unit/test_pipeline.py`
- [X] T077 [US4] Implement `--no-hooks` bypass in pre-commit hook script: detect `--no-hooks` flag or `DEV_STACK_NO_HOOKS=1` env var, skip pipeline entirely, flag skipped run for next CI check per FR-015 in `templates/hooks/pre-commit`
- [X] T078 [US4] Implement `pipeline run` CLI subcommand: invoke PipelineRunner programmatically, wire --force and --stage flags per cli-contract.md in `src/dev_stack/cli/pipeline_cmd.py` and register in `src/dev_stack/cli/main.py`

**Checkpoint**: Pre-commit pipeline runs all 6 stages with correct gate behavior

---

## Phase 6: User Story 8 — Commit Message Agent as Persistent Memory (Priority: P2)

**Goal**: Pipeline stage 6 generates structured commit messages with intent, reasoning, scope, narrative, and git trailers — serving as persistent memory for coding agents

**Independent Test**: Make a code change, run the pipeline, verify the generated commit message contains all R-007 sections and trailers parse correctly via `git log --format='%(trailers)'`

### Implementation for User Story 8

- [X] T041 [P] [US8] Create commit message prompt template per R-007 format (type, scope, intent, reasoning, narrative, trailers) in `templates/prompts/commit_message.txt`
- [X] T043 [US8] Implement git trailer parser/formatter (parse trailers from commit text, format Spec-Ref/Task-Ref/Agent/Pipeline trailers) in `src/dev_stack/pipeline/commit_format.py`
- [X] T044 [US8] Wire commit message stage into PipelineRunner as stage 6 — invoke AgentBridge with prompt, write result to .git/COMMIT_EDITMSG in `src/dev_stack/pipeline/runner.py`
- [X] T045 [US8] Integration test: generate commit message from staged diff → verify all sections present, trailers parse, summary ≤72 chars in `tests/integration/test_commit_message.py`

**Checkpoint**: Every commit gets a structured, agent-memory-optimized message

---

## Phase 7: User Story 3 — Update Stack (Priority: P2)

**Goal**: `dev-stack update` safely merges new stack capabilities into an existing repo, preserving user customizations in marker-delimited sections

**Independent Test**: Initialize repo with stack v1, run update against v2 that adds a hook and modifies a file — verify new hook added, modified file presented as diff, user customizations untouched

### Implementation for User Story 3

- [X] T046 [US3] Implement version comparison logic: read current manifest version, compare against latest available, compute module diffs in `src/dev_stack/manifest.py`
- [X] T047 [US3] Implement update command: resolve modules, detect conflicts via marker comparison, present per-file diff, apply marker-based merging in `src/dev_stack/cli/update_cmd.py`
- [X] T048 [US3] Register update command with CLI group, wire --modules, --json, --dry-run flags in `src/dev_stack/cli/main.py`
- [X] T049 [US3] Handle incomplete update state: detect partial update (check for .dev-stack/update-in-progress marker), offer resume or rollback in `src/dev_stack/cli/update_cmd.py`
- [X] T050 [US3] Integration test: init v1 → update to v2 → verify new module added, existing markers preserved, manifest version bumped in `tests/integration/test_update.py`

**Checkpoint**: Full lifecycle (init → update → rollback) works for any repository

---

## Phase 8: User Story 7 — Spec Kit Integration (Priority: P2)

**Goal**: `dev-stack init` integrates GitHub Spec Kit — `.specify/` directory with templates, scripts, and constitution — so `/speckit.*` commands work immediately

**Independent Test**: Run `dev-stack init`, verify `.specify/` exists with constitution, templates, and scripts; run a speckit command and verify it executes correctly

### Implementation for User Story 7

- [X] T051 [P] [US7] Create .specify/ scaffold templates: constitution.md template, templates/, scripts/bash/ stubs, memory/ directory in `templates/speckit/`
- [X] T052 [US7] Implement SpecKitModule: install (vendor templates + `uv tool install spec-kit`), uninstall, update (preserve constitution, refresh templates), verify in `src/dev_stack/modules/speckit.py`
- [X] T053 [US7] Implement Spec Kit update logic: diff vendored templates vs latest, preserve user constitution and custom specs, refresh scripts in `src/dev_stack/modules/speckit.py`
- [X] T054 [US7] Integration test: init with speckit module → verify .specify/ structure, constitution exists, `specify --version` callable in `tests/integration/test_speckit.py`

**Checkpoint**: Spec Kit is fully integrated and functional from first init

---

## Phase 9: User Story 5 — MCP Server Suite Installation (Priority: P3)

**Goal**: `dev-stack mcp install` configures Context7, GitHub, sequential-thinking, Hugging Face, and NotebookLM MCP servers for the detected coding agent

**Independent Test**: Run `dev-stack mcp install` with no prior config, verify all server configs written to agent-specific location; run `dev-stack mcp verify` and confirm health check results

### Implementation for User Story 5

- [X] T055 [P] [US5] Create MCP server config templates for Claude (.claude/settings.local.json) and Copilot (.github/copilot-mcp.json) per R-008 in `templates/mcp/`
- [X] T056 [US5] Implement MCPServersModule: install (detect agent, write config, validate env vars), uninstall, update, verify (health checks) per data-model.md MCPServerConfig in `src/dev_stack/modules/mcp_servers.py`
- [X] T057 [US5] Implement mcp install command: read servers from manifest or --servers flag, check env vars, write agent-specific config in `src/dev_stack/cli/mcp_cmd.py`
- [X] T058 [US5] Implement mcp verify command: test connectivity to each server, report pass/fail/latency per cli-contract.md in `src/dev_stack/cli/mcp_cmd.py`
- [X] T059 [US5] Register mcp command group (install, verify subcommands) in `src/dev_stack/cli/main.py`
- [X] T060 [US5] Contract test: validate mcp install --json and mcp verify --json output schemas in `tests/contract/test_cli_json_output.py`

**Checkpoint**: All MCP servers configured and verifiable for any supported agent

---

## Phase 10: User Story 6 — Repository Visualization (Priority: P3)

**Goal**: `dev-stack visualize` generates D2 architecture diagrams showing entry points, feature blocks, and flows — using coding agents (not API calls) as the AI backbone, inspired by the noodles pipeline

**Independent Test**: Run `dev-stack visualize` on a repo with source code, verify D2 diagrams generated with correct node types; modify a file, run `dev-stack visualize --incremental`, verify only changed nodes regenerated

### Implementation for User Story 6

- [X] T061 [P] [US6] Implement source file scanner: walk directory (respect .gitignore), concatenate files with line-numbered format per R-001 step 1 in `src/dev_stack/visualization/scanner.py`
- [X] T062 [P] [US6] Create overview D2 template with shape/color/status conventions (oval=entry, rect=feature, diamond=end) per R-001 in `src/dev_stack/visualization/templates/overview.d2`
- [X] T063 [US6] Implement agent-driven schema generation: construct noodles-inspired overview prompt, invoke AgentBridge, parse JSON response with nodes/flows per R-001 step 2 in `src/dev_stack/visualization/schema_gen.py`
- [X] T064 [US6] Implement JSON-to-D2 generator: deterministic conversion of node/flow schema to D2 text with shapes, colors, tooltips, status tags per R-001 step 3 in `src/dev_stack/visualization/d2_gen.py`
- [X] T065 [US6] Implement incremental update: manifest comparison (.dev-stack/viz/manifest.json), detect changed files, re-generate only affected nodes per R-001 step 4 in `src/dev_stack/visualization/incremental.py`
- [X] T066 [US6] Implement VisualizationModule (install: check d2 CLI, create output dir; verify: d2 available; update: refresh templates) in `src/dev_stack/modules/visualization.py`
- [X] T067 [US6] Implement visualize command: scan → schema_gen → d2_gen → d2 CLI render, with --incremental, --output, --format flags per cli-contract.md in `src/dev_stack/cli/visualize_cmd.py`
- [X] T068 [US6] Register visualize command in CLI group in `src/dev_stack/cli/main.py`
- [X] T069 [US6] Unit test for D2 generation: deterministic JSON→D2 output, node types, flow edges, status tags in `tests/unit/test_d2_gen.py`
- [X] T080 [US6] Implement visualization fallback on agent failure: use last known good diagram from `.dev-stack/viz/` cache, report failure without blocking commit pipeline per Edge Case 6, in `src/dev_stack/visualization/schema_gen.py`

**Checkpoint**: Full visualization pipeline operational — scan, analyze, render, incremental update

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Remaining modules, status command, and final validation across all stories

- [X] T070 [P] Implement status command: read manifest, check each module health via verify(), display summary with rich formatting per cli-contract.md in `src/dev_stack/cli/status_cmd.py` and register in `src/dev_stack/cli/main.py`
- [X] T071 [P] Implement CIWorkflowsModule (install: generate .github/workflows/dev-stack-*.yml with per-job justification comments per FR-031/032) in `src/dev_stack/modules/ci_workflows.py`
- [X] T072 [P] Implement DockerModule (install: generate Dockerfile + docker-compose.yml + .dockerignore from templates) in `src/dev_stack/modules/docker.py`
- [X] T073 [P] Create CI workflow templates (multi-platform test, deploy, vulnerability scan) with justification comments in `templates/ci/`
- [X] T074 [P] Create Docker templates (Dockerfile with full pipeline deps, docker-compose.yml, .dockerignore) in `templates/docker/`
- [X] T075 Contract test: verify all ModuleBase subclasses implement install/uninstall/update/verify correctly per module-contract.md in `tests/contract/test_module_interface.py`
- [X] T076 Run quickstart.md end-to-end validation: greenfield init, brownfield init, mcp install, visualize, status — validating SC-001 (init <5min), SC-002 (zero unintended overwrites), SC-003 (pipeline timing), SC-007 (module independence), SC-010 (Docker reproducibility)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational (Phase 2)
- **US2 (Phase 4)**: Depends on Foundational (Phase 2); benefits from US1 init command existing
- **US4 (Phase 5)**: Depends on Foundational (Phase 2), specifically AgentBridge (T010)
- **US8 (Phase 6)**: Depends on US4 pipeline infrastructure (Phase 5, specifically T039)
- **US3 (Phase 7)**: Depends on Foundational (Phase 2); benefits from US2 brownfield logic
- **US7 (Phase 8)**: Depends on Foundational (Phase 2), specifically ModuleBase (T008)
- **US5 (Phase 9)**: Depends on Foundational (Phase 2), specifically ModuleBase (T008)
- **US6 (Phase 10)**: Depends on Foundational (Phase 2), specifically AgentBridge (T010)
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P1)**: Can start after Phase 2 — extends init_cmd.py from US1 but is independently testable
- **US4 (P2)**: Can start after Phase 2 — independent of US1/US2
- **US8 (P2)**: Requires US4 PipelineRunner (T039) — builds on pipeline infrastructure
- **US3 (P2)**: Can start after Phase 2 — reuses brownfield/conflict.py from Phase 2
- **US7 (P2)**: Can start after Phase 2 — independent
- **US5 (P3)**: Can start after Phase 2 — independent
- **US6 (P3)**: Can start after Phase 2 — independent

### Within Each User Story

- Templates/config before module implementation
- Module implementation before CLI command
- CLI command before tests
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1**: T003, T004, T005 can run in parallel
**Phase 2**: T007, T008, T009, T011, T012 can run in parallel; T015, T016, T017 in parallel (after their source tasks)
**After Phase 2**: US1 + US2 can proceed in parallel; US4 + US7 + US5 + US6 can proceed in parallel
**Phase 5**: T034, T035, T036, T042 can run in parallel (independent stage implementations and template creation)
**Phase 10**: T061, T062 can run in parallel
**Phase 11**: T070, T071, T072, T073, T074 all can run in parallel

---

## Parallel Example: User Story 1

```bash
# After Phase 2 completes, launch US1 templates in parallel:
Task T018: "Implement HooksModule in src/dev_stack/modules/hooks.py"
Task T019: "Create pre-commit hook template in templates/hooks/pre-commit"
Task T020: "Create pre-commit config template in templates/hooks/pre-commit-config.yaml"

# Then sequentially:
Task T021: "Module resolver in src/dev_stack/modules/__init__.py"
Task T022: "Init command in src/dev_stack/cli/init_cmd.py"
Task T023: "Register init in src/dev_stack/cli/main.py"

# Then tests in parallel:
Task T024: "Contract test in tests/contract/test_cli_json_output.py"
Task T025: "Integration test in tests/integration/test_init_greenfield.py"
```

---

## Parallel Example: User Story 6

```bash
# After Phase 2 completes, launch scanner and template in parallel:
Task T061: "Source file scanner in src/dev_stack/visualization/scanner.py"
Task T062: "Overview D2 template in src/dev_stack/visualization/templates/overview.d2"

# Then sequentially (each depends on previous):
Task T063: "Schema generation in src/dev_stack/visualization/schema_gen.py"
Task T064: "D2 generator in src/dev_stack/visualization/d2_gen.py"
Task T065: "Incremental update in src/dev_stack/visualization/incremental.py"
Task T066: "VisualizationModule in src/dev_stack/modules/visualization.py"
Task T067: "Visualize command in src/dev_stack/cli/visualize_cmd.py"
Task T068: "Register command in src/dev_stack/cli/main.py"
Task T069: "Unit test in tests/unit/test_d2_gen.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T005)
2. Complete Phase 2: Foundational (T006–T017) — **CRITICAL, blocks everything**
3. Complete Phase 3: User Story 1 (T018–T025, T079)
4. **STOP and VALIDATE**: Run `dev-stack init` in an empty repo, verify full output
5. Deploy/demo if ready — **26 tasks to MVP**

### Incremental Delivery

1. Setup + Foundational → Foundation ready (**17 tasks**)
2. Add US1 → Greenfield init works → Demo (**+9 = 26 tasks**)
3. Add US2 → Brownfield init + rollback works → Demo (**+7 = 33 tasks**)
4. Add US4 → Pre-commit pipeline works → Demo (**+11 = 44 tasks**)
5. Add US8 → Commit messages as AI memory → Demo (**+4 = 48 tasks**)
6. Add US3 → Stack update lifecycle complete → Demo (**+5 = 53 tasks**)
7. Add US7 → Spec Kit integrated → Demo (**+4 = 57 tasks**)
8. Add US5 → MCP servers configured → Demo (**+6 = 63 tasks**)
9. Add US6 → Visualization operational → Demo (**+10 = 73 tasks**)
10. Polish → CI, Docker, status, validation → Complete (**+7 = 80 tasks**)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (Phase 1-2)
2. Once Foundational is done:
   - Developer A: US1 (greenfield) → US2 (brownfield) → US3 (update)
   - Developer B: US4 (pipeline) → US8 (commit agent)
   - Developer C: US7 (spec kit) → US5 (MCP servers) → US6 (visualization)
3. All converge for Phase 11 (Polish)
