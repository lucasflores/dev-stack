# Feature Specification: Greenfield Init Fixes

**Feature Branch**: `008-greenfield-init-fixes`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "3rd greenfield setup attempt in empty repo surfaces four issues: tests directory not created, dev dependencies not added to pyproject.toml, pipeline is hollow on first commit, DEV_STACK_AGENT=none scoping."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tests Scaffold Created on Greenfield Init (Priority: P1)

A developer runs `dev-stack init` in a fresh repository and expects a working test scaffold (`tests/__init__.py` and `tests/test_placeholder.py`) to be created automatically, so that the pipeline's test stage has something to execute on the very first commit.

**Why this priority**: Without test files, the test pipeline stage skips on every commit. This is the most visible broken promise — the init output lists these files as pending but never creates them, undermining trust in the tool's correctness.

**Independent Test**: Run `dev-stack --json init` in a fresh `uv init --package` repo and verify `tests/__init__.py` and `tests/test_placeholder.py` exist on disk with correct content.

**Acceptance Scenarios**:

1. **Given** a freshly initialized git repo with no existing test directory, **When** the user runs `dev-stack --json init`, **Then** the `tests/` directory is created containing `__init__.py` (empty) and `test_placeholder.py` (with a valid import test for the project package).
2. **Given** a repo where `tests/` already exists with user-created test files, **When** the user runs `dev-stack --json init`, **Then** existing test files are preserved and only missing scaffold files are added.
3. **Given** a greenfield init completes, **When** the user inspects the init output/report, **Then** the test files appear in the "created" list (not "pending").

---

### User Story 2 - Dev Dependencies Pre-configured in pyproject.toml (Priority: P1)

A developer runs `dev-stack init` in a fresh repository and expects `[project.optional-dependencies]` to be populated with dev and docs dependency groups (ruff, mypy, pytest, pytest-cov, sphinx), so that the pipeline tools are installable immediately after init.

**Why this priority**: Without dev dependencies declared, the user has no clear path to install the tools the pipeline requires. This directly causes Issue #3 (hollow pipeline) and contradicts the README's documented behavior.

**Independent Test**: Run `dev-stack --json init` in a fresh repo and verify `pyproject.toml` contains `[project.optional-dependencies]` with both `dev` and `docs` groups populated.

**Acceptance Scenarios**:

1. **Given** a freshly initialized git repo, **When** the user runs `dev-stack --json init`, **Then** `pyproject.toml` contains `[project.optional-dependencies.dev]` with ruff, mypy, pytest, and pytest-cov entries.
2. **Given** a freshly initialized git repo, **When** the user runs `dev-stack --json init`, **Then** `pyproject.toml` contains `[project.optional-dependencies.docs]` with sphinx, sphinx-autodoc-typehints, and myst-parser entries.
3. **Given** a brownfield repo that already has custom optional-dependencies, **When** the user runs `dev-stack --json init --force`, **Then** existing dependency groups are preserved and only missing groups are added.

---

### User Story 3 - Pipeline Runs Substantively on First Commit (Priority: P1)

After running `dev-stack init` and committing, the developer expects the pre-commit pipeline to execute its core stages (lint, typecheck, test) rather than skipping them. A pipeline that reports "success" while skipping 5 of 9 stages provides false confidence and is misleading.

**Why this priority**: The entire value proposition of dev-stack is the automated pipeline. If it's hollow on the first commit, the developer gets no feedback on code quality and may not realize stages are skipped until much later.

**Independent Test**: Run `dev-stack --json init` in a fresh repo, install dev dependencies, commit, and verify that lint, typecheck, and test stages produce pass/fail results (not skip).

**Acceptance Scenarios**:

1. **Given** a freshly initialized repo where `dev-stack init` has completed (which auto-installs dev dependencies), **When** the user runs `git add -A && git commit`, **Then** lint, typecheck, and test stages execute (status is pass or fail, not skip).
2. **Given** a freshly initialized repo where dev dependencies have NOT been installed, **When** the pipeline runs and stages skip due to missing tools, **Then** the pipeline reports a clear warning per skipped stage explaining which tool is missing and how to install it.
3. **Given** a freshly initialized repo, **When** all core stages skip due to missing tools, **Then** the pipeline returns success (commit proceeds) but emits a prominent warning banner listing each skipped stage and remediation commands.

---

### User Story 4 - DEV_STACK_AGENT Environment Variable Persists Across Subprocesses (Priority: P2)

A developer sets `DEV_STACK_AGENT=none` before running `dev-stack init` to skip agent-dependent stages. They expect this setting to also apply when the pre-commit hook fires during `git commit`, without needing to separately export the variable.

**Why this priority**: This is a usability/documentation issue. The workaround (using `export`) is simple, but the current behavior is surprising and undocumented, leading to confusion when the hook auto-detects an agent the user intended to suppress.

**Independent Test**: Set `DEV_STACK_AGENT=none` without `export`, run `dev-stack init`, then `git commit`, and verify the hook respects the agent setting.

**Acceptance Scenarios**:

1. **Given** the user runs `export DEV_STACK_AGENT=none` before `dev-stack init`, **When** the pre-commit hook fires during `git commit`, **Then** the hook reads `DEV_STACK_AGENT=none` from the environment and skips agent-dependent stages.
2. **Given** the user sets `DEV_STACK_AGENT=none` inline (e.g., `DEV_STACK_AGENT=none dev-stack init`) without exporting, **When** the pre-commit hook fires during a subsequent `git commit`, **Then** the hook reads agent config from `dev-stack.toml` (which recorded `cli: none` at init time) and skips agent-dependent stages.
3. **Given** both `DEV_STACK_AGENT` env var and `dev-stack.toml` agent config exist, **When** the pre-commit hook fires, **Then** the env var takes precedence over the manifest value.

