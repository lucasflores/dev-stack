# Feature Specification: README Comprehensive Update

**Feature Branch**: `005-readme-update`  
**Created**: 2026-03-08  
**Status**: Draft  
**Input**: User description: "Update the README to reflect all changes since it was last updated — new modules (uv_project, sphinx_docs, vcs_hooks), CodeBoarding visualization replacing D2, expanded 8-stage pipeline, VCS best practices automation (commit linting, branch naming, hooks lifecycle, PR generation, changelog, release versioning, signed commits, scope advisory), new CLI commands (changelog, hooks, pr, release), and constitutional agent instructions."

## Clarifications

### Session 2026-03-09

- Q: Should the update consolidate duplicate README sections (CLI commands, prerequisites, validation each appear twice) or preserve the repetition? → A: Consolidate into single authoritative sections; remove duplicates.
- Q: How should the README organize the 8 VCS Best Practices capabilities — dedicated section or distributed? → A: Distribute into existing sections (hooks into Module Catalog, commands into CLI Essentials, etc.) — no dedicated VCS section.
- Q: How should the consolidated prerequisites table distinguish required vs. optional tools? → A: Single table with a "Required?" column (Yes / Optional) and a note on what degrades without each optional tool.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — New User Reads README and Successfully Initializes Dev-Stack (Priority: P1)

A developer discovers the dev-stack repository, reads the README from top to bottom, and follows the instructions to install the CLI and bootstrap their first project. The README accurately describes all available modules, CLI commands, and prerequisites so the developer does not encounter undocumented features or missing instructions. The Quickstart section works end-to-end without requiring the developer to consult any other document.

**Why this priority**: The README is the primary entry point for all users. If it is inaccurate or incomplete, users cannot adopt the tool. Every other story depends on the README being trustworthy.

**Independent Test**: A new developer follows the README instructions on a clean machine. They install prerequisites, install the CLI, run `dev-stack init` in a new repo, and confirm all documented modules and commands exist. No step fails, and no undocumented behavior surprises them.

**Acceptance Scenarios**:

1. **Given** the README's "Quickstart" and "Install Dev-Stack In Your Repo" sections, **When** a developer follows every step sequentially on a clean macOS or Linux machine with Python 3.11+ and `uv`, **Then** `dev-stack init --json` succeeds and produces all assets listed in the "Review the generated assets" table.
2. **Given** the README's "CLI Essentials" table, **When** the developer cross-references it against `dev-stack --help`, **Then** every command listed in the README exists in the CLI, and every CLI command appears in the README.
3. **Given** the README's "Module Catalog" table, **When** the developer inspects the modules directory (`src/dev_stack/modules/`), **Then** every module listed in the README has a corresponding implementation, and every implemented module appears in the README.
4. **Given** the README's "Automation Pipeline" table, **When** the developer runs `dev-stack pipeline run --force`, **Then** the pipeline stages match the names, order, and gate modes documented in the table.

---

### User Story 2 — Existing User Discovers New Capabilities Through README (Priority: P1)

A developer who previously used dev-stack returns after three feature releases (002, 003, 004). They scan the README to learn about new capabilities: UV Project scaffolding, Sphinx docs, CodeBoarding visualization (replacing D2), VCS best practices (commit linting, branch naming, hooks lifecycle, PR generation, changelog, release versioning, signed commits), and expanded pipeline stages. The README clearly communicates what changed without requiring the developer to read spec documents.

**Why this priority**: Returning users need the README to surface all new capabilities. If documentation lags behind implementation, users miss valuable features and lose trust in the tool.

**Independent Test**: Compare every CLI command, module, pipeline stage, and template against the README. Verify zero omissions and zero references to removed features (e.g., D2 diagrams, the old 6-stage pipeline).

**Acceptance Scenarios**:

1. **Given** the README's "Module Catalog" section, **When** a returning user reads it, **Then** it lists `UV Project`, `Sphinx Docs`, and `VCS Hooks` modules alongside the original modules (Hooks, Spec Kit, MCP Servers, CI Workflows, Docker, Visualization).
2. **Given** the README's "Automation Pipeline" section, **When** a returning user reads it, **Then** it documents all 8 pipeline stages (lint, typecheck, test, security, docs-api, docs-narrative, infra-sync, commit-message) with accurate gate modes.
3. **Given** the README's "Visualization Workflow" section, **When** a returning user reads it, **Then** it describes the CodeBoarding CLI integration with Mermaid.js output — not the old D2-based scanner/schema/generate/render flow.
4. **Given** the README, **When** a returning user searches for "D2", "d2", "d2_gen", or "schema_gen", **Then** zero results are found (all D2 references removed).
5. **Given** the README's CLI table, **When** a returning user reads it, **Then** it includes `dev-stack changelog`, `dev-stack hooks status`, `dev-stack pr`, and `dev-stack release` commands.

