<!--
  ============================================================================
  Sync Impact Report
  ============================================================================
  Version change: N/A → 1.0.0 (initial ratification)
  
  Added principles:
    - I. CLI-First Interface
    - II. Spec-Driven Development
    - III. Automation by Default
    - IV. Brownfield Safety
    - V. AI-Native Architecture
    - VI. Local-First Execution
    - VII. Observability & Documentation
    - VIII. Modularity & Composability
  
  Added sections:
    - Development Workflow & Automation Pipeline
    - Security & Quality Gates
    - Governance
  
  Removed sections: None (initial creation)
  
  Templates requiring updates:
    ✅ .specify/templates/plan-template.md — "Constitution Check" section
        compatible; principles provide concrete gates
    ✅ .specify/templates/spec-template.md — requirements/success criteria
        format aligned with Spec-Driven principle
    ✅ .specify/templates/tasks-template.md — phased task structure
        compatible with Automation by Default and Quality Gates
    ✅ .specify/templates/checklist-template.md — generic format, no
        constitution-specific references needed
    ✅ .specify/templates/agent-file-template.md — development guidelines
        template compatible with AI-Native Architecture principle
  
  Follow-up TODOs: None
  ============================================================================
-->

# Dev-Stack Constitution

## Core Principles

### I. CLI-First Interface

All dev-stack capabilities MUST be accessible through CLI commands.
The primary entry point is a single `init` command that bootstraps a
repository with the full automation suite. A companion `update` command
MUST exist to fold in new stack capabilities over time.

- Every user-facing operation MUST have a corresponding CLI invocation.
- CLI commands MUST support both interactive and non-interactive
  (CI-friendly) modes.
- Output MUST use structured formats (JSON) for machine consumption
  alongside human-readable defaults.
- Exit codes MUST follow POSIX conventions: 0 for success, non-zero
  for failure with meaningful stderr messages.

**Rationale**: A CLI-first approach ensures scriptability, composability
with other tools, and a consistent developer experience regardless of
editor or environment.

### II. Spec-Driven Development

Every feature MUST begin with a specification before implementation
begins. Specifications are authored using GitHub Spec Kit and stored
under `.specify/`.

- No implementation work MUST proceed without a corresponding
  `spec.md` in the feature's spec directory.
- Specifications MUST contain user stories with acceptance scenarios,
  functional requirements, and measurable success criteria.
- Changes to specifications MUST be versioned and reviewable in the
  same PR workflow as code changes.
- The `plan.md` MUST pass the Constitution Check gate before
  implementation proceeds.

**Rationale**: Specs prevent scope creep, ensure alignment between
intent and outcome, and provide AI agents with the structured context
they need to operate autonomously and accurately.

### III. Automation by Default

All repeatable development tasks MUST be automated through git hooks,
agents, or CI pipelines. Manual steps are technical debt.

- Linting, testing, security auditing, documentation updates, and
  commit message generation MUST execute automatically on every commit.
- Automation MUST be idempotent: running the same hook or pipeline
  twice on unchanged code MUST produce identical results.
- New automation MUST be additive: adding a hook or agent MUST NOT
  break existing automation in the pipeline.
- The automation pipeline MUST follow a defined execution order (see
  Development Workflow section).

**Rationale**: Automation eliminates human error in repetitive tasks,
enforces quality gates consistently, and frees developers to focus on
design and implementation decisions.

### IV. Brownfield Safety

Stack operations MUST detect conflicts and MUST NOT overwrite user
changes without explicit consent.

- The `init` command MUST scan for existing configuration files and
  surface potential conflicts before writing anything.
- The `update` command MUST present a diff of proposed changes and
  require user confirmation for any file that would be modified.
- Merge strategies MUST preserve user customizations: stack-managed
  sections MUST be clearly delimited (e.g., with marker comments) to
  enable safe partial updates.
- A rollback mechanism MUST exist for any stack operation that
  modifies existing files.

**Rationale**: Developers adopting dev-stack into existing projects
MUST trust that their configurations, customizations, and working
state will not be silently destroyed.

### V. AI-Native Architecture

AI capabilities MUST use coding agents as the backbone—not raw
API calls to LLM providers. Commit history MUST serve as persistent
agent memory.

- All AI-powered automation (documentation, commit messages, code
  review) MUST operate through coding agent interfaces (e.g., MCP
  servers), not direct OpenAI/Anthropic API calls.
- MCP server configuration (Context7, NotebookLM, GitHub, and others)
  MUST be installable and verifiable through the CLI.
- Commit messages MUST be structured to function as persistent memory
  for coding agents: they MUST include intent, reasoning, scope of
  changes, and references to specs or tasks.
- Agent context MUST be enrichable from commit history, specs, and
  repository visualization—not only from the immediate file diff.

**Rationale**: Coding agents provide tool-use capabilities, structured
reasoning, and context management that raw API calls lack. Rich commit
history transforms version control into an AI-queryable knowledge base
for the project.

### VI. Local-First Execution

Automation MUST prefer local execution. Cloud CI MUST be justified
by clear benefits that local execution cannot provide.

- Git hooks and pre-commit automation MUST run locally by default.
- Docker-based reproducibility MUST be available so that any
  developer can replicate the full automation pipeline on their
  machine.
- Cloud CI MUST be reserved for operations that genuinely require it:
  multi-platform testing, deployment, artifact publishing, or
  security scanning against external vulnerability databases.
- Every cloud CI job MUST have a documented justification for why
  local execution is insufficient.

