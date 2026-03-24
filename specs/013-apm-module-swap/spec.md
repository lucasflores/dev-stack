# Feature Specification: APM Module Swap

**Feature Branch**: `013-apm-module-swap`  
**Created**: 2026-03-24  
**Status**: Draft  
**Input**: User description: "Replace mcp_servers module with apm module that delegates MCP server management to Microsoft's Agent Package Manager (APM) CLI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — APM-Based MCP Server Installation (Priority: P1)

A developer initializes a new dev-stack project. Instead of dev-stack rendering MCP server config files from internal JSON templates, the system bootstraps an `apm.yml` manifest seeded with the same 5 default servers (context7, github, sequential-thinking, huggingface, notebooklm) and runs APM CLI commands to deploy MCP server declarations into agent-native directories.

**Why this priority**: This is the core replacement — without it, there is no migration path away from the `mcp_servers` module. It delivers the primary value of delegating server management to APM.

**Independent Test**: Can be tested by running `dev-stack init` in a fresh project directory and verifying that an `apm.yml` manifest exists with the 5 default servers and that agent-specific config directories (e.g., `.claude/`, `.github/`) contain the expected MCP server declarations produced by APM.

**Acceptance Scenarios**:

1. **Given** a new project directory with no existing configuration, **When** the user runs `dev-stack init`, **Then** an `apm.yml` manifest is created at the project root containing the 5 default MCP server packages.
2. **Given** a freshly initialized `apm.yml` manifest, **When** the init pipeline invokes the `apm` module, **Then** APM installs all default servers and writes agent-native config files to the appropriate directories.
3. **Given** the APM CLI is not installed or not on PATH, **When** the user runs `dev-stack init`, **Then** the system provides a clear error message with instructions to install APM.

---

### User Story 2 — Lockfile-Based Reproducibility (Priority: P2)

A developer clones an existing dev-stack project on a new machine. They run `dev-stack init` and APM resolves the exact package versions from the `apm.lock.yaml` lockfile, producing an identical MCP server configuration to what every other contributor has.

**Why this priority**: Reproducibility across machines is a key advantage over the template approach and delivers immediate value to teams.

**Independent Test**: Can be tested by initializing a project, committing the lockfile, then cloning to a separate directory and running init — the resulting agent config files should be byte-identical.

**Acceptance Scenarios**:

1. **Given** a project with an existing `apm.yml` and `apm.lock.yaml`, **When** a developer runs `dev-stack init`, **Then** APM installs the exact versions pinned in the lockfile.
2. **Given** two machines with the same lockfile, **When** both run the apm module, **Then** the resulting MCP server config files are identical.

---

### User Story 3 — Custom Community Package Installation (Priority: P2)

A developer wants to add a community-contributed MCP server that is not in dev-stack's default set. They add the package name to their `apm.yml` manifest and run `dev-stack init` (or the apm module directly). APM resolves it from the git-based package registry and installs it alongside the defaults.

**Why this priority**: Access to the community ecosystem is a major motivator for adopting APM and differentiates this approach from the hardcoded template model.

**Independent Test**: Can be tested by adding a known community package to `apm.yml` and verifying it appears in the agent config output after installation.

**Acceptance Scenarios**:

1. **Given** an `apm.yml` with an additional community package beyond the defaults, **When** the apm module runs, **Then** the community package is installed and appears in the agent-native config files.
2. **Given** a package name that does not exist in the APM registry, **When** installation is attempted, **Then** the user receives a clear error identifying the unknown package.

---

### User Story 4 — Deprecation of Legacy mcp_servers Module (Priority: P3)

A developer who has been using the legacy `mcp_servers` module upgrades dev-stack. The `mcp_servers` module is no longer part of the default init flow. If their `dev-stack.toml` manifest explicitly lists `mcp-servers`, it still works (opt-in), but new projects use the `apm` module by default.

**Why this priority**: Backward compatibility is important but secondary to delivering the new capability. Users with existing workflows should not break.

**Independent Test**: Can be tested by upgrading dev-stack in a project that explicitly enables `mcp-servers` in its manifest and verifying it still functions, then testing a fresh init to confirm the apm module is used instead.

**Acceptance Scenarios**:

