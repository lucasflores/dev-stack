# Feature Specification: Dev-Stack Ecosystem

**Feature Branch**: `001-dev-stack-ecosystem`  
**Created**: 2026-02-10  
**Status**: Draft  
**Input**: User description: "Develop a green/brownfield dev stack ecosystem that initializes or augments repositories with full automation and AI capabilities"

## Clarifications

### Session 2026-02-10

- Q: How should the stack handle MCP server credentials (API tokens for GitHub, Hugging Face, NotebookLM)? → A: Environment variables only — no secrets written to any file. Stack validates required env vars are set and fails fast with instructions if missing.
- Q: What format and location should the Stack Manifest use? → A: `dev-stack.toml` at the repository root, TOML format, single file.
- Q: What pipeline performance targets apply for projects larger than 50 source files? → A: Linear scaling cap: ≤2 min for ≤200 files, ≤5 min for ≤500 files. Beyond 500 files, stages 1–3 parallelize and wall-clock time is reported.
- Q: How are coding agents invoked by generative pipeline stages (docs, infra sync, commit message, visualization)? → A: Shell out to the user's installed coding agent CLI (e.g., `claude`, `copilot`), auto-detected. No direct LLM API calls.
- Q: How should the rollback mechanism store pre-operation state? → A: Git-based — lightweight git tag (`dev-stack/rollback/<timestamp>`) before each `init`/`update`; rollback restores via `git checkout <ref> -- .`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Initialize a New Repository (Priority: P1)

A developer starts a brand-new project and wants the full dev-stack automation suite from the very first commit. They run a single CLI command that scaffolds the repository with pre-commit automation entrypoints, MCP server configurations, container templates, CI workflows, Spec Kit integration, and visualization tooling—all wired together and ready to use.

**Why this priority**: This is the foundational capability. Without `init`, nothing else in the ecosystem exists. It is the single entry point that materializes the entire value proposition.

**Independent Test**: Run `dev-stack init` in an empty directory and verify that all expected automation files and configurations are generated. Confirm a subsequent `git commit` triggers the full pre-commit pipeline.

**Acceptance Scenarios**:

1. **Given** an empty directory with no git repository, **When** the user runs `dev-stack init`, **Then** the system creates a git repository, scaffolds all automation files (pre-commit automation, container templates, CI workflows, MCP config, Spec Kit structure), and confirms success with a structured summary.
2. **Given** an empty directory, **When** the user runs `dev-stack init` with interactive mode, **Then** the system prompts the user to select which capability modules to install (pre-commit automation, CI, containerization, MCP servers, visualization) and only installs selected modules.
3. **Given** an empty directory, **When** `dev-stack init` completes, **Then** a subsequent `git add . && git commit` triggers the pre-commit pipeline (lint, test, security, docs, commit message) without errors.
4. **Given** an empty directory, **When** `dev-stack init --json` is run, **Then** the output is valid JSON containing all paths and configuration choices for machine consumption.

---

### User Story 2 — Initialize an Existing Repository (Brownfield) (Priority: P1)

A developer has an existing project with its own configuration files (linter configs, Dockerfiles, CI workflows). They want to add dev-stack capabilities without losing their existing customizations. The CLI detects conflicts, presents diffs, and lets the user approve or skip each change.

**Why this priority**: Brownfield adoption is equally critical—most real-world usage will be augmenting existing repos, not greenfield. If the tool destroys existing setups, no one will trust it.

**Independent Test**: Run `dev-stack init` in a repository that already has a Dockerfile, `.github/workflows/`, and linter configs. Verify the system surfaces every conflict and writes nothing without explicit user consent.

**Acceptance Scenarios**:

1. **Given** a repository with an existing Dockerfile, **When** the user runs `dev-stack init`, **Then** the system detects the existing Dockerfile, shows a diff of proposed changes, and asks for confirmation before writing.
2. **Given** a repository with existing CI workflows, **When** conflicts are detected, **Then** the system presents a per-file accept/skip/merge prompt and respects the user's choices.
3. **Given** a repository with custom linter configs, **When** `dev-stack init` completes, **Then** the user's original linter settings are preserved (stack-managed sections are clearly delimited with marker comments).
4. **Given** a brownfield init completes, **When** the user decides to undo, **Then** a rollback command restores all files to their pre-init state.

---

### User Story 3 — Update Stack (Priority: P2)

The dev-stack project evolves over time with new automations, new pre-commit triggers, and new integrations. A developer who previously ran `init` wants to fold in these new capabilities without losing their customizations or overwriting manually tuned configurations.