**Rationale**: Local execution provides faster feedback loops, reduces
dependency on external services, and keeps sensitive code and
credentials off third-party infrastructure where possible.

### VII. Observability & Documentation

Every component MUST be observable, documented, and visualizable.
Documentation updates MUST be automated.

- Repository structure MUST be visualizable through auto-generated
  diagrams (inspired by the noodles project), using coding agents
  as the AI backbone for diagram generation.
- A documentation agent MUST run before the commit message agent to
  ensure all docs reflect the pending changes.
- README and API documentation MUST be auto-updated as part of the
  pre-commit pipeline.
- Structured logging MUST be present in all CLI commands and
  automation scripts to enable debugging and audit trails.

**Rationale**: Observable systems are debuggable systems. Automated
documentation eliminates the perpetual drift between code and docs
that plagues most projects.

### VIII. Modularity & Composability

Each capability MUST be independently installable, testable,
and removable without breaking other capabilities.

- The stack MUST be composed of discrete modules: hooks, MCP servers,
  CI workflows, Docker configuration, visualization, and Spec Kit
  integration.
- Installing or removing any single module MUST NOT cause failures
  in other modules.
- Module dependencies MUST be explicitly declared and enforced—no
  implicit coupling.
- Each module MUST have its own test coverage validating its
  independent operation.

**Rationale**: Modularity enables incremental adoption (users can
start with just hooks and add CI later), simplifies debugging
(failures are isolated), and supports the update mechanism (modules
can be updated independently).

## Development Workflow & Automation Pipeline

The dev-stack automation pipeline executes in a strict order on
every commit. Each stage MUST complete successfully before the
next begins.

### Pre-Commit Pipeline Execution Order

1. **Linting** — Static analysis and code formatting checks.
2. **Type Checking** — Mypy strict-mode type analysis against the
   `src/` package tree.
3. **Testing** — pytest suite (unit and integration tests as
   configured).
4. **Security Audits** — Dependency vulnerability scanning and
   secret detection.
5. **Docs API** — Deterministic Sphinx API reference build
   (`sphinx-apidoc` + `sphinx-build` with `SOURCE_DATE_EPOCH=0`).
6. **Docs Narrative** — Agent-driven narrative documentation
   updates to `docs/guides/` (tutorials, quickstarts, architecture
   walkthroughs). Does NOT generate API reference.
7. **Infrastructure Sync** — Updates CI workflows, Dockerfile,
   and visualization diagrams if source changes warrant it.
8. **Commit Message Agent** — Generates a structured commit
   message encoding intent, reasoning, scope, spec/task
   references, and a summary optimized for agent memory retrieval.

### Pipeline Rules

- If any stage (1–5) fails, the pipeline MUST halt and the commit
  MUST be rejected with actionable error output.
- Stages 6–8 are generative: they produce artifacts. If generation
  fails, the pipeline MUST warn but MAY allow the commit with a
  `--force` flag and a logged justification.
- The pipeline MUST be skippable with an explicit `--no-hooks` flag
  for emergency situations, but skipped runs MUST be flagged in
  the next CI check.

### Dependency Management

- GitHub Spec Kit integration strategy (submodule, fork, uv, or
  script checkout) MUST be evaluated and documented during the
  `init` phase. The chosen strategy MUST support the `update`
  command for seamless version upgrades.
- MCP server dependencies MUST be declared in a manifest file
  and installable via a single CLI command.

## Security & Quality Gates

These gates are non-negotiable. Every commit and every PR MUST
pass all applicable gates.

### Mandatory Gates

| Gate | Scope | Enforcement |
|------|-------|-------------|
| Lint pass | All source files | Pre-commit hook |
| Test pass | All test suites | Pre-commit hook |
| No known vulnerabilities | Dependencies | Pre-commit + CI |
| No secrets in code | All files | Pre-commit hook |
| Docs current | README, API docs | Pre-commit hook |
| Spec exists | New features | PR review checklist |
| Constitution compliance | All PRs | PR review checklist |

### Quality Standards

- Test coverage MUST NOT decrease with any commit. New code MUST
  include corresponding tests.
- Linting rules MUST be consistent across the stack and enforced
  automatically—never manually.
- Security scanning MUST cover both static analysis (source code)
  and dependency analysis (supply chain).

## Governance

This constitution is the supreme governance document for the
dev-stack project. It supersedes all other practices, conventions,
or ad-hoc decisions.

### Amendment Process

1. Propose amendment via a PR modifying this file.
2. Amendment MUST include: rationale for the change, impact
   assessment on existing principles, and a propagation plan
   for dependent templates.
3. Amendment MUST be reviewed and approved by at least one
   maintainer.
4. Upon merge, all dependent templates and specs MUST be
   updated to reflect the amendment (see Sync Impact Report).

### Versioning Policy

This constitution follows semantic versioning:

- **MAJOR**: Backward-incompatible principle removal or
  redefinition (e.g., dropping a core principle).
- **MINOR**: New principle or section added, or existing
  guidance materially expanded.
- **PATCH**: Clarifications, wording improvements, typo fixes,
  non-semantic refinements.

### Compliance Review

- Every PR MUST include a constitution compliance check as
  part of the review process.
- The plan-template's "Constitution Check" section MUST
  reference the principles defined herein.
- Violations MUST be documented in the Complexity Tracking
  table with explicit justification.

**Version**: 1.0.0 | **Ratified**: 2026-02-10 | **Last Amended**: 2026-02-10
