# Research: Universal Init Pipeline

**Feature**: 012-universal-init-pipeline  
**Date**: 2026-03-24  
**Status**: Complete — all NEEDS CLARIFICATION resolved

## R1: Stack Profile Detection — How to detect Python presence

**Decision**: Use `next(repo_root.rglob("*.py"), None)` with directory exclusions.

**Rationale**: The spec requires "any `.py` file exists anywhere in the repository" (FR-005, Clarification session). A simple recursive glob is sufficient and aligns with the spec's intentional broadness ("catch scripts, tests, and ad-hoc Python files"). No need to inspect `pyproject.toml` or require specific directory structure.

**Implementation detail**: Exclude `.git/`, `.venv/`, `venv/`, `node_modules/`, `.dev-stack/`, `__pycache__/` directories from the search to avoid false positives from vendored or cached Python files. Use a generator with `next()` for short-circuit evaluation — stop at the first `.py` file found.

**Alternatives considered**:
- Check for `pyproject.toml` only → rejected: misses repos with loose Python scripts
- Walk `os.walk()` manually → rejected: `rglob` with exclusions is simpler and equivalent
- Use `git ls-files '*.py'` → rejected: introduces dependency on git index state; untracked .py files should count

## R2: Conditional Hook Generation — Static template vs programmatic

**Decision**: Generate `.pre-commit-config.yaml` programmatically in `HooksModule.install()`.

**Rationale**: The current approach copies a static YAML template that always includes Python hooks (ruff, pytest, mypy). Making this conditional requires either (a) two templates with selection logic, or (b) programmatic generation. Programmatic generation is more extensible (future language hooks), keeps logic testable in Python, and avoids template proliferation.

**Implementation detail**: 
- Define a base hook list (always included): `dev-stack-pipeline` 
- Define a Python hook list (conditionally included): `dev-stack-ruff`, `dev-stack-pytest`, `dev-stack-mypy`
- `HooksModule.install()` calls `detect_stack_profile()` and assembles the YAML accordingly
- Use `yaml.dump()` or string construction (no PyYAML dependency needed — simple string templates)
- Preserve user-defined hooks outside managed section markers (FR-012)

**Alternatives considered**:
- Two static template files (python vs non-python) → rejected: doesn't scale, harder to maintain
- Jinja2 templates → rejected: adds dependency, overkill for conditional block inclusion
- pre-commit framework's own config merging → rejected: dev-stack manages its own hooks section

## R3: Body Section Validation — gitlint custom rule approach

**Decision**: New gitlint `CommitRule` subclass in `src/dev_stack/rules/body_sections.py` with rule ID `UC5`.

**Rationale**: The existing commit-msg hook already uses gitlint with custom rules (UC1-UC4) loaded from `dev_stack.rules` package. Adding UC5 follows the established pattern perfectly. The rule checks for `## Intent`, `## Reasoning`, `## Scope`, `## Narrative` headings in the commit body, but only when `Agent:` trailer is present.

**Implementation detail**:
- Rule triggers only on agent commits (presence of `Agent:` trailer in body lines)
- Scans body for markdown headings: `## Intent`, `## Reasoning`, `## Scope`, `## Narrative`
- Missing sections → `RuleViolation` with severity ERROR, listing which sections are absent
- Human commits (no `Agent:` trailer) → rule returns empty list (no enforcement)
- Headings are case-sensitive to match the dev-stack convention exactly

**Alternatives considered**:
- Shell script validation in the hook → rejected: gitlint integration is already the pattern, shell scripts are harder to test
- Regex-based validation in hooks_runner.py → rejected: gitlint rules are composable and testable
- Make body sections warnings instead of errors → rejected: spec says "rejected" (User Story 3, Acceptance Scenario 1)

## R4: Gitignore Managed Section — Marker approach

**Decision**: Use existing `markers.write_managed_section()` from `brownfield.markers` module with section ID `GITIGNORE`.

