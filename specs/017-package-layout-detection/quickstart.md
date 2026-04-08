# Quickstart: Universal Package Layout Detection

**Feature**: `017-package-layout-detection`

## What Changed

The `detect_package_layout()` utility replaces three independent package-detection implementations with a single source of truth. It discovers the project's Python package root regardless of whether the project uses a `src` layout, flat layout, or namespace layout.

## For Pipeline Users (No Action Needed)

If your project uses the standard `src/<pkg>/` layout, **nothing changes**. The pipeline continues to work exactly as before.

If your project uses a **flat layout** (`my_package/` at repo root), the pipeline now automatically detects this and:
- mypy scans the correct package directory
- sphinx-apidoc documents the correct package
- pre-push hooks target the correct directory
- `conf.py` has the correct `sys.path.insert`

## For Module Authors

### Accessing the Detected Layout

In pipeline stages, the layout is available on `StageContext`:

```python
def _execute_my_stage(context: StageContext) -> StageResult:
    layout = context.package_layout
    if layout is None:
        # Backward compatibility: detect independently
        from dev_stack.layout import detect_package_layout
        layout = detect_package_layout(context.repo_root)
    
    for pkg in layout.package_names:
        target = layout.package_root / pkg
        # ... use target path
```

In modules (outside pipeline), call the utility directly:

```python
from dev_stack.layout import detect_package_layout

layout = detect_package_layout(repo_root, manifest=self.manifest)
```

### Layout Properties

```python
layout.layout_style   # LayoutStyle.SRC, LayoutStyle.FLAT, or LayoutStyle.NAMESPACE
layout.package_root   # Path("src") or Path(".")
layout.package_names  # ["my_package"] — sorted, may be empty
```

### Key Rules

1. **Never hardcode `src/`** — always use `layout.package_root`.
2. **Handle empty `package_names`** — greenfield projects may have no packages yet.
3. **Handle multiple packages** — iterate `layout.package_names`, don't assume a single package.
4. **Don't call detection repeatedly** — the pipeline computes it once. If you need it in a module, call once and cache the result.

## For Configuration Users

### Explicit Override

Set `package_name` in your stack manifest to force a specific package name:

```toml
# .dev-stack/stack.toml
[modules.uv_project]
config = { package_name = "my_custom_pkg" }
```

This takes highest precedence over all auto-detection.

### pyproject.toml Hints

The utility reads build-backend configuration:

```toml
# Setuptools
[tool.setuptools.packages.find]
where = ["lib"]  # → package_root = Path("lib")

# Hatch
[tool.hatch.build.targets.wheel]
packages = ["src/my_pkg"]  # → package_root = Path("src"), package_names = ["my_pkg"]
```
