# Research: Init Pipeline Bugfixes (006)

_Generated 2026-03-10 — concrete implementation patterns for 5 technical topics_

---

## Topic 1: Venv-aware Tool Detection in Python

### Decision

Use `shutil.which(tool, path=venv_bin_path)` with an explicit `path` argument pointing to `.venv/bin`, **not** the system `PATH`. This is already partially implemented in `_build_venv_env` + `_run_command` in [stages.py](../src/dev_stack/pipeline/stages.py), but the `_execute_typecheck_stage` function bypasses it by calling bare `shutil.which("mypy")` without restricting the search path.

**Concrete fix pattern:**

```python
def _tool_available_in_venv(tool: str, repo_root: Path) -> bool:
    """Check if *tool* is available inside the project's .venv."""
    venv_bin = repo_root / ".venv" / "bin"
    if not venv_bin.is_dir():
        return False
    return shutil.which(tool, path=str(venv_bin)) is not None
```

For stages that invoke tools via `python -m <module>`, verify with:

```python
def _module_available_in_venv(module: str, repo_root: Path) -> bool:
    """Check if a Python module is importable inside the project's .venv."""
    venv_python = repo_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        return False
    result = subprocess.run(
        [str(venv_python), "-c", f"import {module}"],
        capture_output=True, timeout=10, check=False,
    )
    return result.returncode == 0
```

### Rationale

- `shutil.which(path=...)` is stdlib, zero dependencies, and does exactly what's needed: searches a specific directory instead of `$PATH`.
- The codebase already has `_build_venv_env()` that constructs a modified `PATH` with `.venv/bin` prepended. The `_run_command()` function already uses this env for execution. The bug is only in the **pre-check** that decides whether to skip a stage — it calls `shutil.which("mypy")` without the venv path constraint.
- Using `importlib.util.find_spec()` from the host process won't work because the host process is the dev-stack CLI, not the project's venv. The `find_spec` approach is only valid when running inside the target environment.

### Alternatives Considered

| Approach | Verdict | Why |
|---|---|---|
| `shutil.which("mypy")` (current) | **Rejected** | Finds system mypy, not venv mypy. False positive. |
| `importlib.util.find_spec("mypy")` | **Rejected** | Checks dev-stack's own environment, not the project venv. |
| `Path(".venv/bin/mypy").exists()` | Acceptable but fragile | Doesn't handle Windows (`Scripts/`) or non-standard venv locations. `shutil.which(path=...)` handles lookup correctly. |
| `subprocess.run([".venv/bin/python", "-m", "mypy", "--version"])` | Acceptable for module check | Heavier — spawns a process just to check availability. Reserve for cases where the tool is only usable as `python -m module`. |
| Check `site-packages` for the package directory | **Rejected** | Some packages install under different names than their import (e.g., `scikit-learn` → `sklearn`). Unreliable. |

---

## Topic 2: `uv init --package` Structural Fingerprint

### Decision

Detect a greenfield `uv init --package` pyproject.toml by checking for this **exact structural signature** — all three conditions must be true:

1. **`[build-system]` uses `uv_build` backend**: `build-backend = "uv_build"`
2. **Description is the sentinel default**: `description = "Add your description here"`
3. **No `[tool.*]` sections exist**: No `[tool.ruff]`, `[tool.pytest]`, `[tool.mypy]`, etc.

**Concrete fingerprint function:**

```python
import tomllib

def is_greenfield_uv_package(pyproject_path: Path) -> bool:
    """Return True if pyproject.toml looks like untouched uv init --package output."""
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    # Signal 1: uv_build backend
    build_system = data.get("build-system", {})
    if build_system.get("build-backend") != "uv_build":
        return False

    # Signal 2: default description sentinel
    project = data.get("project", {})
    if project.get("description") != "Add your description here":
        return False

    # Signal 3: no tool configuration sections
    if "tool" in data:
        return False

    return True
```

### Actual `uv init --package` Output (verified)

```toml
[project]
name = "sample-pkg"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
authors = [
    { name = "lucasflores", email = "lucasmacrorieflores@gmail.com" }
]
requires-python = ">=3.12"
dependencies = []

[project.scripts]
sample-pkg = "sample_pkg:main"

[build-system]
requires = ["uv_build>=0.9.24,<0.10.0"]
build-backend = "uv_build"
```

