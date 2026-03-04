# Feature Specification: Init & Pipeline Enhancements — UV Project Module, Sphinx Docs Split, Mypy Type-Checking

**Feature Branch**: `002-init-pipeline-enhancements`  
**Created**: 2026-02-28  
**Status**: Draft  
**Input**: User description: "Develop three interconnected enhancements to the dev-stack ecosystem that elevate project scaffolding, code quality gating, and documentation automation: UV Project Module, Deterministic Sphinx API Docs with Agent Narrative Docs, and Mypy Type-Checking Pipeline Stage."

## Clarifications

### Session 2026-02-28

- Q: Where should Sphinx build output go, and should it be committed to the repo or .gitignore-d? → A: Build to `docs/_build/` (Sphinx default) and add it to `.gitignore`. Not committed; CI rebuilds on demand.
- Q: How should brownfield `pyproject.toml` augmentation handle existing `[tool.*]` sections? → A: Skip-if-exists — only add `[tool.*]` sections that are entirely absent; leave existing user config untouched.
- Q: What specific mypy flags should the `[tool.mypy]` section include ("sensible strict defaults")? → A: Curated subset with `strict = false`: `warn_return_any = true`, `warn_unused_configs = true`, `disallow_incomplete_defs = true`, `check_untyped_defs = true`. Incremental path to full strict.
- Q: How should `dev-stack update` handle the new modules for existing repos initialized before this feature? → A: Offer interactively — `update` detects new available modules and prompts the user to opt in or skip each one. Never auto-installs new foundational modules.
- Q: Should `sphinx_docs` be included in `DEFAULT_GREENFIELD_MODULES` or be opt-in? → A: Default — include `sphinx_docs` in defaults. Batteries-included; the docs-api stage skips gracefully when Sphinx isn't installed, so the scaffolding files are low-cost placeholders.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Greenfield Init Produces a Complete Python Project (Priority: P1)

A developer creates a brand-new project and runs `dev-stack init`. In addition to the existing automation scaffolding (hooks, Spec Kit, MCP, CI, Docker, visualization), the system now also produces a fully-formed Python packaging structure — `pyproject.toml`, `src/<package>/__init__.py`, `.python-version`, `.gitignore`, a lockfile, and a test scaffold — so the developer can immediately write code, run tests, and publish to PyPI without any manual setup.

**Why this priority**: The UV Project module is the foundation for the other two features. Without a `pyproject.toml` and `src/` layout, neither Sphinx docs nor mypy have anything to operate on. This is the single most impactful improvement because it eliminates the manual bootstrapping gap that every greenfield user currently faces.

**Independent Test**: Run `dev-stack init` in an empty directory. Verify that `pyproject.toml` exists with `[build-system]`, `[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.coverage.run]`, and `[tool.mypy]` sections; `src/<pkg>/__init__.py` exists with a `main()` stub; `.python-version` is present; `.gitignore` is Python-specific; `uv.lock` is present; and `tests/test_placeholder.py` contains a passing test. Running `uv run pytest` succeeds immediately.

**Acceptance Scenarios**:

1. **Given** an empty directory, **When** the user runs `dev-stack init`, **Then** the system delegates to `uv init --package <dir-name>` to create `pyproject.toml`, `src/<pkg>/__init__.py`, `.python-version`, `.gitignore`, and `README.md`, then augments `pyproject.toml` with dev-stack opinionated tool configuration, creates `tests/__init__.py` and `tests/test_placeholder.py`, runs `uv lock` to produce `uv.lock`, and registers all files as managed artifacts.
2. **Given** a directory name with hyphens or special characters (e.g., `my-cool-project`), **When** the user runs `dev-stack init`, **Then** the system normalizes the directory name to a valid Python package identifier (e.g., `my_cool_project`) when invoking `uv init --package`.
3. **Given** a completed greenfield init, **When** the user runs the pre-commit pipeline test stage, **Then** the test stage runs `tests/test_placeholder.py` and passes (it no longer skips due to a missing `tests/` directory).
4. **Given** a completed greenfield init, **When** the user inspects `dev-stack.toml`, **Then** all UV-generated files (`pyproject.toml`, `src/<pkg>/__init__.py`, `.python-version`, `.gitignore`, `uv.lock`) appear in the managed files manifest with recorded hashes.

