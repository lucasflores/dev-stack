# Function Contracts: Init & Pipeline Bugfixes

**Branch**: `006-init-pipeline-bugfixes` | **Date**: 2026-03-10

These contracts define the input/output signatures for new and modified functions. They serve as the implementation blueprint for task generation.

---

## Contract 1: `is_greenfield_uv_package` (FR-004)

**File**: `src/dev_stack/brownfield/conflict.py` (or `src/dev_stack/cli/_shared.py`)

```python
def is_greenfield_uv_package(pyproject_path: Path) -> bool:
    """
    Return True if pyproject.toml matches untouched `uv init --package` output.

    Signals checked (all must be True):
    1. build-system.build-backend == "uv_build"
    2. project.description == "Add your description here"
    3. No [tool.*] sections in the TOML

    Args:
        pyproject_path: Absolute path to pyproject.toml

    Returns:
        True if all three signals match (greenfield predecessor)
        False if file doesn't exist, can't be parsed, or any signal fails
    """
```

**Error handling**: Returns `False` on `FileNotFoundError`, `tomllib.TOMLDecodeError`, or `KeyError`. Never raises.

---

## Contract 2: `_tool_available_in_venv` (FR-001, FR-008)

**File**: `src/dev_stack/pipeline/stages.py`

```python
def _tool_available_in_venv(tool: str, repo_root: Path) -> bool:
    """
    Check if a CLI tool is available inside the project's .venv/bin.

    Args:
        tool: Name of the executable (e.g., "mypy", "ruff", "pytest")
        repo_root: Project root directory containing .venv/

    Returns:
        True if the tool exists in .venv/bin/
        False if .venv/bin/ doesn't exist or tool not found
    """
```

**Implementation note**: Uses `shutil.which(tool, path=str(repo_root / ".venv" / "bin"))`. Does NOT fall back to system PATH.

---

## Contract 3: `has_unaudited_secrets` (FR-012)

**File**: `src/dev_stack/pipeline/stages.py`

```python
def has_unaudited_secrets(baseline_path: Path) -> bool:
    """
    Return True if the baseline contains secrets that need attention.

    A secret "needs attention" if:
    - It has no "is_secret" key (unaudited — newly discovered)
    - It has "is_secret": True (confirmed real secret)

    Args:
        baseline_path: Path to .secrets.baseline JSON file

    Returns:
        True if any finding is unaudited or confirmed-real
        False if all findings are audited as false positives
    """
```

**Error handling**: Raises `FileNotFoundError` if baseline doesn't exist (caller must handle). Raises `json.JSONDecodeError` if baseline is malformed.

---

## Contract 4: Modified `_execute_typecheck_stage` (FR-001)

**File**: `src/dev_stack/pipeline/stages.py`

```python
def _execute_typecheck_stage(ctx: StageContext) -> StageResult:
    """
    Execute the typecheck stage using mypy.

    CHANGED BEHAVIOR (FR-001):
    - OLD: shutil.which("mypy") — checks system PATH
    - NEW: _tool_available_in_venv("mypy", ctx.repo_root) — checks .venv only

    When mypy is not in the venv:
    - Returns StageResult(status=SKIP, skipped_reason="mypy not installed in project venv")

    When mypy is in the venv:
    - Runs via _run_command() which already uses venv env
    """
```

---

## Contract 5: Modified `_execute_security_stage` (FR-012)

**File**: `src/dev_stack/pipeline/stages.py`

```python
def _execute_security_stage(ctx: StageContext) -> StageResult:
    """
    Execute the security stage using detect-secrets.

    CHANGED BEHAVIOR (FR-012):
    - OLD: Run `detect-secrets scan`, check exit code (always 0 → always PASS)
    - NEW: Run `detect-secrets scan --baseline .secrets.baseline`, then check
      baseline for unaudited/confirmed-real secrets

    Workflow:
    1. Check if .secrets.baseline exists; if not, generate initial baseline
    2. Run `detect-secrets scan --baseline .secrets.baseline` (updates in-place)
    3. Call has_unaudited_secrets() on the updated baseline
    4. FAIL if unaudited/real secrets found, PASS otherwise
    """
```

