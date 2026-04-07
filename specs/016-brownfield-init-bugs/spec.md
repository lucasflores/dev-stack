# Feature Specification: Brownfield Init Bug Remediation

**Feature Branch**: `016-brownfield-init-bugs`
**Created**: 2026-04-07
**Status**: Draft
**Input**: User description: "Brownfield init bug remediation — 8 bugs found during brownfield init that need reproduction, verification, and fix."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Commit-Message Hook Strips Markdown Headers (Priority: P1)

A developer using agent-generated commits relies on structured `## Intent`, `## Reasoning`, `## Scope`, and `## Narrative` sections in the commit body. The commit-message hook strips all lines starting with `#`, including these required markdown headers, causing UC5 validation to always fail on agent commits. This makes agent-assisted workflows unusable.

**Why this priority**: This is a logic conflict between two core subsystems — the hook pre-processor and the UC5 rule. It blocks every agent-generated commit, making the agent workflow entirely non-functional.

**Independent Test**: Create a commit message file containing `## Intent` headers and run the commit-msg hook; verify the headers survive stripping and UC5 passes.

**Acceptance Scenarios**:

1. **Given** a commit message with `## Intent`, `## Reasoning`, `## Scope`, and `## Narrative` body sections, **When** the commit-msg hook processes the message, **Then** all four markdown headers are preserved in the cleaned message passed to gitlint.
2. **Given** a commit message containing git comment lines (lines matching `# <text>` or bare `#`), **When** the hook processes the message, **Then** only git comment lines are stripped — not markdown headers with `##` or deeper.
3. **Given** a commit message with mixed git comments and markdown headers, **When** UC5 validates the body, **Then** all required `##` sections are found and the commit passes.

---

### User Story 2 — False Greenfield Classification (Priority: P1)

A developer runs `dev-stack init` on a repo that contains existing Python source files (e.g., `eval/`, `config/` packages at the repo root) but has no filename collisions with dev-stack managed files. The system incorrectly classifies this as a greenfield project and runs a full scaffolding pass, overwriting or ignoring existing work.

**Why this priority**: Misclassification changes the entire init pathway. Every downstream step (scaffolding, dependency handling, config generation) produces wrong results when the mode is incorrect.

**Independent Test**: Run `dev-stack init` on a repo containing `.py` files outside `src/` with no `pyproject.toml` or with a non-`uv_build` `pyproject.toml`; verify the system classifies it as brownfield.

**Acceptance Scenarios**:

1. **Given** a repository with Python files (`.py`) or Python packages (directories with `__init__.py`) at the repo root but no `pyproject.toml`, **When** `dev-stack init` runs, **Then** the system classifies the repo as brownfield.
2. **Given** a repository with a `pyproject.toml` that uses `uv_build` backend and default description but also contains Python packages at the repo root, **When** `dev-stack init` runs, **Then** the system classifies the repo as brownfield because pre-existing source code is detected at depth 1.
3. **Given** a truly empty repository (no `.py` files or Python packages at root, no `pyproject.toml`), **When** `dev-stack init` runs, **Then** the system still classifies it as greenfield.
4. **Given** a repository where `.py` files exist only in `.venv/` or `__pycache__/`, **When** `dev-stack init` runs, **Then** those are excluded and the repo is classified as greenfield.

---

### User Story 3 — APM Version Parse Crash (Priority: P1)

A developer has the APM CLI installed. When `dev-stack init` or `dev-stack apm install` runs, the APM CLI outputs its version string decorated with Rich box-drawing or ANSI escape characters. The version parser crashes because `packaging.version.Version` cannot parse ANSI-decorated strings.

**Why this priority**: This crash blocks all APM operations (install, verify, audit) for any user whose APM CLI outputs styled version text. It halts the entire init pipeline.

**Independent Test**: Mock `apm --version` output with ANSI escape sequences and box-drawing characters; verify the version is correctly extracted and compared.

**Acceptance Scenarios**:

1. **Given** the APM CLI outputs a version string wrapped in ANSI escape sequences (e.g., `\x1b[1m0.8.2\x1b[0m`), **When** the version check runs, **Then** the system strips ANSI codes and correctly parses `0.8.2`.
2. **Given** the APM CLI outputs Rich box-drawing characters around the version (e.g., `╭─ apm v0.8.2 ─╮`), **When** the version check runs, **Then** the system extracts `0.8.2` and validates it against the minimum version.
3. **Given** the APM CLI outputs a clean version string with no decoration, **When** the version check runs, **Then** parsing continues to work as before.

---

### User Story 4 — First Commit Guarantee Broken for Brownfield (Priority: P2)

A developer initializes dev-stack on an existing brownfield repo. The README promises that the first commit after init will always pass all checks. However, pre-existing unformatted code triggers lint hard-gate failures (ruff format, ruff check) on the first commit — breaking the guarantee.

**Why this priority**: A broken first-commit experience causes immediate trust loss. Users cannot complete onboarding without manually reformatting their entire pre-existing codebase first.

**Independent Test**: Initialize dev-stack on a repo with intentionally unformatted Python code, then attempt a commit; verify the lint gate either auto-formats or skips pre-existing code on the first commit.

**Acceptance Scenarios**:

1. **Given** a brownfield repo with unformatted Python files and a freshly initialized dev-stack, **When** the developer makes the first commit, **Then** the pipeline auto-formats all Python files via `ruff format` before the lint hard-gate evaluates, and the commit passes.
2. **Given** the first commit has already been made, **When** the developer makes subsequent commits with unformatted code, **Then** the lint hard-gate fails normally (no auto-format).
3. **Given** the above scenario, **When** the developer views documentation, **Then** the README documents that brownfield first-commits include an automatic formatting pass.

---

### User Story 5 — requirements.txt Not Migrated (Priority: P2)

A developer initializes dev-stack on a brownfield repo that has an existing `requirements.txt`. The existing dependencies are silently ignored — they are not merged into `pyproject.toml` and no warning is shown. The developer discovers missing dependencies only at runtime.

**Why this priority**: Silent data loss of dependency information leads to broken builds and wasted debugging time. Users expect either automatic migration or a clear warning.

**Independent Test**: Place a `requirements.txt` with several dependencies in a repo, run `dev-stack init`, and verify dependencies appear in `pyproject.toml` or a warning is displayed.

**Acceptance Scenarios**:

1. **Given** a brownfield repo with a `requirements.txt` file, **When** `dev-stack init` runs interactively, **Then** the system parses the file, displays a preview of the dependencies, and prompts the user for confirmation before merging into `pyproject.toml`.
2. **Given** a `requirements.txt` with pinned versions (e.g., `requests==2.31.0`), **When** the user confirms the merge, **Then** version constraints are preserved in the `[project.dependencies]` format.
3. **Given** a `requirements.txt` with comments and blank lines, **When** the system reads it, **Then** only valid dependency lines are shown in the preview.
4. **Given** a non-interactive environment (CI), **When** `dev-stack init` encounters `requirements.txt`, **Then** the system emits a warning listing the un-migrated dependencies and skips the merge.
5. **Given** the user declines the confirmation prompt, **When** `dev-stack init` continues, **Then** no changes are made to `pyproject.toml` and the init pipeline proceeds normally.

---

### User Story 6 — Existing Packages Invisible to uv_project (Priority: P2)

A developer has Python packages at the repo root (e.g., `eval/`, `config/`, `utils/`) that are not under `src/`. After init, the `uv_project` module scaffolds an empty `src/` layout without detecting or mentioning the existing packages. The developer has no guidance on how to migrate them.

**Why this priority**: Invisible packages mean the developer's existing code is disconnected from the build system, test runner, and type checker with no explanation.

**Independent Test**: Create a repo with top-level Python packages (directories with `__init__.py`), run init, and verify the system detects and reports them.

**Acceptance Scenarios**:

1. **Given** a brownfield repo with Python packages at the repo root (directories containing `__init__.py`), **When** `dev-stack init` runs, **Then** the system detects and lists these packages in its output.
2. **Given** detected root-level packages, **When** the init completes, **Then** the output recommends moving them into the `src/` layout (e.g., `mv eval/ src/eval/`) for compatibility with the `uv_build` backend and dev-stack toolchain.