**Key distinguishing features vs. a mature brownfield project:**

| Field | Greenfield (`uv init --package`) | Brownfield (mature) |
|---|---|---|
| `build-system.build-backend` | `"uv_build"` | `"hatchling"`, `"setuptools.build_meta"`, `"flit_core.buildapi"`, etc. |
| `project.description` | `"Add your description here"` (sentinel) | Actual description |
| `[tool.*]` sections | None | `[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.mypy]`, etc. |
| `project.dependencies` | `[]` (empty list) | Populated |
| `project.optional-dependencies` | Absent | Usually present with `[dev]` group |
| `project.scripts` | Single entry matching package name | May have multiple or different structure |

### Rationale

- The `"Add your description here"` sentinel is the single strongest signal — it is literally impossible in a real project that someone kept this exact string AND has `uv_build` AND has no tool config.
- Using `uv_build` as the build backend is unique to `uv init --package` (as opposed to hatchling/setuptools which are used by other scaffolders and mature projects).
- The absence of `[tool.*]` confirms the user hasn't started configuring linters/formatters yet.

### Alternatives Considered

| Approach | Verdict | Why |
|---|---|---|
| Check only `uv_build` backend | **Insufficient** | User might have switched to `uv_build` in an existing project. |
| Hash the entire file | **Rejected** | Breaks if `uv` changes the author email or `requires-python` version. Too brittle. |
| Check file age / git history | **Rejected** | Unreliable — `uv init` could have been run weeks ago. |
| Check `description == "Add your description here"` alone | Acceptable as shortcut | Works in practice but isn't robust if the user creates a new project with a different scaffolder that uses the same default. Combining with `uv_build` makes it definitive. |

---

## Topic 3: `detect-secrets` Baseline Workflow

### Decision

Use the three-command workflow: `scan` → `audit` → `scan --baseline` for ongoing use. For the dev-stack security stage, run `detect-secrets scan --baseline .secrets.baseline` which **updates the baseline in-place** (merging new findings while preserving prior audit decisions).

### Complete Workflow

#### (a) Generate initial baseline

```bash
detect-secrets scan > .secrets.baseline
```

This produces a JSON file with this structure:
```json
{
  "version": "1.5.0",
  "plugins_used": [ {"name": "AWSKeyDetector"}, ... ],
  "filters_used": [ {"path": "detect_secrets.filters.allowlist.is_line_allowlisted"}, ... ],
  "results": {
    "path/to/file.py": [
      {
        "type": "Secret Keyword",
        "filename": "path/to/file.py",
        "hashed_secret": "25910f981e85ca04baf359199dd0bd4a3ae738b6",
        "is_verified": false,
        "line_number": 42
      }
    ]
  },
  "generated_at": "2026-03-10T19:18:56Z"
}
```

**Key detail**: By default, `detect-secrets scan` only scans **git-tracked files** (files known to `git ls-files`). Use `--all-files` to include untracked files.

#### (b) Audit findings (mark false positives)

```bash
detect-secrets audit .secrets.baseline
```

This opens an **interactive TUI** — for each finding, you press `y` (real secret), `n` (false positive), or `s` (skip). It modifies the baseline in-place, adding `"is_secret": true|false` to each entry. An unaudited finding has **no `is_secret` key**.

```json
{
  "type": "Secret Keyword",
  "hashed_secret": "...",
  "is_verified": false,
  "is_secret": false,        // ← added by audit: false = false positive
  "line_number": 42
}
```

#### (c) Subsequent scans (detect only NEW findings)

```bash
detect-secrets scan --baseline .secrets.baseline
```

This **modifies `.secrets.baseline` in-place**:
- **Preserves** existing entries and their `is_secret` audit decisions
- **Adds** newly detected secrets (without `is_secret` key — they are "unaudited")
- **Removes** entries for files/lines that no longer exist

**Critical behavior verified experimentally**: The command always exits `0` regardless of whether new findings are added. To detect new unaudited findings in CI/pipeline, you must parse the JSON:

```python
import json

def has_unaudited_secrets(baseline_path: Path) -> bool:
    """Return True if baseline contains findings not yet audited."""
    with open(baseline_path) as f:
        baseline = json.load(f)
    for secrets in baseline["results"].values():
        for secret in secrets:
            if "is_secret" not in secret:
                return True  # unaudited finding
            if secret["is_secret"] is True:
                return True  # confirmed real secret
    return False
```