---

### User Story 3 — Developer Understands VCS Best Practices Workflow (Priority: P2)

A developer reads the README to understand how dev-stack automates version control best practices. The README explains commit message linting, branch naming enforcement, PR auto-description, changelog generation, release versioning, signed commit enforcement, and scope advisory — with enough detail to configure and use each capability without reading the spec.

**Why this priority**: VCS best practices is the largest new feature set (spec 004) with 9 user stories and 46 functional requirements. The README must surface this complexity in a digestible format so users can progressively adopt capabilities.

**Independent Test**: A developer reads only the VCS-related README sections and successfully configures commit linting, pushes a compliant branch, generates a PR description, creates a changelog, and performs a release.

**Acceptance Scenarios**:

1. **Given** the README's Module Catalog (VCS Hooks row) and Configuration sections, **When** a developer reads them, **Then** they understand that commit-msg hooks validate conventional commit format and trailers automatically.
2. **Given** the README's Module Catalog (VCS Hooks row) and Configuration sections, **When** a developer reads them, **Then** they understand that branch naming enforcement happens at push time (not at branch creation) and is configurable via `pyproject.toml`.
3. **Given** the README's CLI Essentials table, **When** a developer reads the changelog, hooks, pr, and release rows, **Then** they understand how to run `dev-stack pr`, `dev-stack changelog`, and `dev-stack release` with their key flags.

---

### User Story 4 — README Accurately Reflects Repository Structure (Priority: P2)

A developer inspects the repository layout section of the README and uses it to navigate the codebase. The directory tree and architecture snapshot accurately reflect the current directory structure, including new packages (`vcs/`, `rules/`) and updated package contents (visualization with CodeBoarding files, new templates).

**Why this priority**: The repository map helps contributors orient themselves. Inaccurate maps cause wasted time navigating a codebase that doesn't match documentation.

**Independent Test**: Compare the README's "Repository Layout" tree against the actual file system. Verify every listed path exists and every significant directory appears. Spot-check that the "Architecture Snapshot" descriptions match module responsibilities.

**Acceptance Scenarios**:

1. **Given** the README's "Repository Layout" section, **When** a developer compares it to the actual file system, **Then** all listed paths exist and all significant source directories (`vcs/`, `rules/`, `visualization/`, `brownfield/`, `pipeline/`, `modules/`, `cli/`, `templates/`) appear.
2. **Given** the README's "Architecture Snapshot", **When** a developer reads the description for `visualization/`, **Then** it describes CodeBoarding-based scanning, Mermaid output, and README injection — not D2 generation.
3. **Given** the README's spec assets section, **When** a developer reads it, **Then** it references all spec directories (001 through 004) — not just 001.

---

### Edge Cases

