# Data Model: Init & Pipeline Bugfixes

**Branch**: `006-init-pipeline-bugfixes` | **Date**: 2026-03-10

## Existing Entities (Modified)

### PipelineRunResult (`pipeline/runner.py`)

```python
@dataclass(slots=True)
class PipelineRunResult:
    results: list[StageResult]
    success: bool                      # CHANGED: True only when no hard-gate failures
    aborted_stage: str | None = None
    skip_flag_detected: bool = False
    parallelized: bool = False
```

**Change (FR-006)**: The `success` field is currently computed as `aborted_stage is None or force`. This must change to `not has_hard_failures` — independent of `force`. The `force` flag determines whether the pipeline keeps running (already handled by the runner loop), not whether the outcome is "success."

**State transitions for `success`:**

| All stages pass | Soft-only failures | Hard failure + no force | Hard failure + force |
|---|---|---|---|
| `True` | `True` | `False` (aborted) | `False` (ran all, but hard failure existed) |

---

### StageResult (`pipeline/stages.py`)

No structural change. Existing fields are sufficient:

```python
@dataclass(slots=True)
class StageResult:
    stage_name: str
    status: StageStatus          # PASS | FAIL | WARN | SKIP
    failure_mode: FailureMode    # HARD | SOFT
    duration_ms: int
    output: str = ""
    skipped_reason: str | None = None   # Used by FR-001 ("mypy not installed in venv")
```

---

### ExitCode (`cli/main.py`)

No structural change. Existing codes are sufficient:

```python
class ExitCode:
    SUCCESS = 0
    GENERAL_ERROR = 1
    INVALID_USAGE = 2
    CONFLICT = 3
    AGENT_UNAVAILABLE = 4
    PIPELINE_FAILURE = 5          # Used for both "failed" and "completed_with_failures"
    ROLLBACK_FAILURE = 10
```

**Note (FR-006)**: `PIPELINE_FAILURE = 5` is used for all non-success outcomes. The JSON `status` field distinguishes `"failed"` (aborted early) from `"completed_with_failures"` (ran all stages under `--force`). No new exit code needed.

---

### ConflictReport / FileConflict (`brownfield/conflict.py`)

No structural change. Already supports the allowlist pattern:

```python
@dataclass(slots=True)
class FileConflict:
    path: Path
    conflict_type: ConflictType    # NEW | MODIFIED | DELETED
    proposed_hash: str
    current_hash: str | None = None
    diff: str | None = None
    resolution: str = "pending"    # Can be set to "greenfield_predecessor" to skip
```

**Change (FR-004)**: The `resolution` field will be set to `"greenfield_predecessor"` by the fingerprint check for files that match the `uv init --package` signature. The existing `has_existing_conflicts()` helper already filters by `resolution == "pending"`, so marking predecessors as resolved is sufficient.

---

### Init mode detection (`cli/init_cmd.py`)

Current `_determine_mode()`:

```python
def _determine_mode(already_initialized: bool, has_conflicts: bool) -> str:
    if already_initialized:
        return "reinit"
    if has_conflicts:
        return "brownfield"
    return "greenfield"
```

**Change (FR-004/FR-005)**: After the conflict report is built, a new step filters out greenfield-predecessor conflicts. If all conflicts are resolved as predecessors, `has_existing_conflicts` returns `False`, yielding `"greenfield"` mode. No change to the function signature — the filtering happens upstream.

---

## New Functions (No New Types)

### `is_greenfield_uv_package(pyproject_path: Path) -> bool`

**Location**: `brownfield/conflict.py` or `cli/_shared.py` (colocated with conflict helpers)

```python
import tomllib

def is_greenfield_uv_package(pyproject_path: Path) -> bool:
    """Return True if pyproject.toml matches untouched uv init --package output."""
    if not pyproject_path.exists():
        return False
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    build_system = data.get("build-system", {})
    if build_system.get("build-backend") != "uv_build":
        return False
    project = data.get("project", {})
    if project.get("description") != "Add your description here":
        return False
    if "tool" in data:
        return False
    return True
```

**Signals**: `uv_build` backend + sentinel description + no `[tool.*]` sections.

---

### `_tool_available_in_venv(tool: str, repo_root: Path) -> bool`

**Location**: `pipeline/stages.py` (alongside existing stage helpers)

```python
def _tool_available_in_venv(tool: str, repo_root: Path) -> bool:
    """Check if tool is available inside the project's .venv."""
    venv_bin = repo_root / ".venv" / "bin"
    if not venv_bin.is_dir():
        return False
    return shutil.which(tool, path=str(venv_bin)) is not None
```

**Used by**: `_execute_typecheck_stage` (FR-001), and potentially other stage executors for consistency (FR-008).

---

### `has_unaudited_secrets(baseline_path: Path) -> bool`

**Location**: `pipeline/stages.py` (inline to `_execute_security_stage`)

```python
def has_unaudited_secrets(baseline_path: Path) -> bool:
    """Return True if baseline contains unaudited or confirmed-real secrets."""
    with open(baseline_path) as f:
        baseline = json.load(f)
    for secrets in baseline.get("results", {}).values():
        for secret in secrets:
            if "is_secret" not in secret:
                return True   # unaudited finding
            if secret["is_secret"] is True:
                return True   # confirmed real secret
    return False
```

**Used by**: `_execute_security_stage` (FR-012).

---

## Serialization Changes

### Pipeline JSON output (`pipeline_cmd.py → _serialize_run`)

Current:
```json
{"status": "success" | "failed", "forced": true, ...}
```

New (FR-006):
```json
{"status": "success" | "completed_with_failures" | "failed", "forced": true, ...}
```

| `result.success` | `force` | `status` |
|---|---|---|
| `True` | any | `"success"` |
| `False` | `True` | `"completed_with_failures"` |
| `False` | `False` | `"failed"` |

---

### Version JSON output (`cli/main.py`)

New (FR-009):
```json
{"status": "ok", "version": "0.1.0", "prog_name": "dev-stack"}
```

---

## Relationship Diagram

```
PipelineRunner
  ├─ runs → PipelineStage[] (9 stages)
  │   └─ each executes via StageExecutor → StageResult
  │       ├─ _tool_available_in_venv() [NEW: FR-001/FR-008]
  │       └─ has_unaudited_secrets()    [NEW: FR-012]
  ├─ produces → PipelineRunResult
  │   └─ success = not has_hard_failures [CHANGED: FR-006]
  └─ serialized by → _serialize_run()
      └─ status: success | completed_with_failures | failed [CHANGED: FR-006]

init_command
  ├─ calls → build_conflict_report()
  │   └─ filters via → is_greenfield_uv_package() [NEW: FR-004]
  ├─ calls → _determine_mode()
  │   └─ greenfield when predecessors are allowlisted [CHANGED: FR-004/FR-005]
  ├─ calls → uv sync --all-extras [NEW: FR-002/FR-003]
  ├─ delegates dry-run on initialized → update preview [CHANGED: FR-007]
  └─ calls → create_rollback_tag() [CHANGED: FR-013 — also in greenfield]

cli group
  ├─ @click.version_option() [NEW: FR-009]
  └─ update command help= [CHANGED: FR-010]
```
