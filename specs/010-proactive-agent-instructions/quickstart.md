# Quickstart: Proactive Agent Instruction File Creation

**Feature**: 010-proactive-agent-instructions  
**Date**: 2025-03-11

## What Changes

After this feature, `dev-stack init` in a greenfield repo will automatically create the coding agent's instruction file with dev-stack's TDD and atomic-commit clauses. No manual file creation needed.

## Before (current behavior)

```bash
$ mkdir my-project && cd my-project && git init && uv init --package
$ DEV_STACK_AGENT=claude dev-stack init

# Result: .dev-stack/instructions.md exists ✓
# Result: CLAUDE.md does NOT exist ✗
# Claude never sees the instructions.
```

## After (new behavior)

```bash
$ mkdir my-project && cd my-project && git init && uv init --package
$ DEV_STACK_AGENT=claude dev-stack init

# Result: .dev-stack/instructions.md exists ✓
# Result: CLAUDE.md exists ✓ — with managed section containing TDD/atomic-commit clauses
# Claude reads CLAUDE.md on next invocation and follows the instructions.
```

## Per-Agent File Created

| Detected Agent | File Created |
|----------------|--------------|
| `claude` | `CLAUDE.md` |
| `copilot` | `.github/copilot-instructions.md` |
| `cursor` | `.cursorrules` |
| `none` | *(no agent file)* |

## Files Modified

| File | Change |
|------|--------|
| `src/dev_stack/modules/vcs_hooks.py` | Add `AGENT_FILE_MAP`, `_get_agent_file_path()`, `_create_agent_file()`, uninstall cleanup |
| `tests/unit/test_vcs_hooks_module.py` | New tests for proactive creation, idempotency, uninstall cleanup |
| `tests/integration/test_hooks_lifecycle.py` | Integration test for greenfield init with agent detection |

## Verification

```bash
# After implementation, verify in a fresh test repo:
DEV_STACK_AGENT=claude dev-stack --json init 2>&1 | python3 -c "
import json, sys
data = json.load(sys.stdin)
modules = data.get('modules', {})
vcs = modules.get('vcs_hooks', {})
files = [str(f) for f in vcs.get('files_created', [])]
assert any('CLAUDE.md' in f for f in files), 'CLAUDE.md not in files_created'
print('PASS: CLAUDE.md created')
"
```
