# CLI Behavior Contracts: Dev-Stack Update Workflow Bug Fixes

**Feature**: 021-update-workflow-bugs  
**Phase**: 1 — Design  
**Date**: 2026-04-26

These contracts describe the observable CLI behavior before and after each fix. They are the acceptance criteria translated into concrete input/output expectations.

---

## Contract 1 — `pyproject.toml` declares `packaging` (Bug 1 / FR-001)

### Trigger

Any `dev-stack` command executed in an environment where `packaging` is not independently installed.

### Before (broken)

```
$ python -m pip install dev_stack-1.0.0-py3-none-any.whl
$ dev-stack --version
Traceback (most recent call last):
  ...
ModuleNotFoundError: No module named 'packaging'
```

### After (fixed)

```
$ python -m pip install dev_stack-1.0.0-py3-none-any.whl
$ dev-stack --version
dev-stack 1.0.0
```

`packaging` is pulled in transitively by pip's dependency resolution. No manual step required.

### File Changed

`pyproject.toml` — `[project].dependencies`

---

## Contract 2 — `dev-stack update` reports outdated modules after version bump (Bug 2 / FR-002, FR-003)

### Trigger

`dev-stack update` run in a project whose `dev-stack.toml` records module versions from an older release.

### Before (broken)

```
$ cat .dev-stack.toml | grep version    # project recorded 0.1.0 at install time
version = "0.1.0"

$ dev-stack update
✓ No modules require updates.           # FALSE — package is now 1.0.0
```

### After (fixed)

```
$ cat .dev-stack.toml | grep version
version = "0.1.0"

$ dev-stack update
  Modules to update: apm, ci-workflows, hooks, sphinx_docs, uv_project
  ...
✓ Update complete.
```

After update, `dev-stack.toml` records `1.0.0` for all modules. Running `dev-stack update` again:

```
$ dev-stack update
✓ No modules require updates.           # CORRECT — all at 1.0.0
```

### Source Changed

`src/dev_stack/modules/__init__.py` — `latest_module_entries()` and new `_package_version()` helper  
`src/dev_stack/modules/base.py` — `version` property on `ModuleBase`  
`src/dev_stack/modules/*.py` — remove `VERSION = "..."` class constants

---

## Contract 3 — Pipeline summary does not emit "missing tools" advisory on filtered runs (Bug 3 / FR-004, FR-005)

### Trigger

`dev-stack pipeline --stage <name>` where all dev tools (ruff, pytest, mypy) are installed.

### Before (broken)

```
$ dev-stack pipeline --stage docs-api

Pipeline complete.
  [skip] lint     — filtered via --stage
  [skip] typecheck — filtered via --stage
  [skip] test     — filtered via --stage
  [pass] docs-api  — 2340ms

⚠ No substantive validation: lint, typecheck, test all skipped due to missing tools.
  Run 'uv sync --extra dev' to install.   ← WRONG: tools are present, stages were filtered
```

### After (fixed) — all tools present, filter used

```
$ dev-stack pipeline --stage docs-api

Pipeline complete.
  [skip] lint     — filtered via --stage
  [skip] typecheck — filtered via --stage
  [skip] test     — filtered via --stage
  [pass] docs-api  — 2340ms
                  ← No advisory (tools are present; skip is intentional)
```

### After (correct) — tool genuinely absent

```
$ dev-stack pipeline   # ruff not installed

Pipeline complete.
  [skip] lint     — ruff not installed in project venv — run 'uv sync --extra dev ...' to install
  ...

⚠ No substantive validation: lint, typecheck, test all skipped due to missing tools.
  Run 'uv sync --extra dev' to install.   ← CORRECT: advisory only fires here
```

### Source Changed

`src/dev_stack/pipeline/runner.py` — hollow-pipeline guard condition (lines ~219–226)

---

## Contract 4 — `dev-stack --json status` `pipeline` block carries `as_of` and `stale` fields (Bug 4 / FR-006, FR-007)

### Trigger

`dev-stack --json status` after any pipeline run.

### Before (broken)

```json
{
  "pipeline": {
    "timestamp": "2026-04-24T10:00:00Z",
    "success": true,
    "aborted_stage": null,
    "stages": [
      { "name": "infra-sync", "status": "warn", ... }
    ]
  }
}
```
No way to determine whether `stages` reflects a full run or a filtered `--stage infra-sync` run. An agent sees `infra-sync: warn` and investigates drift that does not exist.

### After (fixed) — full run

```json
{
  "pipeline": {
    "timestamp": "2026-04-26T09:00:00Z",
    "as_of": "2026-04-26T09:00:00Z",
    "stale": false,
    "success": true,
    "aborted_stage": null,
    "stages": [...]
  }
}
```

### After (fixed) — previous run was `--stage infra-sync`

```json
{
  "pipeline": {
    "timestamp": "2026-04-24T10:00:00Z",
    "as_of": "2026-04-24T10:00:00Z",
    "stale": true,
    "success": true,
    "aborted_stage": null,
    "stages": [
      { "name": "infra-sync", "status": "warn", ... },
      { "name": "lint", "status": "skip", "skipped_reason": "filtered via --stage", ... }
    ]
  }
}
```

`stale: true` signals to any consumer that `stages` is not a full pipeline snapshot.

### Source Changed

`src/dev_stack/pipeline/runner.py` — `_record_pipeline_run()` method
