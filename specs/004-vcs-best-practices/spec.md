# Feature Specification: Version Control Best Practices Automation

**Feature Branch**: `004-vcs-best-practices`  
**Created**: 2026-03-08  
**Status**: Draft  
**Input**: User description: "Add a comprehensive version control best practices automation layer to dev-stack — commit message linting, branch naming enforcement, git hook lifecycle management, PR auto-description generation, changelog generation, semantic release versioning, signed commit enforcement, and constitutional-level agent behavioral practices for atomic commits and test-driven development."

## Clarifications

### Session 2026-03-08

- Q: When dev-stack is upgraded and hook templates change, what should `dev-stack init` do on re-run? → A: Auto-update managed hooks if checksum matches manifest (unmodified); skip with warning if manually modified.
- Q: Should dev-stack declare and enforce a minimum git version for SSH signing? → A: Check git version only when SSH signing is enabled; warn and skip signing configuration if git < 2.34.
- Q: Which directory level should the scope advisory "3+ directories" heuristic measure? → A: Both — two independent rules: (1) 3+ repo-root directories triggers it, and (2) 3+ source subpackages (e.g., cli/, modules/, pipeline/ under the main package) triggers it.
- Q: How should dev-stack integrate instructions into agent-specific files (append vs symlink)? → A: Append with managed section markers (`<!-- === DEV-STACK:INSTRUCTIONS:BEGIN === -->` / `END`), idempotent and updatable on re-init. Reuses the existing managed-marker pattern from README injection.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Commit Message Linting on Every Commit (Priority: P1)

A developer (human or AI agent) authors a commit in a dev-stack-enabled repository. When they run `git commit`, the `commit-msg` hook automatically validates the message against conventional commit format and trailer rules before the commit is finalized. Violations produce a clear, actionable error message and the commit is rejected.

**Why this priority**: Commit message quality is the foundation that every other capability in this feature relies upon — PR descriptions, changelogs, and release versioning all parse commit subjects and trailers. Without consistent message format, downstream automation breaks.

**Independent Test**: Can be fully tested by initializing a dev-stack project, making a code change, and attempting commits with valid and invalid messages. Delivers value by catching malformed commits immediately.

**Acceptance Scenarios**:

1. **Given** a dev-stack-initialized repo with `commit-msg` hook installed, **When** a user commits with message `feat(cli): add pr command`, **Then** the commit succeeds without errors.
2. **Given** a dev-stack-initialized repo, **When** a user commits with message `added stuff`, **Then** the hook rejects the commit with an error explaining conventional commit format.
3. **Given** a pipeline-generated commit (contains `Agent` trailer), **When** the commit message is missing required trailers (`Spec-Ref`, `Task-Ref`, `Pipeline`, `Edited`), **Then** the hook rejects the commit listing the missing trailers.
4. **Given** a manually authored commit (no `Agent` trailer), **When** the subject line is valid conventional commit format, **Then** the commit succeeds even without trailers.
5. **Given** a commit with `Spec-Ref: specs/999-nonexistent/spec.md`, **When** the hook validates trailer values, **Then** the commit is rejected with an error that the referenced path does not exist.
6. **Given** a commit with `Pipeline: lint=pass,typecheck=fail`, **When** the hook validates the `Pipeline` trailer, **Then** the hook emits a warning (not a block) about the failed stage.

---

### User Story 2 — Git Hook Lifecycle Management (Priority: P1)

A developer runs `dev-stack init` in their repository. The system installs managed git hooks (`commit-msg`, `pre-push`, and optionally `pre-commit`) into `.git/hooks/`. The developer can later check hook status, and when they uninstall dev-stack, the hooks are cleanly removed.

**Why this priority**: Hook management is the enforcement mechanism for commit linting (Story 1) and branch naming (Story 3). Without it, validation rules exist but are never triggered.

**Independent Test**: Can be tested by running `dev-stack init`, inspecting `.git/hooks/` for managed hook files, verifying hook headers, running `dev-stack hooks status`, and running `dev-stack uninstall` to confirm cleanup.

**Acceptance Scenarios**:

