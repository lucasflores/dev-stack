# Quickstart — 007 Init Onboarding Fixes

**Branch**: `007-init-onboarding-fixes`

## Change Summary

Six inter-related fixes to the `dev-stack init` onboarding pipeline. All changes are to existing files; no new modules or commands.

## Implementation Order

### Step 1: Fix `detect-secrets` Exclusions (P1 BLOCKING)

**Files**: [init_cmd.py](../../src/dev_stack/cli/init_cmd.py), [stages.py](../../src/dev_stack/pipeline/stages.py)

1. In `_generate_secrets_baseline()`: add `--exclude-files '\.dev-stack/|\.secrets\.baseline'` to the `detect-secrets scan` command  
2. In `_execute_security_stage()`: add the same `--exclude-files` flag to the scan command for defense-in-depth  
3. The exclusion regex uses Python `re.search()` against relative paths

**Verify**: `dev-stack init` in a fresh repo → `.secrets.baseline` has zero entries from `.dev-stack/` paths

### Step 2: Fix `has_existing_conflicts` Resolution Filter

**File**: [_shared.py](../../src/dev_stack/cli/_shared.py)

1. In `has_existing_conflicts()`: add `if conflict.resolution == "pending"` filter to the `any()` generator  

**Verify**: `uv init --package foo && dev-stack init` succeeds without `--force`; `mode = "greenfield"` in manifest

### Step 3: Fix `DEV_STACK_AGENT=none` Early Return

**File**: [config.py](../../src/dev_stack/config.py)

1. In `detect_agent()`: after `cli = explicit.lower()`, add `if cli == "none": return AgentInfo(cli="none", path=None)` before calling `_resolve_cli()`  

**Verify**: `DEV_STACK_AGENT=none dev-stack --json init --force` → `"cli": "none"`, `"path": null`

### Step 4: Reorder Default Greenfield Modules

**File**: [modules/\_\_init\_\_.py](../../src/dev_stack/modules/__init__.py)

1. Change `DEFAULT_GREENFIELD_MODULES` from `("uv_project", "sphinx_docs", "hooks", "vcs_hooks", "speckit")` to `("uv_project", "sphinx_docs", "hooks", "speckit", "vcs_hooks")`

**Verify**: No module dependency cycles; `speckit.install()` runs before `vcs_hooks.install()`

### Step 5: Redirect Constitution Template to Speckit

**File**: [vcs_hooks.py](../../src/dev_stack/modules/vcs_hooks.py)

1. In `_generate_constitutional_files()`:
   - Check if `.specify/templates/` exists
   - If yes: inject baseline practices into `.specify/templates/constitution-template.md` (managed section markers)
   - If no: skip constitution content entirely
   - Never create root-level `constitution-template.md`
2. On reinit: detect root `constitution-template.md` with `# Dev-Stack Baseline Practices` signature → extract user content → append to speckit template → delete root file
3. Update `MANAGED_FILES` to reference new path
4. Update `verify()` to check new path

**Verify**: `dev-stack init` → no `constitution-template.md` at repo root; content in `.specify/templates/constitution-template.md`

### Step 6: Update README Initial Commit Section

**File**: [README.md](../../README.md)

1. Document the clean initial commit workflow (no `--no-verify` needed after detect-secrets fix)
2. Add `--no-verify` as a troubleshooting fallback only, with explanation of when it should be used

**Verify**: README greenfield quickstart matches actual behavior

## Testing Strategy

| Layer | What to test |
|---|---|
| Unit | `has_existing_conflicts()` with pending vs. resolved conflicts |
| Unit | `detect_agent()` with `DEV_STACK_AGENT=none` |
| Unit | `_generate_secrets_baseline()` command construction includes `--exclude-files` |
| Unit | `_generate_constitutional_files()` targets speckit template path |
| Integration | Full greenfield flow: `uv init --package` → `dev-stack init` → first commit |
| Contract | Security stage excludes `.dev-stack/`, reports real secrets |

## Key Decisions

- **Single `--exclude-files` regex**: `'\.dev-stack/|\.secrets\.baseline'` with alternation (not multiple flags)
- **Defense-in-depth**: exclusion added to both initial baseline AND security stage scan
- **Constitution skip when no speckit**: If speckit is not installed, vcs_hooks creates no constitution file at all
- **Reinit migration**: Signature-based detection (`# Dev-Stack Baseline Practices`) identifies dev-stack files; user content below `## User-Defined Requirements` is preserved
