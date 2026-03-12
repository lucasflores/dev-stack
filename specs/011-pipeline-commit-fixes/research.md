# Research: Pipeline Commit Fixes

**Feature**: `011-pipeline-commit-fixes`
**Date**: 2026-03-12

## R1: Git prepare-commit-msg Hook Arguments & Behavior

### Decision
Use the `prepare-commit-msg` hook's `$2` (source) argument to reliably detect whether a user supplied a message, eliminating the stale `COMMIT_EDITMSG` problem.

### Findings

**Hook signature**: `prepare-commit-msg <message-file> [<source>] [<sha>]`

| Command | `$2` (source) | `$3` (SHA) |
|---|---|---|
| `git commit` (no flags) | *(absent)* | *(absent)* |
| `git commit -m "msg"` | `message` | *(absent)* |
| `git commit -F file` | `message` | *(absent)* |
| `git commit -t tpl` | `template` | *(absent)* |
| `git commit` with `commit.template` set | `template` | *(absent)* |
| `git merge` (auto-commit) | `merge` | *(absent)* |
| `git commit --amend` | `commit` | `<HEAD SHA>` |
| `git commit -c <sha>` | `commit` | `<sha>` |
| `git commit --squash=<sha>` | `squash` | *(absent)* |

**Key insight**: When source is absent or `template`, the user has NOT provided a message — this is when the pipeline should generate one. When source is `message`, `commit`, `merge`, or `squash`, the user or git has already provided content → skip generation.

### Rationale
This replaces the current `_user_message_provided()` function which reads `COMMIT_EDITMSG` — a file that persists across commits and causes false positives. The hook source argument is authoritative and per-invocation.

### Alternatives Considered
- **Check `GIT_EDITOR` env var**: Git sets `GIT_EDITOR=:` when no editor will open. Too indirect — doesn't tell us about the message source.
- **Parse `/proc/*/cmdline` for `-m` flag**: Fragile, non-portable, security risk.
- **Timestamp COMMIT_EDITMSG**: Still subject to race conditions and doesn't address the fundamental issue.

## R2: Hook Execution Order

### Decision
The execution order confirms our stage distribution is correct:

```
1. pre-commit           ← stages 1-2 (lint, typecheck)
2. prepare-commit-msg   ← stages 3-9 (test through commit-message)
3. [editor opens]
4. commit-msg           ← message validation (existing)
5. post-commit          ← notification only
```

### Findings
- `pre-commit` fires first — validates staged changes. Can abort via exit 1.
- `prepare-commit-msg` fires second — receives message file path. Can modify the file in place. Can abort via exit 1.
- Editor opens after `prepare-commit-msg` (unless `--no-edit`, `-m`, etc.).
- `commit-msg` fires after editor closes — receives final message file for validation.

### Rationale
Stages 1-2 (lint, typecheck) are fast, non-agent, validation-only gates that should block before the heavier stages run. Stages 3-9 include agent invocations and the commit-message writer — they need to run after pre-commit succeeds but before the editor opens.

### Critical implication
The pipeline now spans two hooks. If a HARD failure occurs in stages 3-5 (test, security) during `prepare-commit-msg`, the hook must exit 1 to abort the commit — same behavior as the current pre-commit approach.

## R3: prepare-commit-msg and Editor Interaction

### Decision
Write the generated commit message to the message file (`$1`). If the user has no `-m`/`--no-edit`, the editor will open showing the generated message — the user can review and edit it before finalizing.

### Findings
- `prepare-commit-msg` runs BEFORE the editor opens.
- The hook writes to `$1` (the message file) in place.
- If the editor opens, it shows the hook's modifications — user can edit.
- If `--no-edit` is set (or `-m` was used), the editor is skipped and the file content is used directly.
- The hook CANNOT suppress the editor programmatically. This is by design.

### Rationale
This is actually a feature, not a bug: the developer gets to review the AI-generated message before it's committed. For `--no-edit` workflows, the message is used directly.

## R4: Copilot CLI Sandbox Mode

### Decision
Remove `--allow-all` and `COPILOT_ALLOW_ALL=true` from hook-context invocations. Use `--deny-tool='write'` to explicitly prevent filesystem modifications during the commit pipeline.

### Findings
Copilot CLI has granular permission flags:

