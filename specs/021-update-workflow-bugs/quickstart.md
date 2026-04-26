# Quickstart: Dev-Stack Update Workflow Bug Fixes

**Feature**: 021-update-workflow-bugs  
**Branch**: `021-update-workflow-bugs`

---

## What this fixes

Four bugs encountered when updating dev-stack in a live project:

1. **`packaging` undeclared** — crash on first run after fresh install
2. **Module VERSION constants stale** — `dev-stack update` reports no updates needed when modules are outdated
3. **"Missing tools" advisory on filtered runs** — false warning when using `--stage`
4. **Stale pipeline data in status** — `dev-stack --json status` shows old run data as if it's live health

---

## Files changed

| File | Bug(s) | Change |
|---|---|---|
| `pyproject.toml` | 1 | Add `packaging>=24.0` to `[project].dependencies` |
| `src/dev_stack/modules/__init__.py` | 2 | Add `_package_version()` helper; update `latest_module_entries()` |
| `src/dev_stack/modules/base.py` | 2 | Add `version` property that calls `_package_version()` |
| `src/dev_stack/modules/apm.py` | 2 | Remove `VERSION = "0.1.0"` |
| `src/dev_stack/modules/ci_workflows.py` | 2 | Remove `VERSION = "0.1.0"` |
| `src/dev_stack/modules/docker.py` | 2 | Remove `VERSION = "0.1.2"` |
| `src/dev_stack/modules/hooks.py` | 2 | Remove `VERSION = "0.1.0"` |
| `src/dev_stack/modules/sphinx_docs.py` | 2 | Remove `VERSION = "0.1.0"` |
| `src/dev_stack/modules/uv_project.py` | 2 | Remove `VERSION = "0.1.0"` |
| `src/dev_stack/modules/visualization.py` | 2 | Remove `VERSION = "1.0.0"` |
| `src/dev_stack/pipeline/runner.py` | 3, 4 | Fix hollow-pipeline guard; add `as_of`/`stale` to `_record_pipeline_run()` |

---

## Implementation order

### Step 1 — Declare `packaging` dependency (Bug 1)

In `pyproject.toml`, add to `[project].dependencies`:

```toml
"packaging>=24.0",
```

**Verify**: `pip install .` in a clean venv, then `dev-stack --help` — must not raise `ModuleNotFoundError`.

---

### Step 2 — Single-source module version (Bug 2)

**2a.** Add helper to `src/dev_stack/modules/__init__.py`:

```python
def _package_version() -> str:
    try:
        from importlib.metadata import version
        return version("dev-stack")
    except Exception:
        return DEFAULT_MODULE_VERSION
```

**2b.** Update `latest_module_entries()` in the same file — replace `getattr(module_cls, "VERSION", DEFAULT_MODULE_VERSION)` with `_package_version()`.

**2c.** Add `version` property to `ModuleBase` in `src/dev_stack/modules/base.py`:

```python
@property
def version(self) -> str:
    from dev_stack.modules import _package_version
    return _package_version()
```

**2d.** Remove `VERSION = "..."` class attributes from all module files: `apm.py`, `ci_workflows.py`, `docker.py`, `hooks.py`, `sphinx_docs.py`, `uv_project.py`, `visualization.py`.

Update any `self.VERSION` references in `verify()` methods in those files to `self.version` (property).

**Verify**:

```python
from dev_stack.modules import latest_module_entries
entries = latest_module_entries()
assert all(e.version == "1.0.0" for e in entries.values())
```

---

### Step 3 — Fix hollow-pipeline advisory (Bug 3)

In `src/dev_stack/pipeline/runner.py`, replace the hollow-pipeline guard:

```python
# Before
if core_results and all(r.status == StageStatus.SKIP for r in core_results):
    warnings.append(...)

# After
if core_results and all(r.status == StageStatus.SKIP for r in core_results):
    tool_missing = any(
        r.skipped_reason != "filtered via --stage" for r in core_results
    )
    if tool_missing:
        warnings.append(...)
```

**Verify**: Run `dev-stack pipeline --stage docs-api` in a project with all tools installed. No `uv sync` advisory must appear.

---

### Step 4 — Add `as_of` and `stale` to pipeline run record (Bug 4)

In `src/dev_stack/pipeline/runner.py`, in `_record_pipeline_run()`, add two fields to the payload:

```python
now_str = datetime.now(timezone.utc).strftime(ISO_FORMAT)
stale = (
    summary.aborted_stage is not None
    or any(r.skipped_reason == "filtered via --stage" for r in summary.results)
)
payload = {
    "timestamp": now_str,
    "as_of": now_str,
    "stale": stale,
    ...
}
```

**Verify**:

```python
# After a --stage run
state = json.loads(Path(".dev-stack/pipeline/last-run.json").read_text())
assert state["stale"] is True
assert "as_of" in state

# After a full run
state = json.loads(Path(".dev-stack/pipeline/last-run.json").read_text())
assert state["stale"] is False
```

---

## Testing checklist

- [ ] Bug 1: `pip install` wheel into clean venv → `dev-stack --help` succeeds
- [ ] Bug 2: Project at `0.1.x` modules + new wheel → `dev-stack update` reports modules to update
- [ ] Bug 2: After update → `dev-stack update` reports "No modules require updates"
- [ ] Bug 3: `dev-stack pipeline --stage docs-api` (tools installed) → no `uv sync` advisory
- [ ] Bug 3: `dev-stack pipeline` with ruff absent → `uv sync` advisory appears
- [ ] Bug 4: After `--stage` run → `status.pipeline.stale == true`, `as_of` present
- [ ] Bug 4: After full run → `status.pipeline.stale == false`, `as_of` present
- [ ] Regression: Existing unit tests pass (`uv run pytest`)
