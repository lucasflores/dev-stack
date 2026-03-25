# Feature Specification: Remove SpecKit Module — Consolidate Under APM

**Feature Branch**: `014-apm-module-swap`  
**Created**: 2026-03-24  
**Status**: Draft  
**Input**: User description: "Remove the speckit module from dev-stack and consolidate all agent-package management under the existing APM module."  
**Prior Art**: [feasibility-apm-replaces-speckit.md](../feasibility-apm-replaces-speckit.md)

## Clarifications

### Session 2026-03-24

- Q: When `dev-stack update` encounters `[modules.speckit]` in `dev-stack.toml`, what should happen to that TOML section? → A: Mark it deprecated (add `deprecated = true`) but keep it in the file.
- Q: Should Agency reviewer and LazySpecKit entries in the default `apm.yml` template be pinned to a specific git ref or track the default branch? → A: Pin to a specific git tag or commit SHA for reproducible installs.
- Q: Should migration clean up on-disk artifacts previously created by the speckit module (e.g., `.dev-stack/bin/specify` shim, `.lazyspeckit/` directory)? → A: No cleanup — leave existing artifacts on disk; they are inert and do not interfere.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New Project Initialization (Priority: P1)

A developer runs `dev-stack init` on a fresh, empty directory to bootstrap a new project. Today this command sets up the APM module and the speckit module together. After this change, `dev-stack init` sets up only the APM module, which now declares all agent dependencies (Agency reviewers, LazySpecKit prompts and reviewers, MCP servers) through an expanded `apm.yml` manifest. The developer then runs `specify init --here --ai copilot` once to scaffold the `.specify/` directory — a post-init step documented in the README.

**Why this priority**: This is the primary user-facing workflow. If greenfield initialization breaks, no new project can be created.

**Independent Test**: Run `dev-stack init` on a clean directory and verify that the `apm.yml` file is created with all expected dependencies (Agency reviewers, LazySpecKit prompts/reviewers, MCP servers), that the speckit module is not installed, and that no vendored template files are copied into the project.

**Acceptance Scenarios**:

1. **Given** a fresh empty directory, **When** the developer runs `dev-stack init`, **Then** an `apm.yml` manifest is created containing Agency reviewer entries, LazySpecKit prompt/reviewer entries, and MCP server entries — and no speckit-related files or directories are created.
2. **Given** a successfully initialized project, **When** the developer runs `specify init --here --ai copilot`, **Then** the `.specify/` template directory is scaffolded with the constitution, plan/spec/tasks/checklist templates, and bash scripts.
3. **Given** a successfully initialized project, **When** the developer inspects the `dev-stack.toml` manifest, **Then** there is no `[modules.speckit]` section present.

---

### User Story 2 - Existing Project Update with speckit Module (Priority: P1)

A developer working on an existing downstream project has `[modules.speckit]` in their `dev-stack.toml`. They run `dev-stack update` after upgrading dev-stack to the new version. The update command detects the removed speckit module and skips it gracefully — no crash, no traceback, just an informational message.

**Why this priority**: Breaking existing projects on update is a critical regression. This is equal priority to P1 because many active projects carry a speckit entry in their manifest.

**Independent Test**: Create a `dev-stack.toml` containing `[modules.speckit]` with `installed = true`, then run `dev-stack update` and verify it completes without error and logs a message indicating the speckit module has been retired.

**Acceptance Scenarios**:

1. **Given** a project with `[modules.speckit]` in `dev-stack.toml`, **When** the developer runs `dev-stack update`, **Then** the command completes successfully without error.
2. **Given** a project with `[modules.speckit]` in `dev-stack.toml`, **When** the developer runs `dev-stack update`, **Then** an informational message is displayed explaining that the speckit module has been removed and its functionality is now provided by APM and `specify init`.
3. **Given** a project with `[modules.speckit]` and `[modules.apm]` in `dev-stack.toml`, **When** the update completes, **Then** the `apm.yml` manifest includes the Agency reviewer and LazySpecKit entries that were previously provided by the speckit module. *(Note: This scenario only applies when the APM module is also installed in the project.)*
4. **Given** a project with `[modules.speckit]` in `dev-stack.toml`, **When** the update completes, **Then** the `[modules.speckit]` section is marked with `deprecated = true` but remains in the file (not deleted).

