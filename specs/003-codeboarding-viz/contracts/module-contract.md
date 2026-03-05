# Module Contract: VisualizationModule (CodeBoarding)

**Branch**: `003-codeboarding-viz` | **Date**: 2026-03-04

---

## Module Identity

```python
class VisualizationModule(ModuleBase):
    NAME = "visualization"
    VERSION = "1.0.0"  # Major bump: D2 → CodeBoarding
    DEPENDS_ON = ()
    MANAGED_FILES = (".codeboarding/", ".dev-stack/viz/")
```

---

## Lifecycle Methods

### `install(*, force: bool = False) -> ModuleResult`

**Behavior**:
1. Create `.codeboarding/` directory (state + output)
2. Create `.dev-stack/viz/` directory (manifest store)
3. Verify `codeboarding` CLI is available on PATH via `shutil.which("codeboarding")`
4. If CLI not found: return success with warning (CLI can be installed later)

**Returns**:
```python
ModuleResult(
    success=True,
    message="Visualization module installed",
    files_created=[Path(".codeboarding/"), Path(".dev-stack/viz/")],
    warnings=["CodeBoarding CLI not found on PATH; install via 'pip install codeboarding'"]  # conditional
)
```

**Postconditions**:
- `.codeboarding/` directory exists
- `.dev-stack/viz/` directory exists

---

### `uninstall() -> ModuleResult`

**Behavior**:
1. Load injection ledger from `.codeboarding/injected-readmes.json`
2. For each entry in ledger: remove the managed section from the README file
3. Delete `.codeboarding/` directory (entire tree)
4. Delete `.dev-stack/viz/` directory (entire tree)
5. Delete legacy `docs/diagrams/` directory if present (migration cleanup)

**Returns**:
```python
ModuleResult(
    success=True,
    message="Visualization assets removed",
    files_modified=[Path("README.md"), ...],  # READMEs with sections removed
    files_deleted=[Path(".codeboarding/"), Path(".dev-stack/viz/")],
    warnings=[]
)
```

**Postconditions**:
- No managed section markers remain in any README listed in the ledger
- `.codeboarding/` and `.dev-stack/viz/` directories do not exist
- Legacy `docs/diagrams/` removed if it existed

---

### `update() -> ModuleResult`

**Behavior**: Delegates to `install(force=True)`.

**Returns**: Same as `install()`.

---

### `verify() -> ModuleStatus`

**Behavior**:
1. Check `.codeboarding/` directory exists
2. Check `.dev-stack/viz/` directory exists
3. Check `codeboarding` CLI is on PATH
4. Report health status

**Returns**:
```python
ModuleStatus(
    name="visualization",
    installed=True,           # dirs exist
    version="1.0.0",
    healthy=True,             # dirs exist AND CLI found
    issue=None,               # or descriptive string
    config={
        "codeboarding_path": "/path/to/codeboarding",  # or None
        "output_dir": ".codeboarding/"
    }
)
```

**Health matrix**:

| Dirs exist | CLI found | `installed` | `healthy` | `issue` |
|------------|-----------|-------------|-----------|---------|
| Yes | Yes | `True` | `True` | `None` |
| Yes | No | `True` | `False` | `"CodeBoarding CLI not found"` |
| No | Yes | `False` | `False` | `"Visualization directories missing"` |
| No | No | `False` | `False` | `"Visualization directories missing"` |

---

## Constants

```python
CODEBOARDING_OUTPUT_DIR = Path(".codeboarding")
VIZ_STATE_DIR = Path(".dev-stack/viz")
LEGACY_DOCS_DIR = Path("docs/diagrams")       # D2 legacy, cleaned on uninstall
ANALYSIS_INDEX = "analysis.json"
INJECTION_LEDGER = "injected-readmes.json"
ROOT_MARKER_ID = "architecture"
COMPONENT_MARKER_ID = "component-architecture"
DEFAULT_DEPTH_LEVEL = 2
DEFAULT_TIMEOUT_SECONDS = 300
```

---

## Managed Section Markers

### Root README (top-level architecture)

```markdown
<!-- === DEV-STACK:BEGIN:architecture === -->
```mermaid
graph LR
  ...
```
<!-- === DEV-STACK:END:architecture === -->
```

### Component README (sub-diagram)

```markdown
<!-- === DEV-STACK:BEGIN:component-architecture === -->
```mermaid
graph LR
  ...
```
<!-- === DEV-STACK:END:component-architecture === -->
```

---

## Injection Ledger Contract

**File**: `.codeboarding/injected-readmes.json`  
**Owner**: dev-stack (VisualizationModule)  
**Lifecycle**: Created/updated on each `visualize` run; read during `uninstall()`

```json
{
  "version": 1,
  "generated_at": "2026-03-04T12:00:00Z",
  "entries": [
    {
      "readme_path": "README.md",
      "marker_id": "architecture",
      "component_name": null
    },
    {
      "readme_path": "src/agents/README.md",
      "marker_id": "component-architecture",
      "component_name": "LLM Agent Core"
    }
  ]
}
```

**Invariants**:
- Each `(readme_path, marker_id)` pair is unique
- `component_name` is `null` only for the root architecture entry
- The ledger is the single source of truth for cleanup — no directory scanning needed