1. **Given** a fresh git repository, **When** the user runs `dev-stack init`, **Then** `commit-msg` and `pre-push` hook scripts are written to `.git/hooks/` with a managed header comment, and `.dev-stack/hooks-manifest.json` records each hook's name, checksum, and installation timestamp.
2. **Given** a repo where `.git/hooks/commit-msg` already exists and was NOT installed by dev-stack, **When** the user runs `dev-stack init`, **Then** the existing hook is NOT overwritten and the user receives a warning with instructions for manual integration.
3. **Given** a dev-stack-initialized repo, **When** the user runs `dev-stack hooks status`, **Then** the output lists each managed hook, its installation date, and whether the file matches the expected checksum or has been manually modified.
4. **Given** a dev-stack-initialized repo, **When** the user runs `dev-stack uninstall`, **Then** all managed hooks whose files still match the expected checksum are removed, and the manifest is cleared.
5. **Given** `[tool.dev-stack.hooks] pre-commit = true` in `pyproject.toml`, **When** the user runs `dev-stack init`, **Then** a `pre-commit` hook running lint and typecheck pipeline stages is also installed.

---

### User Story 3 — Branch Naming Enforcement (Priority: P2)

A developer creates a local branch with any name and works freely. When they attempt to push a branch to the remote, the `pre-push` hook validates the branch name against a configurable pattern. Non-compliant branch names are blocked from pushing.

**Why this priority**: Branch naming consistency is important for traceability and release automation, but it has less immediate impact than commit-level validation (Story 1). Developers can work locally with any name and only need compliance at push time.

**Independent Test**: Can be tested by creating branches with valid and invalid names and attempting `git push`. Delivers value by enforcing consistent naming across all contributors.

**Acceptance Scenarios**:

1. **Given** a dev-stack-initialized repo with default branch pattern, **When** a user pushes branch `feat/003-codeboarding-viz`, **Then** the push succeeds.
2. **Given** a dev-stack-initialized repo, **When** a user pushes branch `my-random-branch`, **Then** the push is rejected with an error showing the required pattern.
3. **Given** exempt branches configured as `["main", "master", "develop"]`, **When** a user pushes branch `main`, **Then** the push succeeds without pattern validation.
4. **Given** a custom pattern in `pyproject.toml` under `[tool.dev-stack.branch]`, **When** the pre-push hook runs, **Then** the custom pattern is used instead of the default.
5. **Given** a spec-kit workflow is active and `spec.md` declares a feature branch, **When** the current branch name does not match the spec's declared branch, **Then** a warning is emitted (non-blocking).

---

### User Story 4 — Constitutional Practices for Agents (Priority: P2)

A developer initializes a project with dev-stack. The initialization generates a constitution template (for spec-kit users) and an instructions file (for non-spec-kit users) containing non-negotiable practices for atomic commits and test-driven development. When an agent operates in the repository, these instructions are available in its context.

**Why this priority**: Behavioral guardrails for AI agents represent a key differentiator of dev-stack. However, they produce value only when agents actually read and follow the instructions, which makes this P2 relative to the hard-enforcement capabilities.

**Independent Test**: Can be tested by running `dev-stack init`, verifying the generated constitution template and instructions file contain the required clauses, and verifying that agent-specific file detection/linking works.

**Acceptance Scenarios**:

1. **Given** a fresh repository, **When** the user runs `dev-stack init`, **Then** a `constitution-template.md` is generated containing "Dev-Stack Baseline Practices" with "Atomic Commits" and "Test-Driven Development" subsections, plus a "User-Defined Requirements" section.
2. **Given** a fresh repository, **When** the user runs `dev-stack init`, **Then** `.dev-stack/instructions.md` is generated containing the same atomic commit and TDD clauses.
3. **Given** a repository containing `.github/copilot-instructions.md`, **When** `dev-stack init` runs, **Then** the user is prompted to inject dev-stack instructions into the Copilot file using managed section markers, and the injected content is wrapped in `<!-- === DEV-STACK:INSTRUCTIONS:BEGIN === -->` / `<!-- === DEV-STACK:INSTRUCTIONS:END === -->` markers.
4. **Given** a repository containing `CLAUDE.md`, **When** `dev-stack init` runs, **Then** the user is prompted to inject dev-stack instructions into the Claude file using managed section markers.
5. **Given** a repository with no recognized agent instruction files, **When** `dev-stack init` runs, **Then** only `.dev-stack/instructions.md` is created and no agent-file prompts are shown.

