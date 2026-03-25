# Research: Remove SpecKit Module — Consolidate Under APM

**Feature**: 014-apm-module-swap | **Date**: 2026-03-24

## R1: APM Dependency Pinning Syntax

**Decision**: Pin all new `apm.yml` entries to a specific git tag using `#v<tag>` suffix on the package URI. Commit SHA pinning (`#abc1234`) is the fallback when a tag is unavailable.

**Rationale**: The spec's clarification Q2 mandates reproducible installs via pinned refs. APM's dependency format supports `#<ref>` suffix on git-based package URIs (tags, branches, or commit SHAs). Tags are preferred because they are human-readable and semantic; commit SHAs provide exact reproducibility when tags don't exist. The existing `apm.yml` template uses bare registry URIs for MCP servers (e.g., `ghcr.io/...`) which are pinned by the APM registry's own version resolution and lockfile.

**Key format**:
```yaml
dependencies:
  apm:
    - msitarzewski/agency-agents#v0.7.3
    - Hacklone/lazy-spec-kit#v1.0.0
  mcp:
    - ghcr.io/upstash/context7-mcp-server      # Registry-pinned via lockfile
```

**Alternatives considered**:
- Branch tracking (`#main`): Rejected — violates reproducibility requirement from clarification Q2.
- No pinning (bare URI): Rejected — same reason.
- Individual file URIs: Over-specified — APM resolves entire packages, not individual files.

## R2: Agency Reviewer Exact Paths and Mapping

**Decision**: Declare `msitarzewski/agency-agents` as a single APM dependency. APM resolves the full package and installs the reviewer files.

**Rationale**: The current speckit module's `_AGENCY_REVIEWER_MAP` downloads individual files via HTTP from the GitHub raw content API. APM replaces this with a standard git dependency that fetches the entire package. The 5 reviewers are:

| Remote path in `msitarzewski/agency-agents` | Installed filename (by speckit) |
|---------------------------------------------|-------------------------------|
| `testing/testing-reality-checker.md` | `spec-compliance.md` |
| `engineering/engineering-security-engineer.md` | `security.md` |
| `testing/testing-performance-benchmarker.md` | `performance.md` |
| `testing/testing-accessibility-auditor.md` | `accessibility.md` |
| `engineering/engineering-backend-architect.md` | `architecture.md` |

**Note**: APM installs files using the original filenames from the package, not the renamed aliases speckit used. This is acceptable — the rename mapping was speckit-specific convenience. APM's install paths are controlled by the package's `apm.yml` or by APM's default placement rules.

**Alternatives considered**:
- Re-creating the rename mapping in APM: Over-engineering. The original filenames are descriptive.
- Keeping speckit just for renaming: Defeats purpose of removal.

## R3: LazySpecKit Exact Paths

**Decision**: Declare `Hacklone/lazy-spec-kit` as a single APM dependency. APM resolves the prompt and reviewer files.

**Rationale**: The current speckit module vendors 3 files from this repo:

| File | Source path |
|------|-------------|
| `LazySpecKit.prompt.md` | `prompts/LazySpecKit.prompt.md` (788 lines) |
| `code-quality.md` | `reviewers/code-quality.md` (79 lines) |
| `test.md` | `reviewers/test.md` (79 lines) |

APM's package resolution handles these natively — the package's `apm.yml` declares which files are prompts vs reviewers, and APM installs them to the correct locations.

**Alternatives considered**:
- Continuing to vendor these files: Rejected — the whole point is APM manages dependencies.
- Separate APM entries per file: Unnecessary — single package reference suffices.

## R4: Migration Handler Pattern for Deprecated Modules

**Decision**: Add a migration check in `update_cmd.py` that detects `[modules.speckit]` in existing `dev-stack.toml`, marks it with `deprecated = true`, logs an informational message, and skips module instantiation for unknown/deprecated modules.

**Rationale**: The spec's FR-004 requires graceful handling. The `update_cmd.py` already has a `ModuleDelta` pattern that tracks added/updated/removed modules. The migration can be implemented as:

