# Research — 007 Init Onboarding Fixes

## Topic 1: `detect-secrets --exclude-files` Regex Syntax

### Decision

Use a **single `--exclude-files` flag with pipe-alternation** for the initial baseline generation and the security stage scan:

```bash
detect-secrets scan --exclude-files '\.dev-stack/|\.secrets\.baseline'
```

### Rationale

**Regex format**: `--exclude-files` accepts a Python `re.search()` regex pattern matched against **relative paths from the repo root** (not absolute paths). Result keys in the baseline JSON are always relative (e.g., `.dev-stack/hooks-manifest.json`, `secret.txt`).

**Single vs. multiple flags**: Both work. Passing multiple `--exclude-files` flags stores them as an **array** in the `filters_used` section:

```json
{"path": "detect_secrets.filters.regex.should_exclude_file", "pattern": ["\\.dev-stack/", "\\.secrets\\.baseline"]}
```

A single flag with alternation stores a single-element array:

```json
{"path": "detect_secrets.filters.regex.should_exclude_file", "pattern": ["\\.dev-stack/|\\.secrets\\.baseline"]}
```

Both are functionally equivalent. A single alternation pattern is simpler for code construction.

**Filter persistence**: When `--exclude-files` is passed during the initial `detect-secrets scan > .secrets.baseline`, the exclude pattern is persisted in the baseline's `filters_used` array. Subsequent `detect-secrets scan --baseline .secrets.baseline` respects the stored filters — no need to re-pass `--exclude-files` on every invocation.

**Verified experimentally** (detect-secrets ≥1.5):

| Test | Result |
|---|---|
| Single `--exclude-files` with `\|` alternation | Files matching either side excluded from results |
| Multiple `--exclude-files` flags | Both stored as array elements, both applied |
| Path format in results | Always relative from repo root (e.g., `.dev-stack/hooks-manifest.json`) |
| Filter persistence in baseline | `--exclude-files` regex stored in `filters_used`, respected by `--baseline` |
| Regex applied to what paths | Relative paths from git root (same as `git ls-files` output) |

### Alternatives Considered

| Approach | Verdict | Reason |
|---|---|---|
| Single `--exclude-files` with alternation | **Selected** | Simplest code, one CLI arg, persists in baseline |
| Multiple `--exclude-files` flags | Viable | Works identically but more CLI args to construct |
| `.secrets.baseline` config file approach | Rejected | Spec clarification says CLI args, no config file |
| `--exclude-lines` instead | Rejected | Operates on line content, not file paths |

---

## Topic 2: `detect-secrets scan --baseline` vs Bare Scan for Initial Baseline

### Decision

Use **`detect-secrets scan [--exclude-files ...] > .secrets.baseline`** (stdout redirect) for the **initial** baseline. Use **`detect-secrets scan --baseline .secrets.baseline`** for **subsequent** scans in the security stage. These are **compatible and complementary**.

### Rationale

**Initial baseline generation**: `detect-secrets scan` outputs JSON to stdout. Redirect to file creates the baseline. This is the correct approach for initial creation because `--baseline` requires the file to already exist.

**`--baseline` on non-existent file**: Experimentally verified — `detect-secrets scan --baseline <nonexistent>` **fails with exit code 2** and error message `"Invalid path"`. It cannot create a baseline from scratch.

**Compatibility**: The two commands produce compatible JSON. `--baseline` reads the existing baseline, preserves audit decisions (`is_secret` fields), merges new findings, and removes stale entries. The JSON schema is identical.

**Current code correctness**: The current `_generate_secrets_baseline()` in `init_cmd.py` correctly uses stdout redirect. The current `_execute_security_stage()` in `stages.py` correctly uses `--baseline`. The workflow is:

1. `init_cmd.py`: `detect-secrets scan > .secrets.baseline` (creates initial baseline)
2. `stages.py`: `detect-secrets scan --baseline .secrets.baseline` (updates in-place on subsequent runs)

**The fix needed**: Add `--exclude-files` to **both** commands so the initial baseline never contains `.dev-stack/` entries, and subsequent scans inherit the exclusion filter from the stored `filters_used`.

**Verified experimentally**:

| Scenario | Behavior |
|---|---|
| `detect-secrets scan > file` | Writes fresh JSON baseline to stdout → file |
| `detect-secrets scan --baseline file` (exists) | Updates file in-place, preserves audit decisions, exit code 0 |
| `detect-secrets scan --baseline file` (not exists) | **Fails** with exit code 2: `"Invalid path"` |
| `--exclude-files` on initial scan | Pattern stored in `filters_used` |
| `--baseline` on file with stored `--exclude-files` | Respects the stored filter — excluded files stay excluded |

### Alternatives Considered