**Why this priority**: Without a safe update path, users are stuck on the version they initialized with. This is the lifecycle management capability that makes the ecosystem sustainable.

**Independent Test**: Initialize a repo with v1 of the stack, then run `dev-stack update` against a v2 that adds a new pipeline trigger and modifies the container template. Verify the new trigger is added, the container change is presented as a diff requiring approval, and no existing user customizations are lost.

**Acceptance Scenarios**:

1. **Given** a repository initialized with dev-stack v1, **When** the user runs `dev-stack update`, **Then** the system compares current files against the latest stack version and presents a summary of additions, modifications, and removals.
2. **Given** the update summary is presented, **When** the user approves changes, **Then** new files are added, modified files are merged respecting marker-delimited user sections, and a changelog entry is written.
3. **Given** the update includes a new pre-commit trigger, **When** the update completes, **Then** the new trigger is installed and functional in the pre-commit pipeline without disturbing existing automation.
4. **Given** an update fails mid-way, **When** the user re-runs `dev-stack update`, **Then** the system detects the incomplete state and offers to resume or rollback.

---

### User Story 4 — Pre-Commit Automation Pipeline (Priority: P2)

A developer makes code changes and runs `git commit`. The pre-commit pipeline automatically runs linting, tests, security audits, documentation generation, infrastructure sync, and commit message generation—in that order. Failures in hard gates block the commit; failures in generative stages warn but allow override.

**Why this priority**: This is the core automation value loop. It transforms every commit into a quality-assured, well-documented, AI-memory-enriched checkpoint.

**Independent Test**: Make a code change, stage it, and run `git commit`. Verify each pipeline stage executes in order, lint/test/security failures block the commit, and the documentation and commit message agents produce valid output.

**Acceptance Scenarios**:

1. **Given** staged changes with a linting error, **When** the user runs `git commit`, **Then** the pipeline halts at the lint stage with an actionable error message and the commit is rejected.
2. **Given** staged changes that pass lint/test/security, **When** the documentation agent runs, **Then** README and relevant docs are auto-updated to reflect the pending changes.
3. **Given** all pipeline stages succeed, **When** the commit message agent runs, **Then** a structured commit message is generated containing: intent, reasoning, scope summary, spec/task references, and a narrative section optimized for future agent context retrieval.
4. **Given** the documentation agent fails, **When** the user passes `--force`, **Then** the commit proceeds with a warning logged, and the next CI run flags the skipped stage.
5. **Given** the user needs to skip pre-commit automation entirely, **When** they pass `--no-hooks`, **Then** the commit proceeds unblocked, and the next commit or CI run flags the skipped pipeline.

---

### User Story 5 — MCP Server Suite Installation (Priority: P3)

A developer wants coding agents to have access to external tools (Context7 for docs, GitHub for repo operations, sequential thinking for reasoning, Hugging Face for models, NotebookLM for research). The CLI installs and configures MCP servers that are not already present, respecting existing MCP configurations.

**Why this priority**: MCP servers are the interface layer between coding agents and external capabilities. Without them, the AI-native architecture principle is unmet—but the core pipeline can function without them initially.

**Independent Test**: Run `dev-stack init` (or `dev-stack mcp install`) in a repo with no MCP configuration. Verify all configured MCP servers are installed and reachable. Then run again in a repo that already has a Context7 MCP server configured and verify it is not overwritten.

**Acceptance Scenarios**:

1. **Given** a repository with no MCP configuration, **When** the user runs the MCP install command, **Then** configuration files for Context7, GitHub, sequential thinking, Hugging Face, and NotebookLM MCP servers are created and validated.
2. **Given** a repository with an existing Context7 MCP config, **When** the MCP install command runs, **Then** the existing Context7 config is preserved and only missing servers are added.
3. **Given** MCP servers are installed, **When** the user runs a verification command, **Then** connectivity to each configured server is tested and results are reported.

---

### User Story 6 — Repository Visualization (Priority: P3)

A developer wants to understand the architecture and data flow of their codebase at a glance. The system generates interactive diagrams (inspired by the noodles project) that show entry points, feature blocks, and code flows—using coding agents as the AI backbone rather than direct LLM API calls.

**Why this priority**: Visualization is a powerful observability tool but is not blocking for core development workflow. It enhances understanding and documentation but can be adopted incrementally.

**Independent Test**: Run the visualization command on a repository with source code. Verify structured architecture diagrams are generated showing entry points, feature blocks, and flows. Verify diagrams update incrementally when source code changes.

**Acceptance Scenarios**:

