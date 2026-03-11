# Internal Contracts: Pipeline Commit Hygiene

**Feature Branch**: `009-pipeline-commit-hygiene`
**Date**: 2026-03-10

These are internal API contracts — function signatures and behavioral interfaces within
the pipeline module. There are no external REST/GraphQL APIs in this feature.

## Contract 1: StageResult.output_paths

**Module**: `src/dev_stack/pipeline/stages.py`

```python
@dataclass(slots=True)
class StageResult:
    stage_name: str
    status: StageStatus
    failure_mode: FailureMode
    duration_ms: int
    output: str = ""
    skipped_reason: str | None = None
    output_paths: list[Path] = field(default_factory=list)  # NEW
```

**Invariants**:
- `output_paths` contains absolute `Path` objects
- Only populated when `status` is `PASS` or `SKIP`
- When `status` is `FAIL` or `WARN`, `output_paths` MUST be empty
- Paths may reference files that don't yet exist on disk (e.g., if stage decides not to write)

## Contract 2: StageContext Hook Context

**Module**: `src/dev_stack/pipeline/stages.py`

```python
@dataclass(slots=True)
class StageContext:
    repo_root: Path
    manifest: StackManifest | None = None
    force: bool = False
    agent_bridge: AgentBridge | None = None
    completed_results: list[StageResult] | None = None
    hook_context: str | None = None  # NEW: "pre-commit" when running as hook
    dry_run: bool = False            # NEW: no file mutations in dry-run
```

**Environment variable contract**:
- The pre-commit hook script sets `DEV_STACK_HOOK_CONTEXT=pre-commit`
- `PipelineRunner` reads `os.environ.get("DEV_STACK_HOOK_CONTEXT")` and passes it to `StageContext`

## Contract 3: Auto-Staging Function

**Module**: `src/dev_stack/pipeline/runner.py`

```python
def _auto_stage_outputs(
    repo_root: Path,
    paths: list[Path],
) -> list[str]:
    """Stage pipeline output files into the git index.

    Parameters
    ----------
    repo_root:
        Repository root for running git commands.
    paths:
        Absolute paths to files that should be staged.

    Returns
    -------
    list[str]
        Paths that were successfully staged (relative to repo_root).

    Behavior
    --------
    - Only stages paths that exist on disk.
    - Skips paths matched by .gitignore (checks via `git check-ignore`).
    - Runs `git add <path>` for each eligible file.
    - If `git add` fails for any path, logs a warning and continues.
    - Never raises exceptions — returns partial results on failure.
    """
```

**Preconditions**:
- Called only when `hook_context == "pre-commit"` and `dry_run is False`
- Called after all pipeline stages have completed
- All paths are absolute

**Postconditions**:
- Eligible files are staged in the git index
- Return value lists successfully staged paths (relative)
- No exception propagation — failures are logged, not raised

## Contract 4: Security Stage Baseline Comparison

**Module**: `src/dev_stack/pipeline/stages.py`

```python
def _baseline_findings_changed(
    old_content: str,
    new_content: str,
) -> bool:
    """Compare two .secrets.baseline JSON strings, ignoring `generated_at`.

    Returns True if the `results` section differs between old and new.
    Returns True if either string is not valid JSON (conservative: assume changed).
    """
```

**Invariants**:
- Comparison is on the `results` key only
- `generated_at`, `version`, `plugins_used`, `filters_used` are ignored
- Invalid JSON returns `True` (conservative — treat as changed)

## Contract 5: Visualize Stage LLM Key Check

**Module**: `src/dev_stack/pipeline/stages.py`

```python
LLM_API_KEY_VARS: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
)

def _has_llm_api_key() -> bool:
    """Return True if any supported LLM provider API key is set in the environment."""
    return any(os.environ.get(key) for key in LLM_API_KEY_VARS)
```

**Behavior**:
- Checks all 5 keys
- Empty string values are treated as unset (`os.environ.get(key)` returns falsy for `""`)
- Called before CodeBoarding CLI invocation

## Contract 6: Commit-Message Stage `-m` Detection

**Module**: `src/dev_stack/pipeline/stages.py`

```python
def _user_message_provided(repo_root: Path) -> bool:
    """Detect if the user provided a commit message via `-m` flag.

    Checks if `.git/COMMIT_EDITMSG` exists and contains non-comment content,
    which indicates git has already written the user's `-m` message before
    the pre-commit hook runs.
    """
```

**Behavior**:
- Returns `True` if `.git/COMMIT_EDITMSG` exists and has non-empty non-comment lines
- Comment lines start with `#`
- Returns `False` if file doesn't exist or contains only comments/whitespace

## Contract 7: Pre-Commit Hook Script

**Module**: `src/dev_stack/templates/hooks/pre-commit`

```bash
#!/usr/bin/env bash
set -euo pipefail

# ... existing skip checks ...

export DEV_STACK_HOOK_CONTEXT=pre-commit  # NEW

if dev-stack pipeline --help >/dev/null 2>&1; then
  dev-stack pipeline run "$@"
else
  echo "$HOOK_LABEL: pipeline command unavailable; skipping" >&2
fi
```

**Contract**:
- `DEV_STACK_HOOK_CONTEXT` is exported before `dev-stack pipeline run`
- `"$@"` passes through any arguments from git