---

### User Story 5 — PR Auto-Description Generation (Priority: P3)

A developer finishes work on a feature branch and runs `dev-stack pr`. The command collects all commits on the branch, aggregates their trailers, and produces a structured Markdown PR description. If a supported CLI tool is available, it creates the PR directly.

**Why this priority**: PR creation is a frequent but non-critical workflow step. The description is generated from commits (requires Story 1), so it naturally comes after commit quality is established.

**Independent Test**: Can be tested by creating a branch with several commits (some with trailers, some without), running `dev-stack pr --dry-run`, and verifying the rendered Markdown output.

**Acceptance Scenarios**:

1. **Given** a branch with 5 commits (3 with full trailers, 2 manual), **When** the user runs `dev-stack pr --dry-run`, **Then** the rendered Markdown includes: a summary, spec references, task references, AI provenance breakdown, aggregated pipeline status, and a commit list.
2. **Given** GitHub CLI (`gh`) is installed and the remote is GitHub, **When** the user runs `dev-stack pr`, **Then** a pull request is created on GitHub using the rendered description.
3. **Given** neither `gh` nor `glab` is installed, **When** the user runs `dev-stack pr`, **Then** the rendered Markdown is printed to stdout.
4. **Given** a branch with no commits ahead of `main`, **When** the user runs `dev-stack pr`, **Then** the command exits with a clear message that there are no changes to create a PR for.

---

### User Story 6 — Changelog Generation (Priority: P3)

A developer runs `dev-stack changelog` to generate or update a `CHANGELOG.md` from the repository's conventional commit history. The changelog groups changes by type, annotates AI-authored commits, and links to specs.

**Why this priority**: Changelogs are a release-time artifact. They provide value for project communication but are not part of the core commit-time enforcement loop.

**Independent Test**: Can be tested by making a series of conventional commits (with and without trailers), running `dev-stack changelog`, and verifying the output markdown groups changes correctly with the expected annotations.

**Acceptance Scenarios**:

1. **Given** a repository with tagged releases and conventional commits, **When** the user runs `dev-stack changelog --unreleased`, **Then** a `CHANGELOG.md` is generated/updated covering changes since the last tag, grouped by commit type.
2. **Given** some commits have `Agent` trailers, **When** the changelog is rendered, **Then** those entries are annotated with an AI provenance marker.
3. **Given** some commits have `Edited: true` trailers, **When** the changelog is rendered, **Then** those entries are annotated with a human-edited marker.
4. **Given** git-cliff is not installed, **When** the user runs `dev-stack changelog`, **Then** the command exits with a clear error message and installation instructions.

---

### User Story 7 — Semantic Release Versioning (Priority: P3)

A maintainer runs `dev-stack release` to infer the next version from conventional commit history, bump the version in `pyproject.toml`, generate the changelog entry, and tag the release.

**Why this priority**: Release versioning is the culmination of the commit pipeline. It requires all upstream capabilities (linting, changelogs) to be in place, making it the last story to implement.

**Independent Test**: Can be tested by creating commits of various types (`feat`, `fix`, with `BREAKING CHANGE`), running `dev-stack release --dry-run`, and verifying the correct semver bump is inferred and the expected actions are listed.

**Acceptance Scenarios**:

1. **Given** 3 `fix` commits since the last tag `v1.2.0`, **When** the user runs `dev-stack release --dry-run`, **Then** the output shows the inferred next version as `v1.2.1` with a patch bump.
2. **Given** 1 `feat` commit among the changes, **When** the user runs `dev-stack release`, **Then** the version is bumped as a minor release, `pyproject.toml` is updated, `CHANGELOG.md` is updated, and tag `v{version}` is created.
3. **Given** a commit with `BREAKING CHANGE` footer, **When** the user runs `dev-stack release`, **Then** a major version bump is inferred.
4. **Given** `--bump patch` is passed, **When** the user runs `dev-stack release --bump patch`, **Then** the override bump is applied regardless of commit types.
5. **Given** a commit on the branch has `Pipeline: typecheck=fail` (a HARD-failure stage), **When** the user runs `dev-stack release`, **Then** the command refuses to release and lists the offending commit.
6. **Given** python-semantic-release is not installed, **When** the user runs `dev-stack release`, **Then** a fallback built-in implementation handles version inference and `pyproject.toml` bumping.