1. **Given** a repository with source code, **When** the user runs the visualization command, **Then** the system scans source files, uses a coding agent to identify entry points and flows, and generates machine-readable diagrams.
2. **Given** previously generated diagrams exist, **When** source code changes, **Then** the system detects changes and updates only affected diagram nodes (incremental update).
3. **Given** diagrams are generated, **When** the user views them, **Then** diagrams are interactive—nodes are clickable for drill-down, and tooltips show descriptions.
4. **Given** the visualization module is not installed, **When** other dev-stack features are used, **Then** they function normally without the visualization module (modularity).

---

### User Story 7 — Spec Kit Integration (Priority: P2)

A developer wants to use GitHub Spec Kit's spec-driven development workflow within the dev-stack ecosystem. The `init` command integrates Spec Kit so that `/speckit.*` commands are available, specs are stored under `.specify/`, and the constitution governs all development.

**Why this priority**: Spec Kit is the backbone of the spec-driven development principle in the constitution. It provides the structured workflow that AI agents rely on for context.

**Independent Test**: Run `dev-stack init` and verify that `.specify/` directory exists with templates, scripts, and memory. Run a `/speckit.specify` command and verify it creates a feature branch and spec file.

**Acceptance Scenarios**:

1. **Given** a new repository, **When** `dev-stack init` completes, **Then** Spec Kit is integrated with `.specify/` directory populated with templates, scripts, and the constitution.
2. **Given** Spec Kit is integrated, **When** the user runs a `/speckit.*` command, **Then** it executes correctly using the project's constitution and templates.
3. **Given** a new version of Spec Kit is available, **When** the user runs `dev-stack update`, **Then** Spec Kit templates and scripts are updated while preserving the user's constitution and custom specs.

---

### User Story 8 — Commit Message Agent as Persistent Memory (Priority: P2)

A developer commits changes, and the commit message agent generates a structured commit message that functions as persistent memory for AI agents. The message encodes intent, reasoning, scope, spec/task references, and a narrative summary optimized for future context retrieval—going far beyond conventional commit message best practices.

**Why this priority**: This is the innovation at the heart of the AI-native architecture. Rich commit history transforms version control into a queryable knowledge base that gives coding agents deep project understanding across sessions.

**Independent Test**: Make a code change, trigger the commit pipeline, and verify the generated commit message contains all structured sections. In a subsequent session, verify a coding agent can query commit history and retrieve meaningful context about past decisions and reasoning.

**Acceptance Scenarios**:

1. **Given** code changes pass all pipeline gates, **When** the commit message agent runs, **Then** the generated message includes: a conventional commit prefix (feat/fix/docs/etc.), a concise summary line, an "Intent" section explaining why the change was made, a "Reasoning" section documenting design decisions, a "Scope" section listing affected components, and "References" linking to specs/tasks.
2. **Given** a commit message is generated, **When** a coding agent retrieves project history in a future session, **Then** the structured commit messages provide sufficient context for the agent to understand the evolution of the codebase, past decisions, and the reasoning behind them.
3. **Given** the user disagrees with the generated message, **When** they edit it before confirming, **Then** the edited message is used and the agent's suggestion is logged for feedback improvement.

---

### Edge Cases

- What happens when `dev-stack init` is run inside an existing dev-stack initialized repo? The system MUST detect this and offer to re-initialize (with confirmation) or switch to `update` mode.
- What happens when the pre-commit pipeline encounters a file that is not in any supported language? The system MUST skip unsupported files gracefully and log which files were skipped.
- What happens when MCP servers are unreachable during installation? The system MUST report which servers failed, install the ones that succeeded, and provide retry instructions for failures.
- What happens when `dev-stack update` is run on a repo initialized with a much older stack version? The system MUST handle multi-version jumps by applying changes sequentially or presenting a comprehensive diff.
- What happens when the user's machine has no internet during `init`? The system MUST clearly report which components require internet (Spec Kit download, MCP server setup) and which can be installed offline (pre-commit automation, local configs).
- What happens when the visualization agent fails mid-diagram generation? The system MUST fallback to the last known good diagram and report the failure without blocking the commit pipeline.
- What happens when multiple developers on a team use different stack versions? The system MUST include a stack version marker in the repo so that version mismatches are detected and flagged.

## Requirements *(mandatory)*

### Functional Requirements

**CLI Core**

