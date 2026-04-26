# Feature Specification: Dev-Stack Update Workflow Bug Fixes

**Feature Branch**: `021-update-workflow-bugs`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "Bugs encountered when trying to update dev-stack in a live project: (1) packaging missing from install_requires, (2) Module VERSION constants not bumped alongside pyproject.toml, (3) Pipeline warning 'skipped due to missing tools' fires on filtered stages, (4) dev-stack --json status embeds stale last-pipeline-run data."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fresh Install Runs Without Crashing (Priority: P1)

A developer installs a new dev-stack wheel into a clean project environment and immediately runs `dev-stack` for the first time. With the current bug, this crashes instantly with a `ModuleNotFoundError` because a required dependency was not declared in the package's dependency list. The developer must be able to proceed past first launch without any manual intervention.

**Why this priority**: A crash on first run is a hard blocker — it makes every install path broken until the user manually investigates and patches their environment. It also erodes trust in the release process.

**Independent Test**: Can be fully tested by installing the dev-stack wheel into a fresh virtual environment and running any `dev-stack` command; the command must succeed without a `ModuleNotFoundError` or any other import-related failure.

**Acceptance Scenarios**:

1. **Given** a clean virtual environment with only the dev-stack wheel installed, **When** any `dev-stack` command is run, **Then** the command completes without raising a `ModuleNotFoundError` or any import error related to undeclared dependencies.
2. **Given** a project where dev-stack was freshly installed via pip, **When** a developer inspects the installed package's declared dependencies, **Then** all packages used at runtime are listed as required dependencies.
3. **Given** a developer who has not manually installed any extra packages, **When** they run `dev-stack init` or `dev-stack update`, **Then** the command runs to completion without prompting them to install missing packages.

---

### User Story 2 - `dev-stack update` Accurately Reports Module Update Status (Priority: P2)

A developer bumps the dev-stack package version (e.g., from 0.1.0 to 1.0.0) and runs `dev-stack update` in their project. With the current bug, the command incorrectly reports "No modules require updates" because the module-level version constants inside each module file were not bumped alongside the package version. The developer must receive an accurate report of which modules are outdated so they can update accordingly.

**Why this priority**: A false "no updates needed" result silently corrupts the update workflow. Developers trust the tool's output and will not investigate further, leaving their project on stale module logic without knowing it.

**Independent Test**: Can be fully tested by bumping the dev-stack package version, running `dev-stack update` in a project that has the older module files, and verifying that the command correctly identifies at least one outdated module.

**Acceptance Scenarios**:

1. **Given** a project with modules installed at version 0.1.x, **When** a newer dev-stack release ships updated modules and the developer runs `dev-stack update`, **Then** the command reports the modules that are behind and offers to update them.
2. **Given** a developer who has already updated all modules to the current release's version, **When** they run `dev-stack update`, **Then** the command correctly reports "No modules require updates."
3. **Given** the dev-stack source code, **When** the package version is bumped for a release, **Then** all module-level version identifiers used for update detection are consistent with the new package version — either because they are derived from a single source of truth or because the release process enforces their update.

---

### User Story 3 - Pipeline Skip Warnings Accurately Reflect Skip Reason (Priority: P3)

A developer runs the dev-stack pipeline with a `--stage` filter (e.g., `--stage docs-api`) to run only one specific stage. All other stages are intentionally skipped by the filter. With the current bug, the pipeline summary warns that stages were "skipped due to missing tools" and advises the developer to run `uv sync --extra dev`, even though the tools are present. The developer must see skip messages that accurately distinguish filtered stages from genuinely unavailable stages.

**Why this priority**: While not a blocker, the misleading warning causes the developer to investigate a non-existent environment problem, wasting time and eroding confidence in the tooling.

**Independent Test**: Can be fully tested by running the pipeline with `--stage <any-single-stage>` in a project where all dev tools are installed, then inspecting the pipeline summary output to confirm no "missing tools" or "uv sync" advisory appears.

**Acceptance Scenarios**:

1. **Given** a project where all dev tools are installed and the pipeline is run with `--stage docs-api`, **When** the pipeline summary is displayed, **Then** the skipped stages show a reason of "filtered via --stage" (or equivalent) and no advisory about installing missing tools is shown.
2. **Given** a project where a tool genuinely is not installed, **When** the pipeline runs and a stage is skipped because the required tool is absent, **Then** the pipeline summary shows a reason of "tool not found" (or equivalent) and includes the advisory to run `uv sync --extra dev`.
3. **Given** a pipeline run with a mix of filter-skipped and tool-missing-skipped stages, **When** the summary is displayed, **Then** each skipped stage shows its specific skip reason, and the `uv sync` advisory only appears if at least one stage was skipped due to a missing tool.

---

### User Story 4 - `dev-stack status` Output Reflects Current State, Not Stale History (Priority: P3)

A developer (or an automated agent) runs `dev-stack --json status` to check the current health of a project. With the current bug, the JSON output includes a `pipeline.stages` block reflecting the last pipeline run, which may be from a previous session or a filtered run. The developer must be able to trust that the status output represents the current state of the project, not cached run history.

**Why this priority**: Status output is used for diagnostics and by automated agents. Stale data in the status output causes false investigations and incorrect automated decisions, but does not block the pipeline itself.

**Independent Test**: Can be fully tested by running `dev-stack --json status` after the last pipeline run was a filtered `--stage` run, then verifying that the output either omits the pipeline stages block or clearly labels it as historical data with a timestamp.

**Acceptance Scenarios**:

