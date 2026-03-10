# Research: Greenfield Init Fixes

**Feature**: 008-greenfield-init-fixes
**Date**: 2026-03-10

## Root Cause Analysis

### Issue 1 & 2: Tests directory not created, dev dependencies not added

**Root Cause**: The `uv_project.install()` brownfield guard at [uv_project.py](../../src/dev_stack/modules/uv_project.py) line ~269 returns early when `pyproject.toml` exists and `force=False`, skipping Steps 2–5 (augment pyproject, scaffold tests, uv lock, gitignore).

**Causal Chain**:
1. User runs `uv init --package` in the target repo → creates `pyproject.toml` (vanilla uv_build output)
2. User runs `dev-stack --json init`
3. `init_cmd.py` calls `is_greenfield_uv_package(pyproject.toml)` → returns `True` (correct detection)
4. All `uv_project`-related conflicts are marked `"greenfield_predecessor"` (correct — not real conflicts)
5. `has_existing_conflicts()` returns `False` because no conflicts have `"pending"` resolution
6. `effective_force = force or existing_conflicts` → `effective_force = False`
7. `_install_modules()` calls `uv_project.install(force=False)`
8. Inside `install()`: `brownfield = pyproject.exists()` → `True` (because `uv init` already created it)
9. `brownfield and not force` → `True` → **returns immediately without creating tests or adding deps**

**Decision**: Add a `greenfield_predecessor` parameter to the module install flow. When `init_cmd.py` detects a greenfield uv package, it should pass this context through to `uv_project.install()` so the module knows to skip `uv init` (Step 1) but still execute Steps 2–5 (augment, scaffold, lock, gitignore).

**Rationale**: This is the minimal-invasive fix. The brownfield guard exists for a good reason (protecting existing non-uv pyproject.toml files). The problem is that `init_cmd.py` has the knowledge that this is a greenfield predecessor but doesn't communicate it to the module.

**Alternatives Considered**:
- **Always pass `force=True` when greenfield detected**: Rejected — `force` has broader semantics across all modules; overloading it risks unintended overwrites in other modules
- **Remove brownfield guard entirely**: Rejected — would break brownfield repos where pyproject.toml has custom content
- **Check `is_greenfield_uv_package` inside `uv_project.install()`**: Viable alternative, but duplicates detection logic already in `init_cmd.py`

### Issue 3: Pipeline is hollow on first commit

**Root Cause (Primary)**: Issues 1 & 2 cascade — since optional-dependencies aren't added, `uv sync` in `init_cmd.py` line ~151 doesn't install dev tools. Even though `init_cmd.py` already calls `subprocess.run(["uv", "sync", "--all-extras"], ...)`, the extras don't exist in pyproject.toml, so nothing gets installed.

**Root Cause (Secondary)**: `_tool_available_in_venv()` in `stages.py` checks `.venv/bin/{tool}` and returns `False` when tools aren't installed, causing stages to skip with bare messages like `"ruff not installed in project venv"` — no remediation guidance.

**Root Cause (Tertiary)**: The pipeline runner doesn't distinguish between "all stages passed" and "all core stages skipped". Both produce `success=True`.

**Decision (Primary fix)**: Fix Issues 1 & 2 first — once deps are in pyproject.toml, the existing `uv sync --all-extras` in `init_cmd.py` handles the auto-install.

**Decision (Skip messages)**: Enhance skip reason strings to include remediation commands. Pattern: `"{tool} not installed in project venv — run 'uv sync --extra dev' to install"`.

**Decision (Hollow warning)**: After the pipeline loop in `runner.py`, if all core stages (lint, typecheck, test) have `StageStatus.SKIP`, emit a warning via the `PipelineRunResult` and surface it in `pipeline_cmd.py`'s output formatting.

**Rationale**: The primary fix (unblocking deps) eliminates the hollow pipeline for normal flows. The skip messages and warning banner serve as safety nets for edge cases (e.g., network failure during `uv sync`).

**Alternatives Considered**:
- **Run `uv sync` inside `uv_project.install()` instead of `init_cmd.py`**: Considered but rejected — `init_cmd.py` already has a `uv sync --all-extras` call at line ~151. Moving it creates duplication. The right fix is ensuring deps exist before that call runs.
- **Add a new `--install-tools` pipeline flag**: Rejected — overcomplicates the UX. The pipeline should work without flags after init.

### Issue 4: DEV_STACK_AGENT=none scoping

**Root Cause**: The pre-commit hook (shell script) calls `dev-stack pipeline run`. The pipeline CLI creates an `AgentBridge(repo_root)` which calls `detect_agent()` from `config.py`. `detect_agent()` checks `DEV_STACK_AGENT` env var first, but if it's not exported, it's not inherited by the hook subprocess. It then falls back to scanning for agent binaries (`claude`, `gh copilot`, `cursor`) — and auto-detects whatever is available.

The manifest is NOT read during pipeline execution. `AgentBridge.__init__()` accepts an optional `manifest` parameter but `pipeline_cmd.py` never provides one:

```python
# pipeline_cmd.py line 30
agent_bridge = AgentBridge(repo_root)  # no manifest passed
```

Meanwhile `detect_agent()` in `config.py` has manifest-based detection as priority #2 (after env var), but the manifest is never loaded by the pipeline path.

**Decision**: In `pipeline_cmd.py`, read `dev-stack.toml` and pass the manifest to `AgentBridge`. This enables `detect_agent(manifest)` to use the manifest's agent config as fallback when `DEV_STACK_AGENT` env var is absent.

**Rationale**: The infrastructure already exists — `detect_agent()` supports manifest-based detection, and `AgentBridge` accepts a manifest parameter. The only missing link is loading the manifest in the pipeline CLI command.

**Alternatives Considered**:
- **Write agent config to `.env` file during init**: Rejected — introduces file management complexity and a new convention
- **Have the pre-commit hook script export the variable from dev-stack.toml**: Rejected — requires TOML parsing in bash, fragile
- **Document `export` requirement in README only**: Rejected per clarification — user chose manifest fallback

## Technology Best Practices

### uv sync with optional extras

`uv sync --extra dev --extra docs` installs the declared optional dependency groups into the project's `.venv`. This is idempotent — safe to call multiple times. The existing `uv sync --all-extras` in `init_cmd.py` already handles this correctly once the extras exist in pyproject.toml.

### TOML read-modify-write with tomli_w

`_augment_pyproject()` already uses `tomllib.load()` → modify dict → `tomli_w.dump()`. This preserves TOML structure except for comment stripping (acceptable for machine-managed sections). The skip-if-exists guards (`if "dev" not in opt_deps`) ensure idempotency.

### Pipeline result composition

The `PipelineRunResult` dataclass currently has `results`, `success`, `aborted_stage`, `skip_flag_detected`, `parallelized`. Adding a `warnings` field follows the existing pattern and doesn't break serialization (new field with default).

### Manifest reading in the pipeline path

`read_manifest()` from `manifest.py` handles missing files gracefully (raises `ManifestError`). The pipeline should catch this and proceed without manifest — maintaining backward compatibility with repos that haven't run init yet.
