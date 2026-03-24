# Feature Specification: Universal Init Pipeline

**Feature Branch**: `012-universal-init-pipeline`  
**Created**: 2026-03-24  
**Status**: Draft  
**Input**: User description: "Dev-stack's init pipeline assumes every target repository is a Python project. When initializing a non-Python repo (e.g., markdown, YAML, shell scripts only), several modules produce incorrect, unnecessary, or broken artifacts. Six specific issues must be resolved so dev-stack correctly initializes any repository regardless of language or tech stack."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Non-Python Repo Init Produces a Clean Working Tree (Priority: P1)

A developer runs `dev-stack init` on a repository that contains only markdown files, YAML configs, and shell scripts — no Python source code. After initialization completes, the working tree is clean: no stray untracked files (`.secrets.baseline`, `.dev-stack/pipeline-skipped`), no failed commands (`uv sync`), and only the modules the user selected are present.

**Why this priority**: This is the core promise of universal init. If the working tree is dirty or commands fail on a non-Python repo, dev-stack is fundamentally broken for non-Python use cases.

**Independent Test**: Run `dev-stack init --modules hooks,speckit,vcs_hooks` in a repo with no Python files. Verify `git status` shows a clean tree (only expected tracked files changed), no error output, and exit code 0.

**Acceptance Scenarios**:

1. **Given** a git repository with only `.md`, `.yaml`, and `.sh` files, **When** the user runs `dev-stack init` without selecting `uv_project`, **Then** `uv sync` is never executed and no Python-specific artifacts are created.
2. **Given** a non-Python repo after successful init, **When** the user runs `git status`, **Then** no untracked files from dev-stack side effects appear (no `.secrets.baseline`, no `.dev-stack/pipeline-skipped`).
3. **Given** a non-Python repo after successful init, **When** the user inspects `dev-stack.toml`, **Then** no machine-specific absolute filesystem paths are committed.

---

### User Story 2 — Pre-Commit Hooks Adapt to Project Stack (Priority: P2)

A developer initializes dev-stack on a non-Python repo. The generated `.pre-commit-config.yaml` contains only hooks relevant to the target project's language and stack. Python-specific hooks (linting, type checking, test runner) are omitted when no Python source exists.

**Why this priority**: Hooks that reference missing tools fail noisily on every commit, making the developer experience painful and training users to bypass hooks entirely.

**Independent Test**: Initialize a non-Python repo with the hooks module. Confirm `.pre-commit-config.yaml` does not contain Python-specific hook entries. Then make a commit and verify all hooks pass.

**Acceptance Scenarios**:

1. **Given** a repo with no Python source files and the `hooks` module selected, **When** init completes, **Then** the generated `.pre-commit-config.yaml` does not include hooks for Python-specific tools (ruff, pytest, mypy).
2. **Given** a Python project repo with the `hooks` module selected, **When** init completes, **Then** the generated `.pre-commit-config.yaml` includes the full set of Python hooks (ruff, pytest, mypy) as it does today.
3. **Given** a mixed-language repo that includes at least some Python source files, **When** init completes, **Then** Python hooks are included (non-Python language hooks are out of scope for this feature).

---

### User Story 3 — Commit-Msg Hook Validates Agent Commit Body Sections (Priority: P3)

An AI agent creates a commit. The commit-msg hook validates not only the conventional commit subject line and trailers, but also that the required body sections (Intent, Reasoning, Scope, Narrative) are present. An agent commit with an empty body or missing sections is rejected.

**Why this priority**: Body section validation closes a gap where structurally invalid agent commits pass the hook, undermining the commit hygiene standards the project prescribes.

**Independent Test**: Create a commit message with a valid conventional commit subject and agent trailers but no body sections. Run the commit-msg hook. Verify it rejects the commit with a clear error message identifying the missing sections.

**Acceptance Scenarios**:

1. **Given** a commit message with agent trailers (`Agent:`, `Pipeline:`) but no body sections, **When** the commit-msg hook runs, **Then** it rejects the commit and lists the missing sections (Intent, Reasoning, Scope, Narrative).
2. **Given** a commit message with agent trailers and all four body sections present, **When** the commit-msg hook runs, **Then** it accepts the commit.
3. **Given** a commit message without agent trailers (human commit), **When** the commit-msg hook runs, **Then** body section validation is not enforced (human commits only require conventional commit subject).

---

### User Story 4 — Pipeline Skip Marker Is Always Gitignored (Priority: P4)

