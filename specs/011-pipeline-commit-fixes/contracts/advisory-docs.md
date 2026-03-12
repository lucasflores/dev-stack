# Contract: Advisory Doc Suggestions

**Module affected**: `src/dev_stack/pipeline/stages.py`

## Updated: `_execute_docs_narrative_stage()`

**Current behavior**: Writes agent output directly to `guides_index` file on disk.

**New behavior** (when in hook context):
1. Capture agent response as `AdvisoryDocSuggestion`
2. Append to `.dev-stack/pending-docs.md` instead of writing directly
3. Log a summary to stdout: `"[docs-narrative] Suggestions saved to .dev-stack/pending-docs.md"`

**When NOT in hook context** (CLI invocation): Behavior is unchanged — write directly as before.

## `pending-docs.md` Format

```markdown
# Pending Documentation Suggestions

## [docs-narrative] — 2026-03-12T14:30:00

**Target**: docs/guides/index.md

<suggested content here>

---

## [docs-narrative] — 2026-03-12T15:00:00

**Target**: docs/guides/greetings.md

<suggested content here>

---
```

Each suggestion is appended as a new section with a horizontal rule separator.

## Decision Logic

```python
hook_context = os.environ.get("DEV_STACK_HOOK_CONTEXT")
if hook_context:
    # Advisory mode: save to pending-docs.md
    _append_advisory_suggestion(stage_name, response.content, target_path)
else:
    # Direct mode: write to file (current behavior)
    _write_docs_output(target_path, response.content)
```

## `_append_advisory_suggestion()` (new private function)

```python
def _append_advisory_suggestion(
    stage_name: str,
    content: str,
    target_path: str,
) -> None:
    pending = Path(".dev-stack/pending-docs.md")
    pending.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    section = f"\n## [{stage_name}] — {timestamp}\n\n**Target**: {target_path}\n\n{content}\n\n---\n"
    with pending.open("a") as f:
        f.write(section)
```
