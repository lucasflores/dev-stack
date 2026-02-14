# Data Model: Dev-Stack Ecosystem

**Branch**: `001-dev-stack-ecosystem` | **Date**: 2026-02-10

---

## Entity Relationship Overview

```
StackManifest 1──* Module
Module 1──* ModuleDependency
Module 1──1 ModuleConfig
StackManifest 1──1 AgentConfig
PipelineRun 1──* StageResult
StageResult *──1 PipelineStage
ConflictReport 1──* FileConflict
CommitMemoryRecord 1──1 CommitMetadata
VisualizationRun 1──* DiagramNode
DiagramNode *──* DiagramFlow
```

---

## Entities

### StackManifest

The central configuration file (`dev-stack.toml`) at the repository root.
Single source of truth for what is installed, versions, and rollback state.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | string (semver) | yes | Stack version installed |
| initialized | datetime (ISO 8601) | yes | When `init` was first run |
| last_updated | datetime (ISO 8601) | yes | When last `init` or `update` ran |
| rollback_ref | string | no | Git tag name for rollback point |
| modules | map[string, Module] | yes | Installed modules and their configs |
| agent | AgentConfig | yes | Detected coding agent configuration |

**Validation rules**:
- `version` must be valid semver
- `rollback_ref`, if present, must resolve to a valid git ref
- At least one module must be installed

**State transitions**:
- `uninitialized` → `initialized` (via `dev-stack init`)
- `initialized` → `updated` (via `dev-stack update`)
- `updated` → `rolled-back` (via `dev-stack rollback`)

---

### Module

A discrete, self-contained capability in the stack.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Unique module identifier (e.g., "hooks", "mcp-servers") |
| version | string (semver) | yes | Module version |
| installed | boolean | yes | Whether the module is currently active |
| depends_on | list[string] | no | Module names this module requires |
| config | ModuleConfig | no | Module-specific configuration |

**Valid module names**: `hooks`, `mcp-servers`, `ci-workflows`, `docker`, `visualization`, `speckit`

**Dependency rules**:
- `visualization` depends on `hooks` (diagrams update via pipeline stage 5)
- `speckit` has no dependencies
- `ci-workflows` has no dependencies
- `docker` has no dependencies
- `mcp-servers` has no dependencies
- `hooks` has no dependencies (but all generative stages require `agent` to be configured)

**Validation rules**:
- `name` must be one of the valid module names
- `depends_on` entries must reference valid module names
- Circular dependencies are forbidden

---

### AgentConfig

Configuration for the detected coding agent CLI.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| cli | string | yes | Agent identifier: "claude", "copilot", "cursor", or "none" |
| path | string | no | Absolute path to the agent CLI binary |
| detected_at | datetime | yes | When auto-detection last ran |

**Validation rules**:
- If `cli` is "none", generative pipeline stages (4-6) and visualization are disabled
- `path`, if present, must point to an executable file

---

### PipelineStage

One step in the pre-commit automation pipeline.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| order | integer (1-6) | yes | Execution order |
| name | string | yes | Stage identifier |
| failure_mode | enum | yes | "hard" (blocks commit) or "soft" (warns) |
| requires_agent | boolean | yes | Whether this stage needs the coding agent |
| command | string | yes | Command or function to execute |

**Fixed stage definitions**:

| Order | Name | Failure Mode | Requires Agent |
|-------|------|-------------|----------------|
| 1 | lint | hard | no |
| 2 | test | hard | no |
| 3 | security | hard | no |
| 4 | docs | soft | yes |
| 5 | infra-sync | soft | no (template comparison) |
| 6 | commit-message | soft | yes |

---

### StageResult

Output from executing a single pipeline stage.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| stage_name | string | yes | References PipelineStage.name |
| status | enum | yes | "pass", "fail", "skip", "warn" |
| duration_ms | integer | yes | Execution time in milliseconds |
| output | string | no | stdout/stderr captured |
| skipped_reason | string | no | Why the stage was skipped (e.g., "no agent configured") |

---

### FileConflict