---

### User Story 2 — Brownfield Init With Existing Python Project (Priority: P1)

A developer has an existing repository that already contains a `pyproject.toml`, `src/` layout, or other Python packaging files. They run `dev-stack init` and the UV Project module detects every conflicting file, feeds them through the existing conflict-resolution flow, and never silently overwrites anything.

**Why this priority**: Brownfield safety is equally critical as greenfield scaffolding. Silently overwriting an existing `pyproject.toml` would destroy dependency declarations, build configuration, and project metadata — an unacceptable data-loss scenario.

**Independent Test**: Create a repository with an existing `pyproject.toml` containing custom dependencies. Run `dev-stack init`. Verify the system surfaces a conflict report for `pyproject.toml`, presents a diff, and respects the user's accept/skip/merge decision.

**Acceptance Scenarios**:

1. **Given** a repository with an existing `pyproject.toml`, **When** the user runs `dev-stack init`, **Then** the UV Project module's `preview_files()` method returns `pyproject.toml` (and any other conflicting files) in the conflict report, and the system presents the interactive resolution flow.
2. **Given** a repository with an existing `src/<pkg>/` directory but no `tests/` directory, **When** the user runs `dev-stack init`, **Then** the system creates `tests/__init__.py` and `tests/test_placeholder.py` without conflict (since they don't exist).
3. **Given** a repository with an existing `.python-version`, **When** the conflict resolution offers a merge, **Then** the user can choose to keep their existing version pin.

---

### User Story 3 — Pre-Commit Pipeline Includes Type Checking (Priority: P2)

A developer makes code changes and runs `git commit`. The pre-commit pipeline now includes a mypy type-checking stage that runs after linting and before testing. Type errors in the source code block the commit, catching bugs that linting alone cannot detect.

**Why this priority**: Static type checking closes a significant quality gap in the current pipeline. It sits between lint and test in value: cheaper to run than tests, catches a class of bugs that linting misses (wrong argument types, missing return types, None-safety violations). This is a direct improvement to every commit.

**Independent Test**: Create a Python file with a deliberate type error (e.g., calling a function with wrong argument types). Stage it and run `git commit`. Verify the pipeline rejects the commit at the typecheck stage with a clear error message pointing to the type violation.

**Acceptance Scenarios**:

1. **Given** staged changes with a type error, **When** the user runs `git commit`, **Then** the pipeline halts at the "typecheck" stage (stage 2, after lint) with an actionable error message from mypy and the commit is rejected.
2. **Given** staged changes that pass all type checks, **When** the pipeline continues, **Then** the test stage (stage 3) runs next.
3. **Given** a repository where mypy is not installed, **When** the pipeline runs, **Then** the typecheck stage skips with a warning ("mypy not found, skipping type check") and the pipeline continues to the test stage.
4. **Given** a greenfield project initialized with the UV Project module, **When** the user inspects `pyproject.toml`, **Then** a `[tool.mypy]` section is present with sensible strict defaults, and `mypy` is listed as a dev dependency.

---

### User Story 4 — Deterministic API Documentation From Source (Priority: P2)

A developer writes or updates Python docstrings in their source code. The pre-commit pipeline's "docs-api" stage runs Sphinx to mechanically generate API reference documentation from those docstrings. The build is deterministic — the same source always produces the same docs — and any Sphinx warning or error blocks the commit.

**Why this priority**: API reference documentation should be derived mechanically from source, not rewritten by an agent on every commit. This eliminates non-determinism from API docs, makes doc quality a gatable check, and frees the agent for higher-value narrative writing.

**Independent Test**: Add a Python function with a docstring. Stage and commit. Verify the "docs-api" stage runs Sphinx, produces output in `docs/_build/` or `docs/api/`, and exits successfully. Then introduce a malformed docstring (e.g., broken reStructuredText). Verify the stage fails and blocks the commit.

**Acceptance Scenarios**:

1. **Given** a project with documented Python source, **When** the pre-commit pipeline reaches the "docs-api" stage (stage 5), **Then** Sphinx builds API documentation from docstrings without errors, producing output in `docs/_build/`.
2. **Given** a Sphinx build that emits warnings, **When** the "docs-api" stage evaluates the result, **Then** the stage fails (hard gate) and the commit is rejected with the Sphinx warning output.
3. **Given** a greenfield project initialized with dev-stack, **When** the user inspects the project structure, **Then** `docs/conf.py`, `docs/index.rst`, and `docs/Makefile` exist, configured to point apidoc at `src/`, all three are tracked as managed files, and `docs/_build/` is added to `.gitignore`.
4. **Given** a project where Sphinx is not installed, **When** the "docs-api" stage runs, **Then** the stage skips with a warning rather than failing, allowing projects that haven't adopted Sphinx to proceed.

---

### User Story 5 — Agent-Driven Narrative Documentation (Priority: P3)

A developer commits changes and the pipeline's "docs-narrative" stage invokes the coding agent to produce or update curated narrative documentation — tutorials, quickstarts, architecture walkthroughs, capability guides — in `docs/guides/`. The agent no longer generates API reference material (that's handled by the deterministic "docs-api" stage). This stage is a soft gate: it skips gracefully if no agent is available.

