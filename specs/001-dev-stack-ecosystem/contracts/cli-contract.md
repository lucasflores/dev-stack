# CLI Contract: dev-stack

**Branch**: `001-dev-stack-ecosystem` | **Date**: 2026-02-10

---

## Global Conventions

- All commands support `--json` flag for machine-readable JSON output
- All commands support `--verbose` flag for debug-level logging
- All commands support `--dry-run` flag where applicable (shows what would change)
- Exit codes follow POSIX conventions (see table below)
- Human output to stdout; diagnostic/progress to stderr
- Colors auto-disabled when stdout is not a TTY

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (see stderr) |
| 2 | Invalid arguments or usage |
| 3 | Conflict detected (brownfield) |
| 4 | Agent not found or unavailable |
| 5 | Pipeline stage failure (hard) |
| 10 | Rollback failure |

---

## Commands

### `dev-stack init [--modules MODULE,...] [--force] [--json] [--dry-run]`

Initialize a repository with the dev-stack ecosystem.

**Behavior**:
1. Detect if brownfield (existing files that overlap)
2. If brownfield and no `--force`: generate ConflictReport, exit 3
3. If greenfield or `--force`: install all/selected modules
4. Create `dev-stack.toml` manifest
5. Create rollback tag `dev-stack/rollback/<timestamp>`
6. Detect coding agent, write AgentConfig

**Default modules**: hooks, speckit (greenfield); none auto-selected (brownfield)

**JSON output schema** (`--json`):
```json
{
  "status": "success" | "conflict" | "error",
  "mode": "greenfield" | "brownfield",
  "manifest_path": "dev-stack.toml",
  "rollback_ref": "dev-stack/rollback/20260210T120000Z",
  "modules_installed": ["hooks", "speckit", "mcp-servers"],
  "agent": {
    "cli": "claude",
    "path": "/usr/local/bin/claude"
  },
  "conflicts": [
    {
      "path": ".pre-commit-config.yaml",
      "conflict_type": "modified",
      "resolution": "pending"
    }
  ]
}
```

---

### `dev-stack update [--modules MODULE,...] [--json] [--dry-run]`

Add modules or update existing ones.

**Behavior**:
1. Read existing `dev-stack.toml`
2. Resolve dependencies for requested modules
3. Detect conflicts with marker comparison
4. If conflicts: present interactive merge (or exit 3 with `--json`)
5. Apply updates within marker-delimited sections
6. Create pre-update rollback tag
7. Update `dev-stack.toml` timestamp and module versions

**JSON output schema** (`--json`):
```json
{
  "status": "success" | "conflict" | "error",
  "modules_updated": ["visualization"],
  "modules_added": ["docker"],
  "rollback_ref": "dev-stack/rollback/20260210T130000Z",
  "conflicts": []
}
```

---

### `dev-stack rollback [--ref TAG] [--json]`

Restore the repository to a previous state.

**Behavior**:
1. If `--ref` provided: use that tag; else: use latest `dev-stack/rollback/*` tag
2. Validate ref exists and is a dev-stack tag
3. Run `git checkout <ref> -- .` for managed files only
4. Update `dev-stack.toml` with restored state
5. Delete rollback tags newer than the restored one

**JSON output schema** (`--json`):
```json
{
  "status": "success" | "error",
  "restored_ref": "dev-stack/rollback/20260210T120000Z",
  "files_restored": [".pre-commit-config.yaml", "pyproject.toml"],
  "tags_cleaned": ["dev-stack/rollback/20260210T130000Z"]
}
```

---

### `dev-stack mcp install [--servers SERVER,...] [--json]`

Install and configure MCP servers.

**Behavior**:
1. Read desired servers from `dev-stack.toml` or `--servers` flag
2. Check for required environment variables (warn if missing)
3. Write agent-specific config file (e.g., Claude `settings.json`, Copilot `mcp.json`)
4. Run health check for each server if available

**JSON output schema** (`--json`):
```json
{
  "status": "success" | "partial" | "error",
  "servers": [
    {
      "name": "context7",
      "installed": true,
      "env_vars_present": true,
      "health_check": "pass"
    },
    {
      "name": "github",
      "installed": true,
      "env_vars_present": false,
      "missing_vars": ["GITHUB_TOKEN"],
      "health_check": "skip"
    }
  ]
}
```

---

### `dev-stack mcp verify [--json]`

Verify MCP server connectivity and configuration.

**JSON output schema** (`--json`):
```json
{
  "status": "all_pass" | "partial" | "all_fail",
  "servers": [
    {"name": "context7", "status": "pass", "latency_ms": 250},
    {"name": "github", "status": "fail", "error": "GITHUB_TOKEN not set"}
  ]
}
```

---

### `dev-stack visualize [--incremental] [--output DIR] [--format svg|png] [--json]`

Generate codebase visualization diagrams.

**Behavior**:
1. Scan source files (respects `.gitignore`)
2. If `--incremental`: compare against `.dev-stack/viz/manifest.json`
3. Invoke agent for schema generation (overview + per-node)
4. Generate D2 diagram markup from schemas
5. Render via `d2` CLI to target format
6. Store manifest for future incremental runs

**JSON output schema** (`--json`):
```json
{
  "status": "success" | "error",
  "diagrams": [
    {"name": "overview", "path": "docs/diagrams/overview.svg", "nodes": 8, "flows": 12},
    {"name": "auth_module", "path": "docs/diagrams/auth_module.svg", "nodes": 5, "flows": 7}
  ],
  "files_scanned": 42,
  "files_changed": 3,
  "agent_invocations": 4,
  "total_duration_ms": 15200
}
```

**Requires**: Agent configured, D2 CLI installed

---

### `dev-stack status [--json]`

Show current stack status and module health.

**JSON output schema** (`--json`):
```json
{
  "manifest_version": "0.1.0",
  "mode": "brownfield",
  "agent": {"cli": "claude", "status": "available"},
  "modules": {
    "hooks": {"installed": true, "version": "0.1.0", "healthy": true},
    "visualization": {"installed": true, "version": "0.1.0", "healthy": false, "issue": "d2 CLI not found"}
  },
  "last_pipeline_run": "2026-02-10T12:00:00Z",
  "rollback_available": true,
  "rollback_ref": "dev-stack/rollback/20260210T120000Z"
}
```
