# Contract: Init Pipeline Changes

**Module**: `src/dev_stack/cli/init_cmd.py`

## Purpose

Make the init pipeline universal — correctly initialize any repository regardless of language or tech stack (FR-001, FR-002, FR-007, FR-009, FR-010).

## Change 1: Gate `uv sync` (FR-001)

**Current**: `uv sync --all-extras` runs unconditionally after module install.

**New**: Only runs when `uv_project` is in the selected module list.

```python
# Before
subprocess.run(["uv", "sync", "--all-extras"], cwd=str(repo_root), check=True)

# After
if "uv_project" in module_names:
    try:
        subprocess.run(["uv", "sync", "--all-extras"], cwd=str(repo_root), check=True)
    except subprocess.CalledProcessError as exc:
        # ... existing warning logic
```

**Test**: Init non-Python repo without `uv_project` → `uv sync` never called.

## Change 2: Gate secrets baseline (FR-002)

**Current**: `_generate_secrets_baseline(repo_root)` runs unconditionally.

**New**: Only runs when a secrets-related module is selected. Since no dedicated secrets module currently exists, this effectively disables it for all init runs until one is added.

```python
# Before
_generate_secrets_baseline(repo_root)

# After  
if _has_secrets_module(module_names):
    _generate_secrets_baseline(repo_root)

def _has_secrets_module(module_names: list[str]) -> bool:
    """Check if any secrets scanning module is in the selected modules."""
    SECRETS_MODULES = {"secrets", "security"}
    return bool(set(module_names) & SECRETS_MODULES)
```

**Test**: Init without secrets module → `.secrets.baseline` not created.

## Change 3: Manifest agent path (FR-007)

**Current**: `manifest.agent = AgentConfig(cli=agent_info.cli, path=agent_info.path)`

**New**: `manifest.agent = AgentConfig(cli=agent_info.cli)` — path not persisted.

**Test**: After init, `dev-stack.toml` contains no `path` key in `[agent]` section.

## Change 4: Gitignore managed section (FR-009)

**New function**: Called during init regardless of module selection.

```python
def _ensure_gitignore_managed_section(repo_root: Path) -> None:
    """Ensure .dev-stack/ is in .gitignore via managed section."""
    from ..brownfield.markers import write_managed_section
    write_managed_section(repo_root / ".gitignore", "GITIGNORE", ".dev-stack/")
```

**Placement**: Called after module install, before manifest write.

**Test**: After init, `.gitignore` contains managed section with `.dev-stack/`.

## Execution Order (post-change)

```
1. Parse modules
2. Build manifest
3. Detect agent (runtime, no path persistence)
4. Instantiate modules
5. Detect conflicts
6. Create rollback tag
7. Install modules (hooks module uses stack profile)
8. Apply post-install overrides
9. IF uv_project in modules: run uv sync        ← CHANGED (gated)
10. IF secrets module in modules: generate baseline  ← CHANGED (gated)
11. Ensure .gitignore managed section              ← NEW
12. Write manifest (no path in agent config)       ← CHANGED
13. Emit result
```

## Invariants

- `uv sync` NEVER runs unless `uv_project` module is selected (FR-001)
- `.secrets.baseline` NEVER created unless secrets module is selected (FR-002)
- `dev-stack.toml` NEVER contains absolute filesystem paths (FR-007, SC-006)
- `.dev-stack/` is ALWAYS in `.gitignore` (FR-009, SC-007)
- Each module is self-contained — no cross-module side effects (FR-010)