**Why this priority**: Narrative documentation (tutorials, guides) is high-value content that benefits from AI generation, but it cannot be mechanically derived from source. By splitting this from API docs, each stage does what it's best at. This is lower priority because the deterministic API docs stage delivers the most immediate, reliable value.

**Independent Test**: Make a code change, stage it, and commit. Verify the "docs-narrative" stage runs after "docs-api", invokes the agent, and produces or updates content in `docs/guides/`. Then disconnect the agent and verify the stage skips with a warning.

**Acceptance Scenarios**:

1. **Given** staged changes and an available coding agent, **When** the pipeline reaches the "docs-narrative" stage (stage 6), **Then** the agent generates or updates narrative docs in `docs/guides/` focusing on tutorials, quickstarts, and walkthroughs — not API reference material.
2. **Given** no coding agent is available, **When** the "docs-narrative" stage runs, **Then** it skips gracefully with a warning and the pipeline continues.
3. **Given** the docs prompt template, **When** the agent receives instructions, **Then** the prompt explicitly directs the agent to produce narrative/tutorial content only, not API reference documentation.

---

### User Story 6 — Full 8-Stage Pipeline Execution (Priority: P2)

A developer runs the full pre-commit pipeline and observes all 8 stages executing in the correct order: lint → typecheck → test → security → docs-api → docs-narrative → infra-sync → commit-message. Stage counts, names, and ordering are consistent across CLI output, pipeline configuration, and all documentation.

**Why this priority**: The pipeline is the central automation artifact. If stage ordering, counts, or names are inconsistent across code, tests, documentation, and CLI output, the ecosystem loses credibility. This cross-cutting story ensures coherence.

**Independent Test**: Run `dev-stack pipeline --status` or trigger a full commit. Verify exactly 8 stages are listed, in the stated order, with correct hard/soft gate assignments.

**Acceptance Scenarios**:

1. **Given** a fully initialized project, **When** the user triggers the pre-commit pipeline, **Then** exactly 8 stages execute in order: lint (hard) → typecheck (hard) → test (hard) → security (hard) → docs-api (hard) → docs-narrative (soft) → infra-sync (soft) → commit-message (soft).
2. **Given** the pipeline configuration, **When** any test or contract asserts on stage count or names, **Then** it references 8 stages with the names and ordering above.
3. **Given** the user runs `dev-stack status`, **Then** the displayed pipeline stages match the 8-stage definition.

---

### User Story 7 — Managed Artifacts and Drift Detection (Priority: P3)

After initialization, all new files from the three features (UV-generated files, Sphinx config files, mypy config) are registered as managed artifacts. The infra-sync stage detects drift in these files and reports changes. Rollback restores them to their post-install state.

