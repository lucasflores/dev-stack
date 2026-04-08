# Internal API Contract: detect_package_layout()

**Module**: `src/dev_stack/layout.py`  
**Feature**: `017-package-layout-detection`

## Function Signature

```python
def detect_package_layout(
    repo_root: Path,
    manifest: dict[str, Any] | None = None,
) -> PackageLayout:
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_root` | `Path` | Yes | Absolute path to the repository root |
| `manifest` | `dict[str, Any] \| None` | No | Parsed stack manifest (`.dev-stack/stack.toml`). When provided, checked for explicit `package_name` config. |

## Return Value

Returns `PackageLayout` — never raises, never returns `None`.

| Field | Type | Description |
|-------|------|-------------|
| `layout_style` | `LayoutStyle` | One of `SRC`, `FLAT`, `NAMESPACE` |
| `package_root` | `Path` | Relative path to package root (e.g., `Path("src")` or `Path(".")`) |
| `package_names` | `list[str]` | Sorted list of discovered package names. May be empty. |

## Behavior Contract

### Precedence Order

1. **Manifest config**: If `manifest["modules"]["uv_project"]["config"]["package_name"]` exists, resolve its layout style from the filesystem (check `src/{name}/` → SRC, `{name}/` at root → FLAT, else default SRC) and return.
2. **pyproject.toml build-backend hints**:
   - **2a. Setuptools**: If `[tool.setuptools.packages.find]` has a `where` key, use the first entry as package root. If `namespaces = true`, set layout style to `NAMESPACE`.
   - **2b. Hatch**: If `[tool.hatch.build.targets.wheel]` has a `packages` key, derive package root and names from the path entries.
3. **src/ scan**: If `repo_root/src/` exists and contains subdirectories with `__init__.py`, return `SRC` layout.
4. **Repo root scan**: Use `scan_root_python_sources()` to find packages at repo root. If found, return `FLAT` layout.
5. **Default**: Return `SRC` layout with empty `package_names` (greenfield default).

### Invariants

- Always returns a `PackageLayout` (no exceptions, no `None`).
- `package_names` is always sorted alphabetically.
- `package_root` is always relative to `repo_root`.
- When multiple packages exist at a given level, all are returned.
- When config/hints conflict with filesystem, logs a warning and falls through.

### Side Effects

- Reads filesystem (directory listing, `pyproject.toml` parsing).
- Logs warnings for ambiguous layouts or config/filesystem conflicts via `logging.getLogger(__name__)`.
- No writes, no network access, no mutation of inputs.

---

## Consumer Contracts

### StageContext Threading

```python
# In runner.py — computed once before stage execution
layout = detect_package_layout(repo_root, manifest)
context = StageContext(repo_root=repo_root, ..., package_layout=layout)
```

### Typecheck Stage

```python
# In _execute_typecheck_stage()
layout = context.package_layout
# If layout is None (backward compat), fall back to src/ check
if layout is None:
    layout = detect_package_layout(context.repo_root)

# Mypy targets all discovered packages under the package root
for pkg in layout.package_names:
    target = str(layout.package_root / pkg)
    # Run: python3 -m mypy {target}
```

### Docs-API Stage

```python
# In _execute_docs_api_stage()
layout = context.package_layout or detect_package_layout(context.repo_root)

for pkg in layout.package_names:
    apidoc_target = str(layout.package_root / pkg)
    # Run: sphinx.ext.apidoc -o docs/api {apidoc_target} -f --module-first -e
```

### Hooks

```python
# In _build_hook_list()
# Hook entry uses all package directories
targets = " ".join(str(layout.package_root / pkg) for pkg in layout.package_names)
HookEntry(
    id="dev-stack-mypy",
    name="mypy type check",
    entry=f"python3 -m mypy {targets}",
    types=("python",),
)
```

### Sphinx conf.py

```python
# In _render_conf_py()
# Relative path from docs/ to package root
# NAMESPACE with package_root == Path(".") is treated like FLAT
if layout.package_root == Path("."):
    relative_root = ".."
else:
    relative_root = f"../{layout.package_root}"
# Renders: sys.path.insert(0, os.path.abspath("{relative_root}"))
```

### Sphinx Makefile

```python
# In _render_makefile()
# NAMESPACE with package_root == Path(".") is treated like FLAT
for pkg in layout.package_names:
    if layout.package_root == Path("."):
        apidoc_path = f"../{pkg}"
    else:
        apidoc_path = f"../{layout.package_root}/{pkg}"
    # Renders: python3 -m sphinx.ext.apidoc -o api {apidoc_path} -f --module-first -e
```

### preview_files()

```python
# In UvProjectModule.preview_files()
layout = detect_package_layout(self.repo_root, self.manifest)
pkg = layout.package_names[0] if layout.package_names else _normalize_name(self.repo_root.name)

# For greenfield (SRC layout, empty package_names) -> propose src/{pkg}/__init__.py
# For brownfield SRC -> propose src/{pkg}/__init__.py
# For brownfield FLAT -> propose {pkg}/__init__.py (no src/ prefix)
if layout.layout_style == LayoutStyle.FLAT:
    files[Path(f"{pkg}/__init__.py")] = ...
else:
    files[Path(f"src/{pkg}/__init__.py")] = ...
```
