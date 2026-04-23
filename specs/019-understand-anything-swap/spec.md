# Feature Specification: Replace Codeboarding With Understand-Anything

**Feature Branch**: `019-understand-anything-swap`  
**Created**: 2026-04-22  
**Status**: Draft  
**Input**: User description: "Remove Codeboarding entirely and replace it with Understand-Anything for whole-repo interactive graph exploration with iterative updates and no README diagrams."

## Clarifications

### Session 2026-04-22

- Q: How should pre-commit enforce stale or missing graph state? → A: Block local commits until graph refresh succeeds.
- Q: Should graph artifacts be versioned in the repository? → A: Commit .understand-anything artifacts (excluding intermediate/ and diff-overlay.json) and require updates when relevant code changes.
- Q: How should graph-impacting changes be determined? → A: Use Understand-Anything incremental/diff-based detection and block commits if detection cannot run.
- Q: Where should graph freshness enforcement run? → A: Enforce in both local pre-commit and required CI checks.
- Q: What storage policy should apply to committed graph JSON artifacts? → A: Use regular Git by default and require Git LFS when committed graph JSON artifacts exceed 10 MB.
- Q: What counts as a supported interactive plugin experience? → A: At minimum VS Code + GitHub Copilot plugin and Claude Code plugin workflows, validated by opening the graph dashboard, searching a node, and inspecting relationships.
- Q: How is graph freshness determined as "in sync"? → A: Required graph artifacts must exist and parse, impact detection must not be indeterminate, graph-impacting code changes must include synchronized graph artifact updates, and both local and CI validation must pass.
- Q: How is contributor sampling measured for SC-004? → A: Minimum sample size is 10 contributors over a 30-day window with documented onboarding or usage sessions.
- Q: How is CI mergeability enforced? → A: Protected branches must require status check `dev-stack-graph-freshness` (or a documented equivalent mapped check name).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Repository Graph (Priority: P1)

As a maintainer, I can generate an interactive graph for the full repository using Understand-Anything so architecture understanding is centralized in one tool instead of static README diagrams.

**Why this priority**: This is the core replacement objective. Without a full graph generation path, the migration away from Codeboarding is incomplete.

**Independent Test**: Can be fully tested by running the documented initial graph generation flow in a clean clone and confirming an interactive whole-repo graph is produced and explorable.

**Acceptance Scenarios**:

1. **Given** a repository clone without prior graph artifacts, **When** a maintainer follows the documented initial graph generation flow, **Then** an interactive graph of the entire repository is produced.
2. **Given** the generated graph exists, **When** a maintainer opens it in the supported web plugin experience, **Then** they can navigate repository relationships without relying on README diagrams.

---

### User Story 2 - Iterative Graph Refresh (Priority: P2)

As a contributor, I can update the existing Understand-Anything graph after code changes without repeating the full initial setup so graph upkeep fits the repository's pre-commit workflow philosophy.

**Why this priority**: Daily contributor workflows depend on fast, repeatable updates. Iterative refresh keeps graph maintenance practical.

**Independent Test**: Can be fully tested by generating a baseline graph, changing code in a scoped area, running the iterative update flow, and confirming the graph reflects new relationships.

**Acceptance Scenarios**:

1. **Given** an existing repository graph and new code changes, **When** a contributor runs the iterative update process, **Then** the graph updates to include the changed code relationships.
2. **Given** a stale graph during commit preparation, **When** pre-commit checks run, **Then** the commit is blocked and contributors receive clear guidance to refresh the graph before retrying.
3. **Given** a teammate clones the repository, **When** they open the interactive graph workflow, **Then** committed graph artifacts are available without requiring a full fresh pipeline run.
4. **Given** local checks are bypassed or missed, **When** required CI validation runs for the change, **Then** the change fails until graph artifacts and freshness checks pass.

---

### User Story 3 - Remove Codeboarding Footprint (Priority: P3)

As a project maintainer, I can remove Codeboarding-specific references, assets, and documentation guidance so the project has a single, consistent graphing approach.

**Why this priority**: Consolidating on one graphing system reduces confusion and prevents contributors from maintaining obsolete diagram workflows.

**Independent Test**: Can be fully tested by searching project workflows and docs for Codeboarding references and confirming only Understand-Anything guidance remains.

**Acceptance Scenarios**:

1. **Given** migration changes are complete, **When** maintainers review project documentation and automation workflows, **Then** Codeboarding-specific instructions and artifacts are absent from active project paths.
2. **Given** a contributor reads project guidance, **When** they look for architecture visualization instructions, **Then** they are directed only to Understand-Anything graph generation and exploration.

---