---

### User Story 8 — Signed Commit Enforcement (Priority: P4)

A developer opts into signed commits via dev-stack configuration. During `dev-stack init`, SSH signing is configured locally. At push time, the pre-push hook warns or blocks if agent-generated commits are unsigned.

**Why this priority**: Signed commits are an advanced provenance feature. They add significant trust guarantees but require external setup (SSH keys) and are opt-in, making them lower priority than the core enforcement stories.

**Independent Test**: Can be tested by enabling signing in `pyproject.toml`, running `dev-stack init`, verifying git config values, and attempting to push unsigned agent-generated commits.

**Acceptance Scenarios**:

1. **Given** `[tool.dev-stack.signing] enabled = true` in `pyproject.toml`, **When** the user runs `dev-stack init`, **Then** git config is set for `commit.gpgsign = true`, `gpg.format = ssh`, and `user.signingkey` to the detected SSH public key.
2. **Given** signing is enabled but no SSH key is found, **When** `dev-stack init` runs, **Then** the user receives guidance for generating an SSH key and signing is not configured.
3. **Given** `enforcement = "warn"` and an unsigned commit with `Agent` trailer, **When** the user pushes, **Then** the pre-push hook emits a warning but allows the push.
4. **Given** `enforcement = "block"` and an unsigned commit with `Agent` trailer, **When** the user pushes, **Then** the pre-push hook blocks the push with an error.
5. **Given** a manually authored commit (no `Agent` trailer) that is unsigned, **When** the user pushes, **Then** no signing-related warning or block is triggered regardless of enforcement setting.

---

### User Story 9 — Scope Advisory Check in Pipeline (Priority: P4)

During the commit-message pipeline stage, a non-blocking heuristic check detects when staged changes appear to span multiple unrelated concerns. The warning surfaces in the `Pipeline` trailer as `scope-check=warn`.

**Why this priority**: This is a soft advisory signal that supports atomic commit practices. It never blocks work and serves as a gentle nudge. It is the lowest-effort, lowest-risk addition.

**Independent Test**: Can be tested by staging files across 3+ top-level source directories and running the commit-message pipeline stage, then verifying the `scope-check=warn` trailer appears.

**Acceptance Scenarios**:

1. **Given** staged files touch only `src/dev_stack/cli/` and `tests/unit/`, **When** the commit-message pipeline stage runs, **Then** no scope warning is emitted.
2. **Given** staged files touch `src/dev_stack/cli/`, `src/dev_stack/modules/`, and `src/dev_stack/pipeline/` (3+ source subpackages), **When** the commit-message pipeline stage runs, **Then** a `scope-check=warn` entry appears in the `Pipeline` trailer.
3. **Given** staged files include both `specs/` and `src/` changes, **When** the commit-message pipeline stage runs, **Then** a `scope-check=warn` entry appears.
4. **Given** a scope warning is emitted, **When** the user proceeds, **Then** the commit is NOT blocked — the warning is informational only.

---

### Edge Cases

- What happens when the user has a global `.gitlint` config that conflicts with dev-stack's custom rules? **Assumption**: Dev-stack passes its config explicitly to gitlint, overriding any global config.
- What happens when `git push` is to a fork rather than origin? **Assumption**: Branch naming enforcement applies to the branch name itself regardless of remote.
- What happens if the `.git/hooks/` directory does not exist? **Assumption**: The hook installation step creates it if missing (standard git behavior).
- What happens if two hooks compete (e.g., pre-existing husky hooks)? **Assumption**: Dev-stack detects the unmanaged hook and refuses to overwrite, warning the user.
- What happens when `git-cliff` or `python-semantic-release` is installed but at an incompatible version? **Assumption**: Version requirements are documented; if the tool runs and produces an error, dev-stack surfaces that error with a suggestion to upgrade.
- What happens when a release is attempted with zero conventional commits since the last tag? **Assumption**: `dev-stack release` exits with a message that no version bump is needed.
- What happens during `dev-stack uninstall` if a managed hook has been manually modified? **Assumption**: The checksum mismatch is detected, the user is warned, and the modified hook is NOT deleted.
- What happens when `dev-stack init` runs in a monorepo where multiple dev-stack projects share one `.git`? **Assumption**: Hooks are per-`.git` directory; the last `dev-stack init` wins. This is documented as a known limitation.