The `.dev-stack/pipeline-skipped` file is used by the pre-commit hook as a skip marker. This file must always be gitignored regardless of which modules are installed, so it never shows up as an untracked file.

**Why this priority**: An untracked skip marker dirties the working tree and confuses developers who didn't expect dev-stack to modify their repo state outside of selected modules.

**Independent Test**: Initialize a repo without `uv_project`. Trigger the pipeline skip marker to be written. Verify `git status` does not show it as untracked.

**Acceptance Scenarios**:

1. **Given** a repo initialized without `uv_project`, **When** the pipeline writes `.dev-stack/pipeline-skipped`, **Then** `git status` does not list it as untracked because `.dev-stack/pipeline-skipped` (or `.dev-stack/`) is covered by `.gitignore`.
2. **Given** a repo initialized with any combination of modules, **When** inspecting `.gitignore`, **Then** the `.dev-stack/` directory is covered within a `DEV-STACK:BEGIN:GITIGNORE` / `DEV-STACK:END:GITIGNORE` managed section.

---

### User Story 5 — Secrets Scanning Only Runs When Requested (Priority: P5)

Dev-stack does not generate a `.secrets.baseline` file during init unless the user has explicitly opted in to a secrets scanning module or configuration. No side effects from tools the user did not request.

**Why this priority**: Stray files from unrequested tools violate the module self-containment principle and pollute the working tree.

**Independent Test**: Run init without any secrets-related module. Verify `.secrets.baseline` does not exist after init.

**Acceptance Scenarios**:

1. **Given** init is run without a secrets scanning module, **When** init completes, **Then** no `.secrets.baseline` file is created in the repo.
2. **Given** init is run with a secrets scanning module explicitly selected, **When** init completes, **Then** `.secrets.baseline` is created as expected.

---

### User Story 6 — No Machine-Specific Paths in Committed Config (Priority: P6)

The `dev-stack.toml` manifest does not store absolute filesystem paths that are specific to the initializing machine. Agent detection paths are resolved at runtime, not persisted in committed config.

**Why this priority**: Machine-specific paths break portability and are useless to collaborators on other machines.

**Independent Test**: Run init and inspect `dev-stack.toml`. Verify no absolute filesystem paths appear in the file.

**Acceptance Scenarios**:

1. **Given** a user runs `dev-stack init`, **When** `dev-stack.toml` is written, **Then** it does not contain absolute filesystem paths in the `[agent]` section.
2. **Given** a collaborator clones a repo with `dev-stack.toml`, **When** they run any dev-stack command, **Then** the agent is detected dynamically at runtime without relying on persisted paths.

---

### Edge Cases

- What happens when a polyglot repo has some Python files but the user did not select `uv_project`? Hooks should detect languages from repo contents, not from module selection.
- What happens if `detect-secrets` is installed globally and runs as part of a pre-commit hook the user had before dev-stack init? Dev-stack must not interfere with pre-existing user hooks.
- What happens when a commit message body has some sections but not all four? The hook should report which specific sections are missing.
- What happens on a fresh repo with no `.gitignore` at all? The init pipeline must create one with at least the `.dev-stack/` entry.
- What happens if the agent path was previously persisted in `dev-stack.toml` and the user runs `dev-stack init --force`? The stale path should be removed, not preserved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The init pipeline MUST NOT execute `uv sync` unless the `uv_project` module is explicitly selected for installation.
- **FR-002**: The `security` pipeline stage MUST NOT run `detect-secrets scan` (and thus MUST NOT generate a `.secrets.baseline` file) unless a secrets scanning module is explicitly selected in the manifest.
- **FR-003**: The `commit-msg` hook MUST validate that agent commits (identified by the presence of `Agent:` trailer) contain all four required body sections: Intent, Reasoning, Scope, and Narrative.
- **FR-004**: The `commit-msg` hook MUST NOT enforce body section requirements on human commits (commits without agent trailers).
- **FR-005**: The hooks module MUST detect whether the target project contains Python source code by checking for the existence of any `.py` file in the repository (glob `**/*.py`), and conditionally include Python-specific hooks (ruff, pytest, mypy) in `.pre-commit-config.yaml`. Non-Python languages are out of scope for this feature; their hooks may be added in future iterations.
- **FR-006**: The hooks module MUST include the dev-stack pipeline hook in `.pre-commit-config.yaml` for all projects regardless of language.
- **FR-007**: The `dev-stack.toml` manifest MUST persist `agent.cli` (e.g., `"claude"`) as a portable preference hint, but MUST NOT persist `agent.path` or any other absolute filesystem path.
- **FR-008**: Agent detection MUST resolve the agent CLI path at runtime via `$PATH` lookup rather than relying on a stored path. The persisted `agent.cli` value serves only as a preference hint for which CLI to look for first.
- **FR-009**: The init pipeline MUST ensure `.dev-stack/` is in `.gitignore` using a `DEV-STACK:BEGIN:GITIGNORE` / `DEV-STACK:END:GITIGNORE` managed section. If `.gitignore` does not exist, it MUST be created. This applies regardless of which modules are installed.
- **FR-010**: Each module MUST be self-contained — no module may produce artifacts or side effects that depend on another module being present.
- **FR-011**: When body sections are missing from an agent commit, the commit-msg hook MUST provide a clear error message listing which specific sections are absent.
- **FR-012**: The hooks module MUST preserve any pre-existing user-defined hooks when generating `.pre-commit-config.yaml`, only adding dev-stack-managed hooks via managed section markers.

