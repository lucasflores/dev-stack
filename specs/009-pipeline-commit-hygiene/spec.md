# Feature Specification: Pipeline Commit Hygiene

**Feature Branch**: `009-pipeline-commit-hygiene`
**Created**: 2026-03-10
**Status**: Draft
**Input**: User description: "Fix 6 issues discovered during end-to-end greenfield init testing of dev-stack v0.1.0 in a fresh repository. These issues fall into two themes: (1) the pre-commit pipeline mutates the working tree during hook execution, making the first commit require multiple attempts and leaving perpetually dirty state; and (2) soft-gate stages (6, 8, 9) have documentation gaps, silent failures, or misleading status reports."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — First Commit Succeeds on the First Attempt (Priority: P1)

A developer has just bootstrapped a new project with `git init`, `uv init --package`, and `dev-stack --json init`. They run `git add -A && git commit -m "Initial commit"`. The pre-commit hook invokes the dev-stack pipeline, which generates and modifies files (security baseline, API docs, narrative guides). After the pipeline completes successfully, the commit lands cleanly on the first attempt — no index/working-tree mismatch, no need for a second `git add && git commit` cycle.

**Why this priority**: This is the greenfield happy path. If the very first commit fails, the developer's first impression is broken trust. The README promises "no `--no-verify` needed," so this must work.

**Independent Test**: Run the full greenfield flow (`git init` → `uv init --package` → `dev-stack --json init` → `git add -A && git commit -m "Initial commit"`) in a fresh temporary directory. The commit must succeed on the first attempt.

**Acceptance Scenarios**:

1. **Given** a freshly initialized project with all files staged, **When** the user runs `git commit -m "Initial commit"`, **Then** the pre-commit pipeline runs to completion and the commit succeeds without error.
2. **Given** a freshly initialized project with all files staged, **When** the pre-commit pipeline generates or modifies files (e.g., `.secrets.baseline`, API docs, narrative guides), **Then** those files are automatically staged before the hook exits, so no index mismatch occurs.
3. **Given** a freshly initialized project with all files staged, **When** the commit succeeds on the first attempt, **Then** `git status` immediately after shows a clean working tree with no modified or untracked pipeline outputs.

---

### User Story 2 — Working Tree Stays Clean After Every Commit (Priority: P1)

