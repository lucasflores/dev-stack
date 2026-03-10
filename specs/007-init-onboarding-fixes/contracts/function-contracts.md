# Function Contracts: Init Onboarding Fixes

**Feature**: 007-init-onboarding-fixes  
**Date**: 2026-03-10

---

## Contract 1: `_generate_secrets_baseline(repo_root: Path) -> None`

**File**: `src/dev_stack/cli/init_cmd.py`  
**FRs**: FR-001, FR-002

### Current Signature
```python
def _generate_secrets_baseline(repo_root: Path) -> None
```

### Changed Behavior

**Before**: Runs `detect-secrets scan` without exclusions. SHA-256 checksums in `.dev-stack/hooks-manifest.json` are recorded as findings. `.secrets.baseline` itself may be scanned on subsequent runs.

**After**: Runs `detect-secrets scan --exclude-files '\.dev-stack/|\.secrets\.baseline'` so that:
1. Files under `.dev-stack/` are never scanned
2. `.secrets.baseline` itself is never scanned
3. The exclusion pattern is stored in the baseline's `filters_used` for persistence

### Preconditions
- `detect-secrets` is installed (checked via `shutil.which`)
- `.secrets.baseline` does NOT already exist (early return if it does)

### Postconditions
- `.secrets.baseline` exists at `repo_root / ".secrets.baseline"`
- Baseline contains no results for paths matching `.dev-stack/*`
- Baseline contains no results for `.secrets.baseline`
- Baseline `filters_used` includes the `--exclude-files` regex pattern
- Real secrets in user files ARE included in results

---

## Contract 2: `_execute_security_stage(context: StageContext) -> StageResult`

**File**: `src/dev_stack/pipeline/stages.py`  
**FRs**: FR-001, FR-002, FR-003

### Current Signature
```python
def _execute_security_stage(context: StageContext) -> StageResult
```

### Changed Behavior

**Before**: Runs `detect-secrets scan --baseline .secrets.baseline` without exclusions. Self-referential entries may appear; `.dev-stack/` entries may persist.

**After**: Runs `detect-secrets scan --baseline .secrets.baseline --exclude-files '\.dev-stack/|\.secrets\.baseline'` for defense-in-depth. The exclusion is already stored in `filters_used` from the initial baseline, but explicit CLI args ensure correctness even if the baseline is regenerated externally.

### Preconditions
- `.secrets.baseline` exists (if not, stage skips with PASS)
- `pip-audit` has already run (first half of security stage)

### Postconditions
- Returns `StageStatus.PASS` when no unaudited or confirmed-real secrets exist
- Returns `StageStatus.FAIL` when unaudited or confirmed-real secrets exist in user files
- `.dev-stack/` files never cause a FAIL
- `.secrets.baseline` self-referential entries never cause a FAIL

---

## Contract 3: `has_existing_conflicts(report: ConflictReport) -> bool`

**File**: `src/dev_stack/cli/_shared.py`  
**FRs**: FR-005

### Current Signature
```python
def has_existing_conflicts(report: ConflictReport) -> bool
```

### Changed Behavior

**Before**: `return any(conflict.current_hash for conflict in report.conflicts)` — counts ALL conflicts with existing files, regardless of resolution.

**After**: `return any(c.current_hash for c in report.conflicts if c.resolution == "pending")` — only unresolved conflicts count.

### Preconditions
- `report` has been processed by predecessor detection (greenfield predecessor resolution already applied)

### Postconditions
- Returns `False` when all conflicts are resolved (greenfield_predecessor, accepted, merged, etc.)
- Returns `True` only when at least one pending conflict has `current_hash` set
- Consistent with `ConflictReport.all_resolved` property semantics

---

## Contract 4: `detect_agent(manifest: StackManifest | None = None) -> AgentInfo`

**File**: `src/dev_stack/config.py`  
**FRs**: FR-006

### Current Signature
```python
def detect_agent(manifest: StackManifest | None = None) -> AgentInfo
```

### Changed Behavior

**Before**: `DEV_STACK_AGENT=none` → `_resolve_cli("none")` → `shutil.which("none")` returns `None` → falls through to auto-detection.

**After**: `DEV_STACK_AGENT=none` → early return `AgentInfo(cli="none", path=None)` before calling `_resolve_cli()`.

### Preconditions
- None (detection order: env var → manifest → AGENT_PRIORITY)

### Postconditions
- When `DEV_STACK_AGENT=none` (case-insensitive): returns `AgentInfo(cli="none", path=None)`, no binary resolution attempted
- When `DEV_STACK_AGENT` is set to a valid agent name: existing behavior preserved
- When `DEV_STACK_AGENT` is unset: existing behavior preserved

---

## Contract 5: `_determine_mode(already_initialized: bool, has_conflicts: bool) -> str`

**File**: `src/dev_stack/cli/init_cmd.py`  
**FRs**: FR-012

### Current Signature
```python
def _determine_mode(already_initialized: bool, has_conflicts: bool) -> str
```

### Changed Behavior

No code change to this function. The fix is upstream: `has_existing_conflicts()` now returns `False` when all conflicts are greenfield predecessors, so `_determine_mode(False, False)` correctly returns `"greenfield"`.

### Postconditions
- `uv init --package` → `dev-stack init` results in `mode = "greenfield"` (not `"brownfield"`)
- Repos with genuine unresolved conflicts still get `mode = "brownfield"`

---

## Contract 6: `VcsHooksModule._generate_constitutional_files(...)`

**File**: `src/dev_stack/modules/vcs_hooks.py`  
**FRs**: FR-009, FR-010, FR-011

### Current Signature
```python
def _generate_constitutional_files(
    self,
    created: list[Path],
    modified: list[Path],
    warnings: list[str],
) -> None
```

### Changed Behavior

**Before**: Writes `constitution-template.md` to repo root from `TEMPLATE_DIR / "constitution-template.md"`.

**After**:
1. Checks if `.specify/templates/` directory exists (speckit installed)
2. If YES: reads baseline practices from source template, injects into `.specify/templates/constitution-template.md` using managed section markers
3. If NO: skips constitution content entirely (no file created)
4. Never creates a root-level `constitution-template.md`
5. On reinit: if root `constitution-template.md` exists with dev-stack signature (`# Dev-Stack Baseline Practices`), extracts user content below `## User-Defined Requirements`, appends to speckit template, deletes root file

### Preconditions
- `self.repo_root` is valid
- Called during `install()` lifecycle

### Postconditions
- No `constitution-template.md` at repo root (FR-009)
- If speckit installed: `.specify/templates/constitution-template.md` contains baseline practices (FR-010)
- If speckit not installed: no constitution file anywhere (FR-010 clarification)
- On reinit with existing root file: user content preserved, root file removed (FR-011)

---

## Contract 7: `DEFAULT_GREENFIELD_MODULES` reorder

**File**: `src/dev_stack/modules/__init__.py`  
**FRs**: FR-010 (supporting)

### Changed Value

**Before**: `("uv_project", "sphinx_docs", "hooks", "vcs_hooks", "speckit")`  
**After**: `("uv_project", "sphinx_docs", "hooks", "speckit", "vcs_hooks")`

### Postconditions
- `speckit.install()` runs before `vcs_hooks.install()`
- `.specify/templates/constitution-template.md` exists when `vcs_hooks._generate_constitutional_files()` executes
- No dependency cycles introduced (both modules have `DEPENDS_ON = ()`)