---

### Edge Cases

- What happens when `uv init --package` partially fails (e.g., creates `pyproject.toml` but not `src/`) — does the test scaffold still attempt to run? **Out of scope**: partial `uv init` failure is a `uv` bug, not a dev-stack concern. The scaffold will still attempt to create test files regardless.
- What happens when the user has a custom `pyproject.toml` with an existing but empty `[project.optional-dependencies]` section?
- What happens when `uv lock` or `uv sync` fails after dependencies are added (e.g., network issue, conflicting version constraints)? Init should warn and continue per FR-009.
- What happens when the tests directory exists but `test_placeholder.py` is missing?
- How does the pipeline behave when only some tools are installed (e.g., ruff is present but mypy is not)? **Covered by FR-004**: Each individual skipped stage emits its own remediation hint. The hollow-pipeline warning (FR-005) only fires when ALL three core stages skip. Partial hollowness is handled by per-stage skip messages.

## Clarifications

### Session 2026-03-10

- Q: Should init auto-install dev dependencies or just instruct the user? → A: Auto-install — init automatically runs `uv sync --extra dev --extra docs` after adding deps to pyproject.toml.
- Q: When all core pipeline stages skip, should the pipeline block the commit or warn? → A: Warn but allow — pipeline returns success with a prominent warning banner listing skipped stages, preserving commit flow.
- Q: How should DEV_STACK_AGENT=none persist across subprocesses? → A: Manifest fallback — hook reads agent config from `dev-stack.toml` when `DEV_STACK_AGENT` env var is not set.
- Q: If `uv sync` fails during auto-install, should init fail entirely? → A: Warn and continue — init succeeds with a warning that `uv sync` failed, includes the command for manual retry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `uv_project` module MUST create `tests/__init__.py` and `tests/test_placeholder.py` during greenfield init, and these files MUST appear in the "created" files list in the init report.
- **FR-002**: The `uv_project` module MUST add `[project.optional-dependencies.dev]` (ruff, mypy, pytest, pytest-cov) and `[project.optional-dependencies.docs]` (sphinx, sphinx-autodoc-typehints, myst-parser) to `pyproject.toml` during init.
- **FR-003**: The init command MUST automatically run `uv sync --extra dev --extra docs` (or `uv sync --all-extras`) after optional dependencies have been added to `pyproject.toml`, so that pipeline tools are installed and available for the first commit without manual steps.
- **FR-004**: When pipeline stages skip due to missing tools, the skip message MUST include the tool name and a remediation hint (e.g., "ruff not installed — run `uv sync --extra dev` to install").
- **FR-005**: When all core pipeline stages (lint, typecheck, test) skip, the pipeline MUST return success (allowing the commit) but MUST emit a prominent warning banner listing each skipped stage, so the user is aware that no substantive validation occurred.
- **FR-006**: The pre-commit hook MUST read the agent config from `dev-stack.toml` as a fallback when the `DEV_STACK_AGENT` environment variable is not set, so the user's init-time agent choice persists into hook subprocesses without requiring `export`.
- **FR-007**: The `uv_project` module MUST preserve existing test files and optional-dependency groups when running in brownfield or `--force` mode.
- **FR-008**: The `uv_project` module MUST run `uv lock` after adding optional dependencies so the lockfile reflects the new dependency groups.
- **FR-009**: If `uv sync --extra dev --extra docs` fails during init (e.g., network error, version conflict), the init MUST still succeed for all scaffolding artifacts, but MUST emit a warning with the failure reason and the exact command for manual retry.

### Key Entities

- **Init Report**: The structured output of `dev-stack init` containing module results, files created, files pending, warnings, and detected agent info.
- **Pipeline Stage Result**: Per-stage outcome (pass/fail/skip/warn) with duration, output, and skip reason. Skip reasons must now include remediation guidance.
- **Stack Manifest (`dev-stack.toml`)**: Persisted configuration including module versions, agent detection, and rollback tag. Agent config stored here should serve as fallback for hook subprocesses.
- **Greenfield Predecessor**: A repository where `uv init --package` has already been run (creating a vanilla `pyproject.toml` with `uv_build` backend) but `dev-stack init` has not yet run. Detected by `is_greenfield_uv_package()`. This state requires the brownfield guard to allow augmentation (Steps 2–5) while skipping re-initialization (Step 1).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After running `dev-stack init` in a fresh repo, 100% of the files listed in the init report as "created" exist on disk (zero files reported as "pending" that were supposed to be created).
- **SC-002**: After running `dev-stack init` (which auto-installs dev dependencies), the first `git commit` executes at least 4 pipeline stages with pass/fail results (not skip).
- **SC-003**: A new user following only the README greenfield instructions can go from empty repo to a passing pipeline (with substantive stage execution) without needing undocumented steps or workarounds.
- **SC-004**: 100% of pipeline skip messages include the missing tool name and a remediation command.
- **SC-005**: Setting `DEV_STACK_AGENT=none` during init results in agent-dependent stages being skipped during the subsequent commit, with no additional user steps beyond what the README documents.

### Assumptions

- The user has `uv` installed and available on PATH (documented prerequisite).
- The greenfield flow assumes no pre-existing `pyproject.toml`; brownfield flows are tested separately.
- The `uv_project` module's `_scaffold_tests()` and `_augment_pyproject()` helper functions already contain the correct logic — the issue is likely in the install flow not invoking them or a sequencing/ordering problem between modules.
- The pipeline's `_tool_available_in_venv()` check is the gating mechanism for stage skipping; remediation hints will be added to the skip reason strings.
- The `dev-stack.toml` manifest already stores agent config; the hook may just need to read it as a fallback when the environment variable is not set.
