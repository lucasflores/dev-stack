# Quickstart: Pipeline Commit Fixes

## What Changed

This feature fixes 4 problems in the dev-stack pipeline's git hook integration:

1. **Dirty commit messages** — Agent responses (markdown, tool artifacts) were written directly as commit messages. Now a `response_parser` extracts clean messages using a last-code-fence heuristic.
2. **Hooks don't use git's message plumbing** — Commit message generation moved from `pre-commit` to `prepare-commit-msg` hook, which receives `$1` (message file path) from git directly.
3. **Stale change detection** — The prepare-commit-msg source argument (`$2`) replaces the unreliable `_user_message_provided()` function that read `COMMIT_EDITMSG` too early.
4. **Uncontrolled agent writes** — Agents run in sandbox mode during hooks (no filesystem writes). Doc suggestions go to `.dev-stack/pending-docs.md` instead of being applied directly.

## New Files

| File | Purpose |
|------|---------|
| `src/dev_stack/pipeline/response_parser.py` | Extracts clean commit messages from raw agent output |
| `src/dev_stack/templates/hooks/prepare-commit-msg` | Shell wrapper for the new hook |
| `src/dev_stack/templates/hooks/prepare-commit-msg.py` | Python entry point for prepare-commit-msg |

## Modified Files

| File | Change |
|------|--------|
| `src/dev_stack/pipeline/stages.py` | Uses `response_parser` for commit stage; advisory mode for docs-narrative |
| `src/dev_stack/pipeline/agent_bridge.py` | Adds `sandbox` parameter with `--deny-tool` flags |
| `src/dev_stack/pipeline/runner.py` | Filters stages by `DEV_STACK_HOOK_CONTEXT` |
| `src/dev_stack/vcs/hooks_runner.py` | Adds `run_prepare_commit_msg_hook()` |
| `src/dev_stack/templates/hooks/pre-commit` | Runs only stages 1–2 (was running full pipeline) |

## Developer Workflow

### Testing the Response Parser

```python
from dev_stack.pipeline.response_parser import extract_commit_message

# Agent returned markdown with a fenced block
raw = """Here's your commit message:

```
feat(pipeline): add sandbox mode for hook execution

Prevents agent stages from modifying staged content during git hooks.
```

This follows conventional commits format.
"""

result = extract_commit_message(raw)
assert result.subject == "feat(pipeline): add sandbox mode for hook execution"
assert result.extraction_method.value == "code_fence"
```

### Testing Hook Context

```bash
# Simulate prepare-commit-msg with no user message
DEV_STACK_HOOK_CONTEXT=prepare-commit-msg dev-stack hooks run prepare-commit-msg .git/COMMIT_EDITMSG

# Simulate with -m flag (should skip generation)
DEV_STACK_HOOK_CONTEXT=prepare-commit-msg dev-stack hooks run prepare-commit-msg .git/COMMIT_EDITMSG message
```

### Debug Logging

```bash
# Enable debug logging for any pipeline run
DEV_STACK_DEBUG=1 git commit

# Logs written to .dev-stack/logs/pipeline-<timestamp>.log
```

### Reviewing Pending Doc Suggestions

After a commit, check for advisory suggestions:

```bash
cat .dev-stack/pending-docs.md
```

Apply or discard suggestions manually, then clear the file.

## Stage Distribution

| Hook | Stages | Purpose |
|------|--------|---------|
| `pre-commit` | 1 (lint), 2 (typecheck) | Fast quality gates |
| `prepare-commit-msg` | 3–9 (test → commit-message) | Generation & integration stages |
| `commit-msg` | gitlint validation | Message format check |
| `pre-push` | Unchanged | Push-time checks |
