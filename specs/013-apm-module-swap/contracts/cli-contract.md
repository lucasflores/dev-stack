# CLI Contract: APM Module

**Feature**: 013-apm-module-swap | **Date**: 2026-03-24

## Command Group: `dev-stack apm`

### `dev-stack apm install`

**Description**: Install MCP server packages from `apm.yml` manifest using APM CLI.

**Options**:
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--force` | `bool` | `False` | Force reinstall even if lockfile is current |

**Behavior**:
1. Verify APM CLI is on PATH and meets minimum version (FR-006, FR-007)
2. If `apm.yml` does not exist, bootstrap with defaults (FR-002, FR-003)
3. If `apm.yml` exists, prompt user: skip / merge / overwrite (FR-013)
4. Run `apm install` (FR-004, FR-005)
5. Report per-server success/failure (FR-015)

**Exit Codes**:
| Code | Meaning |
|------|---------|
| 0 | All servers installed successfully |
| 1 | Partial or full install failure |
| 4 | APM CLI not found on PATH |

**JSON Output** (`--json`):
```json
{
  "success": true,
  "servers_installed": ["context7", "github", "sequential-thinking", "huggingface", "notebooklm"],
  "servers_failed": [],
  "manifest": "apm.yml",
  "lockfile": "apm.lock.yaml",
  "warnings": []
}
```

**Human Output**:
```
✓ APM CLI v0.9.0 detected
✓ apm.yml bootstrapped with 5 default servers
✓ context7 installed
✓ github installed
✓ sequential-thinking installed
✓ huggingface installed
✓ notebooklm installed
✓ apm.lock.yaml generated

5/5 MCP servers installed successfully.
```

---

### `dev-stack apm audit`

**Description**: Run APM security audit on installed MCP server packages.

**Options**:
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | `Choice[text, json, sarif, markdown]` | `text` | Output format |
| `--output` | `Path` | stdout | Write report to file |

**Behavior**:
1. Verify APM CLI is on PATH (FR-006)
2. Run `apm audit -f {format}` (FR-009)
3. If `--output` specified, pass `-o {path}` to APM
4. Surface APM's exit code and findings

**Exit Codes**:
| Code | APM Exit | Meaning |
|------|----------|---------|
| 0 | 0 | No findings |
| 1 | 1 | Critical findings (tag chars, bidi overrides) |
| 2 | 2 | Warning findings (zero-width chars) |
| 4 | N/A | APM CLI not found |

**JSON Output** (`--json --format json`):
```json
{
  "success": true,
  "findings_count": 0,
  "severity": "clean",
  "report_path": null
}
```

---

## Module Protocol: `APMModule`

### `install(force: bool = False) -> ModuleResult`

Called by: `dev-stack init` pipeline, `dev-stack apm install`

**Pre-conditions**:
- `repo_root` is a valid directory

**Post-conditions on success**:
- `apm.yml` exists at `repo_root / "apm.yml"`
- `apm.lock.yaml` exists at `repo_root / "apm.lock.yaml"`
- Agent-native config dirs populated by APM

**ModuleResult fields**:
- `success`: `True` if all servers installed
- `files_created`: List of files APM created/modified
- `warnings`: Per-server failure messages if partial install

### `verify() -> ModuleStatus`

**Checks**:
1. APM CLI on PATH → `healthy = False` if missing
2. APM version >= `MIN_APM_VERSION` → warning if below
3. `apm.yml` exists → `installed = True/False`
4. `apm.lock.yaml` exists → warning if missing
5. `apm.lock.yaml` mtime >= `apm.yml` mtime → warning if stale

### `uninstall() -> ModuleResult`

**Removes**: `apm.yml`, `apm.lock.yaml`
**Does NOT remove**: Agent-native config files (those are managed by APM)

### `update() -> ModuleResult`

**Equivalent to**: `install(force=True)` — re-runs `apm install` against existing manifest

---

## Init Pipeline Integration

When `dev-stack init` runs with `apm` in the module list:

```
resolve_module_names(requested=None, include_defaults=True)
  → includes "apm" (from DEFAULT_GREENFIELD_MODULES)
  → excludes "mcp-servers" (no longer in defaults)

instantiate_modules(repo_root, manifest, module_names)
  → APMModule(repo_root, manifest)

for module in modules:
    module.install()
    → APMModule.install()
      → _check_apm_cli()
      → _bootstrap_manifest() with user prompt if needed
      → _run_apm(["install"])
      → _parse_install_result()
```