---

### User Story 7 — --json Pipeline Run Broken (Priority: P3)

A developer or CI system runs `dev-stack --json <command>` expecting machine-readable JSON output as documented in the README. For certain commands or pipeline runs, no JSON output is produced — only human-readable text is emitted.

**Why this priority**: Broken JSON output prevents CI integration and automated tooling from consuming dev-stack output, but human workflows are unaffected.

**Independent Test**: Run `dev-stack --json init` and `dev-stack --json pipeline run` and verify all output is valid JSON.

**Acceptance Scenarios**:

1. **Given** a user runs any dev-stack command with the `--json` flag, **When** the command completes (success or failure), **Then** all primary output is valid, parseable JSON.
2. **Given** the `--json` flag is set, **When** a pipeline stage produces output, **Then** each stage result is included in the JSON payload.
3. **Given** the `--json` flag is not set, **When** commands run, **Then** output behavior is unchanged (human-readable text).

---

### User Story 8 — Typecheck Blind to Existing Code (Priority: P3)

A developer has Python packages outside `src/` (e.g., at the repo root). The mypy configuration generated by dev-stack sets `mypy_path` to `src` only, meaning existing code in other directories is never type-checked. No warning is shown about uncovered code.

**Why this priority**: While not a blocker, this creates a false sense of type safety — developers believe their code is checked when it is not.

**Independent Test**: Place typed Python code with deliberate type errors outside `src/`, run the type-check pipeline stage, and verify those errors are reported.

**Acceptance Scenarios**:

1. **Given** a brownfield repo with typed Python packages outside `src/`, **When** the mypy pipeline stage runs, **Then** a warning is emitted listing the uncovered packages and recommending migration to the `src/` layout.
2. **Given** the system detects packages outside `src/`, **When** mypy config is generated, **Then** `mypy_path` remains set to `src` (not automatically expanded) and the warning includes the specific package names.

---

### Edge Cases

- What happens when `requirements.txt` contains editable installs (`-e .`) or URL-based dependencies?
- What happens when a repo has both `requirements.txt` and `requirements-dev.txt`?
- What happens when the APM CLI outputs multi-line version information (e.g., version + build metadata)?
- What happens when a brownfield repo has nested Python packages (e.g., `lib/mypackage/`)?
- What happens when a commit message intentionally uses `#` as a comment character mid-line (not at line start)?
- What happens when `--json` is combined with `--verbose`?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The commit-message hook MUST only strip git comment lines (lines matching `^# ` or `^#$`) and MUST preserve markdown header lines (`##`, `###`, etc.).
- **FR-002**: The greenfield detection logic MUST check for pre-existing `.py` files or directories containing `__init__.py` at the repository root (depth 1 only, excluding `.git`, `__pycache__`, `.venv`, `node_modules`, `.tox`) when determining if a repo is greenfield or brownfield.
- **FR-003**: The APM version parser MUST strip ANSI escape sequences and non-alphanumeric decorations from CLI output before parsing the version string.
- **FR-004**: When a `requirements.txt` exists during brownfield init, the system MUST parse the file, display a preview of dependencies to be added, and prompt the user for confirmation before merging into `pyproject.toml`. In non-interactive mode (CI), the system MUST emit a warning listing un-migrated dependencies and skip the merge.
- **FR-005**: The init pipeline MUST scan for Python packages at the repo root (directories containing `__init__.py`, using a shared helper in `uv_project`) during brownfield init, list them in the output, and recommend migrating them into the `src/` layout.
- **FR-006**: The `--json` flag MUST produce valid JSON output for all commands that support it (`init`, `status`, `apm`, `visualize`, `pipeline`, `update`, `rollback`, `hooks`, `version`, `release`, `changelog`, `pr`), including full pipeline runs.
- **FR-007**: On the first commit after a brownfield init, the pipeline MUST auto-format pre-existing code (via `ruff format`) before the lint hard-gate runs, so the commit passes without manual intervention. Subsequent commits MUST be hard-gated normally. The README MUST document that brownfield first-commits include an automatic formatting pass.
- **FR-008**: The mypy configuration MUST keep `mypy_path` set to `src`. When root-level Python packages are detected outside `src/`, the system MUST emit a warning listing the uncovered packages and recommending `src/` migration.

