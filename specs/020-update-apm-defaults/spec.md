# Feature Specification: Update APM Default Packages and Manifest Version

**Feature Branch**: `020-update-apm-defaults`
**Created**: 2026-04-24
**Status**: Draft
**Input**: User description: "Update default apm packages/servers. Bump apm manifest version. Remove all mcp servers from the default. Specify agents/skills to pick up from the lucasflores/agent-skills repo. Manifest should only contain specific paths. Verify the generated manifest installs agents/skills/prompt correctly with apm."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fresh Init Produces Correct Default Manifest (Priority: P1)

A developer initializes a new project using dev-stack on a machine where the APM CLI is available. The resulting `apm.yml` contains no MCP server declarations and includes only the four approved agent-skills entries. Running `apm install` on that manifest completes without errors.

**Why this priority**: This is the primary observable outcome of the change. Every new project bootstrapped after this change must produce the correct manifest — incorrect defaults propagate silently to all new users.

**Independent Test**: Run `dev-stack init` in an empty directory; inspect the generated `apm.yml` and confirm no `mcp` section is present, exactly four `apm` entries are listed matching the approved paths, and `apm install` exits with code 0.

**Acceptance Scenarios**:

1. **Given** an empty directory with no `apm.yml`, **When** `dev-stack init` is run with the APM CLI available, **Then** the generated `apm.yml` contains no `mcp` key and has exactly four entries under `dependencies.apm`.
2. **Given** the generated `apm.yml` from scenario 1, **When** `apm install` is run, **Then** all four dependencies install successfully: one agent into `.github/agents/`, one prompt into `.github/prompts/`, and two skills into `.github/skills/`.
3. **Given** the generated `apm.yml`, **When** a developer inspects the manifest version field, **Then** the version is `2.0.0`.

---

### User Story 2 - Merge Strategy Preserves No MCP Entries (Priority: P2)

A developer runs `dev-stack apm install` on a project that already has an `apm.yml` and chooses the merge strategy. The merge does not re-introduce any MCP servers, and only adds the four approved agent-skills entries if not already present.

**Why this priority**: The merge path is the most common path for existing projects upgrading their manifest. Silently adding MCP servers would be a regression.

**Independent Test**: Create an `apm.yml` with no `mcp` section and run `dev-stack apm install` choosing merge; confirm no `mcp` key appears in the file after the operation.

**Acceptance Scenarios**:

1. **Given** an existing `apm.yml` with no `mcp` section, **When** the merge strategy is used, **Then** the resulting file still has no `mcp` key.
2. **Given** an existing `apm.yml` that already contains some of the four approved entries, **When** the merge strategy is used, **Then** duplicates are not introduced and the missing entries are added.

---

### User Story 3 - Preview Reflects Updated Defaults (Priority: P3)

Before committing to initializing APM, a developer previews what files would be created. The preview shows the updated manifest content with no MCP servers and the four specific agent-skills paths.

**Why this priority**: The preview command gives developers a dry-run view before any changes. Stale defaults here mislead decision-making.

**Independent Test**: Call the `preview_files()` path for the APM module; confirm the returned content matches the new template.

**Acceptance Scenarios**:

1. **Given** the APM CLI is available, **When** the `preview_files` operation is invoked, **Then** the preview shows an `apm.yml` with no `mcp` section and exactly the four approved `apm` entries.

---

### Edge Cases

- What happens when an existing `apm.yml` contains MCP servers and the merge strategy is used? — The merge MUST NOT add any MCP servers back; existing entries in the file are preserved as-is (not removed by the module).
- What happens when `apm install` is run and one of the four path-specific entries is unavailable upstream? — APM reports a failure for that entry; the module surfaces the error as a warning in the `ModuleResult`.
- What happens when the APM CLI is not installed? — Behavior is unchanged from current: `install` returns early with a clear error; `preview_files` returns an empty dict.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The default `apm.yml` template MUST contain no `mcp` section and no MCP server entries.
- **FR-002**: The default `apm.yml` template MUST list exactly the following four entries under `dependencies.apm`, in order:
  - `lucasflores/agent-skills/agents/idea-to-speckit.agent.md`
  - `lucasflores/agent-skills/prompts/AutoSpecKit.prompt.md`
  - `lucasflores/agent-skills/skills/commit-pipeline`
  - `lucasflores/agent-skills/skills/dev-stack-update`
