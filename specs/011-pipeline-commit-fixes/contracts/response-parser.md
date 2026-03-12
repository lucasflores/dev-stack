# Contract: response_parser module

**Module**: `src/dev_stack/pipeline/response_parser.py`
**Purpose**: Extract clean commit messages from raw agent stdout, isolating parsing logic from pipeline stage code.

## Public API

### `extract_commit_message(raw: str) -> ParsedCommitMessage | None`

Extracts a commit message from agent output.

**Algorithm**:
1. If `raw` is empty/whitespace → return `None`
2. Scan for fenced code blocks (triple-backtick)
3. If found → extract content of the **last** fenced block (strip language tag)
4. If no fenced blocks → use `raw.strip()` as-is
5. Validate: not empty, subject line ≤ 200 chars, no tool-artifact lines
6. Split into `subject` + `body` (first line vs rest after blank line)
7. Return `ParsedCommitMessage`

**Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `raw` | `str` | Raw stdout content from `AgentResponse.content` |

**Returns**: `ParsedCommitMessage | None` — `None` if extraction fails validation.

**Raises**: No exceptions — returns `None` on failure.

### `ExtractionMethod` (Enum)

```python
class ExtractionMethod(str, Enum):
    CODE_FENCE = "code_fence"
    PLAIN_TEXT = "plain_text"
```

### `ParsedCommitMessage` (dataclass)

```python
@dataclass(frozen=True)
class ParsedCommitMessage:
    subject: str
    body: str | None
    raw_content: str
    extraction_method: ExtractionMethod
    source_hash: str
```

## Integration Point

**Before** (current `_execute_commit_stage`):
```python
body_text = response.content.strip()
upsert_trailers(body_text, stage_ctx)
```

**After**:
```python
from dev_stack.pipeline.response_parser import extract_commit_message

parsed = extract_commit_message(response.content)
if parsed is None:
    logger.warning("Failed to extract commit message from agent response")
    return StageResult(status=StageStatus.FAILED, ...)
upsert_trailers(parsed.raw_content, stage_ctx)
```