After any successful commit (not just the first), `git status` shows a clean working tree. Pipeline stages that rewrite files (such as the security baseline's `generated_at` timestamp) do not leave behind uncommitted modifications.

**Why this priority**: A perpetually dirty working tree after every commit is a constant source of confusion and noise. It undermines developer confidence in the tool and trains them to ignore `git status`.

**Independent Test**: After a successful commit, run `git status --porcelain`. The output must be empty.

**Acceptance Scenarios**:

1. **Given** a project where the security baseline already exists, **When** a commit runs the pipeline and the security stage rewrites the baseline with an updated timestamp but no new findings, **Then** `git status` shows no modified files after commit.
2. **Given** a project with existing API docs and narrative guides, **When** a commit runs the pipeline and the docs stages regenerate those files, **Then** `git status` shows no modified or untracked files after commit.

---

### User Story 3 — Visualize Stage Skips Gracefully Without LLM API Key (Priority: P2)

A developer has installed the optional CodeBoarding dependency but has not configured an LLM API key. When the pipeline reaches the visualize stage (stage 8), it detects the missing API key, produces a clear skip message explaining the prerequisite, and continues to the next stage without a raw error trace.

**Why this priority**: The README describes CodeBoarding as "Optional" with "gracefully skipped when absent," but a raw error about missing API keys is neither graceful nor informative. This is important but lower priority than the commit-blocking issues.

**Independent Test**: Install CodeBoarding, unset all LLM API key environment variables, run the pipeline. Verify stage 8 reports a skip with a human-readable message mentioning which API key(s) to set.

**Acceptance Scenarios**:

1. **Given** CodeBoarding is installed but no LLM provider API key is set, **When** the pipeline reaches the visualize stage, **Then** the stage reports status "skip" with a message listing the five supported API keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`).
2. **Given** CodeBoarding is installed but no LLM provider API key is set, **When** the visualize stage skips, **Then** no raw traceback or error stack is displayed to the user.
3. **Given** CodeBoarding is installed and a valid LLM API key is set, **When** the pipeline reaches the visualize stage, **Then** the stage executes normally.

---

### User Story 4 — Commit-Message Stage Reports Honestly When Inactive (Priority: P2)

A developer runs `git commit -m "my message"` and the commit-message stage (stage 9) reports its actual effect accurately. When the user supplies a message with `-m`, the stage does not falsely claim to have written a structured commit message. The status report reflects what actually happened.

**Why this priority**: Misleading status reports erode developer trust in pipeline output. If the stage says "pass" and claims to have written a message, but the actual commit message is unchanged, all pipeline status messages become suspect.

**Independent Test**: Run `git commit -m "test message"` and inspect both the pipeline output and the actual commit message (`git log -1 --format=%B`). The pipeline status for stage 9 must accurately reflect whether the message was actually modified.

**Acceptance Scenarios**:

1. **Given** the user commits with `-m "message"`, **When** the commit-message stage runs, **Then** the stage status reflects that the user-supplied message was used and no structured narrative was generated.
2. **Given** the user commits without `-m` (interactive editor), **When** the commit-message stage runs with a supported agent, **Then** the stage generates a structured commit message and reports "pass" accurately.
3. **Given** the user commits with `-m "message"` and the stage does not modify it, **When** the pipeline report is displayed, **Then** the status is "skip" (not "pass") with a message explaining that `-m` overrides generated messages.

---

### User Story 5 — README Documents Soft-Gate Prerequisites (Priority: P3)

A developer reading the README understands the prerequisites for optional pipeline stages before encountering unexpected behavior. The CodeBoarding/visualize stage documentation clearly states the LLM API key requirement. The commit-message stage documentation clarifies the behavior when using `-m`.

**Why this priority**: Documentation fixes are lowest friction but important for long-term onboarding. They prevent rather than fix issues.

**Independent Test**: Review the README for the visualize stage section; confirm it mentions the LLM API key requirement. Review the commit-message stage section; confirm it clarifies `-m` flag behavior.

**Acceptance Scenarios**:

1. **Given** a developer reads the README section on the visualize stage, **When** they look for prerequisites, **Then** they find documentation stating that an LLM API key (e.g., `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`) is required for CodeBoarding to function.
2. **Given** a developer reads the README section on the commit-message stage, **When** they look for behavior details, **Then** they find documentation explaining that `-m` flag messages take precedence and the stage only generates messages in interactive commit mode.

---

### Edge Cases

- What happens when a pipeline stage generates a new file that didn't exist before (e.g., first-time API doc generation) — **resolved**: auto-staging handles both untracked (new) and modified (tracked) files equally (confirmed by FR-006).
- What happens when a pipeline stage fails mid-execution after partially modifying a file — **resolved**: partial/failed stage outputs are NOT auto-staged; only outputs from stages with status "pass" or "skip" are staged.
- What happens when the user has manually modified a pipeline output file (e.g., edited `.secrets.baseline`) and the pipeline overwrites it — **resolved**: pipeline-generated files (`.secrets.baseline`, `docs/api/`, `docs/guides/`, `.codeboarding/`) are stack-managed outputs that are regenerated on every commit. User edits to these files are overwritten by design; users should not manually edit auto-generated outputs. This is consistent with constitution Principle IV (Brownfield Safety) which protects user *configuration* files via conflict detection, not auto-generated artifacts.
- What happens when `git add` of pipeline outputs fails (e.g., `.gitignore` excludes a pipeline output path)? — **resolved**: auto-staging skips gitignored paths (FR-007) and logs a warning on `git add` failure without failing the commit (FR-009).
- What happens during a `--dry-run` pipeline execution — **resolved**: no auto-staging occurs during dry-run (confirmed by FR-008).
- What happens when the pipeline runs outside of a pre-commit hook (e.g., `dev-stack pipeline run` directly) — **resolved**: no auto-staging occurs; working tree is left as-is for manual review (confirmed by FR-003).

## Requirements *(mandatory)*

### Functional Requirements

#### Theme A: Pipeline Auto-Staging During Pre-Commit (Issues 1, 2, 3, 6)

- **FR-001**: When the pipeline runs as a pre-commit hook, the system MUST automatically stage files generated or modified by pipeline stages that completed with status "pass" or "skip" before the hook exits. Outputs from stages that reported "fail" MUST NOT be auto-staged.
- **FR-002**: The set of auto-staged paths MUST include at minimum: `.secrets.baseline`, API doc output directory, narrative guide output files (`quickstart.md`, `development.md`, `index.md`), and `.codeboarding` directory.
- **FR-003**: Auto-staging MUST only occur when the pipeline is executing within a pre-commit hook context, not during standalone `dev-stack pipeline run` invocations.
- **FR-004**: The security stage MUST compare scan findings against the existing `.secrets.baseline` (ignoring the `generated_at` timestamp field). If findings are identical, the baseline file MUST NOT be rewritten. Only when findings differ (new findings, removed findings, or changed findings) MUST the baseline be updated.
- **FR-005**: If `.secrets.baseline` content changes (new findings, removed findings), the updated file MUST be staged automatically. *(Corollary of FR-001 applied to the security baseline; included for explicit traceability to Issue 3.)*
- **FR-006**: Auto-staging MUST handle both newly created files (untracked) and modified files (already tracked).
- **FR-007**: Auto-staging MUST NOT stage files that the user has excluded via `.gitignore`.
- **FR-008**: During `--dry-run` pipeline execution, no auto-staging MUST occur.
- **FR-009**: If auto-staging fails (e.g., `git add` returns non-zero), the pipeline MUST log a warning but NOT fail the commit.

#### Theme B: Soft-Gate Stage Behavior (Issues 4, 5)

- **FR-010**: The visualize stage (stage 8) MUST check for the presence of any of the following LLM API keys before attempting to invoke CodeBoarding: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`.
- **FR-011**: When none of the five supported LLM API keys are set, the visualize stage MUST report status "skip" with a human-readable message listing all five supported environment variable names.
- **FR-012**: The visualize stage MUST NOT display raw error tracebacks or exception messages to the user when the failure is a known missing-prerequisite condition.
- **FR-013**: The commit-message stage (stage 9) MUST detect when the user has provided a message via `-m` flag and report status accurately (not "pass").
- **FR-014**: When `-m` is used, the commit-message stage MUST report status "skip" with a message explaining that user-supplied messages take precedence over generated messages.

#### Theme C: Documentation (Issues 4, 5)

- **FR-015**: The README MUST document the LLM API key requirement for the CodeBoarding/visualize stage, listing all five supported environment variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`.
- **FR-016**: The README MUST document that the commit-message stage generates structured messages only in interactive commit mode and that `-m` flag messages take precedence.

### Key Entities

- **Pipeline Context**: Whether the pipeline is running as a pre-commit hook or standalone; controls auto-staging behavior.
- **Pipeline Output Manifest**: The set of known file paths that pipeline stages may generate or modify; hardcoded per-stage in the pipeline source (not user-configurable). Used to determine what to auto-stage.
- **Stage Status**: The status a pipeline stage reports upon completion — must accurately reflect what the stage actually did (pass, fail, skip, warn).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The greenfield flow (`git init` → `uv init --package` → `dev-stack --json init` → `git add -A && git commit`) completes successfully on the first `git commit` attempt, 100% of the time.
- **SC-002**: After any successful commit, `git status --porcelain` produces empty output (clean working tree) 100% of the time.
- **SC-003**: When CodeBoarding is installed but no LLM API key is set, the visualize stage reports "skip" with a descriptive message and no raw error output.
- **SC-004**: When committing with `-m`, the commit-message stage status is never reported as "pass" — it is reported as "skip".
- **SC-005**: The README includes prerequisite documentation for the visualize stage (LLM API key) and commit-message stage (`-m` behavior).
- **SC-006**: No pipeline stage leaves untracked or modified files in the working tree when running as a pre-commit hook.

## Clarifications

### Session 2026-03-10

- Q: When a pipeline stage fails mid-execution after partially modifying a file, should auto-staging still stage that file's changes? → A: Only auto-stage outputs from stages that reported "pass" or "skip".
- Q: Should the pipeline output manifest be hardcoded or configurable? → A: Hardcoded in source — each stage declares its output paths.
- Q: Which LLM provider API keys should the visualize stage check for? → A: All five: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`.
- Q: When the pipeline runs outside of a pre-commit hook, should it still auto-stage? → A: No — leave working tree as-is for manual review.
- Q: How should the security stage avoid unnecessary `.secrets.baseline` rewrites? → A: Run scan, compare findings (ignoring `generated_at` timestamp) against existing baseline, only write if findings differ.

## Assumptions

- The pipeline can reliably determine whether it is running inside a pre-commit hook context versus a standalone invocation (e.g., via environment variable or calling context detection).
- The set of pipeline output paths is known and finite; a manifest-based approach is sufficient (no need for generic working-tree diffing).
- `git add` of specific paths within a pre-commit hook is supported and does not interfere with git's commit process.
- The security stage can load the existing `.secrets.baseline` JSON, run `detect-secrets scan`, and compare the `results` section of both to determine whether findings changed (ignoring the `generated_at` timestamp field).
- The commit-message stage can detect whether the user supplied `-m` (e.g., by checking if `.git/COMMIT_EDITMSG` was written before the hook ran or by inspecting git's hook arguments).
- Specs 006, 007, and 008 handle adjacent concerns (greenfield conflict detection, security self-scanning exclusions, dev dependency installation) and this spec does not duplicate that work.

## Scope Boundaries

**In scope**:
- Auto-staging pipeline-generated files during pre-commit hook execution
- Preventing unnecessary `.secrets.baseline` rewrites (timestamp-only changes)
- Graceful skip behavior for the visualize stage when LLM API key is missing
- Honest status reporting for the commit-message stage when `-m` is used
- README documentation updates for soft-gate prerequisites

**Out of scope**:
- Greenfield conflict detection and mode labeling (covered by spec 006)
- Security stage self-scanning exclusions for `.dev-stack/` (covered by spec 007)
- Dev dependency installation and `uv sync` during init (covered by spec 008)
- Pipeline stage execution order changes
- New pipeline stages or removal of existing stages
