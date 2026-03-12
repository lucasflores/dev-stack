# Data Model: Proactive Agent Instruction File Creation

**Feature**: 010-proactive-agent-instructions  
**Date**: 2025-03-11

## Entities

### AgentFileMap (new constant)

A static mapping from agent CLI name to its canonical instruction file path (relative to repo root).

| Agent CLI | File Path | Notes |
|-----------|-----------|-------|
| `claude` | `CLAUDE.md` | Repo root |
| `copilot` | `.github/copilot-instructions.md` | Requires `.github/` directory |
| `cursor` | `.cursorrules` | Repo root |

**Validation Rules**:
- Agent CLI must be one of `"claude"`, `"copilot"`, `"cursor"`. The value `"none"` is explicitly excluded.
- Exactly one file is created per init (the detected agent's file).

### Agent Instruction File (managed artifact)

An agent-specific file at the canonical path, containing a dev-stack managed section with instruction clauses.

| Attribute | Type | Source |
|-----------|------|--------|
| Path | `Path` (relative to repo root) | `AGENT_FILE_MAP[agent_cli]` |
| Content | Managed section | `markers.write_managed_section(path, "DEV-STACK:INSTRUCTIONS", template_content)` |
| Owned by | `VcsHooksModule` | Lifecycle: install → update → uninstall |

**State Transitions**:

```
[not exists] --init (agent detected)--> [created with managed section]
[created with managed section] --update--> [managed section refreshed]
[created with managed section] --user edits--> [managed section + user content]
[managed section only] --uninstall--> [deleted]
[managed section + user content] --uninstall--> [user content only]
```

### Manifest Agent Section (existing, read-only)

The `"agent"` key in the manifest dict passed to modules. Not modified by this feature.

| Field | Type | Example |
|-------|------|---------|
| `cli` | `str` | `"claude"`, `"copilot"`, `"cursor"`, `"none"` |
| `path` | `str \| None` | `"/usr/local/bin/claude"` |
| `detected_at` | `str` (ISO 8601) | `"2025-03-11T12:00:00Z"` |

### MANAGED_FILES (unchanged)

Remains a static class-level tuple (base files only). The dynamic agent file is NOT added to `MANAGED_FILES` — it is resolved at runtime via the `_get_agent_file_path()` instance method. Lifecycle methods (`update()`, `uninstall()`, `preview_files()`) handle the agent file through this helper.

**Static tuple** (unchanged):
```
.git/hooks/commit-msg
.git/hooks/pre-push
.dev-stack/hooks-manifest.json
.dev-stack/instructions.md
.specify/templates/constitution-template.md
cliff.toml
```

**Agent file** (resolved at runtime via `_get_agent_file_path()`):
```
# When agent=claude:
_get_agent_file_path() → repo_root / AGENT_FILE_MAP["claude"] → CLAUDE.md
```

**Why not dynamic?** The contract test in `test_module_interface.py` accesses `MANAGED_FILES` as a class attribute via `getattr(cls, "MANAGED_FILES", ())`. A `@property` only resolves on instances, so converting would break the test.

## Relationships

```
detect_agent() → AgentInfo.cli
    ↓
manifest.agent.cli (stored in manifest dict)
    ↓
VcsHooksModule.manifest["agent"]["cli"]
    ↓
AGENT_FILE_MAP[cli] → file path
    ↓
markers.write_managed_section(path, "DEV-STACK:INSTRUCTIONS", content)
    ↓
Agent Instruction File (created/updated)
```
