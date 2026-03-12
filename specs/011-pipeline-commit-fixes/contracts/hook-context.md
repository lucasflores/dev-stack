# Contract: Hook Context & Stage Routing

**Modules affected**:
- `src/dev_stack/vcs/hooks_runner.py` (new function)
- `src/dev_stack/pipeline/runner.py` (stage filtering)
- New template: `src/dev_stack/templates/hooks/prepare-commit-msg`
- New template: `src/dev_stack/templates/hooks/prepare-commit-msg.py`

## New: `run_prepare_commit_msg_hook(message_file, source, commit_sha)`

**Location**: `src/dev_stack/vcs/hooks_runner.py`

**Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `message_file` | `str` | Path to `.git/COMMIT_EDITMSG` (git's `$1`) |
| `source` | `str \| None` | Message source: `message`, `template`, `merge`, `squash`, `commit`, or `None` |
| `commit_sha` | `str \| None` | Commit SHA when source is `commit` |

**Behavior**:
1. Build hook context (the `HookContext` data model entity is a **design-time concept** — at runtime, context is passed via env vars `DEV_STACK_HOOK_CONTEXT` and `DEV_STACK_MESSAGE_FILE`; no `HookContext` class needs to be instantiated)
2. If `source in ("message", "commit", "merge", "squash")` → exit early (no generation needed)
3. Set env `DEV_STACK_HOOK_CONTEXT=prepare-commit-msg`
4. Set env `DEV_STACK_MESSAGE_FILE=<message_file>`
5. Call `PipelineRunner.run()` with stages 3–9
6. Write resulting commit message to `message_file`

**Returns**: Exit code `int` with differential semantics:
- Stages 3–5 (test, security, docs-api) failure → `1` (abort commit)
- Stages 6–8 (docs-narrative, infra-sync, visualize) failure → `0` (non-blocking; log warning)
- Stage 9 (commit-message) failure → `0` (fallback to git's default editor behavior per FR-009)
- Message-file write errors (PermissionError, OSError) → `0` (log warning, allow git editor fallback)

**Error handling**: All pipeline invocations within the hook MUST be wrapped in try/except. Stage 9 failures and message-file write errors MUST NOT abort the commit — the hook exits 0 to let the editor open with the default/template message.

## Updated: `PipelineRunner.run()` Stage Filtering

**Current**: Runs all stages regardless of hook context.

**New behavior**: When `DEV_STACK_HOOK_CONTEXT` is set, filter `STAGES` by hook context mapping:

```python
HOOK_STAGE_MAP = {
    "pre-commit": [1, 2],          # lint, typecheck
    "prepare-commit-msg": [3, 4, 5, 6, 7, 8, 9],  # test → commit-message
}
```

If `DEV_STACK_HOOK_CONTEXT` is not set (CLI invocation), run all stages as before.

## Hook Templates

### `prepare-commit-msg` (shell wrapper)

```bash
#!/usr/bin/env bash
# Installed by dev-stack init
COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"
COMMIT_SHA="$3"
exec dev-stack hooks run prepare-commit-msg "$COMMIT_MSG_FILE" "$COMMIT_SOURCE" "$COMMIT_SHA"
```

### `prepare-commit-msg.py` (Python entry)

```python
def run_prepare_commit_msg_hook(
    message_file: str,
    source: str | None = None,
    commit_sha: str | None = None,
) -> int:
    ...
```

## Updated: `pre-commit` Hook Template

**Current**: Runs full pipeline (`dev-stack pipeline run "$@"`).

**New**: Runs only `dev-stack hooks run pre-commit "$@"` — which triggers stages 1–2 only.

The existing `run_pre_commit_hook()` already only runs lint+typecheck, so this is a template fix, not a logic change.