1. **Given** an existing project with `mcp-servers` explicitly listed in `dev-stack.toml`, **When** the user runs `dev-stack init` after upgrading, **Then** the legacy `mcp_servers` module executes as before.
2. **Given** a new project with no modules specified, **When** `dev-stack init` runs, **Then** the `apm` module is used instead of `mcp_servers`.
3. **Given** a project using the legacy module, **When** the user runs init, **Then** a deprecation warning is displayed recommending migration to the `apm` module.

---

### User Story 5 — Security Auditing of MCP Configurations (Priority: P3)

A security-conscious developer wants to audit their MCP server configurations for hidden Unicode characters or compromised packages. They run `dev-stack apm audit` which invokes APM's audit capability and receive a report of any findings.

**Why this priority**: Security auditing is a valuable addition but is not blocking for the core migration. It adds a layer of trust that the template approach lacked.

**Independent Test**: Can be tested by running the audit command against a known-clean configuration and against a configuration with a deliberately suspicious entry, verifying the report reflects each case accurately.

**Acceptance Scenarios**:

1. **Given** a project with installed MCP server packages, **When** the user runs the audit command, **Then** APM scans the configuration and reports any findings (clean or flagged).
2. **Given** a clean set of MCP server configurations, **When** audit is run, **Then** the report indicates no issues found.

---

### Edge Cases

- What happens when `apm.yml` already exists from a previous (non-dev-stack) APM setup? The module prompts the user to choose: skip (keep existing file), merge (add missing defaults), or overwrite (replace with fresh defaults).
- What happens when the APM CLI version is too old to support required features? The module should check the version and warn the user if it is below the minimum supported version.
- What happens when APM's registry is unreachable (offline)? The module reports the network error, lists any servers that were partially installed, and suggests re-running once connectivity is restored. If a lockfile exists, it suggests using the lockfile for offline installation.
- What happens when there is a conflict between a default server package and a user-added package? The module should surface APM's conflict resolution output to the user.
- What happens when `apm.lock.yaml` is present but `apm.yml` has been modified since the lock was generated? The module should warn and suggest regenerating the lockfile.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an `apm` module that replaces `mcp_servers` as the default mechanism for MCP server configuration during `dev-stack init`.
- **FR-002**: The `apm` module MUST bootstrap an `apm.yml` manifest file at the project root when one does not already exist.
- **FR-003**: The bootstrapped `apm.yml` MUST be seeded with 5 default MCP server packages: context7, github, sequential-thinking, huggingface, and notebooklm.
- **FR-004**: The `apm` module MUST invoke the APM CLI to install MCP server declarations into agent-native directories (e.g., `.claude/`, `.github/`, `.cursor/`, `.opencode/`).
- **FR-005**: The `apm` module MUST ensure that `apm install` generates an `apm.lock.yaml` lockfile that pins exact versions of installed packages after installation.
- **FR-006**: The `apm` module MUST detect when the APM CLI is not available on PATH and report a clear, actionable error message.
- **FR-007**: The `apm` module MUST check that the installed APM CLI version meets the minimum supported version and warn the user if it does not.
- **FR-008**: Users MUST be able to add community-contributed APM packages to their `apm.yml` and have them installed alongside the defaults.
- **FR-009**: The `apm` module MUST support APM's `apm audit` capability to scan MCP server configurations for security issues (hidden Unicode characters, compromised packages).
- **FR-010**: The `mcp_servers` module MUST be removed from the default module set (`DEFAULT_GREENFIELD_MODULES`) and replaced by the `apm` module.
- **FR-011**: The `mcp_servers` module MUST remain functional when explicitly listed in a project's `dev-stack.toml` manifest (opt-in backward compatibility).
- **FR-012**: When the legacy `mcp_servers` module is explicitly invoked, the system MUST display a deprecation warning recommending migration to the `apm` module.
- **FR-013**: When `apm.yml` already exists, the `apm` module MUST prompt the user to choose one of three actions: skip (use existing file as-is), merge (additively insert missing defaults), or overwrite (replace with fresh defaults). The module MUST NOT silently overwrite user customizations. In non-interactive environments (e.g., CI), the module MUST default to "skip" to preserve brownfield safety. The merge operation MUST identify servers by name regardless of format (registry URI vs self-defined dict) to avoid duplicates.
- **FR-014**: The `apm` module MUST surface actionable error messages when APM package resolution or registry access fails. Error messages MUST include the failed package name and a suggestion (e.g., check spelling, verify registry access).
- **FR-015**: When APM installation fails mid-way (e.g., network timeout after partial install), the module MUST report which servers succeeded and which failed, leave the partial state intact, and allow the user to re-run to complete installation (fail-forward, no rollback).
- **FR-016**: The `apm` module MUST expose explicit CLI subcommands (`dev-stack apm install`, `dev-stack apm audit`) in addition to running automatically during `dev-stack init`, mirroring the existing `dev-stack mcp` subcommand pattern.