## Requirements *(mandatory)*

### Functional Requirements

#### Commit Message Linting

- **FR-001**: The system MUST validate that every commit message subject follows conventional commit format: `type(scope): description`, where `type` is one of: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **FR-002**: The system MUST require trailers (`Spec-Ref`, `Task-Ref`, `Agent`, `Pipeline`, `Edited`) on any commit containing an `Agent` trailer, and MUST NOT require trailers on commits without an `Agent` trailer.
- **FR-003**: The system MUST validate that `Spec-Ref` and `Task-Ref` trailer values, when present, reference paths that exist in the repository. Paths MUST be relative to the repo root, use forward slashes, and resolve to an existing file or directory.
- **FR-004**: The system MUST emit a warning (non-blocking) when a `Pipeline` trailer contains any `=fail` entry.
- **FR-004a**: All hook rejection and warning messages MUST include: the rule ID (e.g., UC1, UC2), a description of the violation, and the expected format or value. This enables testable assertions against error output.
- **FR-005**: The system MUST use gitlint as the linting engine, with custom rule classes provided by dev-stack.

#### Branch Naming

- **FR-006**: The system MUST validate branch names against a configurable regex pattern at push time, with a default pattern enforcing `{type}/{slug}` format.
- **FR-007**: The system MUST exempt a configurable list of branch names (default: `main`, `master`, `develop`, `staging`, `production`) from pattern validation.
- **FR-008**: The system MUST allow configuration of the branch name pattern and exempt list via `pyproject.toml` under `[tool.dev-stack.branch]`.
- **FR-009**: The system MUST NOT block local branch creation — enforcement applies only at push time.
- **FR-010**: The system SHOULD warn (non-blocking) when the current branch name does not match the active spec's declared feature branch, if spec-kit is active.

#### Git Hook Lifecycle

- **FR-011**: The system MUST install managed git hooks to `.git/hooks/` during `dev-stack init`, with each hook containing a managed header comment: `# managed by dev-stack — do not edit manually`.
- **FR-012**: The system MUST maintain a hook manifest at `.dev-stack/hooks-manifest.json` recording hook name, file checksum, and installation timestamp.
- **FR-013**: The system MUST NOT overwrite an existing hook that was not installed by dev-stack (detected by absence of the managed header).
- **FR-014**: The system MUST cleanly remove managed hooks during `dev-stack uninstall`, only deleting hooks whose file checksum matches the manifest.
- **FR-014a**: When `dev-stack init` is re-run and managed hook templates have changed, the system MUST auto-update hooks whose current file checksum matches the manifest (unmodified). If a hook has been manually modified (checksum mismatch), the system MUST skip the update and warn the user.
- **FR-015**: The system MUST provide a `dev-stack hooks status` command showing installed hooks, expected vs actual checksums, and modification status.
- **FR-016**: The system MUST support configuring which hooks are installed via `[tool.dev-stack.hooks]` in `pyproject.toml` (default: `commit-msg = true`, `pre-push = true`, `pre-commit = false`).

#### Constitutional Practices