- **FR-001**: System MUST provide a `dev-stack init` command that initializes a repository with the full automation suite.
- **FR-002**: System MUST provide both interactive and non-interactive modes for `init` and `update` commands. All other CLI commands MUST support non-interactive (CI-friendly) mode.
- **FR-003**: System MUST output structured JSON when `--json` flag is passed, and human-readable text by default.
- **FR-004**: System MUST return POSIX-standard exit codes (0 success, non-zero failure with meaningful stderr).
- **FR-005**: System MUST provide a `dev-stack update` command that safely merges new stack capabilities into an existing initialized repo.

**Brownfield Safety**

- **FR-006**: The `init` command MUST scan for existing configuration files and surface all potential conflicts before writing any file.
- **FR-007**: The `update` command MUST present a per-file diff of proposed changes and require explicit user consent for modifications.
- **FR-008**: Stack-managed file sections MUST be delimited with unique marker comments to enable safe partial updates that preserve user customizations.
- **FR-009**: System MUST provide a git-based rollback mechanism: before each `init` or `update`, the stack creates a lightweight git tag (`dev-stack/rollback/<timestamp>`) capturing the pre-operation state. The `dev-stack rollback` command restores to that snapshot via `git checkout <ref> -- .` for managed files. The rollback reference is recorded in `dev-stack.toml`.

**Spec Kit Integration**

- **FR-010**: System MUST integrate GitHub Spec Kit using a hybrid strategy: the Spec Kit CLI (`specify`) is installed as an external tool via `uv tool install`, while `.specify/` templates and scripts are vendored locally into each project repository for per-project customization and offline availability.
- **FR-011**: System MUST preserve the project's constitution and custom specs when updating Spec Kit components.

**Pre-Commit Pipeline**

- **FR-012**: System MUST install pre-commit automation entrypoints that execute a 6-stage pipeline: lint → test → security audit → documentation agent → infrastructure sync → commit message agent.
- **FR-013**: Failures in stages 1–3 (lint, test, security) MUST halt the pipeline and reject the commit with actionable error output.
- **FR-014**: Failures in stages 4–6 (documentation, infra sync, commit message) MUST warn but allow the commit to proceed with a `--force` flag.
- **FR-015**: System MUST support a `--no-hooks` flag to skip the pipeline entirely, with skipped runs flagged in the next CI check.
- **FR-037**: Generative pipeline stages (4–6) and visualization MUST invoke coding agents by shelling out to the user's installed agent CLI (e.g., `claude`, `copilot`, `cursor`). The stack MUST auto-detect the available agent CLI at init time and record the choice in `dev-stack.toml`. If no agent CLI is detected, generative stages MUST be skipped with a warning.

**MCP Servers**

- **FR-016**: System MUST install and configure MCP servers for Context7, GitHub, sequential thinking, Hugging Face, and NotebookLM if not already present.
- **FR-017**: System MUST detect existing MCP configurations and skip servers that are already configured.
- **FR-018**: System MUST provide a verification command that tests connectivity to each configured MCP server.

**Containerization**

- **FR-019**: System MUST generate a Dockerfile that enables reproducible execution of the full automation pipeline.
- **FR-020**: The Dockerfile MUST be kept in sync with the stack's dependencies—updated automatically when the infrastructure sync stage detects changes.

**Visualization**

- **FR-021**: System MUST generate deterministic, text-based diagrams visualizing repository architecture, entry points, feature blocks, and code flows.
- **FR-022**: Diagram generation MUST use coding agents (via MCP or equivalent agent interfaces) as the AI backbone—not direct OpenAI/Anthropic API calls.
- **FR-023**: System MUST support incremental diagram updates (only regenerate nodes affected by code changes).

**Commit Message Agent**

- **FR-024**: The commit message agent MUST produce structured messages containing: conventional commit prefix, summary, intent, reasoning, scope, and spec/task references.
- **FR-025**: Commit messages MUST be structured to serve as persistent memory for coding agents, enabling future context retrieval from version history.
- **FR-026**: The commit message format MUST include a machine-parseable metadata section (e.g., YAML front matter or structured trailer) for programmatic retrieval by agents.

**Documentation Agent**

- **FR-027**: The documentation agent MUST auto-update README, API docs, and repository diagrams to reflect pending code changes before the commit message is generated.
- **FR-028**: Documentation updates MUST be additive—existing user-written documentation sections MUST NOT be overwritten.

**Security**

- **FR-029**: The pre-commit pipeline MUST include dependency vulnerability scanning.
- **FR-030**: The pre-commit pipeline MUST include secret detection (API keys, passwords, tokens in source files).
- **FR-036**: MCP server configurations MUST reference credentials exclusively via environment variables — no tokens, keys, or secrets shall be written to any configuration file. The stack MUST validate that required environment variables are set at runtime and fail fast with clear setup instructions when they are missing.