| Approach | Verdict | Reason |
|---|---|---|
| Stdout redirect for initial, `--baseline` for updates | **Selected** | Correct workflow, both compatible |
| Always use `--baseline` | Broken | Fails on non-existent file |
| Don't use `--baseline`, re-scan from scratch each time | Rejected | Loses audit decisions, can't distinguish false positives |
| Touch empty file then `--baseline` | Rejected | Would fail JSON parsing |

---

## Topic 3: Speckit Module Install Order

### Decision

**Option (c)**: Have `vcs_hooks` check whether `speckit` is in the module install list and conditionally inject content into `.specify/templates/constitution-template.md` only when speckit has already run. Since speckit runs **after** `vcs_hooks` in the default order, **change the install order** so speckit runs before `vcs_hooks`.

Recommended new order: `("uv_project", "sphinx_docs", "hooks", "speckit", "vcs_hooks")`

### Rationale

**Current order**: `("uv_project", "sphinx_docs", "hooks", "vcs_hooks", "speckit")`

**The problem**: `vcs_hooks.install()` calls `_generate_constitutional_files()` which writes `constitution-template.md` to the **repo root**. Per FR-009/FR-010, it should instead inject into `.specify/templates/constitution-template.md` — but that directory doesn't exist yet because `speckit` hasn't run.

**Analysis of each option**:

**(a) Change install order** — Move `speckit` before `vcs_hooks`:
- **Pros**: Simplest fix. After speckit runs, `.specify/templates/constitution-template.md` exists. `vcs_hooks` can inject content into it directly.
- **Cons**: Requires checking that no other module dependencies are violated. `vcs_hooks.DEPENDS_ON` is currently empty, and `speckit` has no dependency on `vcs_hooks`, so reordering is safe.
- **Risk**: Low. The dependency resolver (`resolve_module_names`) does topological sort respecting `DEPENDS_ON`. Since neither module declares the other as a dependency, the order is determined by position in `DEFAULT_GREENFIELD_MODULES`.

**(b) Post-install hook / deferred injection**:
- **Pros**: No ordering change needed.
- **Cons**: Requires new infrastructure (post-install callback system). Over-engineered for this single use case. Adds complexity to the module lifecycle.
- **Verdict**: Rejected — too much new machinery.

**(c) `vcs_hooks` creates `.specify/templates/` itself if speckit is in the install list**:
- **Pros**: Works regardless of order.
- **Cons**: `vcs_hooks` reaches into speckit's directory structure, creating coupling. If speckit changes its template path, `vcs_hooks` breaks. Also, `vcs_hooks` doesn't currently have visibility into the module install list — it would need a new parameter or context.
- **Verdict**: Feasible but fragile.

**Selected: (a) + guard in `vcs_hooks`**. Change the default order to put `speckit` before `vcs_hooks`, AND add a guard in `_generate_constitutional_files()` that checks if `.specify/templates/` exists before writing there (falling back to skipping if speckit is not installed, per FR-010).

### Implementation Notes

1. Change `DEFAULT_GREENFIELD_MODULES` in `modules/__init__.py`:
   ```python
   DEFAULT_GREENFIELD_MODULES: Sequence[str] = ("uv_project", "sphinx_docs", "hooks", "speckit", "vcs_hooks")
   ```
2. Update `_generate_constitutional_files()` to target `.specify/templates/constitution-template.md` instead of repo root.
3. Guard: if `.specify/templates/` doesn't exist (speckit not installed), skip constitution content entirely.
4. Update `MANAGED_FILES` to replace `"constitution-template.md"` with `".specify/templates/constitution-template.md"`.
5. Update `verify()` to check the new path.

### Alternatives Considered

| Approach | Verdict | Reason |
|---|---|---|
| **(a)** Reorder + guard | **Selected** | Minimal change, no new infra, clean separation |
| **(b)** Post-install hooks | Rejected | Over-engineered for one use case |
| **(c)** `vcs_hooks` creates speckit dirs | Rejected | Cross-module coupling, fragile |
| Add `speckit` as `DEPENDS_ON` for `vcs_hooks` | Viable supplement | Would enforce ordering via dependency resolver; combine with (a) for belt-and-suspenders |

---

## Topic 4: `has_existing_conflicts` and Greenfield Predecessor Logic

### Decision

**Filter to only `pending` resolution** in `has_existing_conflicts()`. A conflict resolved as `greenfield_predecessor` should not count as a blocking conflict.

### Rationale

**Current code** (`_shared.py:72-73`):

```python
def has_existing_conflicts(report: ConflictReport) -> bool:
    return any(conflict.current_hash for conflict in report.conflicts)
```

This returns `True` if **any** conflict has `current_hash` set (i.e., the file exists on disk), regardless of resolution status. The problem: after the greenfield predecessor resolution loop marks `uv init --package` files as `resolution="greenfield_predecessor"`, `has_existing_conflicts()` still sees them because they have a `current_hash`.

