# Feature Specification: Init & Pipeline Bugfixes

**Feature Branch**: `006-init-pipeline-bugfixes`
**Created**: 2026-03-10
**Status**: Draft
**Input**: User description: "Fix 14 critical, high, medium, and low severity bugs in the init flow, pipeline execution, and CLI UX that block new users from completing the README-documented bootstrap workflow"

## Clarifications

### Session 2026-03-10

- Q: Should init install dev deps via `uv sync --all-extras`, move them to core dependencies, or use `uv sync --extra dev`? → A: `uv sync --all-extras` (dev deps stay in optional-dependencies)
- Q: How should the security stage exclude false positives from `detect-secrets scan`? → A: Use a `.secrets.baseline` file (standard detect-secrets workflow) with audited exclusions
- Q: When hard gates fail under `--force`, should the exit code also change or only the JSON status? → A: Both — JSON `"completed_with_failures"` and non-zero exit code (exit 1)
- Q: How should init verify that pre-existing files came from `uv init --package` vs. user-created? → A: Check structural fingerprint of `pyproject.toml` (minimal uv-generated structure)
- Q: What should `--dry-run init` report on an already-initialized repo? → A: Preview what `update` would change (files added/modified/conflicted)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Greenfield Bootstrap Completes Without Errors (Priority: P1)

A new user clones the repo, runs `uv init --package`, then `dev-stack init`, and successfully makes their first commit — all without `--no-verify` or manual workarounds.

**Why this priority**: This is the primary onboarding flow documented in the README. If the first commit is blocked, no new user can adopt Dev-Stack.

**Independent Test**: Run the full greenfield flow (`uv init --package` → `dev-stack init` → edit a file → `git add . && git commit`) in a fresh temporary directory and confirm the commit succeeds.

**Acceptance Scenarios**:

1. **Given** a fresh git repo with `uv init --package` completed, **When** the user runs `dev-stack init`, **Then** init completes with `"status": "success"`, creates `dev-stack.toml`, and installs hooks.
2. **Given** dev-stack is initialized in a fresh repo, **When** the user runs `git commit`, **Then** the pre-commit hook pipeline completes without blocking the commit (stages with missing optional tools skip gracefully).
3. **Given** mypy is not installed in the project venv, **When** the typecheck stage runs, **Then** it detects mypy is absent from the venv and skips with a clear "skipped — mypy not installed" message.
4. **Given** dev-stack init has completed, **When** the user checks the project venv, **Then** a `.venv` directory exists with all dev dependencies installed (ruff, pytest, mypy).

---

### User Story 2 — Init Correctly Handles Expected Greenfield Files (Priority: P1)

The init command recognizes that files created by `uv init --package` (pyproject.toml, `__init__.py`) are expected predecessors in the greenfield flow rather than conflicts.

**Why this priority**: Without this fix, every greenfield user hits an immediate conflict error, breaking the documented happy path.

**Independent Test**: Run `uv init --package` then `dev-stack init` (without `--force`) and confirm no conflict is reported for `uv init`-generated files.

**Acceptance Scenarios**:

1. **Given** a repo bootstrapped with `uv init --package`, **When** the user runs `dev-stack init` (no --force), **Then** init proceeds without conflict errors for pyproject.toml or `__init__.py`.
2. **Given** a repo bootstrapped with `uv init --package`, **When** the user runs `dev-stack --json init`, **Then** the output reports `"mode": "greenfield"` (not "brownfield").
3. **Given** a truly brownfield repo with pre-existing custom pyproject.toml, **When** the user runs `dev-stack init`, **Then** conflicts are correctly detected and reported.

---

### User Story 3 — Pipeline Accurately Reports Stage Results (Priority: P2)

The pipeline reports an honest top-level status that reflects whether hard-gate stages actually passed or failed, even when `--force` is used.

**Why this priority**: Misleading success reports erode trust and hide real issues. Users and CI systems need accurate pass/fail signals.

**Independent Test**: Run `dev-stack --json pipeline run --force` with a failing hard-gate stage and verify the JSON output reflects the failure in the top-level status.

**Acceptance Scenarios**:

1. **Given** a project where a hard-gate stage (typecheck, test) fails, **When** the pipeline runs with `--force`, **Then** the JSON output reports `"status": "completed_with_failures"` (not "success") and lists failed stages.
2. **Given** all hard-gate stages pass, **When** the pipeline runs, **Then** the JSON output reports `"status": "success"`.
3. **Given** only soft-gate stages fail, **When** the pipeline runs, **Then** the JSON output reports `"status": "success"` with warnings for the soft-gate failures.

---

### User Story 4 — Dry-Run Init Works on Initialized Repos (Priority: P2)

A user can run `dev-stack --dry-run init` on a repo that already has `dev-stack.toml` to preview what changes would occur, supporting the validation checklist's brownfield safety check.

**Why this priority**: The validation checklist explicitly calls for this command. Failing here breaks the documented verification workflow.