**Why this priority**: Drift detection and rollback are lifecycle management features. They are important for long-term trust but less urgent than getting the initial scaffolding and pipeline stages working correctly.

**Independent Test**: Initialize a project. Manually edit `docs/conf.py` or `pyproject.toml`. Run the pipeline. Verify infra-sync reports the drift. Then run `dev-stack rollback`. Verify the files are restored.

**Acceptance Scenarios**:

1. **Given** a project initialized with all three features, **When** the user manually edits a managed Sphinx config file, **Then** the infra-sync stage reports the drift with a hash mismatch.
2. **Given** a reported drift, **When** the user runs `dev-stack rollback`, **Then** the managed files are restored to their post-install state.
3. **Given** a project initialized with the UV Project module, **When** the user manually edits `uv.lock`, **Then** infra-sync detects the hash mismatch and reports it.

---

### Edge Cases

- What happens when `uv` is not installed on the system PATH? The UV Project module MUST fail with a clear error message ("uv CLI not found — install uv: https://docs.astral.sh/uv/getting-started/installation/") and abort initialization, since it is a required foundation module.
- What happens when the repository directory name contains characters invalid for Python package identifiers (e.g., leading digits, spaces)? The module MUST normalize the name (replace hyphens with underscores, strip invalid characters) and inform the user of the normalized package name.
- What happens when `uv init --package` fails (e.g., disk full, permission error)? The module MUST capture the error output, surface it to the user, and trigger the rollback flow so no partial artifacts remain.
- What happens when Sphinx is not installed but the "docs-api" stage is reached? The stage skips with a warning rather than failing, allowing gradual adoption.
- What happens when mypy is not installed but the "typecheck" stage is reached? The stage skips with a warning rather than failing.
- What happens when a brownfield project has a `pyproject.toml` that already contains `[tool.ruff]` or `[tool.mypy]` sections? The augmentation step MUST use skip-if-exists semantics: only add `[tool.*]` sections that are entirely absent in the existing file; leave existing user configuration untouched. No deep-merging or per-section conflict prompts.
- What happens when `uv lock` fails due to unresolvable dependencies after augmenting `pyproject.toml`? The module MUST report the dependency resolution failure, leave the `pyproject.toml` in place for manual correction, and not register `uv.lock` as managed.
- What happens when the project has no Python source files yet (empty `src/<pkg>/`)? Sphinx apidoc produces no documentation. The "docs-api" stage MUST pass (not fail) in this case, with output indicating no modules were found.
- What happens when a user who initialized before this feature runs `dev-stack update`? The update MUST detect the new `uv_project` and `sphinx_docs` modules, prompt the user to opt in or skip each one, and never auto-install foundational scaffolding without consent.

## Requirements *(mandatory)*

### Functional Requirements — UV Project Module