### Key Entities

- **Module**: A self-contained init plugin (e.g., `hooks`, `uv_project`, `vcs_hooks`, `speckit`) that produces specific artifacts for a repo. Modules declare dependencies and managed files.
- **Stack Profile**: A characterization of the target repository's languages and tooling, used by modules to adapt their output. Derived from file extensions and config files present in the repo.
- **Manifest (`dev-stack.toml`)**: The committed configuration file tracking installed modules, versions, and settings — must be portable across machines. Stores `agent.cli` as a preference hint but no absolute paths.
- **Managed Section**: A demarcated region within a file (bounded by `DEV-STACK:BEGIN` / `DEV-STACK:END` markers) that dev-stack owns and can update without disturbing user content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `dev-stack init` completes successfully on a non-Python repository (only markdown, YAML, shell scripts) with zero errors, zero warnings about missing tools, and a clean `git status` afterward.
- **SC-002**: 100% of agent commits with missing body sections are rejected by the commit-msg hook with an actionable error message.
- **SC-003**: 100% of human commits (no agent trailers) pass the commit-msg hook without body section enforcement.
- **SC-004**: After init on a non-Python repo, the `.pre-commit-config.yaml` contains zero Python-specific hook entries.
- **SC-005**: After init on a Python repo, the `.pre-commit-config.yaml` contains the same Python hook entries as the current behavior (no regressions).
- **SC-006**: `dev-stack.toml` contains zero absolute filesystem paths across any init scenario.
- **SC-007**: The `.dev-stack/` directory is gitignored in 100% of init scenarios regardless of module selection.

## Clarifications

### Session 2026-03-24

- Q: What scope of language support should the hooks module deliver for stack-aware hook generation? → A: Python-aware only. Detect whether Python is present; if yes, include Python hooks; if no, omit them. No hooks for other languages yet.
- Q: How does `.secrets.baseline` get created during init? → A: The `security` pipeline stage runs `detect-secrets scan` during pre-commit hook pipeline execution. Fix: security stage must skip secrets scanning when no secrets module is selected.
- Q: Should `dev-stack.toml` still persist the agent CLI name or drop all agent config? → A: Keep `cli` as a portable preference hint, drop only the `path` field. Runtime resolves path dynamically.
- Q: How should dev-stack manage the `.dev-stack/` gitignore entry? → A: Use `DEV-STACK:BEGIN` / `DEV-STACK:END` managed section markers in `.gitignore`. Create the file if absent. This is consistent with how dev-stack manages other shared files.
- Q: What counts as "Python present" for hook generation purposes? → A: Any `.py` file exists anywhere in the repository (simple glob check). No need for `pyproject.toml` or specific directory structure.

## Assumptions

- The `.secrets.baseline` file is created by the `security` pipeline stage (`_execute_security_stage`) which runs `detect-secrets scan` during pre-commit hook pipeline execution. The fix is to make this stage check whether a secrets scanning module is selected in the manifest before running.
- Python detection uses a simple heuristic: check whether any `.py` file exists anywhere in the repository (`**/*.py` glob). No need to inspect `pyproject.toml` or require a specific directory structure. This is intentionally broad to catch scripts, tests, and ad-hoc Python files.
- "Agent commit" vs "human commit" distinction is reliably determined by the presence of the `Agent:` trailer in the commit message.
- The four body sections (Intent, Reasoning, Scope, Narrative) are identified by `## Intent`, `## Reasoning`, `## Scope`, and `## Narrative` headings in the commit message body.