#### For pre-commit hooks (alternative approach)

```bash
detect-secrets-hook --baseline .secrets.baseline <staged-files...>
```

This is the **pre-commit hook entry point**. It:
- Exits `1` if any file contains secrets **not accounted for** in the baseline
- Exits `0` if all secrets are in the baseline (audited or not)
- Only scans the files you pass as arguments (not the whole repo)

### Rationale

- The `--baseline` flag on `detect-secrets scan` is the designed workflow for ongoing secret management — it merges rather than overwrites.
- The `detect-secrets-hook` approach is better for pre-commit because it only checks staged files, not the entire repo.
- The baseline JSON is self-contained: plugins, filters, results, and audit decisions all live in one file.

### Alternatives Considered

| Approach | Verdict | Why |
|---|---|---|
| `detect-secrets scan` without baseline (current code) | **Broken** | Scans whole repo every time, no way to mark false positives, always reports known findings. |
| `detect-secrets-hook --baseline` in pre-commit | **Best for hooks** | Only checks staged files, respects baseline, non-zero exit on new secrets. |
| `detect-secrets scan --baseline` + parse JSON | **Best for pipeline stage** | Full repo scan with differential detection. Needed for the security stage. |
| Run `detect-secrets scan` and diff against stored baseline manually | **Rejected** | Reinventing what `--baseline` already does. |
| `trufflehog` or `gitleaks` instead | **Rejected** for now | Different tool, different workflow. detect-secrets is already a dependency. |

---

## Topic 4: Click `--version` Flag Best Practices

### Decision

Use `@click.version_option()` decorator on the `@click.group()` definition. Let Click auto-detect the version via `importlib.metadata.version("dev-stack")`, with a fallback to `__version__`.

**Concrete implementation:**

```python
from importlib.metadata import version, PackageNotFoundError

def _get_version() -> str:
    try:
        return version("dev-stack")
    except PackageNotFoundError:
        from dev_stack import __version__
        return __version__

@click.group()
@click.version_option(
    version=_get_version(),
    prog_name="dev-stack",
    message="%(prog)s %(version)s",
)
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON output.")
@click.option("--verbose", is_flag=True, help="Enable verbose logging to stderr.")
@click.option("--dry-run", is_flag=True, help="Preview actions without writing changes.")
@click.pass_context
def cli(ctx: click.Context, json_output: bool, verbose: bool, dry_run: bool) -> None:
    """Dev Stack automation CLI."""
    ...
```

**Output**: `dev-stack --version` → `dev-stack 0.1.0`

### Rationale

- `click.version_option()` is Click's built-in mechanism. It adds `--version` as an eager option that prints and exits — standard CLI behavior.
- `importlib.metadata.version()` reads from the installed package metadata (the `PKG-INFO`/`METADATA` file in site-packages). This is the canonical source of truth when the package is installed via `pip install` or `uv pip install`.
- The `__version__` fallback handles development mode where the package might not be installed but imported from source.
- The decorator goes on the **group**, not on individual commands, so `dev-stack --version` works at the top level.

### Alternatives Considered

| Approach | Verdict | Why |
|---|---|---|
| `@click.version_option()` on group (chosen) | **Best** | Standard Click pattern. Auto-handles `--version` flag, eager exit, clean output. |
| Manual `version` subcommand (current) | **Rejected** | `dev-stack version` exists but prints "dev-stack CLI ready" — not the version number. This is non-standard; every CLI tool uses `--version`, not a `version` subcommand. |
| `click.version_option(package_name="dev-stack")` (auto-detect) | Acceptable | Lets Click call `importlib.metadata.version()` internally. But can fail with unhelpful `RuntimeError` if package name doesn't match. Explicit is better. |
| Read `pyproject.toml` at runtime | **Rejected** | Fragile — `pyproject.toml` isn't available in installed packages. `importlib.metadata` is the correct abstraction. |
| Only use `__version__` from `__init__.py` | Acceptable but inferior | Works, but requires manual synchronization between `__init__.py` and `pyproject.toml`. `importlib.metadata` is the single source of truth for installed packages. |

---

## Topic 5: Pipeline Exit Code Semantics with `--force`

### Decision