- **FR-001**: The system MUST delegate Python project scaffolding to `uv init --package <name>`, where `<name>` defaults to the repository directory name normalized to a valid Python package identifier.
- **FR-002**: The system MUST register all files produced by `uv init` (`pyproject.toml`, `src/<pkg>/__init__.py`, `.python-version`, `.gitignore`, `README.md`) as managed artifacts in the stack manifest, with recorded content hashes.
- **FR-003**: After `uv init` completes, the system MUST augment the generated `pyproject.toml` to add `[tool.ruff]` configuration, `[tool.pytest.ini_options]`, `[tool.coverage.run]`, a `[tool.mypy]` section with curated defaults (`strict = false`, `warn_return_any = true`, `warn_unused_configs = true`, `disallow_incomplete_defs = true`, `check_untyped_defs = true`, `python_version` matching `.python-version`), and dev-stack as a dev dependency. In brownfield mode, the augmentation MUST use skip-if-exists semantics: only add `[tool.*]` sections that are entirely absent; leave existing user configuration untouched.
- **FR-004**: After `uv init` completes, the system MUST add `sphinx`, `sphinx-autodoc-typehints`, and `myst-parser` to `[project.optional-dependencies] docs = [...]` in the generated `pyproject.toml`.
- **FR-005**: After `uv init` completes, the system MUST add `mypy` to `[project.optional-dependencies] dev = [...]` in the generated `pyproject.toml`.
- **FR-006**: The system MUST scaffold `tests/__init__.py` and `tests/test_placeholder.py` (containing a single passing test) after `uv init` completes.
- **FR-007**: After all augmentations, the system MUST run `uv lock` to produce a `uv.lock` file and register it as a managed artifact.
- **FR-008**: In brownfield mode, the module MUST feed conflicting files through the existing `ConflictReport` / interactive resolution flow — never silently overwrite.
- **FR-009**: The module MUST expose a `preview_files()` method that returns the list of files it would create, for brownfield conflict detection.
- **FR-010**: The module MUST have no `DEPENDS_ON` entries (it is a foundation module).
- **FR-011**: The module's `verify()` method MUST check that `pyproject.toml`, `src/<pkg>/__init__.py`, `.python-version`, and `uv.lock` exist.
- **FR-012**: The module MUST be included in `DEFAULT_GREENFIELD_MODULES` and execute before the hooks module during initialization.
- **FR-013**: When `uv` is not found on the system PATH, the module MUST fail with a clear error message and abort initialization.

### Functional Requirements — Sphinx Docs Pipeline Split

- **FR-014**: The current single "docs" pipeline stage (stage 4) MUST be replaced with two stages: "docs-api" (hard gate, deterministic, no agent) and "docs-narrative" (soft gate, agent-driven).
- **FR-015**: The "docs-api" stage MUST run Sphinx (apidoc + build) to generate API documentation from Python docstrings. It MUST fail on Sphinx warnings or errors.
- **FR-016**: The "docs-narrative" stage MUST invoke the coding agent to produce or update curated narrative documentation (tutorials, walkthroughs, guides) in `docs/guides/`. It MUST skip gracefully if no agent is available.
- **FR-017**: A new module ("sphinx_docs") MUST scaffold `docs/conf.py`, `docs/index.rst`, and `docs/Makefile` during initialization, with configuration pointing apidoc at `src/`.
- **FR-018**: The Sphinx docs module SHOULD depend on the UV Project module (since it needs `src/<pkg>/` to exist).
- **FR-019**: All Sphinx config files (`docs/conf.py`, `docs/index.rst`, `docs/Makefile`) MUST be registered as managed artifacts (drift-detectable, rollback-safe).
- **FR-019a**: The "docs-api" stage MUST output to `docs/_build/`, and `docs/_build/` MUST be added to `.gitignore` during initialization. Build output is NOT committed to the repo; CI regenerates it on demand.
- **FR-020**: The docs prompt template MUST be revised to instruct the agent to produce narrative/tutorial content only — not API reference material.
- **FR-021**: If Sphinx is not installed when the "docs-api" stage runs, the stage MUST skip with a warning rather than fail.

### Functional Requirements — Mypy Type-Checking Stage

- **FR-022**: The system MUST add a "typecheck" pipeline stage that runs mypy against the project source.
- **FR-023**: The typecheck stage MUST be a hard gate — type errors block the commit.
- **FR-024**: The typecheck stage MUST execute after lint (stage 1) and before test (stage 3), as stage 2.
- **FR-025**: If mypy is not installed (not on PATH), the stage MUST skip with a warning rather than fail.
- **FR-026**: The pre-commit hook configuration template MUST include a mypy hook entry.

### Functional Requirements — Cross-Cutting