1. **Given** a project where the last pipeline run was `--stage infra-sync` from a previous session, **When** a developer runs `dev-stack --json status`, **Then** the output does not show stale per-stage pipeline results as if they represent the current project health.
2. **Given** a developer who needs to understand the current health of their project, **When** they inspect the status output, **Then** all data shown either reflects real-time checks or is clearly marked as historical with a timestamp indicating when it was recorded.
3. **Given** an automated agent consuming `dev-stack --json status`, **When** pipeline stage data is included, **Then** the agent can programmatically distinguish between live health data and cached historical pipeline results.

---

### Edge Cases

- What happens when a developer runs `dev-stack update` immediately after a fresh install before any pipeline run has occurred? The status output must not crash or show empty/null fields for the pipeline block.
- What happens when `--stage` is given an invalid stage name? The skip reason should still be "filtered" (or "invalid stage"), not "missing tool."
- What happens when a module's version identifier is missing entirely (not just outdated)? The update command must handle this gracefully and report the module as requiring attention.
- What happens when the last pipeline run data on disk is corrupted or from an incompatible format? The status command must degrade gracefully rather than crashing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dev-stack package MUST declare all packages it imports at runtime as explicit required dependencies so that a clean install is fully functional without manual intervention.
- **FR-002**: Module version identifiers MUST be derived at runtime from the installed package metadata (e.g., `importlib.metadata.version("dev-stack")`) rather than stored as per-module `VERSION` constants, eliminating the possibility of a stale constant causing a missed update.
- **FR-003**: The `dev-stack update` command MUST correctly report modules as outdated when the installed module version is behind the current release's module version.
- **FR-004**: The pipeline terminal summary MUST distinguish between stages skipped due to `--stage` filtering and stages skipped because a required tool is not installed, using separate, unambiguous human-readable labels for each case. No change to machine-readable JSON output is required.
- **FR-005**: The `uv sync --extra dev` advisory in the terminal pipeline summary MUST only appear when at least one stage was skipped because a required tool was genuinely absent, not when all skips are due to stage filtering.
- **FR-006**: The `pipeline` block in `dev-stack --json status` MUST include a top-level `as_of` field (ISO 8601 timestamp) — i.e. `pipeline.as_of` — recording when that pipeline run occurred, so consumers can determine data freshness.
- **FR-007**: The `pipeline` block in `dev-stack --json status` MUST include a top-level boolean `stale` field — i.e. `pipeline.stale` — set to `true` whenever the recorded run did not execute all pipeline stages (due to `--stage` filtering, a mid-run failure, or any other partial-execution cause), and `false` only when the recorded run completed all stages successfully.

### Key Entities

- **Module Version Identifier**: The version string used by `dev-stack update` to compare the installed module against the available release. After this fix, this value is derived at runtime from installed package metadata rather than hardcoded in each module file.
- **Skip Reason**: The label attached to each skipped pipeline stage in the summary, distinguishing "filtered via --stage" from "tool not found."
- **Status Output**: The JSON document produced by `dev-stack --json status`, used by both developers and automated agents to assess project health.
- **Pipeline Run Record**: The persisted record of the last pipeline execution, including per-stage outcomes and timestamps; distinct from live project health data. Surfaced in `dev-stack --json status` as the top-level `pipeline` object, with `pipeline.as_of` (ISO timestamp) and `pipeline.stale` (boolean) at the top level of that object — not nested under `pipeline.stages`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can install a new dev-stack wheel into a clean environment and successfully run any `dev-stack` command on the first attempt, with zero manual dependency installation steps required.
- **SC-002**: When a dev-stack release bumps the package version, running `dev-stack update` in a project with older module files reports at least one outdated module — a "No modules require updates" result is only correct when all module versions match the current release.
- **SC-003**: When a developer runs the pipeline with `--stage <name>` and all dev tools are installed, zero "missing tools" warnings appear in the pipeline summary for the filtered-out stages.
- **SC-004**: A developer or automated agent reading `dev-stack --json status` can determine data freshness programmatically by reading `pipeline.as_of` (ISO timestamp) and `pipeline.stale` (boolean) without any manual cross-referencing.
- **SC-005**: Zero new false-positive skip warnings or false-negative update reports are introduced by this fix — existing correct behavior for genuinely missing tools and genuinely up-to-date modules is preserved.

## Clarifications

### Session 2026-04-26

- Q: How should module version identifiers be kept in sync with the package version? → A: Derive at runtime from installed package metadata (e.g., `importlib.metadata`); no per-module `VERSION` constant.
- Q: Should the skip-reason fix apply to machine-readable JSON output or terminal display only? → A: Display-only — fix the terminal summary text; no change to JSON output.
- Q: How should stale `pipeline.stages` data be handled in `dev-stack --json status`? → A: Annotate with timestamp — keep `pipeline.stages` but add `as_of` (ISO timestamp) and `stale: true/false` so consumers can judge freshness without a breaking change.
- Q: When should `stale: true` be set on `pipeline.stages`? → A: Any incomplete run — `stale: true` whenever the run did not execute all stages (filtered via `--stage`, failed mid-run, or otherwise partial).

## Assumptions

- The `dev-stack update` comparison mechanism already reads module-level version identifiers; the fix replaces per-module `VERSION` constants with runtime derivation from the installed package's metadata so there is a single source of truth and no manual sync step.
- The pipeline runner already tracks the reason a stage was skipped internally; surfacing that reason correctly in the summary is a presentation fix, not an architectural change.
- The `dev-stack --json status` command reads the last pipeline run record from a persisted file; the fix requires either filtering that data out of the health-status response or annotating it with metadata already available (e.g., run timestamp).
- All four bugs are independent and can be fixed and shipped separately.