**Independent Test**: Initialize a repo with `dev-stack init`, then run `dev-stack --dry-run --json init` and confirm it returns a conflict/change preview instead of an error.

**Acceptance Scenarios**:

1. **Given** a repo already initialized with dev-stack, **When** the user runs `dev-stack --dry-run --json init`, **Then** the output lists which files would conflict or be modified — without erroring out.
2. **Given** a repo already initialized with dev-stack, **When** the user runs `dev-stack --dry-run --json init`, **Then** no files are modified on disk.

---

### User Story 5 — CLI Version and Help Are Complete (Priority: P3)

The CLI provides a working `--version` flag that prints the actual version number, and all commands have help descriptions.

**Why this priority**: Standard CLI conventions. Missing version info and blank help text signal an unfinished tool.

**Independent Test**: Run `dev-stack --version` and confirm it prints a semantic version. Run `dev-stack --help` and confirm all commands have descriptions.

**Acceptance Scenarios**:

1. **Given** the CLI is installed, **When** the user runs `dev-stack --version`, **Then** the actual semantic version number is printed (e.g., "dev-stack 0.1.0").
2. **Given** the CLI is installed, **When** the user runs `dev-stack --help`, **Then** every command (including `update`) has a non-blank description.
3. **Given** the CLI is installed, **When** the user runs `dev-stack --json version`, **Then** the JSON output includes the version number in a `"version"` field.

---

### User Story 6 — Security Stage Properly Evaluates Findings (Priority: P3)

The security stage evaluates `detect-secrets scan` output for actual findings instead of always reporting PASS, while correctly handling known false positives (e.g., SHA-256 checksums in hook manifests).

**Why this priority**: A security gate that always passes provides false assurance. Users expect the pipeline to surface real secrets.

**Independent Test**: Add a test file with a known secret pattern, run the security stage, and confirm it reports FAIL. Then remove it and confirm known false positives (hook manifest checksums) do not trigger failures.

**Acceptance Scenarios**:

1. **Given** a repo with a file containing a high-entropy secret, **When** the security stage runs, **Then** it reports FAIL with details about the finding.
2. **Given** a repo where `detect-secrets scan` only finds SHA-256 checksums in `hooks-manifest.json`, **When** the security stage runs, **Then** it reports PASS (known false positives are excluded).

---

### User Story 7 — README Validation Commands Use Correct Syntax (Priority: P3)

The README documents correct CLI flag positions so users can copy-paste validation commands verbatim.

**Why this priority**: Users who follow the README validation checklist encounter errors on every command, undermining confidence in the tool.

**Independent Test**: Copy each validation command from the README, run it, and confirm no "unrecognized option" errors.

**Acceptance Scenarios**:

1. **Given** the README validation checklist, **When** a user copies any listed command verbatim, **Then** the command executes without flag-position errors.

---

### User Story 8 — Rollback Tags Created for Greenfield Flow (Priority: P4)

The init command ensures a rollback tag exists even in the greenfield flow, enabling the validation checklist's rollback verification.

**Why this priority**: Low severity — rollback is a safety net feature, not part of the primary workflow. But the validation checklist references it.

**Independent Test**: Run the full greenfield flow and confirm `git tag -l 'dev-stack-rollback-*'` returns at least one tag.

**Acceptance Scenarios**:

1. **Given** a greenfield repo with no prior commits, **When** `dev-stack init` completes, **Then** a rollback tag is created (init creates an initial commit if none exists before tagging).
2. **Given** a greenfield repo with an existing commit, **When** `dev-stack init` completes, **Then** a rollback tag pointing to the pre-init commit is created.

### Edge Cases

- What happens when the user has a system-level mypy (e.g., via pyenv or Homebrew) but no venv-level mypy? The typecheck stage must check the venv — not the system PATH.
- What happens when `uv init --package` is run in a directory that already has a `src/` layout? Init must distinguish between "uv-generated expected files" and "pre-existing user files."
- What happens when `detect-secrets scan` finds findings in files listed in `.gitignore`? The security stage should focus on tracked files only.
- How does the pipeline behave when the `.venv` directory is deleted mid-workflow? Stages should fail gracefully rather than crash.
- What happens when `dev-stack init --dry-run` is run before any init has occurred? It should preview the full set of files that would be created.
- What happens when `dev-stack init` is run with `--modules` that conflict with already-installed modules? Should report the overlap clearly. *(Out of scope for this feature — future consideration.)*

## Requirements *(mandatory)*

### Functional Requirements

**Critical — Init Flow**

- **FR-001**: The typecheck pipeline stage MUST detect whether mypy is available *within the project virtual environment* rather than on the system PATH. If mypy is not in the venv, the stage MUST skip gracefully with a clear log message.
- **FR-002**: The `dev-stack init` command MUST install dev dependencies (ruff, mypy, pytest) into the project venv by running `uv sync --all-extras` during initialization, keeping dev tools in `[project.optional-dependencies]` rather than core dependencies.
- **FR-003**: The `dev-stack init` command MUST create a `.venv` directory by running `uv sync --all-extras` (not just `uv lock`) during initialization, ensuring the venv exists with all extras installed.