**Rationale**: The codebase already has a mature managed section system used by vcs_hooks module. Using the same mechanism for `.gitignore` is consistent (Constitution Principle IV: Brownfield Safety). The `.gitignore` file uses `#` comment prefix, which `_marker_pair()` already handles for non-extension files.

**Implementation detail**:
- Call `write_managed_section(repo_root / ".gitignore", "GITIGNORE", ".dev-stack/\n")` during init
- This runs regardless of which modules are selected (FR-009)
- Creates `.gitignore` if it doesn't exist (handled by `write_managed_section`)
- Preserves all existing user content outside the managed section markers

**Alternatives considered**:
- Simple string append (like sphinx_docs module) → rejected: not idempotent, can't update section on re-init
- Dedicated gitignore module → rejected: over-engineering for a single entry; this is init infrastructure, not a module

## R5: Agent Path Removal — Manifest serialization change

**Decision**: Remove `path` from `AgentConfig.to_dict()`. Keep `cli` as the only persisted field. Resolve path at runtime via `shutil.which()` / `$PATH`.

**Rationale**: FR-007 requires no absolute filesystem paths in `dev-stack.toml`. FR-008 requires runtime resolution. The `path` field is only used transiently by `AgentBridge` and pipeline stages. Persisting it offers no benefit (it's machine-specific) and breaks portability.

**Implementation detail**:
- `AgentConfig.to_dict()`: remove the `if self.path is not None: payload["path"] = self.path` line
- `AgentConfig.from_dict()`: ignore `path` key if present (backward compat with existing manifests)
- `detect_agent()`: already resolves path via `shutil.which()` — no change needed
- Init command: `manifest.agent = AgentConfig(cli=agent_info.cli)` — drop the `path=` kwarg
- Existing manifests with `path` field: silently ignored on read, removed on next write

**Alternatives considered**:
- Keep `path` as a relative path → rejected: agent CLIs are system-installed, not repo-relative
- Add a `portable_path` field → rejected: unnecessary complexity; `cli` + `shutil.which()` is sufficient

## R6: Secrets Baseline Gating — Module selection check

**Decision**: `_generate_secrets_baseline()` checks whether any secrets-related module is in the selected module list before running.

**Rationale**: FR-002 requires no `.secrets.baseline` unless explicitly requested. The function currently runs unconditionally during init. The fix is a simple guard clause.

**Implementation detail**:
- Pass `module_names` to `_generate_secrets_baseline(repo_root, module_names)`
- Check if any secrets-related module name is in the list (currently no dedicated secrets module exists, so the function should be a no-op unless one is added in the future)
- Alternative: remove the call entirely until a secrets module is implemented, guarded by a TODO comment
- The pipeline security stage already handles the case correctly — it skips detect-secrets when `.secrets.baseline` doesn't exist

**Alternatives considered**:
- Add a dedicated `secrets` module → deferred to future feature; out of scope
- Move secrets scanning into the security pipeline stage only → partially done already; init path is the remaining issue

## R7: User Hook Preservation (FR-012) — Managed sections in YAML

**Decision**: Use managed section markers in `.pre-commit-config.yaml` to delimit dev-stack hooks.

**Rationale**: YAML supports `#` comments. Dev-stack can write its hooks within `# === DEV-STACK:BEGIN:HOOKS ===` / `# === DEV-STACK:END:HOOKS ===` markers. User hooks outside these markers are preserved. This matches the pattern used for `.gitignore` and agent instruction files.

**Implementation detail**:
- On first install: write full config with managed section
- On update/re-init: replace only the managed section, preserving user content
- Use `brownfield.markers.write_managed_section()` on the YAML file
- Dev-stack hooks go inside markers; user hooks before/after are untouched

**Alternatives considered**:
- Parse YAML, merge, and rewrite → brittle; loses comments and formatting
- Separate files (dev-stack hooks + user hooks) → rejected: pre-commit framework reads one config file
