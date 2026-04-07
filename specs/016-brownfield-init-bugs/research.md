# Research: Brownfield Init Bug Remediation

**Feature**: 016-brownfield-init-bugs | **Date**: 2026-04-07

## R1 — Commit-Message Hook Comment Stripping (FR-001)

**Decision**: Replace `ln.startswith("#")` with `re.match(r"^# |^#$", ln)` to only strip git comment lines.

**Rationale**: Git uses `# ` (hash-space) or bare `#` (end-of-line) as comment indicators. Markdown headers use `##` (double-hash) or deeper. The current regex strips all lines starting with `#`, which is over-broad and destroys UC5's required `## Intent` / `## Reasoning` / `## Scope` / `## Narrative` headers. The narrower regex preserves markdown headers while still stripping git comments.

**Alternatives considered**:
- Reading `core.commentChar` from git config — rejected as out of scope (assumption: default `#` only).
- Stripping only lines matching `# --- >8 ---` scissors — too narrow, misses normal git comments.

**Implementation site**: `src/dev_stack/vcs/hooks_runner.py` line 37 — single-line change.

---

## R2 — Greenfield Classification Logic (FR-002)

**Decision**: Add a root-level scan for `.py` files and directories with `__init__.py` to `is_greenfield_uv_package()` in `conflict.py`. If any are found at depth 1 (excluding `.git`, `__pycache__`, `.venv`, `node_modules`, `.tox`), return `False` (brownfield) regardless of `pyproject.toml` signals.

**Rationale**: The current check only examines `pyproject.toml` structure (uv_build backend, default description, no `[tool]` sections). A repo that was `uv init --package`'d but then had code added to it at the root level passes all three checks and is misclassified. Scanning the root is fast (single `os.listdir` + stat calls) and catches the common brownfield case without deep traversal.