### Key Entities

- **APM Manifest (`apm.yml`)**: The declarative file listing MCP server packages to install. Created at project root, seeded with defaults, extensible by users.
- **APM Lockfile (`apm.lock.yaml`)**: Generated by APM after installation. Pins exact package versions for reproducible installations across machines.
- **APM Module**: The new dev-stack module that orchestrates APM CLI commands (`apm init`, `apm install`, `apm audit`) as part of the init pipeline.
- **MCP Servers Module (legacy)**: The existing module (~270 LOC) that renders agent-specific config files from internal JSON templates. Deprecated and removed from defaults, available via opt-in.
- **Default Server Set**: The 5 MCP server packages (context7, github, sequential-thinking, huggingface, notebooklm) seeded into every new `apm.yml`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running `dev-stack init` in a new project produces a valid `apm.yml` with the 5 default servers and an `apm.lock.yaml` lockfile — no internal JSON templates are used.
- **SC-002**: Agent-native MCP config files (`.claude/`, `.github/`, etc.) are produced by APM, not by dev-stack template rendering.
- **SC-003**: Two separate machines with the same `apm.lock.yaml` produce identical MCP server configurations after running init.
- **SC-004**: Users can add any APM-compatible community package to `apm.yml` and have it installed alongside defaults without modifying dev-stack source code.
- **SC-005**: The `mcp_servers` module no longer executes during default init; it functions only when explicitly opted into via `dev-stack.toml`.
- **SC-006**: Running `dev-stack apm audit` correctly invokes `apm audit`, passes format/output arguments through to APM, and surfaces APM's exit code and report content to the user.
- **SC-007**: The ~270 LOC `mcp_servers` module is no longer on the default code path for new projects. MCP config rendering is fully delegated to APM for default installations.

## Assumptions

- The APM CLI is publicly available and can be installed by users independently (e.g., via npm or a standalone binary). Dev-stack does not bundle or auto-install APM.
- APM's git-based package registry contains entries for the 5 default MCP server packages that dev-stack currently supports.
- APM's `apm.yml` format supports specifying packages by name in a way that the `apm install` command can resolve from the registry.
- APM produces an `apm.lock.yaml` (or equivalent lockfile) deterministically, enabling reproducible installs.
- The APM CLI supports a version check mechanism (e.g., `apm --version`) that dev-stack can invoke to verify compatibility.
- Dev-stack's existing `ModuleBase` protocol and module registry can accommodate the new `apm` module without architectural changes.

## Clarifications

### Session 2025-03-24

- Q: When APM CLI fails mid-install, how should the module behave? → A: Fail-forward — report which servers succeeded/failed, leave partial state, let user re-run (no rollback).
- Q: Should APM operations only run implicitly during init, or also via dedicated CLI subcommands? → A: Both — run during `dev-stack init` and provide explicit `dev-stack apm install` / `dev-stack apm audit` subcommands, matching the existing `dev-stack mcp` pattern.
- Q: When `apm.yml` already exists at init time, what should the module do? → A: Prompt the user to choose: skip (use existing), merge (add missing defaults), or overwrite (replace with fresh defaults).

## Out of Scope

- Packaging dev-stack's own assets (agent instructions, prompts, skills, reviewers) as APM packages — this is a planned follow-on effort.
- Auto-installing the APM CLI if it is not found on PATH. Users are responsible for installing APM independently.
- Migrating existing projects from `mcp_servers` to `apm` automatically. Users migrating must manually update their `dev-stack.toml` or re-init.
- Supporting APM server management beyond the init pipeline (e.g., runtime MCP server orchestration or live hot-reloading of server configs).
