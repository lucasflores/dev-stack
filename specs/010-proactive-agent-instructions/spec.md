# Feature Specification: Proactive Agent Instruction File Creation

**Feature Branch**: `010-proactive-agent-instructions`  
**Created**: 2025-03-11  
**Status**: Draft  
**Input**: User description: "Currently the instructions.md file with our pre-written clauses will never be picked up for a greenfield dev-stack init. We need to remedy this. dev-stack should create the agent file proactively based on the detected agent."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Greenfield init creates the right agent file automatically (Priority: P1)

A user initializes a brand-new repository with `dev-stack init`. The CLI detects which coding agent is available (Claude, GitHub Copilot, or Cursor) and proactively creates the corresponding agent instruction file with dev-stack's pre-written clauses (atomic commits, TDD). The user's coding agent picks up the instructions on its next invocation without any manual steps.

**Why this priority**: This is the core bug fix. Today, greenfield init writes `.dev-stack/instructions.md` but no agent will ever discover it. Without this, the entire constitutional-instructions feature is dead on arrival for new repos.

**Independent Test**: Run `dev-stack init` in a fresh repo with a detected agent → verify the agent-specific file exists and contains the instructions.

**Acceptance Scenarios**:

1. **Given** an empty git repo with `claude` detected as the coding agent, **When** the user runs `dev-stack init`, **Then** `CLAUDE.md` is created at the repo root containing the dev-stack instruction clauses wrapped in managed section markers.
2. **Given** an empty git repo with `copilot` detected as the coding agent, **When** the user runs `dev-stack init`, **Then** `.github/copilot-instructions.md` is created (and `.github/` directory is created if needed) containing the dev-stack instruction clauses wrapped in managed section markers.
3. **Given** an empty git repo with `cursor` detected as the coding agent, **When** the user runs `dev-stack init`, **Then** `.cursorrules` is created at the repo root containing the dev-stack instruction clauses wrapped in managed section markers.
4. **Given** an empty git repo with `DEV_STACK_AGENT=none`, **When** the user runs `dev-stack init`, **Then** only `.dev-stack/instructions.md` is created and no agent-specific file is generated.
5. **Given** an empty git repo with no agent CLI available on PATH, **When** the user runs `dev-stack init`, **Then** only `.dev-stack/instructions.md` is created and no agent-specific file is generated.

---

### User Story 2 - Brownfield init injects into existing agent file (Priority: P2)

A user initializes dev-stack in a repo that already has an agent instruction file (e.g., `CLAUDE.md` with custom content). Dev-stack injects its instructions as a managed section without overwriting the user's existing content.

**Why this priority**: Preserving existing user content in brownfield repos is critical for adoption safety. This is the existing FR-019 behavior that must continue working alongside the new proactive creation.

**Independent Test**: Create a repo with a pre-existing `CLAUDE.md` containing custom content, run `dev-stack init` → verify the original content is preserved and dev-stack instructions are added within managed markers.

**Acceptance Scenarios**:

1. **Given** a repo with an existing `CLAUDE.md` containing user-written instructions, **When** the user runs `dev-stack init`, **Then** the existing content is preserved and dev-stack clauses are appended within managed section markers.
2. **Given** a repo with an existing `CLAUDE.md` that already contains a dev-stack managed section, **When** the user runs `dev-stack init` again, **Then** the managed section is updated in-place without duplication.

---

### User Story 3 - Update and uninstall respect the created agent file (Priority: P3)

When `dev-stack update` runs, the proactively created agent file's managed section is refreshed if the instructions template has changed. When `dev-stack uninstall` (via the vcs_hooks module) runs, the managed section is removed. If the agent file was created by dev-stack and contains only the managed section, the file itself is removed.

**Why this priority**: Lifecycle management ensures clean updates and teardowns. Without this, stale instructions persist or orphan files accumulate.

**Independent Test**: Run `dev-stack init`, then `dev-stack update` → verify managed section is refreshed. Then uninstall → verify cleanup.

**Acceptance Scenarios**:

1. **Given** a repo where `dev-stack init` proactively created `CLAUDE.md`, **When** the user runs `dev-stack update` after the instructions template has changed, **Then** the managed section in `CLAUDE.md` is updated to reflect the new template.
2. **Given** a repo where `dev-stack init` proactively created `CLAUDE.md` with only the managed section, **When** the vcs_hooks module is uninstalled, **Then** the managed section is removed and the empty file is deleted.
3. **Given** a repo where the user added custom content to a dev-stack-created `CLAUDE.md`, **When** the vcs_hooks module is uninstalled, **Then** only the managed section is removed and the file is preserved with the user's content intact.

