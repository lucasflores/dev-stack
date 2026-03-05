# CLI Contract: `dev-stack visualize` (CodeBoarding)

**Branch**: `003-codeboarding-viz` | **Date**: 2026-03-04

---

## Command Signature

```
dev-stack visualize [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--incremental` | flag | `False` | Only re-analyze changed files; passes `--incremental` to CodeBoarding |
| `--depth-level` | `int` | `2` | Number of decomposition levels (1 = top-level only) |
| `--no-readme` | flag | `False` | Run analysis without injecting diagrams into README files |
| `--timeout` | `int` | `300` | Subprocess timeout in seconds for CodeBoarding CLI |
| `--json` | flag | `False` | Output machine-readable JSON (inherited from global) |
| `--verbose` | flag | `False` | Debug-level logging (inherited from global) |

---

## Behavior

### Normal Flow

1. Verify `codeboarding` CLI is on PATH → error if not found (exit 4)
2. If `--incremental`: load manifest, compare file hashes → skip if unchanged
3. Build CodeBoarding command: `codeboarding --local . --depth-level <N>` [+ `--incremental`]
4. Execute subprocess with `timeout` seconds
5. Parse `.codeboarding/analysis.json` for component index
6. Extract Mermaid diagrams from `.codeboarding/overview.md` and `<Component_Name>.md`
7. Unless `--no-readme`:
   a. Inject top-level diagram into `README.md` (marker: `architecture`)
   b. Inject sub-diagrams into component folder `README.md` files (marker: `component-architecture`)
   c. Update injection ledger (`.codeboarding/injected-readmes.json`)
8. Save manifest
9. Report results

### Error Handling

| Condition | Behavior | Exit Code |
|-----------|----------|-----------|
| CodeBoarding CLI not on PATH | Print installation guidance | 4 |
| CodeBoarding non-zero exit | Display stderr verbatim, no README changes | 1 |
| Subprocess timeout | Display timeout message, no README changes | 1 |
| `analysis.json` missing or malformed | Report parse error | 1 |
| Component `.md` file missing | Log warning, skip that component, continue | 0 (with warnings) |
| README write permission denied | Log warning, skip that file, continue | 0 (with warnings) |

---

## JSON Output Schema (`--json`)

### Success

```json
{
  "status": "success",
  "depth_level": 2,
  "components_found": 5,
  "diagrams_injected": 6,
  "readmes_modified": [
    "README.md",
    "agents/README.md",
    "static_analyzer/README.md"
  ],
  "files_scanned": 47,
  "files_changed": 3,
  "incremental": false,
  "skipped": false,
  "codeboarding_output": ".codeboarding/",
  "warnings": []
}
```

### Incremental (no changes)

```json
{
  "status": "success",
  "skipped": true,
  "reason": "No files changed since last run",
  "files_scanned": 47,
  "files_changed": 0,
  "incremental": true
}
```

### Error

```json
{
  "status": "error",
  "message": "CodeBoarding CLI not found on PATH. Install via: pip install codeboarding",
  "exit_code": 4
}
```

### Error (subprocess failure)

```json
{
  "status": "error",
  "message": "CodeBoarding exited with code 1:\n<stderr content>",
  "exit_code": 1
}
```

---

## Human Output Examples

### Success (default)

```
Visualization complete:
  Components: 5 found
  Diagrams: 6 injected
  READMEs modified:
    - README.md (architecture)
    - agents/README.md (component-architecture)
    - static_analyzer/README.md (component-architecture)
```

### Incremental (no changes)

```
All diagrams up to date (no files changed).
```

### Error (CLI missing)

```
Error: CodeBoarding CLI not found on PATH.
Install via: pip install codeboarding
Then run: codeboarding-setup
```

---

## Subprocess Invocation Contract

### Command Construction

```python
cmd = ["codeboarding", "--local", str(repo_root)]
cmd += ["--depth-level", str(depth_level)]
if incremental:
    cmd.append("--incremental")
```

### Execution

```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=timeout_seconds,
    check=False,
    cwd=repo_root,
)
```

### Expected postconditions on success (exit 0)

- `.codeboarding/analysis.json` exists and is valid JSON
- `.codeboarding/overview.md` exists and contains a Mermaid code block
- For each component with `can_expand: true` at the produced depth, a corresponding `.codeboarding/<Name>.md` exists
