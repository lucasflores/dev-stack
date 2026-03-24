# Research: APM Module Swap

**Feature**: 013-apm-module-swap | **Date**: 2026-03-24

## R1: APM CLI Commands and Integration Surface

**Decision**: Invoke APM CLI via `subprocess.run()` for `apm install` and `apm audit`. Dev-stack writes `apm.yml` directly via `_bootstrap_manifest()` using PyYAML (not `apm init`).

**Rationale**: APM is a standalone CLI tool (installed via npm/binary). There is no Python SDK — the documented integration pattern is CLI invocation. This matches how dev-stack already shells out to external tools (e.g., `uv` in `uv_project` module, `git` in `vcs_hooks`). We do not use `apm init` because dev-stack needs to seed the manifest with specific default servers and support the merge strategy — writing YAML directly gives full control.

**Key APM commands used**:
| Command | Purpose | When |
|---------|---------|------|
| `apm --version` | Version check (FR-007) | Module `verify()` and pre-install |
| `apm install` | Install all deps from `apm.yml`, generate lockfile | During `install()` and `dev-stack apm install` |
| `apm audit` | Security scan | During `dev-stack apm audit` |
| `apm audit -f json` | Machine-readable security report | JSON output mode |

**Alternatives considered**:
- Python APM SDK: Does not exist. APM is CLI-only.
- Reimplementing APM logic in Python: Defeats the purpose of delegating to APM.
- npm programmatic API: Unnecessary indirection; `subprocess` is simpler and already battle-tested in the codebase.

## R2: APM Manifest (`apm.yml`) Format for MCP Servers

**Decision**: Generate `apm.yml` with `dependencies.mcp` section containing the 5 default servers as registry references.

**Rationale**: APM's documented `apm.yml` format uses `dependencies.mcp` for MCP server declarations. Servers can be referenced by their registry URI (e.g., `ghcr.io/github/github-mcp-server`). No custom YAML schema needed.

**Default apm.yml template**:
```yaml
name: {{ PROJECT_NAME }}
version: 1.0.0
dependencies:
  mcp:
    - ghcr.io/upstash/context7-mcp-server
    - ghcr.io/github/github-mcp-server
    - ghcr.io/modelcontextprotocol/sequentialthinking-server
    - ghcr.io/huggingface/mcp-server
    - ghcr.io/notebooklm/mcp-server
```

**Note**: Exact registry URIs for each server need verification against the live APM MCP registry at implementation time. The spec's 5 defaults (context7, github, sequential-thinking, huggingface, notebooklm) must each have a corresponding registry entry. If any doesn't exist yet, the implementation should use the self-defined server format with explicit command/args as a fallback:
```yaml
    - name: notebooklm
      registry: false
      transport: stdio
      command: npx
      args: ["--yes", "notebooklm-mcp", "start"]
```

**Alternatives considered**:
- Using `dependencies.apm` (for non-MCP packages): Wrong section. MCP servers belong in `dependencies.mcp`.
- Generating raw agent config files directly: This is what `mcp_servers` already does. APM is the replacement.

## R3: APM Lockfile (`apm.lock.yaml`) Handling

**Decision**: Let APM manage the lockfile entirely. Dev-stack only checks for its existence.

**Rationale**: APM automatically generates `apm.lock.yaml` during `apm install`. The lockfile captures resolved commit SHAs, deployed file paths, and version info. Dev-stack should not parse, modify, or generate this file — only check its existence for `verify()` health checks and warn if `apm.yml` was modified after the lock was generated (by comparing file mtimes).

**Lockfile structure** (from APM docs):
```yaml
lockfile_version: "1.0"
generated_at: "2026-01-22T10:30:00Z"
apm_version: "0.8.0"
dependencies:
  owner/package:
    repo_url: "..."
    resolved_commit: "abc123"
    version: "1.0.0"
    deployed_files:
      - .github/copilot-mcp.json
mcp_servers:
  - context7
  - github
```

**Alternatives considered**:
- Parsing lockfile for verification: Over-engineering. The lockfile format may change across APM versions. Existence check + mtime comparison is sufficient.

## R4: Existing `apm.yml` Conflict Resolution (Interactive Prompt)

