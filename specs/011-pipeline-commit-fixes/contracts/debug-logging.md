# Contract: Debug Logging

**Modules affected**: All pipeline stages, `response_parser.py`, `hooks_runner.py`

## Activation

Debug logging is enabled when the environment variable `DEV_STACK_DEBUG=1` is set.

## Log Directory

```
.dev-stack/logs/
├── pipeline-<timestamp>.log    # Full pipeline run
├── stage-<name>-<timestamp>.log  # Per-stage detail
```

## What Gets Logged

| Event | Log Content |
|-------|-------------|
| Agent invocation | Full prompt, command line (redacted secrets), sandbox mode |
| Agent response | Raw stdout (full content), stderr if non-empty |
| Response parsing | Extraction method, source_hash, extracted subject |
| Hook context | hook_name, source, commit_sha, stages selected |
| Staged snapshot | diff_hash before/after, match result |
| Stage skip | Stage name, reason (hook context filtering) |

## Log Format

```
[2026-03-12T14:30:00.123Z] [DEBUG] [response_parser] extraction_method=CODE_FENCE subject="feat: add new pipeline stage" source_hash=abc123...
[2026-03-12T14:30:00.456Z] [DEBUG] [agent_bridge] sandbox=true agent=copilot cmd="gh copilot -- ..."
[2026-03-12T14:30:01.789Z] [DEBUG] [staged_snapshot] before=def456... after=def456... match=true
```

## Implementation

Use Python's `logging` module with a conditional file handler:

```python
import logging
import os

def _configure_debug_logging() -> None:
    if os.environ.get("DEV_STACK_DEBUG") != "1":
        return
    log_dir = Path(".dev-stack/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / f"pipeline-{timestamp}.log")
    handler.setLevel(logging.DEBUG)
    logging.getLogger("dev_stack").addHandler(handler)
```

No debug output goes to stdout/stderr — file-only to avoid interfering with agent output capture.