- What happens when a user follows the README on Windows (WSL or native)? **Assumption**: The README targets macOS/Linux; WSL on Windows is a supported path. The `brew install` line in Quickstart includes a note about alternative package managers.
- What happens when the user has dev-stack installed from an older version and reads the updated README? **Assumption**: The README documents the `dev-stack update` command to bring existing installations current.
- What happens when optional tools (CodeBoarding CLI, git-cliff, python-semantic-release, gh/glab) are missing? **Assumption**: The README clearly marks which tools are optional and what functionality degrades without them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The README MUST list all 9 modules currently implemented: Hooks, Spec Kit, MCP Servers, CI Workflows, Docker, Visualization, UV Project, Sphinx Docs, and VCS Hooks.
- **FR-002**: The README MUST document all 8 pipeline stages in order: lint, typecheck, test, security, docs-api, docs-narrative, infra-sync, commit-message — with accurate gate modes (hard/soft) for each.
- **FR-003**: The README MUST list all CLI commands: `init`, `update`, `rollback`, `mcp install|verify`, `pipeline run`, `visualize`, `status`, `changelog`, `hooks status`, `pr`, `release`, and `version`.
- **FR-004**: The README MUST remove all references to D2 diagrams, the `d2` CLI tool, `d2_gen.py`, `schema_gen.py`, and the old 4-step visualization workflow (scan → schema → generate D2 → render).
- **FR-005**: The README MUST describe the CodeBoarding-based visualization workflow: CodeBoarding CLI invocation → Mermaid.js diagram generation → README injection with managed markers.
- **FR-006**: The README MUST document the `--depth-level`, `--incremental`, `--no-readme`, and `--timeout` flags for the `visualize` command.
- **FR-007**: The README MUST document all VCS capabilities by distributing them into existing sections: the VCS Hooks module into the Module Catalog table, `changelog`/`hooks status`/`pr`/`release` into the CLI Essentials table, commit linting and branch naming into the Automation Pipeline or Module Catalog descriptions, and configuration knobs (`[tool.dev-stack.*]`) into the relevant section where each capability is introduced. There MUST NOT be a standalone "VCS Best Practices" top-level section.
- **FR-008**: The README MUST document configuration via `pyproject.toml` under `[tool.dev-stack.*]` sections (branch naming patterns, hook selection, signing settings).
- **FR-009**: The README MUST present a single consolidated prerequisites table with columns: Tool, Purpose, and Required? (Yes / Optional). Required tools: Python 3.11+, uv, git 2.30+, coding agent CLI. Optional tools: CodeBoarding CLI, git-cliff, python-semantic-release, gh/glab, mypy, sphinx — each with a brief note on what degrades without it. The `d2` entry MUST be removed entirely.
- **FR-010**: The README MUST update the "Review the generated assets" table to include new assets: `constitution-template.md`, `.dev-stack/instructions.md`, `cliff.toml`, `.git/hooks/commit-msg`, `.git/hooks/pre-push`, `docs/conf.py`, `docs/index.rst`.
- **FR-011**: The README MUST update the "Repository Layout" tree to include `vcs/`, `rules/`, and accurately describe `visualization/` contents.
- **FR-012**: The README MUST update the "Architecture Snapshot" to describe the VCS package, rules engine, and CodeBoarding-based visualization.
- **FR-013**: The README MUST reference all spec directories (001 through 004) in the "Spec Assets" or "Additional Resources" section.
- **FR-014**: The README MUST document that the `sphinx_docs` module generates `docs/conf.py`, `docs/index.rst`, and `docs/Makefile` and that `docs/_build/` is gitignored.
- **FR-015**: The README MUST document that `dev-stack init` now scaffolds a complete Python project structure (via `uv init --package`) when no `pyproject.toml` exists (greenfield mode).
- **FR-016**: The README MUST document the constitutional practices feature: `constitution-template.md` and `.dev-stack/instructions.md` generation, and agent instruction file detection/injection.
- **FR-017**: The README MUST consolidate duplicate sections (CLI commands, prerequisites, validation) into single authoritative sections — no topic should appear in two separate places. The table of contents, clear section hierarchy, code examples, and dual-audience flow (overview → install → usage → reference) MUST be preserved.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of implemented CLI commands appear in the README's command table, verified by comparing `dev-stack --help` output against the documented list.
- **SC-002**: 100% of implemented modules appear in the README's module catalog, verified by comparing `src/dev_stack/modules/*.py` against the documented list.
- **SC-003**: Zero references to D2, `d2_gen.py`, `schema_gen.py`, or the old visualization workflow remain in the README.
- **SC-004**: All 8 pipeline stages are documented with correct names, order, and gate modes.
- **SC-005**: A new user following only the README instructions can install, initialize, and use dev-stack without consulting any spec document.
- **SC-006**: The repository layout tree matches the actual file system with zero missing significant directories.
- **SC-007**: All 4 spec directories (001–004) are referenced in the documentation assets section.
- **SC-008**: Optional tool dependencies (CodeBoarding, git-cliff, python-semantic-release, gh, glab, mypy, sphinx) are clearly marked as optional with graceful degradation described.

## Assumptions

- The README serves two audiences: (1) consumers who install and use the CLI in their repos, and (2) contributors who develop dev-stack itself. Both audiences must be served by the same document.
- The existing README structure (sections, table of contents, dual quickstart/install flow) is sound and should be preserved — content needs updating, not restructuring.
- All features from specs 002, 003, and 004 have been implemented and merged into the main branch.
- The `d2` tool is no longer a dependency at any level (not even optional).
- CodeBoarding CLI is the sole visualization backend.
- The pipeline has expanded from 6 stages to 8 stages, with the docs stage split into docs-api (hard gate, Sphinx) and docs-narrative (soft gate, agent).
- The `typecheck` stage (mypy) was inserted between lint and test as a hard gate.
- New CLI commands (`changelog`, `hooks status`, `pr`, `release`) are registered and functional.
- Templates directory now includes `cliff.toml`, `constitution-template.md`, `instructions.md`, and `pr-template.md`.