**Decision**: Use Click's `click.prompt()` with 3 choices — skip, merge, overwrite — when `apm.yml` already exists.

**Rationale**: FR-013 requires an interactive prompt. Click provides `click.prompt(type=click.Choice(['skip', 'merge', 'overwrite']))` which integrates with the existing CLI framework. In non-interactive mode (CI), default to "skip" to preserve safety (Principle IV: Brownfield Safety).

**Merge strategy**: Read existing `apm.yml`, parse `dependencies.mcp` list, additively insert any missing defaults from the template. Preserve all user-added packages. Use PyYAML for round-trip YAML handling.

**Alternatives considered**:
- Always skip (Option A from clarification): Rejected by user — they chose Option C (prompt).
- Always merge silently: Violates Brownfield Safety — user may not want defaults injected.
- Git-style 3-way merge: Over-engineering for a YAML list. Additive insertion is sufficient.

## R5: Deprecation Warning for Legacy `mcp_servers` Module

**Decision**: Add `warnings.warn()` with `DeprecationWarning` in `MCPServersModule.install()` and display via `click.echo()` in CLI output.

**Rationale**: FR-012 requires a visible deprecation notice when the legacy module is explicitly invoked. Python's `warnings` module integrates with test frameworks for assertion, and Click echo ensures visibility in the terminal.

**Warning text**: `"The 'mcp-servers' module is deprecated. Migrate to the 'apm' module: replace 'mcp-servers' with 'apm' in your dev-stack.toml. See: docs/migration-apm.md"`

**Alternatives considered**:
- Raising an exception: Too disruptive — the module must remain functional (FR-011).
- Silent logging only: Not visible enough to drive migration.

## R6: APM CLI Version Checking

**Decision**: Run `apm --version`, parse semver output, compare against `MIN_APM_VERSION` constant in the module.

**Rationale**: FR-007 requires checking APM CLI version meets minimum supported. APM's `--version` flag is documented. Use `packaging.version.Version` (already a dev-stack dependency via setuptools) for safe semver comparison.

**Minimum version**: Set to `0.8.0` initially (the version that supports `apm.lock.yaml` lockfile format version 1.0 and `apm audit`).

**Alternatives considered**:
- Feature detection (try command, check exit code): Fragile — doesn't distinguish "old version" from "missing feature".
- No version check: Spec requires it (FR-007). Users would get cryptic errors from old APM versions.

## R7: Fail-Forward Partial Install Behavior

**Decision**: Parse `apm install` stderr/stdout for per-server success/failure status. Report results in `ModuleResult.warnings`.

**Rationale**: FR-015 requires reporting which servers succeeded/failed on partial install. APM's `apm install` provides output per dependency. The module captures subprocess output, parses it for install status per server, and populates `ModuleResult` accordingly.

**Implementation**: Run `apm install` with `subprocess.run(capture_output=True)`. If exit code is non-zero, parse output for individual server status. Set `ModuleResult.success = False` but populate `files_created` with whatever succeeded. Add failures to `warnings` list.

**Alternatives considered**:
- Installing servers one-by-one in a loop: Slower, loses APM's dependency resolution, and doesn't match how APM is designed to work.
- Rollback on failure: Explicitly rejected in clarification (fail-forward).

## R8: CLI Subcommand Pattern

**Decision**: Create `apm_cmd.py` with Click group `apm` and subcommands `install` and `audit`, following the exact pattern of `mcp_cmd.py`.

**Rationale**: FR-016 requires explicit CLI subcommands. The existing `dev-stack mcp install|verify` pattern in `mcp_cmd.py` is the established convention. The new `dev-stack apm install|audit` should mirror it.

**Commands**:
| Command | Options | Maps to |
|---------|---------|---------|
| `dev-stack apm install` | `--force` | `APMModule.install(force=True)` |
| `dev-stack apm audit` | `--format [text\|json\|sarif\|markdown]`, `--output FILE` | `apm audit -f {format} -o {output}` |

**Alternatives considered**:
- Overloading `dev-stack mcp` with APM support: Confusing — two different backends behind one command.
- No CLI subcommands (init-only): Rejected in clarification — user wants both.
