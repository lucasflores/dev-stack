# Feature Specification: Pipeline Commit Fixes

**Feature Branch**: `011-pipeline-commit-fixes`
**Created**: 2026-03-12
**Status**: Draft
**Input**: User description: "Resolve pipeline commit issues: raw copilot stdout in commit messages, pre-commit hook timing prevents message injection, stale COMMIT_EDITMSG false-positive detection, and gh copilot --allow-all modifying files during pipeline stages"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Commit message is clean and well-structured (Priority: P1)

A developer stages changes and runs `git commit`. The pipeline invokes a coding agent to generate a commit message. The resulting commit message contains only the structured conventional-commit text (subject, body, trailers) with no agent thinking traces, tool-use output, or code fences.

**Why this priority**: If the raw agent response is written as the commit message, every single commit in the repository is polluted with unreadable noise. This is the most immediately visible defect and blocks the pipeline from delivering value.

**Independent Test**: Can be fully tested by invoking the agent bridge with a known prompt and verifying the returned content is parsed to extract only the final commit message, free of code fences, thinking traces, and tool-use artifacts.

**Acceptance Scenarios**:

1. **Given** a copilot agent returns a response containing thinking traces and the commit message inside code fences, **When** the pipeline processes the response, **Then** only the commit message text inside the code fences is extracted and used.
2. **Given** a copilot agent returns a response with tool-use traces interspersed with the final message, **When** the pipeline processes the response, **Then** traces are stripped and only the clean commit message remains.
3. **Given** an agent (e.g., Claude) returns a plain-text response with no code fences, **When** the pipeline processes the response, **Then** the message is used as-is (backward compatible).
4. **Given** an agent response contains multiple code-fenced blocks, **When** the pipeline processes the response, **Then** the last code-fenced block is used as the commit message (the agent's final answer).

---

### User Story 2 — Generated commit message is actually recorded by git (Priority: P1)

A developer stages changes and runs `git commit` (no `-m` flag). The pipeline generates a commit message. The generated message is the one git actually records — not an earlier, stale, or ignored version.

**Why this priority**: Even if the message is perfectly cleaned (US1), it is useless if git never reads it. The current architecture writes to COMMIT_EDITMSG from a pre-commit hook, but git has already captured the message by that point. This is the architectural root cause that makes the entire commit-message feature non-functional.

**Independent Test**: Can be fully tested by running `git commit` end-to-end in a test repository with the pipeline installed, then inspecting `git log -1 --format=%B` to confirm the generated message was recorded.

**Acceptance Scenarios**:

1. **Given** a developer runs `git commit` with no `-m` flag and no editor override, **When** the pipeline generates a commit message, **Then** the recorded commit contains the pipeline-generated message.
2. **Given** a developer runs `git commit -m "manual message"`, **When** the pipeline runs, **Then** the user's manual message is preserved and the pipeline does not overwrite it.
3. **Given** the pipeline's commit-message stage fails or the agent is unavailable, **When** the commit proceeds, **Then** git falls back to its default behavior (opens editor or uses whatever message the user provided).

---

### User Story 3 — Stale COMMIT_EDITMSG does not suppress message generation (Priority: P2)

A developer makes a commit with `-m "fix typo"`. Later, the developer stages new changes and runs `git commit` (no `-m`). The pipeline does not incorrectly skip commit message generation due to a leftover COMMIT_EDITMSG file from the previous commit.

**Why this priority**: This is a high-frequency false-positive: after any `-m` commit, every subsequent commit without `-m` would be wrongly skipped. It erodes trust in the pipeline's reliability, but unlike US1/US2 it only triggers in a specific (though common) sequence.

**Independent Test**: Can be tested by performing two sequential commits — first with `-m`, second without — and verifying the pipeline generates a message for the second commit.

**Acceptance Scenarios**:

1. **Given** a stale COMMIT_EDITMSG exists from a prior commit, **When** the developer runs `git commit` without `-m`, **Then** the pipeline correctly detects that no user message was provided for the current commit and proceeds with generation.
2. **Given** no COMMIT_EDITMSG file exists (fresh clone), **When** the developer runs `git commit` without `-m`, **Then** the pipeline proceeds with message generation.
3. **Given** the developer runs `git commit -m "my message"`, **When** the pipeline checks for a user-supplied message, **Then** it correctly detects the user's intent using a reliable mechanism (not file existence alone).

---

### User Story 4 — Pipeline stages do not modify the developer's staged content (Priority: P2)

A developer stages specific files and runs `git commit`. During the pipeline, agent-powered stages (e.g., docs-narrative) do not modify, add, or remove files from the working tree or staging area. The commit records exactly the changes the developer originally staged.

**Why this priority**: Silently altering a developer's staged content is a data integrity violation. Developers must be able to trust that what they stage is what gets committed. This also causes downstream confusion since later pipeline stages (e.g., commit-message) analyze a diff that no longer matches the original intent.

**Independent Test**: Can be tested by recording the staged diff before the pipeline runs and comparing it to the staged diff after the pipeline completes, asserting they are identical.

**Acceptance Scenarios**:

1. **Given** a developer has staged specific changes, **When** the docs-narrative stage invokes the coding agent, **Then** the agent does not modify any files in the working tree or staging area.
2. **Given** the docs-narrative stage runs, **When** it completes, **Then** `git diff --cached` produces the same output as before the stage ran.
3. **Given** any agent-powered pipeline stage runs, **When** the agent attempts to modify files, **Then** the pipeline prevents or sandboxes those modifications so the developer's staged content is unaffected.

---

### Edge Cases

- What happens when the agent response is completely empty (no code fences, no text)? The pipeline should treat this as a failed generation and fall back gracefully.
- What happens when the agent response contains code fences but the content inside is empty? The pipeline should treat this as a failed generation.
- What happens during a merge commit or rebase operation? The pipeline should detect non-standard commit flows and skip message generation.
- What happens when COMMIT_EDITMSG is locked by another process? The pipeline should handle file-access errors gracefully without crashing.
- What happens when the developer amends a commit (`git commit --amend`)? The pipeline preserves the existing commit message (source = `commit`); generation is skipped. If the developer wants a new message, they use `--amend -m "..."` or edit manually.
- What happens if the agent modifies files that are not tracked by git? The pipeline's sandbox should still prevent untracked file creation in the working tree.

## Requirements *(mandatory)*

### Functional Requirements

**Response Parsing (Problem 1)**

- **FR-001**: The system MUST extract the clean commit message from a raw agent response, stripping any thinking traces, tool-use output, and surrounding prose.
- **FR-002**: The system MUST detect and extract content from code-fenced blocks (``` or ~~~) in the agent response.
- **FR-003**: When multiple code-fenced blocks are present, the system MUST use the last block as the commit message (the agent's final answer).
- **FR-004**: When no code fences are present, the system MUST use the full response content as the commit message (backward compatibility with agents that return clean output).
- **FR-005**: The system MUST reject extracted messages that are empty or contain only whitespace, treating them as failed generation.

**Hook Timing (Problem 2)**

- **FR-006**: The pipeline MUST write the generated commit message at a point in git's commit flow where git will actually read and use it. *(Satisfied by FR-007.)*
- **FR-007**: The system MUST use the `prepare-commit-msg` hook (which runs before the editor opens and receives the message file path) for stages 3–9 (test, security, docs-api, docs-narrative, infra-sync, visualize, commit-message), instead of the `pre-commit` hook (which cannot modify the message).
- **FR-008**: The system MUST preserve the user's message when `git commit -m "..."` is used, and skip generation.
- **FR-009**: When the agent is unavailable or generation fails, the system MUST fall back to git's default behavior (open editor with empty/template message) without blocking the commit.
- **FR-010**: The pre-commit hook MUST continue to run lint and typecheck stages (stages 1–2) only; all other stages (3–9) run in prepare-commit-msg.

**Stale COMMIT_EDITMSG Detection (Problem 3)**

- **FR-011**: The system MUST NOT rely on the existence or content of `.git/COMMIT_EDITMSG` to detect whether the user supplied a `-m` flag.
- **FR-012**: The system MUST use a reliable mechanism to detect user-supplied messages — for example, inspecting the message file content passed to the `prepare-commit-msg` hook, or checking the source argument git provides to that hook (`message`, `template`, `merge`, `squash`, `commit`).
- **FR-013**: The system MUST correctly distinguish between "user provided a message via -m" (source = `message`) and "git opened an empty template" (source = `template` or no source).
- **FR-014**: The system MUST skip commit-message generation when `git commit --amend` is used without `-m` (source = `commit` with a SHA), preserving the existing message.

**Staged Content Protection (Problem 4)**

- **FR-015**: Agent-powered pipeline stages that generate content (e.g., docs-narrative) MUST NOT grant the agent filesystem write access during the commit pipeline.
- **FR-016**: The system MUST invoke the coding agent in a read-only or sandboxed mode when called from git hooks (commit pipeline), preventing modifications to the working tree and staging area. Non-hook CLI invocations (e.g., `dev-stack run`) retain current behavior including filesystem write access.
- **FR-017**: The system MUST ensure that `git diff --cached` output is identical before and after any pipeline stage runs during hook-context execution. (Non-hook CLI invocations such as `dev-stack run` are excluded — see Out of Scope.)
- **FR-018**: If an agent-powered stage needs to suggest file changes (e.g., documentation updates), the system MUST capture those suggestions as advisory output in a persistent file (e.g., `.dev-stack/pending-docs.md`) rather than applying them directly. The file persists until the developer reviews and applies or dismisses the suggestions.

**Observability**

- **FR-019**: When `DEV_STACK_DEBUG=1` is set, the system MUST log response-parsing events (input content hash, extraction method used, success/failure, extracted message length) to `.dev-stack/logs/`. When the debug flag is not set, no parse logs are written.

### Key Entities

- **AgentResponse**: The raw output returned by a coding agent CLI invocation. Contains the full stdout which may include thinking traces, tool-use artifacts, and the actual response content.
- **ParsedCommitMessage**: The extracted, clean commit message after processing an AgentResponse. Contains only the subject line, optional body, and optional trailers.
- **HookContext**: Information about which git hook is executing and the arguments git passed to it. Used to determine the correct stage of the commit flow and whether a user-supplied message exists.
- **TrailerData**: Structured metadata (spec-ref, task-ref, agent name, pipeline summary) appended to commit messages as git trailers.
- **StagedSnapshot**: A representation of the staging area's state at a point in time. Used to verify staged content integrity before and after pipeline stages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of commits made through the pipeline contain only clean, conventional-commit-formatted messages — no thinking traces, code fences, or tool-use artifacts appear in any commit message.
- **SC-002**: When `git commit` is run without `-m`, the pipeline-generated message is the one recorded by git in 100% of cases where the agent succeeds.
- **SC-003**: When `git commit -m "..."` is used, the user's manual message is preserved unchanged in 100% of cases.
- **SC-004**: After a `-m` commit followed by a no-flag commit, the pipeline correctly generates a message for the second commit (zero false-positive skips due to stale state).
- **SC-005**: The staged diff (`git diff --cached`) is byte-identical before and after the full pipeline runs, in 100% of pipeline executions.
- **SC-006**: No files in the working tree are created, modified, or deleted by agent-powered pipeline stages during the commit flow.
- **SC-007**: When the agent is unavailable or generation fails, the commit flow completes within 5 seconds using git's default behavior (no hang, no crash).

## Out of Scope

- Sandboxing agent invocations outside the commit pipeline (e.g., `dev-stack run` CLI). Non-hook invocations retain current behavior including `--allow-all`.
- Changing the agent prompt templates or conventional-commit format rules.
- Adding new pipeline stages or changing stage ordering beyond the hook redistribution (pre-commit vs. prepare-commit-msg).
- Multi-agent orchestration or agent selection logic changes.

## Assumptions

- The target git version supports `prepare-commit-msg` hook with source arguments (available since git 1.7.1, effectively all modern installations).
- The coding agents (Claude, Copilot, Cursor) all support a non-interactive, read-only or output-only invocation mode.
- Copilot CLI's `--allow-all` flag is the only mechanism currently granting filesystem write access; removing it or replacing it with a read-only flag is sufficient to sandbox the agent.
- The `prepare-commit-msg` hook receives the message file path, an optional source (`message`, `template`, `merge`, `squash`, `commit`), and an optional commit SHA — per git's documented hook interface.

## Clarifications

### Session 2026-03-12

- Q: Where do the remaining pipeline stages (test, security, docs-api, docs-narrative, infra-sync, visualize) execute? → A: Only lint + typecheck in pre-commit; stages 3–9 (test through commit-message) all run in prepare-commit-msg.
- Q: What should happen with advisory documentation suggestions after the commit? → A: Write suggestions to a persistent file (e.g., `.dev-stack/pending-docs.md`) that persists until the developer reviews and applies or dismisses them.
- Q: Should the pipeline log parsing events for debugging? → A: Log parse events (input hash, extraction method used, success/failure) to `.dev-stack/logs/` debug log file; only written when `DEV_STACK_DEBUG=1`.
- Q: When `git commit --amend` (no `-m`) is used, should the pipeline re-generate or preserve the existing message? → A: Preserve the existing message; source = `commit` with a SHA signals skip generation.
- Q: Is Copilot CLI `--allow-all` removal scoped only to commit-time pipeline, or all AgentBridge.invoke() calls? → A: Sandbox only during commit pipeline (hooks); non-hook CLI invocations retain current behavior including `--allow-all`.
