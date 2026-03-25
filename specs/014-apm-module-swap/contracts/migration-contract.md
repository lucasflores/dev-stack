# Migration Contract: SpecKit Deprecation Handler

**Feature**: 014-apm-module-swap | **Date**: 2026-03-24

## Overview

This contract defines the behavior of the migration handler that detects and gracefully handles `[modules.speckit]` entries in existing `dev-stack.toml` files during `dev-stack update`.

## Contract: `DEPRECATED_MODULES` Registry

**Location**: `src/dev_stack/modules/__init__.py`

```python
DEPRECATED_MODULES: dict[str, str] = {
    "speckit": "The 'speckit' module has been removed. Agent dependencies are now managed by the 'apm' module. Run 'specify init --here --ai copilot' to set up the .specify/ directory.",
}
```

**Behavior**:
- Maps module names to human-readable deprecation messages
- Queried during update when a module in `dev-stack.toml` is not found in `_MODULE_REGISTRY`
- Returns the message string for display to the user

## Contract: Update Command Migration Flow

**Location**: `src/dev_stack/cli/update_cmd.py`

### Pre-conditions
- `dev-stack.toml` exists with one or more `[modules.*]` sections
- One or more module names in the manifest are not in `_MODULE_REGISTRY`

### Flow

```text
For each module_name in dev-stack.toml modules:
  If module_name in _MODULE_REGISTRY:
    → proceed with normal update
  Elif module_name in DEPRECATED_MODULES:
    → emit info message: DEPRECATED_MODULES[module_name]
    → add deprecated = true to the TOML section
    → skip module instantiation
    → do NOT raise error
  Else:
    → emit warning: "Unknown module '{module_name}' — skipping"
    → skip module instantiation
```

### Post-conditions
- `dev-stack.toml` has `deprecated = true` added to `[modules.speckit]` section
- No error raised, no non-zero exit code from this handler
- The `apm.yml` manifest is updated (if APM module runs as part of the update)

### Exit codes
| Scenario | Exit code |
|----------|-----------|
| Deprecated module detected and handled | 0 (success) |
| Deprecated module + other update failures | Non-zero (from other failures, not deprecation) |

### Human output
```
ℹ Module 'speckit' has been removed.
  Agent dependencies are now managed by the 'apm' module.
  Run 'specify init --here --ai copilot' to set up the .specify/ directory.
  Marking [modules.speckit] as deprecated in dev-stack.toml.
```

### JSON output
```json
{
  "deprecated_modules": [
    {
      "name": "speckit",
      "message": "The 'speckit' module has been removed. Agent dependencies are now managed by the 'apm' module. Run 'specify init --here --ai copilot' to set up the .specify/ directory.",
      "action": "marked_deprecated"
    }
  ]
}
```

## Contract: `dev-stack.toml` TOML Mutation

**Pre-mutation**:
```toml
[modules.speckit]
version = "0.1.0"
installed = true
```

**Post-mutation**:
```toml
[modules.speckit]
version = "0.1.0"
installed = true
deprecated = true
```

**Rules**:
- Only `deprecated = true` is added — no existing keys are removed
- The section header `[modules.speckit]` is preserved
- If `deprecated = true` already exists, no duplicate is added (idempotent)
- If `installed = false`, the deprecation is still applied (the module was referenced)

### Rollback

The `deprecated = true` mutation is additive and non-destructive. To roll back:
1. Manually remove the `deprecated = true` line from `[modules.speckit]` in `dev-stack.toml`
2. No automated rollback mechanism is required — the change is trivially reversible by hand-editing one line in a TOML file
3. Re-running `dev-stack update` after rollback will re-apply the deprecation marker (idempotent)

## Contract: Expanded `apm.yml` Template

**Location**: `src/dev_stack/templates/apm/default-apm.yml`

**Pre-change**:
```yaml
name: "{{ PROJECT_NAME }}"
version: "1.0.0"
dependencies:
  mcp:
    - ghcr.io/upstash/context7-mcp-server
    - ghcr.io/github/github-mcp-server
    - ghcr.io/modelcontextprotocol/sequentialthinking-server
    - ghcr.io/huggingface/mcp-server
    - ghcr.io/notebooklm/mcp-server
```

**Post-change**:
```yaml
name: "{{ PROJECT_NAME }}"
version: "1.0.0"
dependencies:
  mcp:
    - ghcr.io/upstash/context7-mcp-server
    - ghcr.io/github/github-mcp-server
    - ghcr.io/modelcontextprotocol/sequentialthinking-server
    - ghcr.io/huggingface/mcp-server
    - ghcr.io/notebooklm/mcp-server
  apm:
    - msitarzewski/agency-agents#<tag>
    - Hacklone/lazy-spec-kit#<tag>
```

**Rules**:
- All `dependencies.mcp` entries are preserved (no regression — FR-007)
- New `dependencies.apm` entries are pinned to specific git tags (clarification Q2)
- The `_merge_manifest()` method must be updated to handle `dependencies.apm` in addition to `dependencies.mcp`
