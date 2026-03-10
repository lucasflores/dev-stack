# Internal API Contracts: Greenfield Init Fixes

**Feature**: 008-greenfield-init-fixes
**Date**: 2026-03-10

## Contract 1: uv_project.install() — Greenfield Predecessor Behavior

### Current Behavior (broken)

```python
def install(self, *, force: bool = False) -> ModuleResult:
    # ...
    pyproject = self.repo_root / "pyproject.toml"
    brownfield = pyproject.exists()
    if brownfield and not force:
        return ModuleResult(success=False, message="pyproject.toml already exists...")
    # Steps 2-5 never reached when pyproject exists and force=False
```

### Required Behavior

When `force=True` and `pyproject.toml` already exists:
- MUST skip `uv init` (Step 1) — pyproject already exists
- MUST execute `_augment_pyproject()` (Step 2) — add tool configs and optional-dependencies
- MUST execute `_scaffold_tests()` (Step 3) — create tests directory and files
- MUST execute `_run_uv_lock()` (Step 4) — update lockfile with new deps
- MUST execute `_ensure_standard_gitignore()` (Step 5) — add Python ignores
- MUST preserve existing content in pyproject.toml, tests/, and .gitignore

### Post-condition

```python
# After install(force=True) on a greenfield predecessor repo:
ModuleResult(
    success=True,
    message="UV project initialized: {pkg_name}",
    files_created=[...],  # includes tests/__init__.py, tests/test_placeholder.py
    warnings=[...]        # includes any augmented TOML sections
)
```

---

## Contract 2: init_cmd.py — Greenfield Force Propagation

### Current Behavior (broken)

```python
effective_force = force or existing_conflicts  # False for greenfield predecessor
_install_modules(module_instances, force=effective_force)  # force=False
```

### Required Behavior

```python
is_greenfield = is_greenfield_uv_package(repo_root / "pyproject.toml")
effective_force = force or existing_conflicts or is_greenfield
_install_modules(module_instances, force=effective_force)  # force=True for greenfield
```

### Invariant

`effective_force` MUST be `True` when `is_greenfield_uv_package()` returns `True`, regardless of the `--force` flag or conflict status.

---

## Contract 3: Pipeline Skip Messages — Remediation Format

### Current Format

```
"ruff not installed in project venv"
"mypy not installed in project venv"
"pytest not installed in project venv"
"sphinx not found, skipping API docs"
```

### Required Format

```
"ruff not installed in project venv — run 'uv sync --extra dev --extra docs' to install"
"mypy not installed in project venv — run 'uv sync --extra dev --extra docs' to install"
"pytest not installed in project venv — run 'uv sync --extra dev --extra docs' to install"
"sphinx not found — run 'uv sync --extra dev --extra docs' to install"
```

### Schema

`skipped_reason: str` — format: `"{tool} {status} — run '{command}' to install"`

---

## Contract 4: PipelineRunResult — Hollow Pipeline Warning

### Current Behavior

```python
@dataclass(slots=True)
class PipelineRunResult:
    results: list[StageResult]
    success: bool
    aborted_stage: str | None = None
    skip_flag_detected: bool = False
    parallelized: bool = False
```

### Required Behavior

```python
@dataclass(slots=True)
class PipelineRunResult:
    results: list[StageResult]
    success: bool
    aborted_stage: str | None = None
    skip_flag_detected: bool = False
    parallelized: bool = False
    warnings: list[str] = field(default_factory=list)  # NEW
```

### Warning Generation Rule

After the stage loop completes, if **all** of the core stages (`lint`, `typecheck`, `test`) have `status == StageStatus.SKIP`:

```python
warnings.append(
    "⚠ No substantive validation: lint, typecheck, test all skipped "
    "due to missing tools. Run 'uv sync --extra dev' to install."
)
```

### Serialization Contract

The `_serialize_run()` function in `pipeline_cmd.py` MUST include `"warnings"` in the output payload:

```json
{
  "status": "success",
  "warnings": ["⚠ No substantive validation: ..."],
  "stages": [...]
}
```

---

## Contract 5: Pipeline Agent Detection — Manifest Fallback

### Current Behavior (broken)

```python
# pipeline_cmd.py
agent_bridge = AgentBridge(repo_root)  # no manifest → detect_agent(None)
```

### Required Behavior

```python
# pipeline_cmd.py
manifest = _try_load_manifest(repo_root)  # read dev-stack.toml if exists
agent_bridge = AgentBridge(repo_root, manifest=manifest)
```

### Detection Priority (unchanged, just wired correctly)

1. `DEV_STACK_AGENT` env var (highest priority)
2. `manifest.agent.cli` from `dev-stack.toml` (fallback)
3. Local binary scan: `claude` → `gh copilot` → `cursor`
4. `AgentInfo(cli="none", path=None)` (no agent)

### Error Handling

If `dev-stack.toml` does not exist or is malformed, `_try_load_manifest()` MUST return `None` (not raise). The pipeline MUST still work in repos that haven't run `dev-stack init`.