> **Traceability note**: FR-002 and FR-003 are both satisfied by a single `uv sync --all-extras` call. FR-002 emphasizes the *dependency installation* outcome; FR-003 emphasizes the *`.venv` creation* outcome. They are intentionally separate requirements to ensure both properties are independently verified.

**Critical — Conflict Detection**

- **FR-004**: The init command MUST recognize files created by `uv init --package` by checking a structural fingerprint of `pyproject.toml` (e.g., minimal `[project]` with no `[tool.*]` sections, default `description`, and uv-generated `[build-system]`). Files matching this fingerprint plus the full `uv init --package` output set — `src/<pkg>/__init__.py`, `.python-version`, and `README.md` — MUST be treated as greenfield predecessors, not conflicts. A `pyproject.toml` with custom tool config, extra dependencies, or non-default build systems MUST be treated as brownfield.
- **FR-005**: The init command MUST report `"mode": "greenfield"` when the only pre-existing files are those generated by `uv init --package`.

**High — Pipeline Accuracy**

- **FR-006**: When the pipeline runs with `--force` and hard-gate stages fail, the top-level JSON status MUST be `"completed_with_failures"` (not `"success"`) and the process MUST exit with a non-zero exit code (`ExitCode.PIPELINE_FAILURE`). The `--force` flag means "run all stages without aborting mid-pipeline" — not "suppress failure signals."
- **FR-007**: The dry-run flag on init MUST work on repos that already have `dev-stack.toml`. When re-run on an initialized repo, it MUST show a preview of what `update` would change — listing files that would be added, modified, or conflicted — without erroring or modifying files on disk.

**High — Environment Isolation**

- **FR-008**: Pipeline stage commands (pytest, mypy, ruff) MUST execute using the project venv's Python interpreter to prevent environment contamination from system-level packages.

**Medium — CLI Completeness**

- **FR-009**: The CLI MUST support a `--version` global flag that prints the package's semantic version number.
- **FR-010**: The `update` command MUST have a non-empty help description visible in `dev-stack --help`.
- **FR-011**: The README validation checklist MUST document the correct flag positions (global flags before the subcommand).

**Medium — Security Stage**

- **FR-012**: The security stage MUST use a `.secrets.baseline` file (the standard `detect-secrets` workflow) to manage known false positives. Init MUST generate an initial baseline; the stage MUST compare scan results against it and report FAIL only for new, unaudited findings.

**Low — Rollback & Greenfield Safety**

- **FR-013**: The init command MUST create a rollback tag in the greenfield flow. If no commits exist, init MUST create an initial commit before tagging.

### Key Entities

- **Pipeline Stage**: An individual step in the 9-stage automation pipeline; has a name, mode (hard/soft gate), execution status (pass/fail/skip), and optional skip reason.
- **Init Mode**: Classification of the target repository as `greenfield` (no prior project structure) or `brownfield` (existing project files); determines conflict detection behavior.
- **Conflict**: A file that init would overwrite but was not generated by a known predecessor tool (e.g., `uv init --package`). Distinguished from "expected predecessor files."
- **Rollback Tag**: A git tag (format: `dev-stack-rollback-*`) created before init modifies files, enabling full restoration.
- **Venv Context**: The project virtual environment (`.venv/`) within which all pipeline stages execute; must be isolated from system-level Python packages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can complete the full greenfield flow (clone → `uv init --package` → `dev-stack init` → first commit) without encountering any errors or needing `--no-verify`.
- **SC-002**: The typecheck stage skips gracefully in 100% of cases where mypy is not installed in the project venv, regardless of system-level mypy presence.
- **SC-003**: `dev-stack init` after `uv init --package` reports zero conflicts for `uv init`-generated files and correctly identifies the mode as "greenfield."
- **SC-004**: Pipeline JSON output accurately reflects stage results — hard-gate failures always surface in the top-level status, even under `--force`.
- **SC-005**: All 8 items in the README validation checklist pass when executed verbatim by a new user following the documented workflow.
- **SC-006**: `dev-stack --version` prints the semantic version number. `dev-stack --help` shows descriptions for all commands.
- **SC-007**: The security stage uses a `.secrets.baseline` file to distinguish real secrets from known false positives. Unaudited or confirmed-real secrets cause FAIL; findings audited as false positives (e.g., SHA-256 checksums in manifest files) are excluded.
- **SC-008**: `dev-stack --dry-run init` works on both fresh repos and already-initialized repos without errors.

## Assumptions

- Users follow the README-documented flow: `uv init --package` before `dev-stack init` for greenfield projects.
- The project uses `uv` as the package manager (not pip or poetry directly).
- `uv sync` with extras is a safe operation that does not break existing venvs.
- The `detect-secrets` baseline file approach is the standard mechanism for excluding known false positives.
- Pipeline stages that skip due to missing optional tools are considered passing (not failing).