**Alternatives considered**:
- Recursive scan — rejected (false positives from `.venv`, vendored code, build artifacts).
- Checking git log for prior commits — rejected (doesn't work if commits predate dev-stack).

**Implementation site**: `src/dev_stack/brownfield/conflict.py` function `is_greenfield_uv_package()` — add scan before the `return True` at end.

---

## R3 — APM Version Parse ANSI Stripping (FR-003)

**Decision**: Add an ANSI-stripping step before version extraction. Use a regex `re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)` to remove escape sequences, then use `re.search(r'\d+\.\d+\.\d+', stripped)` to extract the semver string instead of relying on `split()[-1]`.

**Rationale**: The current code does `result.stdout.strip().split()[-1]` which works for clean output like `apm 0.8.2` but fails for Rich-decorated output like `╭─ apm v0.8.2 ─╮` or ANSI-wrapped `\x1b[1m0.8.2\x1b[0m`. Stripping ANSI first and then searching for a semver pattern is robust against all decoration styles.

**Alternatives considered**:
- Using `--plain` flag on APM CLI — rejected (not all versions support it, would break if flag doesn't exist).
- Parsing only stderr — rejected (version output is on stdout).

**Implementation site**: `src/dev_stack/modules/apm.py` method `_check_apm_cli()` — version parsing logic within the `try` block (line ~192).

---

## R4 — requirements.txt Migration with Confirmation (FR-004)

**Decision**: Add a new helper function `_detect_and_migrate_requirements()` in the init pipeline. Parse `requirements.txt` using line-by-line processing (not `pip-compile`), display a preview table, prompt for confirmation (interactive), or warn and skip (CI).

**Rationale**: No existing requirements.txt parsing exists in the codebase. The `packaging.requirements` library (already a transitive dependency via `packaging`) can parse PEP-508 requirement specifiers. A line-by-line parser that skips comments (`#`), blank lines, `-e` editable installs, and URL-based deps covers the standard case.

**Alternatives considered**:
- Using `pip-compile` to canonicalize — rejected (adds heavy dependency, slower, overkill for a migration warning).
- Using `uv pip compile` — rejected (requires uv to be installed, which may not be the case during init).

**Implementation site**: New function in `src/dev_stack/cli/init_cmd.py`, called after greenfield/brownfield classification. Merges into `[project.dependencies]` in pyproject.toml via `tomli_w`.

---

## R5 — Root-Level Package Detection (FR-005)

**Decision**: Add a scan in the init pipeline (alongside the greenfield check) that finds directories at the repo root containing `__init__.py`. Report them via Rich console output with `src/` migration guidance.

**Rationale**: The current `uv_project` module only looks in `src/` for packages — never at the root. The scan reuses the same depth-1 traversal from R2 but reports results differently: R2 uses presence of `.py` files to flip the greenfield flag, R5 uses the detected package names to emit user guidance.

**Alternatives considered**:
- Automatically moving packages to `src/` — rejected (destructive, breaks imports, should be user's choice).
- Adding to `uv_project.install()` — rejected (better in init_cmd.py where user output is controlled).

**Implementation site**: `src/dev_stack/cli/init_cmd.py`, after module installation, before final summary output.

---

## R6 — First-Commit Auto-Format (FR-007)

**Decision**: Add a "brownfield first-commit" detection using the existing `.dev-stack/` marker directory pattern. When the init pipeline creates the initial commit, write a marker `.dev-stack/brownfield-init`. In the lint stage, if this marker exists, run `ruff format .` (without `--check`) first, then delete the marker and proceed with the normal check. This ensures exactly one auto-format pass.

**Rationale**: No existing "first commit" marker exists for brownfield. The git-based `_has_commits()` check only knows if there are ANY commits, not whether the first dev-stack commit has been made. A file marker is the simplest stateful mechanism and follows the established `.dev-stack/` directory pattern (see `pipeline-skipped`, `update-in-progress`, etc.).

**Alternatives considered**:
- Checking git log for "chore: initial commit for dev-stack init" message — rejected (fragile, message could change).
- Environment variable set during init — rejected (doesn't persist across shell sessions).
- Always auto-format on first commit regardless of greenfield/brownfield — rejected (greenfield code from `uv init` is already formatted).

**Implementation site**: 
- Marker write: `src/dev_stack/cli/init_cmd.py` at end of brownfield init path.
- Marker read + auto-format: `src/dev_stack/pipeline/stages.py` in `_execute_lint_stage()` before the `--check` invocations.
- README update: `README.md` section on first-commit behavior.

---

## R7 — --json Pipeline Output (FR-006)

**Decision**: Audit all CLI commands for JSON output gaps. The research identified the pipeline is ~95% JSON-covered. The primary gap is in `visualize_cmd.py` early-exit paths (lines 60-92) where pre-flight validation only emits human-readable text. Fix by adding JSON payloads to those paths.

**Rationale**: The `CLIContext.json_output` flag is already threaded through all commands. Most commands have complete JSON/human branching. The fix is surgical — add missing JSON branches to identified gap locations.

**Alternatives considered**:
- Middleware/decorator that wraps all commands in JSON — rejected (too invasive, each command has different payload shapes).
- Structured logging to stderr with JSON to stdout — rejected (breaks current architecture).

**Implementation site**: `src/dev_stack/cli/visualize_cmd.py` lines 60-92 (primary gap). Spot-check all other commands.

---

## R8 — mypy Warn-Only for Non-src Packages (FR-008)

**Decision**: In the mypy pipeline stage, before invoking `mypy src/`, scan for root-level packages outside `src/`. If found, emit a warning listing the uncovered packages with `src/` migration guidance. Keep `mypy_path = "src"` unchanged.

**Rationale**: Auto-including arbitrary root directories risks noisy false positives from untyped legacy code. The warn-only approach is consistent with the `src/` migration guidance from FR-005 and doesn't alter the type-checking contract.

**Alternatives considered**:
- Auto-include dirs with `ignore_errors = true` — rejected (complex config, unclear benefit).
- Run mypy twice (for `src/` and root packages separately) — rejected (slower, confusing output).

**Implementation site**: `src/dev_stack/pipeline/stages.py` in `run_mypy_type_checking()` before the `mypy src/` invocation.
