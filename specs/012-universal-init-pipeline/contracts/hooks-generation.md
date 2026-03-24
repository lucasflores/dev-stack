# Contract: Stack-Aware Hook Generation

**Module**: `src/dev_stack/modules/hooks.py`  
**Class**: `HooksModule`

## Purpose

Generate `.pre-commit-config.yaml` with hooks adapted to the target repository's language stack (FR-005, FR-006, FR-012).

## Modified Method: `install()`

```python
def install(self, *, force: bool = False) -> ModuleResult:
    """Install git hooks and pre-commit configuration.
    
    New behavior:
    - Detects stack profile via detect_stack_profile()
    - Generates conditional hook config (Python hooks only when Python present)
    - Preserves user hooks outside managed section markers
    """
```

## New Internal Methods

### `_build_hook_list(profile: StackProfile) -> list[HookEntry]`

Returns the list of hooks to include based on stack profile.

**Always included** (FR-006):
- `dev-stack-pipeline`: runs `dev-stack pipeline run`, no filenames

**Included when `profile.has_python` is True** (FR-005):
- `dev-stack-ruff`: runs `ruff check`, passes filenames
- `dev-stack-pytest`: runs `pytest -q`, no filenames
- `dev-stack-mypy`: runs `python3 -m mypy src/`, types: [python]

### `_render_pre_commit_config(hooks: list[HookEntry]) -> str`

Renders the hook list as YAML-formatted string for the managed section.

```yaml
repos:
  - repo: local
    hooks:
      - id: dev-stack-pipeline
        name: dev-stack pipeline
        entry: dev-stack pipeline run
        language: system
        pass_filenames: false
        stages: [commit]
      # Python hooks below only when has_python=True
```

### Managed Section Strategy (FR-012)

The `.pre-commit-config.yaml` uses managed section markers:

```yaml
# === DEV-STACK:BEGIN:HOOKS ===
repos:
  - repo: local
    hooks:
      ...
# === DEV-STACK:END:HOOKS ===
```

User-defined hooks outside these markers are preserved during re-init.

## Test Cases

| Scenario | Profile | Expected hooks |
|----------|---------|---------------|
| Non-Python repo | `has_python=False` | `dev-stack-pipeline` only |
| Python repo | `has_python=True` | `dev-stack-pipeline` + ruff + pytest + mypy |
| Re-init Python repo | `has_python=True` | Managed section updated, user hooks preserved |
| Force re-init | N/A | Replaces managed section regardless |

## Invariants

- `dev-stack-pipeline` hook is ALWAYS present regardless of stack (FR-006)
- Python hooks are NEVER present when `has_python=False` (FR-005, SC-004)
- User hooks outside managed markers are NEVER modified (FR-012)