- **FR-003**: The `version` field in the default `apm.yml` template MUST be set to `2.0.0` to signal the breaking change in defaults.
- **FR-004**: The `DEFAULT_SERVERS` constant in the APM module MUST be empty (no MCP servers).
- **FR-005**: The `DEFAULT_APM_PACKAGES` constant in the APM module MUST contain exactly the same four path-specific entries defined in FR-002.
- **FR-006**: The merge operation MUST NOT add any MCP servers to an existing manifest, regardless of the previous value of `DEFAULT_SERVERS`. If the merged `mcp` list resolves to empty (no existing entries and no defaults to add), the `mcp` key MUST be omitted entirely from the written manifest rather than written as an empty list.
- **FR-007**: Running `apm install` against the generated manifest MUST result in successful installation of all four dependencies with exit code 0.
- **FR-008**: The merge deduplication key for `apm` entries MUST be the full path before any `#` pin suffix (e.g., `lucasflores/agent-skills/skills/commit-pipeline`), not the bare `owner/repo` prefix. Each distinct path is treated as a separate entry.
- **FR-009**: The success message returned by `_parse_install_result` on a zero exit code MUST read `"All APM dependencies installed successfully"` (replacing the stale `"All MCP servers installed successfully"`).
- **FR-010**: The `APMModule` class docstring MUST read `"Manage APM packages and agent skills via the APM CLI."`

### Key Entities

- **APM manifest template** (`default-apm.yml`): The YAML file used by `preview_files()` and `_render_template()` to seed new projects. It drives both the fresh-install and the preview flows.
- **APMModule constants** (`DEFAULT_SERVERS`, `DEFAULT_APM_PACKAGES`): In-code lists that drive the merge strategy. Must stay synchronized with the template.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh `dev-stack init` on any new project produces an `apm.yml` with zero MCP server entries and exactly four `apm` dependency entries.
- **SC-002**: Running `apm install` against the generated manifest completes with exit code 0 and installs all four declared dependencies.
- **SC-003**: The generated manifest `version` field value is exactly `2.0.0`.
- **SC-004**: All unit and integration tests for the APM module pass after updating assertions to reflect the new defaults.
- **SC-005**: The merge strategy does not introduce MCP entries into any manifest that did not previously have them.

## Clarifications

### Session 2026-04-24

- Q: What should `_merge_manifest` do with the `mcp` block when `DEFAULT_SERVERS` is empty? → A: Omit the `mcp` key entirely if the merged result would be an empty list.
- Q: What should the deduplication key be for path-specific `apm` entries in merge? → A: Full path before `#` — each unique path is a distinct entry.
- Q: What exact version string should the new `default-apm.yml` use? → A: `2.0.0`.
- Q: What should the `_parse_install_result` success message say? → A: `"All APM dependencies installed successfully"`.
- Q: What should the updated `APMModule` class docstring say? → A: `"Manage APM packages and agent skills via the APM CLI."`

## Assumptions

- The APM CLI path-specific package syntax (`owner/repo/path/to/item`) is supported and verified working (confirmed via live `apm install` test).
- The manifest `version` field is a display/tracking field only and does not affect APM CLI behavior; `2.0.0` is the chosen value to signal the breaking change in defaults.
- Existing projects with MCP servers in their `apm.yml` are unaffected — this change only alters the *defaults* written to new manifests and the *merge* additions.
- No migration path is required for existing `apm.yml` files; developers must manually remove MCP entries from pre-existing manifests if desired.
