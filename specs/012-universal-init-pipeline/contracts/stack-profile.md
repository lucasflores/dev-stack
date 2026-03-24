# Contract: Stack Profile Detection

**Module**: `src/dev_stack/config.py`  
**Function**: `detect_stack_profile(repo_root: Path) -> StackProfile`

## Purpose

Scan a repository to determine which languages and tooling are present. Used by modules to adapt their output (FR-005).

## Signature

```python
def detect_stack_profile(repo_root: Path) -> StackProfile:
    """Detect the language/tooling stack of the target repository.
    
    Args:
        repo_root: Absolute path to the repository root.
        
    Returns:
        StackProfile with detected language flags.
    """
```

## Behavior

1. Check for Python files: `next(repo_root.rglob("*.py"), None)` with exclusions
2. Exclude directories: `.git/`, `.venv/`, `venv/`, `node_modules/`, `.dev-stack/`, `__pycache__/`
3. Return `StackProfile(has_python=True)` if any `.py` file found, else `False`

## Exclusion Logic

The rglob scan must skip:
- `.git/` — git internals
- `.venv/`, `venv/` — Python virtual environments  
- `node_modules/` — Node.js dependencies
- `.dev-stack/` — dev-stack internal files
- `__pycache__/` — Python bytecode caches

Implementation approach: Use a filtered walk or test each path segment against exclusion set.

## Test Cases

| Scenario | Input | Expected |
|----------|-------|----------|
| Pure markdown repo | `README.md`, `docs/*.md` | `has_python=False` |
| Python project | `src/pkg/__init__.py` | `has_python=True` |
| Script in root | `setup.py` only | `has_python=True` |
| .py in .venv | `.venv/lib/site.py` only | `has_python=False` |
| Mixed repo | `README.md`, `scripts/run.py` | `has_python=True` |
| Empty repo | no files | `has_python=False` |

## Consumed By

- `HooksModule.install()` — decides which hooks to include
- `init_command()` — passes profile information to modules
