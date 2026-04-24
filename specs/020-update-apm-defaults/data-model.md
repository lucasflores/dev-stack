# Data Model: Update APM Default Packages and Manifest Version

**Feature**: 020-update-apm-defaults  
**Date**: 2026-04-24

---

## Overview

This feature modifies two existing in-memory data structures (class-level constants) and one template file. No new entities are introduced. No database or persistent storage changes are made beyond the template file itself.

---

## Entity: APMModule (modified)

**File**: `src/dev_stack/modules/apm.py`  
**Type**: Python class (singleton-style, instantiated per repo root)

### Changed Fields

| Field | Type | Old Value | New Value | Constraint |
|-------|------|-----------|-----------|-----------|
| `DEFAULT_SERVERS` | `tuple[str, ...]` | `("io.github.upstash/context7", "io.github.github/github-mcp-server", "huggingface/hf-mcp-server")` | `()` | Empty — no MCP servers in defaults |
| `DEFAULT_APM_PACKAGES` | `tuple[str, ...]` | `("lucasflores/agent-skills",)` | (4 path-specific entries — see below) | Must match template exactly |

`DEFAULT_APM_PACKAGES` new value:
```python
(
    "lucasflores/agent-skills/agents/idea-to-speckit.agent.md",
    "lucasflores/agent-skills/prompts/AutoSpecKit.prompt.md",
    "lucasflores/agent-skills/skills/commit-pipeline",
    "lucasflores/agent-skills/skills/dev-stack-update",
)
```

### Invariant

`DEFAULT_APM_PACKAGES` and `dependencies.apm` in `default-apm.yml` MUST always be in sync. They serve two different code paths (fresh install uses the template; merge uses the constants) and must produce the same set of entries.

---

## Entity: APM Manifest Template (modified)

**File**: `src/dev_stack/templates/apm/default-apm.yml`  
**Type**: YAML template file (static asset, rendered at install time)

### Schema

```yaml
name: string          # {{ PROJECT_NAME }} placeholder, rendered at bootstrap
version: string       # Semver string; bumped to "2.0.0"
dependencies:
  # mcp: key REMOVED entirely
  apm:                # list of string; path-specific package entries
    - string          # owner/repo/path/to/item format
```

### Validation Rules

- `name` MUST contain the `{{ PROJECT_NAME }}` placeholder when stored; rendered before write
- `version` MUST be `"2.0.0"` (exact string; not evaluated as semver at runtime)
- `dependencies.mcp` MUST NOT be present
- `dependencies.apm` MUST contain exactly 4 entries matching `DEFAULT_APM_PACKAGES`
- Each `apm` entry MUST follow `owner/repo/path` format (validated by APM CLI at install time)

---

## Behavior Change: `_merge_manifest`

### Merge Logic (MCP section)

| Scenario | Old Behavior | New Behavior |
|----------|-------------|-------------|
| No existing `mcp` entries, `DEFAULT_SERVERS = ()` | Writes `mcp: []` | Omits `mcp` key entirely |
| Existing `mcp` entries, `DEFAULT_SERVERS = ()` | Preserves existing entries, writes them back | Preserves existing entries, writes them back (no change) |
| Existing `mcp` entries + defaults to add | Appends defaults | N/A — no defaults exist |

### Merge Logic (APM deduplication key)

| Entry format | Old dedup key | New dedup key |
|-------------|---------------|---------------|
| `lucasflores/agent-skills` | `lucasflores/agent-skills` | `lucasflores/agent-skills` |
| `lucasflores/agent-skills/skills/commit-pipeline` | `lucasflores/agent-skills/skills/commit-pipeline` | `lucasflores/agent-skills/skills/commit-pipeline` |
| `lucasflores/agent-skills#abc123` | `lucasflores/agent-skills` | `lucasflores/agent-skills` |
| `lucasflores/agent-skills/skills/commit-pipeline#v1.0` | `lucasflores/agent-skills/skills/commit-pipeline` | `lucasflores/agent-skills/skills/commit-pipeline` |

The dedup logic (`split("#")[0]`) is unchanged in code. The behavior change comes from `DEFAULT_APM_PACKAGES` now containing full paths — each path is treated as a distinct entry.

---

## State Transitions

No state machine changes. `verify()`, `install()`, `update()`, `uninstall()`, and `preview_files()` follow unchanged state transitions. The only outputs that change are:

1. The content written to `apm.yml` on fresh install (template change)
2. The entries added during merge (constant change)
3. The success message string on zero exit (string change)