---

### Edge Cases

- What happens when the detected agent changes between init and update (e.g., user switches from Claude to Copilot)? The new agent file should be created; the old one's managed section should be left as-is (user may still want it).
- What happens when multiple agent CLIs are available on PATH? Only the highest-priority agent's file is created (priority order: `claude` > `copilot` > `cursor`), matching the existing `AGENT_PRIORITY` detection order.
- What happens when `DEV_STACK_AGENT` env var overrides to a specific agent? The overridden agent's file is created, consistent with `detect_agent()` behavior.
- What happens when the `.github/` directory doesn't exist and the detected agent is `copilot`? The directory is created automatically before writing `.github/copilot-instructions.md`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When `dev-stack init` runs and detects an agent CLI (not `none`), the system MUST create the corresponding agent instruction file if it does not already exist.
- **FR-002**: The agent-to-file mapping MUST be: `claude` → `CLAUDE.md`, `copilot` → `.github/copilot-instructions.md`, `cursor` → `.cursorrules`.
- **FR-003**: The created agent file MUST contain the dev-stack instruction clauses from the instructions template, wrapped in managed section markers.
- **FR-004**: When the agent instruction file already exists (brownfield), the system MUST inject instructions as a managed section without overwriting existing content (existing FR-019 behavior preserved).
- **FR-005**: When no agent is detected (cli = `none`), the system MUST NOT create any agent-specific file. Only `.dev-stack/instructions.md` is written.
- **FR-006**: The proactively created agent file MUST be reported in the `files_created` list of the module result and included in `--json` output.
- **FR-007**: The proactively created agent file MUST be handled by the module's `update` and `uninstall` lifecycle operations. The file is resolved at runtime via `_get_agent_file_path()` rather than added to the static `MANAGED_FILES` tuple (to preserve contract test compatibility).
- **FR-008**: Parent directories required for the agent file (e.g., `.github/` for copilot) MUST be created automatically if they do not exist.
- **FR-009**: `dev-stack update` MUST refresh the managed section in the agent file when the instructions template has changed.
- **FR-010**: Module uninstall MUST remove the managed section from the agent file. If the file was created by dev-stack and contains only the managed section (no user content), the file MUST be deleted.
- **FR-011**: The `--dry-run` flag MUST report which agent file would be created without actually writing it.
- **FR-012**: The `dev-stack init` `--json` output MUST include the path of the created agent file in the output.

### Non-Functional Requirements

- **NFR-001**: The agent file creation path MUST complete in <100ms (file I/O only, no network calls).
- **NFR-002**: All agent file operations MUST be idempotent — repeated invocations produce the same result.

### Key Entities

- **Agent Instruction File**: The agent-specific file that a coding agent auto-discovers (`CLAUDE.md`, `.github/copilot-instructions.md`, `.cursorrules`). Maps 1:1 to a detected agent CLI.
- **Managed Section**: A delimited block within the agent file owned by dev-stack, identified by `DEV-STACK:INSTRUCTIONS` markers. Enables idempotent updates and clean removal.
- **Instructions Template**: The source content at the instructions template path containing atomic commit and TDD clauses.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a greenfield `dev-stack init` with a detected agent, the agent's instruction file exists and is discoverable by that agent on its next invocation — verified by checking the file at the canonical path.
- **SC-002**: Re-running `dev-stack init` on the same repo does not duplicate the managed section — the agent file contains exactly one set of managed markers.
- **SC-003**: Uninstalling the vcs_hooks module on a repo where the agent file was proactively created leaves no orphaned dev-stack content in the agent file.
- **SC-004**: All existing tests continue to pass — no regressions in brownfield injection behavior.

## Assumptions

- The agent-to-file mapping follows current conventions: Claude reads `CLAUDE.md`, GitHub Copilot reads `.github/copilot-instructions.md`, and Cursor reads `.cursorrules`. If these conventions change, the mapping will need updating.
- Only the primary detected agent's file is created. Users who work with multiple agents can manually create additional files and dev-stack will inject into them on the next `update` or `init` (existing brownfield behavior).
- The `AGENTS.md` file (VS Code multi-agent config) is not proactively created since it serves a different purpose (agent definitions, not general instructions). It continues to be injection-only.

## Scope Boundaries

**In scope**:
- Proactive creation of the agent instruction file during `init`
- Lifecycle management (update, uninstall) for the created file
- Dry-run reporting of the file that would be created

**Out of scope**:
- Creating files for multiple agents simultaneously (only the detected agent)
- Modifying the content of the instructions template itself
- Adding new agent types beyond the existing three (claude, copilot, cursor)
- Changing the agent detection priority order