- **FR-027**: The final pipeline MUST consist of exactly 8 stages in this order: lint → typecheck → test → security → docs-api → docs-narrative → infra-sync → commit-message.
- **FR-028**: `DEFAULT_GREENFIELD_MODULES` MUST be updated to include `uv_project` and `sphinx_docs` alongside the existing `hooks` and `speckit`. The full default set is: `("uv_project", "sphinx_docs", "hooks", "speckit")`.
- **FR-029**: Module install ordering during initialization MUST respect dependencies: uv_project → sphinx_docs → hooks → speckit → (other selected modules).
- **FR-030**: All existing tests (unit, integration, contract) that assert on stage counts, stage names, module lists, or init output MUST be updated to reflect the 8-stage pipeline and expanded module set.
- **FR-031**: The infra-sync stage MUST detect drift in all newly managed files (UV-generated files, Sphinx config files) by hash comparison against their post-install state.
- **FR-032**: During `dev-stack update`, if new modules (`uv_project`, `sphinx_docs`) are available but not installed in the target repo, the system MUST prompt the user interactively to opt in or skip each new module. New modules MUST NOT be auto-installed during update.

### Key Entities

- **UV Project Module (`uv_project`)**: A dev-stack module responsible for delegating Python project scaffolding to the `uv` CLI. Produces `pyproject.toml`, `src/<pkg>/__init__.py`, `.python-version`, `.gitignore`, `uv.lock`, and test scaffolding. Has no dependencies; is depended on by `sphinx_docs`.
- **Sphinx Docs Module (`sphinx_docs`)**: A dev-stack module responsible for scaffolding Sphinx configuration files (`docs/conf.py`, `docs/index.rst`, `docs/Makefile`). Depends on `uv_project`.
- **Pipeline Stage**: A named, ordered step in the pre-commit automation pipeline. Each stage has a failure mode (hard or soft), an optional agent requirement, and an executor function. The pipeline expands from 6 to 8 stages.
- **Managed Artifact**: A file tracked in the stack manifest with a content hash. Subject to drift detection by infra-sync and restoration by rollback.

## Assumptions

- The `uv` CLI (v0.5+) is available on the user's system PATH for greenfield initialization. This is a hard requirement for the UV Project module.
- The target Python version for mypy's `python_version` configuration defaults to the version pinned in `.python-version` (produced by `uv init`). The spec assumes Python 3.12+ as the baseline.
- Sphinx, sphinx-autodoc-typehints, and myst-parser are added as optional documentation dependencies (not required at runtime). Projects that don't install the docs extras will have the docs-api stage skip gracefully.
- The existing `ConflictReport` and interactive resolution flow from brownfield mode is fully functional and can handle the new files without modification to its core logic.
- The directory name normalization for Python package identifiers follows PEP 503 / PEP 625 conventions: hyphens become underscores, leading digits are prefixed, and invalid characters are stripped.
- The pre-commit-config.yaml template is the single source of truth for hook definitions; updating it with a mypy entry is sufficient to activate mypy in the pre-commit flow.
- Agent-driven narrative docs (stage 6) continue to use the existing `AgentBridge` infrastructure with no changes to agent invocation mechanics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A greenfield `dev-stack init` produces a fully functional Python project (pyproject.toml, src layout, tests, lockfile) in under 30 seconds, and `uv run pytest` passes immediately with zero manual steps.
- **SC-002**: 100% of files produced by the UV Project module are registered as managed artifacts and appear in `dev-stack status` output.
- **SC-003**: Brownfield initialization with an existing `pyproject.toml` never overwrites the file without explicit user consent — verified by 100% of brownfield conflict scenarios passing.
- **SC-004**: The pre-commit pipeline executes exactly 8 stages in the defined order, with all hard gates blocking on failure and all soft gates warning on failure.
- **SC-005**: Type errors in source code are caught before tests run — a commit containing a deliberate type error is rejected at the typecheck stage 100% of the time (when mypy is installed).
- **SC-006**: API documentation generated by Sphinx is deterministic — running the "docs-api" stage twice on identical source produces byte-identical output. To achieve this, the `conf.py` template MUST set `html_last_updated_fmt = None` (suppress timestamps) and the docs-api stage executor MUST set `SOURCE_DATE_EPOCH=0` in the subprocess environment.
- **SC-007**: All existing tests (unit, integration, contract) pass after the pipeline expands from 6 to 8 stages, with zero regressions.
- **SC-008**: Drift detection identifies manual edits to any managed file (UV artifacts, Sphinx configs) within a single pipeline run.
