# Data Model: Dev-Stack Update Workflow Bug Fixes

**Feature**: 021-update-workflow-bugs  
**Phase**: 1 — Design  
**Date**: 2026-04-26

---

## Overview

This feature touches four existing data structures. No new entities are introduced. The changes are:

1. **`pyproject.toml` dependency list** — add `packaging>=24.0`
2. **Module version source** — remove per-module `VERSION` constants; derive at runtime from installed package metadata
3. **`StageResult.skipped_reason`** — existing field; the hollow-pipeline guard logic uses it but does not evaluate it correctly
4. **Pipeline run record** — two new fields: `as_of` and `stale`

---

## Entity 1: Module Version (runtime-derived)

### Before

Each module class carries a hardcoded class attribute:

```python
class APMModule(ModuleBase):
    VERSION = "0.1.0"   # per-module constant, manually maintained
```

`latest_module_entries()` reads: `getattr(module_cls, "VERSION", DEFAULT_MODULE_VERSION)`

### After

`ModuleBase` exposes a `version` property backed by a shared helper:

```python
# src/dev_stack/modules/__init__.py
def _package_version() -> str:
    try:
        from importlib.metadata import version
        return version("dev-stack")
    except Exception:
        return DEFAULT_MODULE_VERSION
```

```python
# src/dev_stack/modules/base.py — new property on ModuleBase
@property
def version(self) -> str:
    from dev_stack.modules import _package_version
    return _package_version()
```

`latest_module_entries()` reads: `_package_version()` (same value for all modules).

Per-module `VERSION = "..."` constants are **removed** from all module files.

### Validation Rules

- `_package_version()` MUST never raise; it falls back to `DEFAULT_MODULE_VERSION` on any exception.
- The `version` property MUST return a PEP 440-compatible string.

---

## Entity 2: StageResult (existing, unchanged shape)

```python
@dataclass(slots=True)
class StageResult:
    stage_name: str
    status: StageStatus             # PASS | FAIL | WARN | SKIP
    failure_mode: FailureMode       # hard | soft
    duration_ms: int
    output: str = ""
    skipped_reason: str | None = None   # ← key discriminator field (unchanged)
    output_paths: list[Path] = field(default_factory=list)
```

### Skip Reason Vocabulary (documented, not changed)

| Value | Meaning |
|---|---|
| `"filtered via --stage"` | Stage omitted by explicit `--stage` filter argument |
| `"ruff not installed in project venv — run 'uv sync --extra dev --extra docs' to install"` | Ruff binary absent |
| `"pytest not installed in project venv — run 'uv sync --extra dev --extra docs' to install"` | pytest binary absent |
| `"mypy not installed in project venv — run 'uv sync --extra dev --extra docs' to install"` | mypy binary absent |
| `"sphinx not found — run 'uv sync --extra dev --extra docs' to install"` | sphinx binary absent |
| `"tests directory missing"` | `tests/` not found in repo |
| `"coding agent unavailable"` | No coding agent detected |
| `"no staged changes detected"` | Nothing to act on |

The **hollow-pipeline advisory** fires only when at least one core stage (`lint`, `typecheck`, `test`) was skipped for a reason **other than** `"filtered via --stage"`.

---

## Entity 3: PipelineRunRecord (persisted JSON — extended)

File: `.dev-stack/pipeline/last-run.json`

### Before

```jsonc
{
  "timestamp": "2026-04-25T18:00:00Z",
  "success": true,
  "aborted_stage": null,
  "skip_flag_detected": false,
  "parallelized": false,
  "stages": [
    {
      "name": "lint",
      "status": "pass",
      "failure_mode": "hard",
      "duration_ms": 420,
      "output": "...",
      "skipped_reason": null
    }
  ]
}
```

### After (new fields: `as_of`, `stale`)

```jsonc
{
  "timestamp": "2026-04-25T18:00:00Z",
  "as_of": "2026-04-25T18:00:00Z",      // ← NEW: explicit alias; same value as timestamp
  "stale": false,                         // ← NEW: true if run was partial/incomplete
  "success": true,
  "aborted_stage": null,
  "skip_flag_detected": false,
  "parallelized": false,
  "stages": [...]
}
```

### `stale` Computation

```
stale = (
    summary.aborted_stage is not None              # run failed mid-way
    OR any(r.skipped_reason == "filtered via --stage"
           for r in summary.results)               # --stage filter used
)
```

| Run type | `stale` |
|---|---|
| Full pipeline, all stages pass | `false` |
| Full pipeline, one stage fails (and aborts) | `true` |
| `--stage docs-api` (filter) | `true` |
| Hook-context run (pre-commit: stages 1–2 only) | `false` — hook-filtered stages are not in `results` |
| `--skip-flag` detected (entire pipeline skipped) | `false` — `results` is empty; no filter stages present |

### Backward Compatibility

Consumers reading the old format receive the same fields plus `as_of` and `stale`. No fields are removed or renamed. Consumers that do not read the new fields are unaffected.

---

## Entity 4: pyproject.toml dependency list (trivial)

```toml
# Before
dependencies = [
  "click>=8.1",
  "tomli-w>=1.0",
  "rich>=13.7",
  "pathspec>=0.12",
  "gitlint-core>=0.19",
  "pyyaml>=6.0",
]

# After
dependencies = [
  "click>=8.1",
  "tomli-w>=1.0",
  "rich>=13.7",
  "pathspec>=0.12",
  "gitlint-core>=0.19",
  "pyyaml>=6.0",
  "packaging>=24.0",        # ← NEW
]
```