---

### User Story 3 - Module Registry Reflects Removal (Priority: P2)

A developer or an automated pipeline queries the list of available modules in dev-stack (e.g., via default module lists or help output). The speckit module no longer appears as an available or default module.

**Why this priority**: Correctness of the module registry is important but secondary to the init/update workflows. Stale references are confusing but not blocking.

**Independent Test**: Inspect `DEFAULT_GREENFIELD_MODULES` and `DEFAULT_MODULES` constants and verify neither contains `speckit`.

**Acceptance Scenarios**:

1. **Given** the dev-stack codebase, **When** a developer inspects the default module registry, **Then** `speckit` does not appear in `DEFAULT_GREENFIELD_MODULES` or `DEFAULT_MODULES`.
2. **Given** the dev-stack codebase, **When** a developer runs `dev-stack init` with default settings, **Then** only the modules listed in `DEFAULT_GREENFIELD_MODULES` (minus speckit) are installed.

---

### User Story 4 - APM Manages All Agent Dependencies (Priority: P2)

A developer runs `apm install` (or it runs as part of `dev-stack init`) and the expanded `apm.yml` fetches Agency reviewers, LazySpecKit prompts and reviewers, and MCP servers — everything the speckit module used to install, except the `.specify/` template tree.

**Why this priority**: This validates that APM fully replaces speckit's dependency management. Without it, users lose access to reviewers and prompts after the module is removed.

**Independent Test**: Run `apm install` with the new default `apm.yml` and verify that Agency reviewers, LazySpecKit prompt, LazySpecKit reviewers, and MCP servers are all resolved and installed.

**Acceptance Scenarios**:

1. **Given** the default `apm.yml` template, **When** `apm install` runs, **Then** all five Agency reviewers are fetched and installed.
2. **Given** the default `apm.yml` template, **When** `apm install` runs, **Then** LazySpecKit prompts and reviewers are fetched and installed.
3. **Given** the default `apm.yml` template, **When** `apm install` runs, **Then** all declared MCP servers are fetched and installed.

---

### User Story 5 - README Documents Post-Init Step (Priority: P3)

A new developer reads the README and understands that after running `dev-stack init`, they need to run `specify init --here --ai copilot` to set up the SpecKit template directory. The instructions are clear, positioned in the setup section, and explain why this step is separate.

**Why this priority**: Documentation is important for onboarding but does not affect functional correctness. Developers familiar with the tool may not read the README.

**Independent Test**: Read the README and verify the post-init `specify init` instruction is documented with a clear explanation.

**Acceptance Scenarios**:

1. **Given** the project README, **When** a developer reads the setup/quickstart section, **Then** they find a clearly documented post-init step for running `specify init --here --ai copilot`.
2. **Given** the project README, **When** a developer follows the documented steps in order, **Then** they have a fully functional dev-stack project with all agent dependencies and the `.specify/` template tree.

---

### Edge Cases