A single file conflict detected during brownfield `init` or `update`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| path | string | yes | Relative file path from repo root |
| conflict_type | enum | yes | "new", "modified", "deleted" |
| current_hash | string | no | SHA-256 of existing file (null if new) |
| proposed_hash | string | yes | SHA-256 of proposed content |
| diff | string | no | Unified diff text (for modified files) |
| resolution | enum | yes | "pending", "accepted", "skipped", "merged" |

**State transitions**:
- `pending` → `accepted` (user accepts proposed change)
- `pending` → `skipped` (user rejects proposed change)
- `pending` → `merged` (user chooses manual merge)

---

### ConflictReport

Aggregate of all conflicts detected during a single `init` or `update` operation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| operation | enum | yes | "init" or "update" |
| timestamp | datetime | yes | When the operation started |
| conflicts | list[FileConflict] | yes | All detected conflicts |
| all_resolved | boolean | yes | Whether all conflicts have a non-pending resolution |

---

### CommitMemoryRecord

The structured data embedded in each commit message by the commit message agent.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | yes | Conventional commit type (feat, fix, docs, etc.) |
| scope | string | no | Component scope |
| summary | string | yes | Summary line (max 72 chars) |
| intent | string | yes | Why the change was made |
| reasoning | string | yes | Design decisions and trade-offs |
| affected_components | list[string] | yes | Module/file groups affected |
| narrative | string | yes | 3-5 sentence AI-optimized summary |
| spec_ref | string | no | Path to related spec file |
| task_ref | string | no | Reference to task ID |
| agent | string | yes | Which coding agent generated this |
| pipeline_results | map[string, string] | yes | Stage name → result for this commit |

**Validation rules**:
- `summary` max 72 characters
- `type` must be a valid conventional commit type
- `narrative` must be 50-500 characters

---

### MCPServerConfig

Configuration entry for a single MCP server.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Server identifier (e.g., "context7") |
| package | string | yes | npm package or install source |
| env_vars | list[string] | yes | Required environment variable names |
| health_check | string | no | Command to verify connectivity |
| installed | boolean | yes | Whether config has been written |

**Known servers**:

| Name | Package | Required Env Vars |
|------|---------|-------------------|
| context7 | @upstash/context7-mcp | (none - public) |
| github | @modelcontextprotocol/server-github | GITHUB_TOKEN |
| sequential-thinking | @modelcontextprotocol/server-sequentialthinking | (none) |
| huggingface | @huggingface/mcp-server | HF_TOKEN |
| notebooklm | TBD | GOOGLE_API_KEY |

---

### VisualizationManifest

Tracks file state for incremental diagram updates (stored in `.dev-stack/viz/manifest.json`).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| files | map[string, FileEntry] | yes | Relative path → file metadata |
| created_at | datetime | yes | When manifest was created |
| schema_path | string | no | Path to last generated overview.json |

**FileEntry**:

| Field | Type | Description |
|-------|------|-------------|
| hash | string | SHA-256 of file content |
| lines | integer | Line count |
| last_scanned | datetime | When last included in analysis |

---

### DiagramNode

A node in the generated D2 visualization (from noodles-inspired schema).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique node ID (prefix: ep_, fb_, end_) |
| type | enum | yes | "entry_point", "feature_block", "end" |
| name | string | yes | Human-readable label |
| description | string | yes | Tooltip text |
| status | enum | yes | "added", "updated", "unchanged" |
| files | list[FileRef] | yes | Source files this node represents |

**FileRef**: `{ file: string, lines: [start, end] }`

---

### DiagramFlow

A directed edge between two DiagramNodes.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| from | string | yes | Source node ID |
| to | string | yes | Target node ID |
| description | string | yes | Edge label (data/control flow description) |
| status | enum | yes | "added", "updated", "unchanged" |

**Graph constraints** (from noodles):
- `entry_point` nodes: only outgoing edges
- `feature_block` nodes: at least one incoming and one outgoing edge
- `end` nodes: only incoming edges
- Every node must belong to at least one flow (no orphans)