**CI Integration**

- **FR-031**: System MUST generate CI workflow files for operations that justify cloud execution (multi-platform testing, deployment, artifact publishing, external vulnerability database scanning).
- **FR-032**: Every generated CI job MUST include a comment documenting why local execution is insufficient for that job.

**Modularity**

- **FR-033**: Each capability (pre-commit automation, MCP servers, CI workflows, containerization, visualization, Spec Kit) MUST be independently installable and removable.
- **FR-034**: Installing or removing any single module MUST NOT cause failures in other modules.
- **FR-035**: Module dependencies MUST be explicitly declared in a manifest file.

### Key Entities

- **Stack Manifest**: Central configuration file (`dev-stack.toml`) at the repository root, TOML format. Tracks which modules are installed, their versions, and their dependencies. Used by `init`, `update`, and `rollback` operations. Version-controlled alongside the codebase.
- **Module**: A discrete, self-contained capability (e.g., "pre-commit automation", "mcp-servers", "ci-workflows", "containerization", "visualization", "speckit"). Each module has an install script, uninstall script, and version.
- **Pipeline Stage**: One step in the pre-commit automation pipeline. Has an execution order, a failure mode (hard-fail or warn), and produces defined outputs.
- **Commit Memory Record**: The structured data embedded in each commit message. Contains intent, reasoning, scope, references, and a machine-parseable metadata section.
- **Conflict Report**: Generated during brownfield `init` or `update`. Contains per-file diffs, conflict type (new vs. modified vs. deleted), and user resolution status.
- **MCP Server Config**: Configuration entry for a single MCP server. Contains server name, connection details, and health-check command.

## Assumptions

- The target operating system is macOS or Linux. Windows support (via WSL or native PowerShell) is out of scope for the initial version.
- Python (3.11+) and `uv` are assumed to be available on the developer's machine, as they are prerequisites for Spec Kit.
- Git is installed and the repository uses git for version control.
- A diagram-renderer CLI is an optional dependency—if not installed, visualization features degrade gracefully with a prompt to install.
- MCP server configurations are stored in the standard locations expected by the user's coding agent (e.g., `.github/copilot-mcp.json` for GitHub Copilot, `.claude/settings.local.json` for Claude Code).
- The commit message agent leverages the coding agent invoked by the pre-commit automation entrypoint—it does not make independent LLM API calls.
- At least one supported coding agent CLI (`claude`, `copilot`, `cursor`, or equivalent) is assumed to be installed for generative stages. If absent, those stages degrade gracefully (skip with warning).
- Linting and testing tools (e.g., ruff, pytest) are configured by the stack but their execution depends on the project's language/framework. The stack provides sensible defaults for Python projects.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can go from an empty directory to a fully automated, first commit in under 5 minutes using `dev-stack init`.
- **SC-002**: Running `dev-stack init` on an existing repository with 10+ configuration files produces zero unintended overwrites—every conflict is surfaced and requires user consent.
- **SC-003**: The pre-commit pipeline completes all 6 stages in under 60 seconds for a typical project with fewer than 50 source files, under 2 minutes for up to 200 files, and under 5 minutes for up to 500 files. Beyond 500 files, stages 1–3 (lint, test, security) MUST parallelize and report wall-clock time.
- **SC-004**: `dev-stack update` successfully incorporates new stack features while preserving 100% of user customizations in marker-delimited sections.
- **SC-005**: 90% of commit messages generated by the commit message agent are accepted by developers without manual editing. Measured via an `Edited: true|false` git trailer appended after user confirmation; acceptance rate tracked per-project.
- **SC-006**: The last 20 structured commit messages can be parsed with zero errors by `git log --format='%(trailers)'`, each containing all required trailer keys (Spec-Ref, Agent, Pipeline), and the Narrative sections together form a coherent chronological summary of the project's development.
- **SC-007**: Each module (pre-commit automation, MCP, CI, containerization, visualization, Spec Kit) can be installed and removed independently without causing failures in other modules.
- **SC-008**: Documentation auto-generated by the documentation agent reflects the current state of the codebase: generated docs MUST NOT reference symbols, functions, or files deleted in the current diff, and MUST include references to newly added public APIs.
- **SC-009**: Repository visualization diagrams render within 30 seconds for projects with fewer than 100 source files and update incrementally in under 15 seconds when only a few files change.
- **SC-010**: The Dockerfile generated by `init` allows a developer to replicate the full pre-commit pipeline inside a container on the first try, with no manual dependency installation.