- **FR-017**: `dev-stack init` MUST generate a `constitution-template.md` containing a "Dev-Stack Baseline Practices" section with "Atomic Commits" and "Test-Driven Development" subsections that cannot be removed by users.
- **FR-018**: `dev-stack init` MUST generate `.dev-stack/instructions.md` containing the same atomic commit and TDD clauses as the constitution template.
- **FR-019**: `dev-stack init` MUST detect the presence of agent-specific instruction files (`.github/copilot-instructions.md`, `CLAUDE.md`, `.cursorrules`, `AGENTS.md`) and offer to append dev-stack instructions into them using managed section markers (`<!-- === DEV-STACK:INSTRUCTIONS:BEGIN === -->` / `<!-- === DEV-STACK:INSTRUCTIONS:END === -->`). The injection MUST be idempotent: re-running `dev-stack init` updates the managed section in-place without duplication.
- **FR-020**: The atomic commit clause MUST define a "logical unit of work" as the smallest set of changes that implements a single task, includes passing tests, and leaves the codebase buildable.
- **FR-021**: The TDD clause MUST describe the Red-Green-Refactor cycle with explicit steps for writing failing tests first, minimal implementation to pass, and subsequent refactoring.

#### PR Auto-Description

- **FR-022**: The system MUST provide a `dev-stack pr` command that collects commits on the current branch relative to the upstream tracking branch (default: `main`).
- **FR-023**: The system MUST parse trailers from each commit and aggregate unique `Spec-Ref`, `Task-Ref`, `Agent` values, combined `Pipeline` results, and `Edited` statistics.
- **FR-024**: The system MUST render a structured Markdown PR body from a template including: summary, spec references, task references, AI provenance, pipeline status, and commit list.
- **FR-025**: The system MUST create a PR via GitHub CLI (`gh`) or GitLab CLI (`glab`) when the respective tool is detected, and fall back to printing Markdown to stdout otherwise.
- **FR-026**: The system MUST support a `--dry-run` flag that renders the description without creating a PR.

#### Changelog Generation

- **FR-027**: The system MUST provide a `dev-stack changelog` command that generates or updates a `CHANGELOG.md` grouped by conventional commit type.
- **FR-028**: The system MUST annotate AI-authored commits (those with `Agent` trailer) with a visual marker in the changelog.
- **FR-029**: The system MUST annotate human-edited commits (those with `Edited: true`) with a distinct visual marker.
- **FR-030**: The system MUST support `--unreleased` (changes since last tag) and `--full` (complete history) flags.
- **FR-031**: The system MUST use git-cliff as the rendering engine when available, and MUST exit with clear installation instructions if git-cliff is not installed.
- **FR-032**: `dev-stack init` MUST generate a `cliff.toml` configuration file that parses conventional commits and extracts dev-stack trailers.

#### Release Versioning

- **FR-033**: The system MUST provide a `dev-stack release` command that infers the next semantic version from commit types: `feat` → minor, `fix` → patch, breaking change → major.
- **FR-034**: The system MUST update the version in `pyproject.toml` under `[project] version`.
- **FR-035**: The system MUST create an annotated git tag in the format `v{version}`.
- **FR-036**: The system MUST refuse to release if any commit since the last tag has a hard-failure stage in its `Pipeline` trailer.
- **FR-037**: The system MUST support `--dry-run`, `--bump {major|minor|patch}`, and `--no-tag` flags.
- **FR-038**: The system MUST use python-semantic-release when available and fall back to a built-in minimal implementation for version inference and `pyproject.toml` bumping when it is not.

#### Signed Commits

- **FR-039**: The system MUST support opt-in SSH commit signing configured via `[tool.dev-stack.signing]` in `pyproject.toml`.
- **FR-040**: When signing is enabled, `dev-stack init` MUST configure local git settings for SSH signing (`commit.gpgsign`, `gpg.format`, `user.signingkey`).
- **FR-040a**: When signing is enabled, `dev-stack init` MUST check the installed git version. If git < 2.34, the system MUST warn that SSH signing requires git ≥ 2.34 and skip signing configuration without error.
- **FR-041**: When signing is enabled and no SSH key is detected, the system MUST provide guidance for key generation without configuring signing.
- **FR-042**: The `pre-push` hook MUST warn or block (configurable) if agent-generated commits (those with `Agent` trailer) are unsigned.
- **FR-043**: The system MUST NOT enforce signing requirements on manually authored commits (no `Agent` trailer).

#### Scope Advisory