### Key Entities

- **Init Mode**: Classification of a repository as either greenfield (no existing code) or brownfield (pre-existing code). Drives all downstream init behavior.
- **Commit Message**: Structured text with a subject line and optional body containing markdown-formatted sections. Processed by the hook before validation rules.
- **Pipeline Stage**: An individual check (lint, format, typecheck) in the commit pipeline. Each stage can pass, fail, skip, or warn.
- **Managed File**: A file created or modified by dev-stack modules (e.g., `pyproject.toml`, `apm.yml`). Conflicts arise when managed files overlap with pre-existing files.

## Assumptions

- The git comment character is `#` (the default). Custom `core.commentChar` settings are out of scope for this fix.
- The APM CLI version output contains a semantic version string somewhere in its stdout. The exact format may vary between APM versions.
- `requirements.txt` follows standard pip format (one dependency per line, optional version pinning, comments with `#`).
- The "first commit guarantee" refers specifically to the initial commit after running `dev-stack init`, not subsequent commits.
- Brownfield repos may have Python packages in non-standard layouts (flat, root-level, nested). Detection focuses on directories containing `__init__.py` at the repo root (depth 1). Deeply nested packages (e.g., `lib/mypackage/`) are out of scope for automatic detection.

## Clarifications

### Session 2026-04-07

- Q: When a brownfield repo has an existing `requirements.txt`, should dev-stack auto-merge deps, warn-only, or auto-merge with confirmation? → A: Auto-merge with confirmation (preview + prompt; warn-only in CI).
- Q: How should the lint gate handle pre-existing unformatted code on the first brownfield commit? → A: Auto-format via `ruff format` on first commit, then hard-gate normally on subsequent commits.
- Q: When adding `.py` file detection for greenfield classification, how deep should the scan go? → A: Root-level only (depth 1), excluding `.git`, `__pycache__`, `.venv`, `node_modules`, `.tox`.
- Q: When `uv_project` detects root-level Python packages during brownfield init, what should the guidance recommend? → A: Recommend moving packages into `src/` layout (e.g., `mv eval/ src/eval/`).
- Q: Should mypy config auto-include detected root-level package directories, or warn-only? → A: Warn-only — keep `mypy_path = "src"`, emit a warning listing uncovered packages that need `src/` migration.
- Q: Does `requirements-dev.txt` get migrated alongside `requirements.txt`? → A: Out of scope — only `requirements.txt` is handled. `requirements-dev.txt` and other variant files are not migrated.
- Q: How does `--json` interact with `--verbose`? → A: When `--json` is set, `--verbose` adds a `"debug"` key to the JSON payload with additional diagnostic fields. Human-readable verbose output is suppressed.
- Q: Does auto-format on the first brownfield commit require explicit user consent? → A: Running `dev-stack init` on a brownfield repo constitutes consent for first-commit auto-formatting. The init output and README document this behavior. No additional prompt is required — the `ruff format` pass is part of the documented init contract.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of agent-generated commits with `## Intent/Reasoning/Scope/Narrative` headers pass the commit-msg hook and UC5 validation without manual intervention.
- **SC-002**: Repos containing `.py` files outside `src/` are classified as brownfield in 100% of cases during init.
- **SC-003**: APM version check succeeds for CLI outputs containing ANSI escape codes, box-drawing characters, or plain text — zero parse crashes.
- **SC-004**: Developers see an explicit message about un-migrated `requirements.txt` dependencies within the init output for 100% of brownfield repos that contain the file.
- **SC-005**: All root-level Python packages are listed in init output for brownfield repos, with migration guidance provided.
- **SC-006**: Every command that accepts `--json` produces output that parses as valid JSON, verified by automated tests.
- **SC-007**: The first commit after brownfield init succeeds without requiring manual code reformatting.
- **SC-008**: A warning listing uncovered Python packages outside `src/` is emitted during brownfield init and mypy pipeline stage, with migration guidance.