1. During module resolution in `update`, if a module name from the manifest is not in `_MODULE_REGISTRY`, check if it was a known deprecated module.
2. If it's `speckit`, add `deprecated = true` to the TOML entry and emit an info message.
3. Skip it during module instantiation (don't raise `KeyError`).

The existing `resolve_module_names()` function raises `KeyError` for unknown modules — this needs a guard for deprecated names. A `DEPRECATED_MODULES` mapping in `modules/__init__.py` provides the lookup.

**Implementation pattern**:
```python
# In modules/__init__.py
DEPRECATED_MODULES: dict[str, str] = {
    "speckit": "Removed in 014-apm-module-swap. Use 'apm' module + 'specify init'.",
}
```

**Alternatives considered**:
- Silently ignoring unknown modules: Rejected — user gets no feedback about the retirement.
- Raising an error: Rejected — FR-004 requires graceful completion.
- Auto-deleting the TOML section: Rejected — clarification Q1 says mark deprecated, keep in file.

## R5: Cross-Module References to SpecKit

**Decision**: Update or remove all cross-references to speckit in the codebase beyond the module itself.

**Rationale**: Research identified 4 files outside `speckit.py` that reference speckit:

| File | Reference | Action |
|------|-----------|--------|
| `modules/__init__.py` L15 | `"speckit"` in `DEFAULT_GREENFIELD_MODULES` | Remove from tuple |
| `modules/__init__.py` L98 | `from . import ... speckit ...` | Remove from import |
| `manifest.py` L17 | `("hooks", "speckit")` in `DEFAULT_MODULES` | Change to `("hooks",)` |
| `pipeline/stages.py` L341 | `\.lazyspeckit/` in detect-secrets exclude | Remove pattern |
| `modules/vcs_hooks.py` L384-386 | Variable named `speckit_templates_dir` but references `.specify/templates/` | **Rename variable only** — do NOT remove logic |
| `modules/vcs_hooks.py` L564-573 | Variable named `speckit_templates_dir` but references `.specify/templates/` | **Rename variable only** — do NOT remove logic |

**Critical**: The `vcs_hooks.py` references use a variable named `speckit_templates_dir` but the actual path is `.specify/templates/` (created by `specify init`), **NOT** the vendored `templates/speckit/` directory being deleted. These references must be corrected by renaming the variable to `specify_templates_dir` for clarity. The constitution injection logic itself MUST be preserved — removing it would break constitution template management.
- b) Be removed entirely (since `specify init` handles constitution creation independently).

Renaming the variable for clarity is the correct action — the path `.specify/templates/` is independent of the speckit module being removed.

**Alternatives considered**:
- Removing vcs_hooks constitution injection: **REJECTED — would break constitution template management**. The path `.specify/templates/` is not related to the vendored `templates/speckit/` directory.
- Keeping vcs_hooks constitution injection with a new path: Not needed — the path is already correct (`.specify/templates/`), only the variable name is misleading.

## R6: Files to Delete (Complete Inventory)

**Decision**: Delete 18 files totaling ~3,639 lines.

| Category | Count | Lines | Files |
|----------|-------|-------|-------|
| Module source | 1 | 370 | `src/dev_stack/modules/speckit.py` |
| SpecKit templates | 12 | 2,117 | `src/dev_stack/templates/speckit/**` |
| LazySpecKit templates | 3 | 946 | `src/dev_stack/templates/lazyspeckit/**` |
| Unit tests | 1 | 125 | `tests/unit/test_speckit_lazyspeckit.py` |
| Integration tests | 1 | 81 | `tests/integration/test_speckit.py` |
| **Total** | **18** | **3,639** | |

**Reference edits** (not deletions): ~14 lines across `modules/__init__.py`, `manifest.py`, `pipeline/stages.py`, `modules/vcs_hooks.py`.

## R7: Impact on Existing Tests

**Decision**: Update 2 test files that assert on `DEFAULT_GREENFIELD_MODULES` content; delete 2 test files entirely; verify contract tests still pass.

**Rationale**: Research identified these test impacts:

| Test file | Current assertion | Required change |
|-----------|-------------------|-----------------|
| `tests/unit/test_modules_registry.py` L88 | Asserts `DEFAULT_GREENFIELD_MODULES == ("uv_project", "sphinx_docs", "hooks", "speckit", "vcs_hooks")` | Remove `"speckit"`, add `"apm"` |
| `tests/unit/test_modules_registry.py` L93 | Asserts `"speckit"` present in resolved defaults | Update to not include `"speckit"` |
| `tests/unit/test_apm_module.py` L255 | Asserts `"apm"` in `DEFAULT_GREENFIELD_MODULES` | Already correct, no change needed |
| `tests/contract/test_module_interface.py` | Tests all registered modules | Will pass — speckit simply won't be registered |

**Alternatives considered**:
- Keeping speckit tests as "deprecated module" tests: Pointless — the module no longer exists.

## R8: Expanded `apm.yml` Template Format

**Decision**: Add `dependencies.apm` section to the default template with Agency reviewers and LazySpecKit packages, both pinned to git tags.

**Rationale**: The current `default-apm.yml` only has `dependencies.mcp`. The expanded template adds a `dependencies.apm` section for non-MCP dependencies. This follows APM's dependency format where different dependency types have different sections.

**⚠️ Implementation prerequisite**: Verify that the APM CLI (>= 0.8.0) supports the `dependencies.apm` key before implementing T016-T019. Run `apm --help` or consult APM documentation to confirm. If unsupported, an alternative key or structure may be needed.

**Proposed template**:
```yaml
name: "{{ PROJECT_NAME }}"
version: "1.0.0"
dependencies:
  mcp:
    - ghcr.io/upstash/context7-mcp-server
    - ghcr.io/github/github-mcp-server
    - ghcr.io/modelcontextprotocol/sequentialthinking-server
    - ghcr.io/huggingface/mcp-server
    - ghcr.io/notebooklm/mcp-server
  apm:
    - msitarzewski/agency-agents#v0.7.3
    - Hacklone/lazy-spec-kit#v1.0.0
```

**Note**: The exact git tags (`v0.7.3`, `v1.0.0`) must be verified against the live repos at implementation time. Use the latest stable tag available.

**Alternatives considered**:
- Listing individual files instead of packages: APM resolves at package level.
- Separate `apm.yml` for reviewers vs prompts: Unnecessary complexity.