| Flag | Effect |
|---|---|
| `--allow-all` / `--allow-all-tools` | Allow everything without prompts |
| `--allow-tool='shell(CMD)'` | Allow specific shell commands |
| `--deny-tool='write'` | Deny file write tools (overrides allow) |
| `--deny-tool='shell(CMD)'` | Deny specific shell commands |

**Without any flags**: Copilot enters interactive approval mode (prompts for each tool use). Not suitable for non-interactive hook execution.

**Recommended sandbox flags for hooks**:
```
--deny-tool='write'
--allow-tool='shell(git diff)'
--allow-tool='shell(git log)'
--allow-tool='shell(git show)'
--allow-tool='shell(cat)'
--allow-tool='shell(find)'
```

This permits Copilot to read repository state but not write files.

### Rationale
`--deny-tool` takes precedence over `--allow-tool`, so even if `--allow-all` were accidentally left in, `--deny-tool='write'` would still block filesystem writes. Using selective `--allow-tool` for read-only commands avoids interactive prompts.

### Alternatives Considered
- **Omit all flags**: Enters interactive mode — blocks in hooks since there's no TTY.
- **Container sandboxing**: Overkill for this use case; adds Docker dependency.
- **Capture output only via `--print`**: Not available in Copilot CLI (that's a Claude flag).

## R5: Agent Response Parsing Strategy

### Decision
Implement a `response_parser.py` module that extracts the clean commit message from raw agent output using a layered extraction strategy.

### Findings
Agent responses vary by CLI:

**Claude** (`claude --print`): Returns clean text or JSON. Minimal noise because `--print` disables interactive mode and `--max-turns 1` prevents tool loops.

**Copilot** (`gh copilot`): Returns full session output including:
- Thinking/reasoning traces
- Tool-use invocations and results
- The actual response, often wrapped in code fences (` ```...``` `)
- Status messages and progress indicators

**Cursor** (`cursor --prompt`): Similar to Claude — relatively clean output.

### Parsing strategy (ordered by priority)

1. **Code fence extraction**: Scan for ` ```[lang]\n...\n``` ` or `~~~...~~~` blocks. If found, use the **last** code-fenced block (the agent's final answer after tool use and reasoning).
2. **No code fences**: Use the full response content (backward compatible with Claude/Cursor).
3. **Empty result**: Reject and return failure.

### Validation after extraction
- Strip leading/trailing whitespace
- Reject if empty after stripping
- Reject if first line exceeds 200 characters (likely not a commit subject line)
- Reject if content contains obvious tool-use artifacts (e.g., `Tool:`, `Running:`, `Result:` patterns at line starts)

### Rationale
The last-code-fence heuristic is robust because:
- Agents typically put their final answer in the last code block
- Tool-use traces and thinking appear before the final answer
- Plain responses (no fences) work with the fallback path

### Alternatives Considered
- **JSON output mode**: Only works with Claude (`--output-format json`). Copilot doesn't support structured output.
- **Regex for conventional commit pattern**: Too fragile — commit messages can have varied formats.
- **First code fence**: Wrong — agents often show intermediate results in early code blocks.

## R6: Pre-commit Hook Changes

### Decision
The existing `pre-commit` shell wrapper currently runs `dev-stack pipeline run "$@"` which executes ALL stages. This must be changed to run only stages 1-2.

### Findings
Current `pre-commit` hook template (shell wrapper):
```bash
export DEV_STACK_HOOK_CONTEXT=pre-commit
dev-stack pipeline run "$@"
```

This runs the full pipeline. The pipeline runner checks `DEV_STACK_HOOK_CONTEXT` but doesn't use it to filter stages.

The `pre-commit.py` template is separate — it directly calls `run_pre_commit_hook()` which already only runs lint + typecheck. But the shell wrapper runs the full pipeline.

### Rationale
Two options:
1. **Modify the shell wrapper** to pass `--stage lint --stage typecheck`
2. **Make the runner honor `DEV_STACK_HOOK_CONTEXT`** to auto-select stages

Option 2 is cleaner: the runner already receives `hook_context` — we just need to filter stages based on it.

### Decision
Add hook-context-aware stage filtering to `PipelineRunner.run()`:
- `hook_context="pre-commit"` → run only stages with `order <= 2`
- `hook_context="prepare-commit-msg"` → run only stages with `order >= 3`
- No hook context → run all stages (CLI `dev-stack pipeline run` behavior)