- **FR-044**: The commit-message pipeline stage MUST emit a non-blocking `scope-check=warn` when staged files touch 3 or more repo-root directories (e.g., `src/`, `tests/`, `specs/`), OR when staged files touch 3 or more source subpackages within the main package directory (e.g., `src/dev_stack/cli/`, `src/dev_stack/modules/`, `src/dev_stack/pipeline/`). These are two independent trigger rules.
- **FR-045**: The commit-message pipeline stage MUST emit a non-blocking `scope-check=warn` when staged files include both `specs/` and `src/` changes.
- **FR-046**: The scope advisory MUST never block a commit — it is informational only.

### Key Entities

- **Managed Hook**: A git hook script installed and tracked by dev-stack, identified by a header comment, recorded in a manifest with name, checksum, and timestamp.
- **Hook Manifest**: A JSON ledger at `.dev-stack/hooks-manifest.json` that tracks all managed hooks and their expected state.
- **Custom Lint Rule**: A gitlint rule class provided by dev-stack that validates commit messages beyond standard format checking (e.g., trailer presence, path existence).
- **Constitution Template**: A structured Markdown document defining non-negotiable agent behavioral practices (atomic commits, TDD) plus a user-editable section.
- **Agent Instructions File**: A Markdown file at `.dev-stack/instructions.md` containing the same practices as the constitution, targeted at non-spec-kit workflows.
- **PR Description Template**: A Markdown template used to render aggregated commit data into a structured pull request body.
- **Changelog Configuration**: A `cliff.toml` file that defines how conventional commits and trailers are parsed and rendered into `CHANGELOG.md`.
- **Release Gate**: A validation check that prevents releasing if any commit in the release range contains a hard pipeline failure.

## Assumptions

- Developers use git as their version control system.
- The repository has a standard `.git/` directory (not a bare repo or worktree-only setup).
- `pyproject.toml` exists at the repository root (dev-stack already requires this).
- The pipeline trailer format produced by `commit_format.py` is stable and follows the `key=value` comma-separated pattern (e.g., `Pipeline: lint=pass,typecheck=fail`).
- The user's environment includes Python 3.11+ (consistent with dev-stack's existing requirement).
- SSH keys, when present, are located at standard paths (`~/.ssh/id_ed25519.pub` or `~/.ssh/id_rsa.pub`).
- Agent instruction file conventions (`.github/copilot-instructions.md`, `CLAUDE.md`, `.cursorrules`, `AGENTS.md`) are stable community standards.
- The conventional commit types list (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`) covers the project's needs. Custom types are not supported in the initial version.
- Monorepo setups with multiple dev-stack projects sharing one `.git` directory are a known limitation; the last `dev-stack init` wins for hook management.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of commits in a dev-stack-enabled repo pass conventional commit format validation, measured by zero `commit-msg` hook rejections during normal workflow after initial adoption.
- **SC-002**: All pushed branch names conform to the configured naming pattern, verified by zero `pre-push` rejections for non-exempt, properly-named branches.
- **SC-003**: PR descriptions generated by `dev-stack pr` include all expected sections (summary, spec references, task references, AI provenance, pipeline status, commit list) for branches with trailer-bearing commits.
- **SC-004**: Changelogs accurately group changes by type and annotate AI-authored and human-edited commits, verified by manual review of 3+ generated changelogs.
- **SC-005**: `dev-stack release` correctly infers the semantic version bump in 100% of cases for standard commit patterns (`feat` → minor, `fix` → patch, breaking change → major), verified by dry-run comparisons.
- **SC-006**: Hook installation, status checking, and uninstallation complete within 2 seconds each on a standard repository.
- **SC-007**: Missing optional dependencies (git-cliff, python-semantic-release, gh, glab) produce clear, user-friendly error messages with installation instructions — never uncaught exceptions or stack traces.
- **SC-008**: Constitution and instructions files are generated during `dev-stack init` in under 1 second and contain all required non-negotiable clauses.
- **SC-009**: Agent instruction file detection correctly identifies at least `.github/copilot-instructions.md`, `CLAUDE.md`, `.cursorrules`, and `AGENTS.md` when present.
- **SC-010**: The scope advisory check adds less than 500ms to pipeline execution time.