### Edge Cases

- A contributor attempts an iterative update before an initial graph has ever been generated.
- The graph update process runs after a large refactor and detects widespread changes across many modules.
- Graph generation or refresh fails due to invalid repository state or unsupported content, and contributors need actionable recovery guidance.
- Graph-impact detection fails or returns an indeterminate result during commit checks.
- Local pre-commit hooks are bypassed, but stale graph artifacts are still present in the proposed change.
- A graph refresh causes committed `.understand-anything/*.json` artifacts to exceed 10 MB and requires LFS tracking updates.
- Legacy Codeboarding files or references are reintroduced in a future change.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST remove Codeboarding execution paths from active source code, templates, pipeline stages, and contributor workflows.
- **FR-002**: The project MUST provide a documented initial setup flow to build an Understand-Anything graph that covers the entire repository.
- **FR-003**: The project MUST provide a documented iterative update flow that refreshes the existing graph after repository changes.
- **FR-004**: Graph freshness enforcement MUST run in both local pre-commit hooks and required CI checks, and MUST treat artifacts as "in sync" only when required graph files exist and parse successfully, impact detection is not indeterminate, graph-impacting code changes include synchronized graph artifact updates, and remediation is provided on failure.
- **FR-005**: Architecture documentation entry points (README and related guides) MUST not include generated static architecture diagram blocks or marker-based diagram injection, and MUST direct users to the interactive graph workflow.
- **FR-006**: Contributors MUST be able to access and explore graph relationships through supported interactive plugin experiences (minimum: VS Code + GitHub Copilot plugin and Claude Code plugin workflow), validated by opening the graph dashboard, searching a node, and inspecting relationships.
- **FR-007**: Migration documentation MUST define how existing contributors transition from Codeboarding-based practices to Understand-Anything-based practices.
- **FR-008**: The project MUST enforce a single visualization policy by adding automated guardrails that fail when Codeboarding references or dual-tool guidance are introduced in maintained documentation or automation paths.
- **FR-009**: The project MUST version Understand-Anything graph artifacts in `.understand-anything/` while excluding local scratch outputs (`.understand-anything/intermediate/` and `.understand-anything/diff-overlay.json`), use regular Git storage by default, require Git LFS when committed graph JSON artifacts exceed 10 MB, and include migration compliance checks for existing repositories.
- **FR-010**: The project MUST determine graph-impacting changes using Understand-Anything incremental/diff-derived detection in this order: diff-overlay signal, graph node path intersection, then fail closed as indeterminate; commit checks MUST block with actionable remediation when detection is unavailable or indeterminate.
- **FR-011**: CI graph validation MUST be configured as a required branch-protection status check for mergeability (check name: `dev-stack-graph-freshness`, or a documented equivalent mapped name).

### Key Entities *(include if feature involves data)*

- **Repository Graph**: The generated representation of repository components and their relationships used for architecture exploration.
- **Graph Generation State**: The lifecycle state of graph outputs (not generated, generated, stale, refreshed) used to drive contributor actions.
- **Visualization Workflow Policy**: Project rules that define required generation, iterative refresh, and commit-time validation behaviors.
- **Documentation Entry Points**: README and related guidance locations that direct users to the supported interactive graph experience.

## Assumptions

- Understand-Anything remains available and usable for full-repository graph generation throughout this migration.
- Contributors have access to the supported web plugin environment needed to explore generated graphs.
- Existing Codeboarding outputs are not required as a backward-compatibility deliverable once migration is complete.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of active project guidance and automation paths reference Understand-Anything as the sole supported repository graphing approach.
- **SC-002**: A first-time contributor can complete initial graph generation and open the interactive graph experience in 15 minutes or less using project documentation.
- **SC-003**: After modifying repository code, contributors can refresh graph outputs through the iterative workflow in 5 minutes or less for change sets with fewer than 200 changed files.
- **SC-004**: In migration validation, at least 90% of a sample of at least 10 contributors measured across a 30-day window report they can find architecture relationships via the interactive graph without requiring README-embedded diagrams.
- **SC-005**: 100% of merged changes identified as graph-impacting by the configured Understand-Anything detection flow include synchronized updates to committed `.understand-anything/` graph artifacts.
- **SC-006**: 100% of merged pull requests pass required CI graph freshness validation using status check `dev-stack-graph-freshness` (or documented equivalent mapped check name).
- **SC-007**: 100% of pull requests with committed graph JSON artifacts over 10 MB include correct Git LFS tracking updates.
- **SC-008**: 100% of validation runs on supported plugin experiences complete the three required interactions: open graph dashboard, search a node, and inspect relationships.