**The data model** (`FileConflict`):

| Field | Meaning |
|---|---|
| `current_hash` | SHA-256 of existing file on disk, or `None` if file doesn't exist (NEW conflict) |
| `resolution` | One of: `"pending"`, `"greenfield_predecessor"`, `"accepted"`, `"skipped"`, `"merged"`, `"overwritten"` |

**What should block init**: Only conflicts with `resolution == "pending"` should block. Files marked as `greenfield_predecessor` are known-safe predecessors. Files marked via interactive resolution (`accepted`, `merged`, `skipped`) have already been handled by the user.

**The fix** (per FR-005):

```python
def has_existing_conflicts(report: ConflictReport) -> bool:
    return any(
        conflict.current_hash
        for conflict in report.conflicts
        if conflict.resolution == "pending"
    )
```

**Impact analysis**: This function is called in two places:
1. `init_cmd.py` — determines whether init should prompt for `--force` or interactive resolution. Fix ensures greenfield predecessors don't trigger the conflict flow.
2. `update_cmd.py` — same gating logic for the update command. The fix is correct here too: any pre-resolved conflicts from predecessor detection should not block updates.

**Should we check a different field instead?** No. The combination of `current_hash` (file exists) + `resolution == "pending"` (not yet handled) is the correct predicate. Checking only `resolution` without `current_hash` would wrongly flag NEW files (proposed files that don't exist on disk yet) — but those have `current_hash=None` and are already excluded.

**`ConflictReport.all_resolved` property** (`conflict.py:62-63`):

```python
@property
def all_resolved(self) -> bool:
    return all(conflict.resolution != "pending" for conflict in self.conflicts)
```

This correctly checks resolution status. `has_existing_conflicts` should be consistent with this approach.

### Alternatives Considered

| Approach | Verdict | Reason |
|---|---|---|
| Filter by `resolution == "pending"` | **Selected** | Matches FR-005, consistent with `all_resolved`, precise |
| Filter by `resolution not in ("greenfield_predecessor",)` | Rejected | Too specific — other resolutions (accepted, merged) should also not block |
| Check a different field (e.g., add `blocking: bool`) | Rejected | Over-engineering, resolution status already encodes this |
| Remove `current_hash` check entirely | Rejected | NEW conflicts (no file on disk) must not block either — `current_hash` check correctly excludes them |
| Add separate `has_blocking_conflicts()` | Rejected | Renaming/refactoring existing function is cleaner than adding a new one |

---

## Topic 5: `DEV_STACK_AGENT=none` Early Return

### Decision

Add an early return at the top of `detect_agent()` for the `"none"` case, before calling `_resolve_cli()`.

### Rationale

Current code in `config.py`:
```python
explicit = os.getenv("DEV_STACK_AGENT")
if explicit:
    cli = explicit.lower()
    resolved = _resolve_cli(cli)
    if resolved:
        return resolved
```

`_resolve_cli("none")` calls `shutil.which("none")` which returns `None` (no binary named "none"), so the function falls through to manifest detection and then AGENT_PRIORITY auto-detection. The fix: check `if cli == "none": return AgentInfo(cli="none", path=None)` immediately after lowering the env var.

### Alternatives Considered

| Approach | Verdict | Reason |
|---|---|---|
| Early return in `detect_agent()` | **Selected** | Simplest, most explicit, two-line change |
| Handle "none" in `_resolve_cli()` | Rejected | `_resolve_cli` resolves real binaries; "none" is a sentinel |
| Add "none" to `AGENT_PRIORITY` | Rejected | "none" means "no agent", not an agent candidate |

---

## Topic 6: Constitution Template Migration (Reinit)

### Decision

On reinit, check for a root-level `constitution-template.md` with dev-stack's known content signature (`# Dev-Stack Baseline Practices` as first heading). If found, extract any user-added content below the `## User-Defined Requirements` marker, append it to the speckit template, then delete the root file.

### Rationale

- The managed content in `constitution-template.md` (atomic commits, TDD sections) is already in the dev-stack source template — it doesn't need migration.
- Only the "User-Defined Requirements" section may contain user additions that need preservation.
- The content signature (`# Dev-Stack Baseline Practices`) reliably distinguishes dev-stack files from coincidental same-named files.
- If no user content exists below the marker, simply delete the root file.

### Alternatives Considered

| Approach | Verdict | Reason |
|---|---|---|
| Signature-based detection + selective migration | **Selected** | Safe — won't touch unrelated files |
| Always migrate root file if it exists | Rejected | Could destroy user content unrelated to dev-stack |
| Ignore reinit migration entirely | Rejected | Leaves orphaned root files from prior installs |