- What happens when a project has `[modules.speckit]` in `dev-stack.toml` but speckit was never actually installed (e.g., `installed = false`)? The update command should skip it without error.
- What happens when `dev-stack update` runs on a project that has no speckit entry at all? No migration message is shown; the update proceeds normally.
- What happens when the `apm.yml` already contains some of the dependencies that the expanded template would add (e.g., user manually added Agency reviewers)? APM deduplicates entries; no duplicate installs.
- What happens when a user runs an older version of dev-stack against a project that was initialized with the new version (no speckit in manifest)? The older version should not crash — it simply won't know about speckit and will proceed with the modules it does know about.
- What happens when the upstream Agency or LazySpecKit repositories change their file structure? All entries are pinned to specific git tags or commit SHAs in the `apm.yml` template, so upstream changes do not affect existing installs; users update at their own pace by bumping the pinned ref.
- What happens to on-disk artifacts previously created by the speckit module (e.g., `.dev-stack/bin/specify` shim, `.lazyspeckit/reviewers/` directory, vendored template copies)? They are left in place — no automated cleanup. These files are inert and do not interfere with the APM-managed flow. Users may manually delete them at their discretion.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The speckit module source file, its vendored template directories (`speckit/` and `lazyspeckit/` under the templates directory), and all associated test files MUST be removed from the codebase.
- **FR-002**: The default `apm.yml` template MUST be expanded to declare Agency reviewers (5 entries from `msitarzewski/agency-agents`), LazySpecKit prompts, and LazySpecKit reviewers as APM dependencies. All entries MUST be pinned to a specific git tag or commit SHA (e.g., `#v0.7.3` or `#abc1234`) for reproducible installs.
- **FR-003**: The module registry defaults (`DEFAULT_GREENFIELD_MODULES` and `DEFAULT_MODULES`) MUST be updated to exclude `speckit`.
- **FR-004**: The `dev-stack update` command MUST detect a `[modules.speckit]` entry in existing `dev-stack.toml` files, skip it gracefully with an informational message, and mark the section with `deprecated = true` while retaining it in the file — without raising an error or traceback.
- **FR-005**: The `dev-stack init` command MUST continue to work for greenfield projects — APM handles all agent dependency installation that speckit previously handled.
- **FR-006**: The project README MUST be updated to include a post-init instruction for running `specify init --here --ai copilot` to scaffold the `.specify/` directory.
- **FR-007**: The `apm.yml` template MUST continue to declare MCP server dependencies (no regression from current APM module behavior).
- **FR-008**: All import references and internal wiring that reference the speckit module (e.g., module registry, module factory, init pipeline) MUST be removed or updated.
- **FR-009**: The migration handling MUST ensure that downstream projects can run `dev-stack update` cleanly after the speckit module is removed.
- **FR-010**: The APM minimum version requirement (0.8.0+) MUST be maintained.

### Key Entities

- **Module Registry**: The central catalog defining which modules are available and which are installed by default for greenfield and brownfield projects. The speckit entry must be removed.
- **`apm.yml` Manifest**: The declarative configuration file that APM uses to resolve, install, and manage agent dependencies. It must be expanded to absorb all dependencies previously handled by the speckit module.
- **`dev-stack.toml` Project Manifest**: Per-project configuration file that tracks which modules are installed. Existing files with `[modules.speckit]` must be handled gracefully during updates.
- **Migration Handler**: Logic within the update pipeline that detects removed or deprecated modules, marks them with `deprecated = true` in `dev-stack.toml`, and provides a smooth upgrade path with user-facing messages.

### Assumptions

- The `specify init` CLI command (from the upstream `spec-kit` package) is the canonical, idempotent installer for the `.specify/` template tree. Dev-stack does not need to replicate this functionality.
- Users install `specify-cli` independently via `uv tool install specify-cli` — this is a one-time setup documented in the README, not managed by dev-stack.
- APM v0.8.0+ is capable of resolving and installing all dependency types needed (prompts, reviewers, agents, MCP servers) from git sources.
- The five Agency reviewers are: testing-reality-checker, engineering-security-engineer, testing-performance-benchmarker, testing-accessibility-auditor, and engineering-backend-architect.
- LazySpecKit provides at minimum: one prompt file (`LazySpecKit.prompt.md`) and two reviewer files (`code-quality.md`, `test.md`).
- Downstream projects use `dev-stack.toml` and may have `[modules.speckit]` entries that must survive the upgrade without manual intervention.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `dev-stack init` on a fresh directory completes successfully and produces a project with an `apm.yml` containing all previously speckit-managed dependencies — in under 60 seconds on a standard connection.
- **SC-002**: `dev-stack update` on an existing project with `[modules.speckit]` completes without error and displays a clear migration message.
- **SC-003**: The net codebase reduction is approximately 3,600+ lines (module source ~370, vendored speckit templates ~2,117, vendored LazySpecKit templates ~946, and tests ~206 removed).
- **SC-004**: All existing dev-stack tests pass after the removal, with no test failures unrelated to expected deletions.
- **SC-005**: A developer following the README instructions can go from zero to a fully functional project (with `.specify/` directory) in under 5 minutes.
- **SC-006**: Running `apm install` with the expanded `apm.yml` installs all Agency reviewers, LazySpecKit files, and MCP servers that were previously managed by the speckit module — zero missing dependencies.