When `--force` is used and failures occur: **exit non-zero (exit 1)** and report status as `"completed_with_failures"`. The `--force` flag means "run all stages, don't abort early" — it does **not** mean "suppress the failure signal."

**Concrete implementation:**

```python
# In runner.py — success calculation
has_hard_failures = any(
    r.status == StageStatus.FAIL and r.failure_mode == FailureMode.HARD
    for r in results
)
success = not has_hard_failures  # force doesn't change this

# In pipeline_cmd.py — status and exit code
def _serialize_run(result: PipelineRunResult, force: bool) -> dict:
    if result.success:
        status = "success"
    elif force:
        status = "completed_with_failures"  # ran everything, but had failures
    else:
        status = "failed"  # aborted early
    return {
        "status": status,
        "forced": force,
        ...
    }

# Exit code
if not result.success:
    raise SystemExit(ExitCode.PIPELINE_FAILURE)  # always exit 1 on failure
```

**Exit code matrix:**

| Scenario | `--force` | Status JSON | Exit Code |
|---|---|---|---|
| All stages pass | N/A | `"success"` | 0 |
| Hard failure, no `--force` | `False` | `"failed"` | 1 (aborted early) |
| Hard failure, with `--force` | `True` | `"completed_with_failures"` | 1 (ran all, but failures existed) |
| Only soft failures | N/A | `"success"` | 0 (soft failures are warnings) |

### Rationale

**POSIX convention**: Exit code 0 means success. Any non-zero means failure occurred. The process exit code answers the question: "Did everything succeed?" — not "Did the tool do what I asked?"

**Real-world precedents:**

| Tool | Flag | Behavior |
|---|---|---|
| `make -k` (keep going) | `-k` | Runs all targets despite failures. **Exits non-zero** if any target failed. |
| `eslint --force` | `--force` | Different meaning (lint despite warnings). Exits non-zero if errors found. |
| `pytest --continue-on-collection-errors` | `--co` | Collects all tests despite import errors. **Exits non-zero** if errors occurred. |
| `npm test --force` | `--force` | Continues despite failures. **Exits non-zero.** |
| `terraform apply -auto-approve` | N/A | Different semantics but: always exits non-zero on failure regardless of flags. |

**The distinction matters for CI**: A CI pipeline that runs `dev-stack pipeline run --force` needs to know whether failures occurred. If `--force` returned exit 0, the CI would treat a broken build as successful.

**The `--force` contract**: "I want to see ALL the results, even if some fail" — not "pretend everything is fine."

### Alternatives Considered

| Approach | Verdict | Why |
|---|---|---|
| Exit 1 + `"completed_with_failures"` (chosen) | **Best** | Honest exit code. CI works correctly. JSON gives full detail. `--force` meaning is unambiguous. |
| Exit 0 + `"completed_with_failures"` | **Rejected** | Violates POSIX. CI pipelines would silently pass broken builds. Callers must parse JSON to discover failure — defeats the purpose of exit codes. |
| Exit 0 + `"success"` (current behavior) | **Rejected** | Misrepresents the outcome. The pipeline did NOT succeed — it completed, but with failures. |
| Use a distinct exit code (e.g., exit 2 for "completed with failures") | Acceptable | Allows callers to distinguish "aborted" (exit 1) from "ran fully but had failures" (exit 2). However, adds complexity and the JSON status field already communicates this distinction. YAGNI for now. |

---

## Summary of Key Implementation Points

1. **Venv tool detection**: Replace bare `shutil.which("mypy")` with `shutil.which("mypy", path=str(repo_root / ".venv" / "bin"))` in stage pre-checks. The `_run_command` helper already handles venv-aware execution.

2. **Greenfield fingerprint**: Check three signals: `uv_build` backend + `"Add your description here"` sentinel + no `[tool.*]` sections.

3. **Secrets baseline**: Use `detect-secrets scan --baseline .secrets.baseline` (updates in-place, preserves audit decisions). Check for unaudited findings by looking for entries missing the `"is_secret"` key.

4. **CLI version**: Add `@click.version_option(version=_get_version(), prog_name="dev-stack")` to the `cli` group. Use `importlib.metadata.version()` with `__version__` fallback.

5. **Force exit codes**: `--force` + failures → exit 1 + `"completed_with_failures"`. `--force` means "keep running" not "ignore failures."
