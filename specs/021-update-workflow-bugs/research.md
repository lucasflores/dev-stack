# Research: Dev-Stack Update Workflow Bug Fixes

**Feature**: 021-update-workflow-bugs  
**Phase**: 0 — Pre-Design Research  
**Date**: 2026-04-26

---

## Bug 1 — `packaging` missing from install_requires

### Finding

`src/dev_stack/modules/apm.py` imports `from packaging.version import Version` at the module top level. The `packaging` library is not listed in `[project].dependencies` in `pyproject.toml`. The current dependency list is:

```
click>=8.1, tomli-w>=1.0, rich>=13.7, pathspec>=0.12, gitlint-core>=0.19, pyyaml>=6.0
```

`packaging` is a separate PyPI package distinct from `pip`. Installing the dev-stack wheel alone does not pull it in, causing an immediate `ModuleNotFoundError` on first use of the `apm` command.

### Decision

Add `packaging>=24.0` to `[project].dependencies` in `pyproject.toml`.

### Rationale

`packaging>=24.0` is stable, widely pinned as a transitive dep of many tools, and the `Version` class API has been stable since v21. Pinning `>=24.0` avoids the pre-24 `LegacyVersion` class removal edge cases.

### Alternatives Considered

- Move the import inside the function body (lazy import): avoids the dep declaration problem but is a workaround, not a fix. The dep must be declared regardless.
- Remove `packaging` usage and re-implement version comparison: unnecessary churn.

---

## Bug 2 — Module VERSION constants out of sync

### Finding

`latest_module_entries()` in `src/dev_stack/modules/__init__.py` returns per-module versions by reading the `VERSION` class attribute on each module class:

```python
version = getattr(module_cls, "VERSION", DEFAULT_MODULE_VERSION)
```

`diff_modules()` in `manifest.py` compares `current_entry.version` (from `dev-stack.toml`) against `latest_entry.version` (from `latest_module_entries()`).

Current module `VERSION` constants (as of source audit):

| Module | `VERSION` constant |
|---|---|
| `apm.py` | `0.1.0` |
| `ci_workflows.py` | `0.1.0` |
| `docker.py` | `0.1.2` |
| `hooks.py` | `0.1.0` |
| `sphinx_docs.py` | `0.1.0` |
| `uv_project.py` | `0.1.0` |
| `visualization.py` | `1.0.0` |

Package version in `pyproject.toml`: `1.0.0`.

When the wheel is built at `1.0.0` but most module `VERSION` constants remain at `0.1.x`, `latest_module_entries()` returns `0.1.x`. If a project's `dev-stack.toml` also records `0.1.x` for those modules (because they were installed at that version), `diff_modules()` sees no diff → "No modules require updates."

### Decision

Replace per-module `VERSION` class constants with runtime derivation from `importlib.metadata.version("dev-stack")` (the installed package version). Implement via:

1. A private helper `_package_version() -> str` in `src/dev_stack/modules/__init__.py` that calls `importlib.metadata.version("dev-stack")` and falls back to `DEFAULT_MODULE_VERSION` if the package metadata is not available (e.g., editable installs in CI).
2. `latest_module_entries()` uses `_package_version()` instead of `cls.VERSION`.
3. A `version` `@property` on `ModuleBase` that calls `_package_version()`, used wherever `self.VERSION` is referenced for reporting purposes.
4. Remove `VERSION = "..."` constants from all module files.

### Rationale

Single source of truth: package version in `pyproject.toml` → installed metadata → runtime query. Impossible to forget to bump. The `importlib.metadata` stdlib module (Python 3.8+) is the standard mechanism for this.

### Alternatives Considered

- Procedural checklist (CI gate): would prevent the bug from recurring but would not fix existing installs and relies on humans not skipping the gate.
- `_version.py` file with a single constant imported by all modules: still requires a single manual bump (though only in one place); `importlib.metadata` is strictly better.

---

## Bug 3 — "Missing tools" warning fires on filtered stages

### Finding

The hollow-pipeline advisory in `src/dev_stack/pipeline/runner.py` (lines 219–226):

```python
core_stages = {"lint", "typecheck", "test"}
core_results = [r for r in results if r.stage_name in core_stages]
if core_results and all(r.status == StageStatus.SKIP for r in core_results):
    warnings.append(
        "⚠ No substantive validation: lint, typecheck, test all skipped "
        "due to missing tools. Run 'uv sync --extra dev' to install."
    )
```

The check fires on `status == SKIP` regardless of `skipped_reason`. When `--stage docs-api` is passed, the three core stages get `skipped_reason="filtered via --stage"`, but the warning text says "due to missing tools" and advises `uv sync`.

`skipped_reason` is already correctly set:

| Skip cause | `skipped_reason` value |
|---|---|
| `--stage` filter | `"filtered via --stage"` |
| Tool not installed | `"ruff not installed in project venv — run 'uv sync …'"` |
| `--stage` filter | `"filtered via --stage"` |

The data needed to discriminate is already present; the condition just doesn't use it.

### Decision

Tighten the hollow-pipeline guard to only fire when at least one core stage was skipped due to a missing tool (i.e., `skipped_reason` does not equal `"filtered via --stage"`):

```python
if core_results and all(r.status == StageStatus.SKIP for r in core_results):
    tool_missing = any(
        r.skipped_reason != "filtered via --stage" for r in core_results
    )
    if tool_missing:
        warnings.append(...)
```

### Rationale

Narrow the condition to only the case the advisory is intended for. No new fields, no new data — uses the `skipped_reason` already recorded.

### Alternatives Considered

- Add a separate `skip_category` enum field to `StageResult`: over-engineered for a single condition check; string comparison on the existing field is sufficient.
- Suppress the warning entirely when any `--stage` flag is present: would require threading the selection set into `_record_pipeline_run`; the `skipped_reason` approach is self-contained.

---

## Bug 4 — Stale pipeline data in `dev-stack --json status`

### Finding

`_record_pipeline_run()` in `runner.py` writes this JSON to `.dev-stack/pipeline/last-run.json`:

```json
{
  "timestamp": "2026-04-25T18:00:00Z",
  "success": true,
  "aborted_stage": null,
  "skip_flag_detected": false,
  "parallelized": false,
  "stages": [...]
}
```

`status_cmd.py` reads that file and passes it directly under `"pipeline"` in the JSON payload. No staleness signal exists. A run from a previous session or a `--stage` run looks identical to a fresh, full-pipeline run.

### Decision

Add two fields to the persisted record in `_record_pipeline_run()`:

- `as_of`: ISO 8601 timestamp (same value as `timestamp`; explicit key for programmatic access without guessing field name).
- `stale`: `true` when the run did not execute all stages — computed as:
  ```
  aborted_stage is not None
  OR any stage in results has skipped_reason == "filtered via --stage"
  ```

Hook-context-filtered stages (stages silently removed from `stage_defs` before the loop) are NOT marked stale — hook filtering is expected partial execution, not a diagnostic concern.

No changes required to `status_cmd.py`; the new fields flow through automatically since the full JSON is passed as `"pipeline"`.

### Rationale

Non-breaking: adds fields, removes nothing. Existing consumers see the same structure plus two new fields. The `stale` boolean is machine-actionable; `as_of` removes the ambiguity of the existing `timestamp` key name.

### Alternatives Considered

- Strip `pipeline.stages` from status output: breaking for any consumer reading stage-level data. Spec Q3 clarification explicitly rejected this.
- Move to `pipeline.history` sub-key: requires a shape change that is technically breaking; annotation approach was chosen in spec Q3.