---

## Contract 6: Modified `PipelineRunner.run` → success calculation (FR-006)

**File**: `src/dev_stack/pipeline/runner.py`

```python
# BEFORE (line ~108):
success = aborted_stage is None or force

# AFTER:
has_hard_failures = any(
    r.status == StageStatus.FAIL and r.failure_mode == FailureMode.HARD
    for r in results
)
success = not has_hard_failures
```

**Note**: `force` no longer affects `success`. It only affects whether the runner continues past hard failures (already handled in the run loop).

---

## Contract 7: Modified `_serialize_run` → three-state status (FR-006)

**File**: `src/dev_stack/cli/pipeline_cmd.py`

```python
def _serialize_run(result: PipelineRunResult, force: bool) -> dict:
    """
    CHANGED BEHAVIOR:
    - OLD: "success" | "failed"
    - NEW: "success" | "completed_with_failures" | "failed"

    Logic:
        if result.success → "success"
        elif force → "completed_with_failures"
        else → "failed"
    """
```

**Exit code**: `raise SystemExit(ExitCode.PIPELINE_FAILURE)` for both `"failed"` and `"completed_with_failures"`.

---

## Contract 8: Modified `init_command` → uv sync + dry-run + rollback (FR-002, FR-003, FR-007, FR-013)

**File**: `src/dev_stack/cli/init_cmd.py`

```python
def init_command(ctx: CLIContext, modules_csv: str | None, force: bool) -> None:
    """
    CHANGED BEHAVIOR:

    FR-002/FR-003: After module installation, run:
        subprocess.run(["uv", "sync", "--all-extras"], cwd=repo_root, check=True)
    This creates .venv and installs all optional-dependencies groups.

    FR-004: Before _determine_mode(), check pyproject.toml fingerprint:
        if is_greenfield_uv_package(repo_root / "pyproject.toml"):
            # Mark matching conflicts as "greenfield_predecessor"

    FR-007: When already_initialized and not force:
        if ctx.dry_run:
            # Delegate to update-preview instead of erroring
            # Reuses the same output structure as _emit_dry_run_summary():
            # {"status": "ok", "dry_run": true, "changes": [{"path": ..., "action": "add"|"modify"|"conflict"}]}
            _emit_update_preview(ctx, repo_root, manifest, module_instances)
            return
        # else: existing error behavior

    FR-013: Create rollback tag in greenfield flow too:
        # Remove the should_create_rollback guard that skips greenfield
        # If no commits exist, create initial commit before tagging
    """
```

---

## Contract 9: CLI `--version` flag (FR-009)

**File**: `src/dev_stack/cli/main.py`

```python
@click.group()
@click.version_option(
    version=_get_version(),
    prog_name="dev-stack",
    message="%(prog)s %(version)s",
)
# ... existing options ...
def cli(ctx, json_output, verbose, dry_run):
    """Dev Stack automation CLI."""
```

Helper:
```python
def _get_version() -> str:
    from importlib.metadata import version, PackageNotFoundError
    try:
        return version("dev-stack")
    except PackageNotFoundError:
        return getattr(__import__("dev_stack"), "__version__", "0.0.0-dev")
```

---

## Contract 10: Update command help text (FR-010)

**File**: `src/dev_stack/cli/update_cmd.py`

```python
# BEFORE:
@cli.command("update")

# AFTER:
@cli.command("update", help="Update dev-stack configuration and module files in an existing repository.")
```

---

## Contract 11: README flag position fixes (FR-011)

**File**: `README.md`

Pattern: Move global flags (`--json`, `--dry-run`, `--verbose`) before the subcommand.

```diff
- dev-stack status --json
+ dev-stack --json status

- dev-stack init --dry-run
+ dev-stack --dry-run init

- dev-stack pipeline run --json
+ dev-stack --json pipeline run
```
