# Implementation Plan: Proactive Agent Instruction File Creation

**Branch**: `010-proactive-agent-instructions` | **Date**: 2025-03-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-proactive-agent-instructions/spec.md`

## Summary

When `dev-stack init` detects a coding agent (Claude, Copilot, or Cursor), it should proactively create the agent's canonical instruction file (`CLAUDE.md`, `.github/copilot-instructions.md`, or `.cursorrules`) and inject dev-stack's constitutional clauses via managed section markers. Today the instructions template is written to `.dev-stack/instructions.md` but never wired into agent-discoverable files on greenfield repos. The fix adds a new `_create_agent_file()` method to `VcsHooksModule` and calls it from `_generate_constitutional_files()` using the detected agent CLI from `self.manifest["agent"]["cli"]`.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Click (CLI), tomli/tomli-w (TOML), pathlib (filesystem)  
**Storage**: Filesystem — repo-local files managed by brownfield markers  
**Testing**: pytest (unit + integration), monkeypatch for filesystem isolation  
**Target Platform**: macOS, Linux (developer workstations)  
**Project Type**: Single Python package (`src/dev_stack/`)  
**Performance Goals**: N/A — file I/O only, <100ms for the new code path  
**Constraints**: Must not break existing brownfield injection (FR-019)  
**Scale/Scope**: 3 agent types, 1 new file created per init

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. CLI-First Interface** | PASS | No new CLI commands. Existing `init`, `update`, `--dry-run`, `--json` flags handle the new behavior. Agent file path reported in JSON output (FR-006, FR-012). |
| **II. Spec-Driven Development** | PASS | This plan is derived from spec 010. All FRs traced to acceptance scenarios. |
| **III. Automation by Default** | PASS | Agent file creation is fully automatic — no manual steps. Idempotent via managed section markers. |
| **IV. Brownfield Safety** | PASS | Existing files are never overwritten; managed sections are injected (FR-004). New files are only created when absent. Rollback via existing tag mechanism. |
| **V. AI-Native Architecture** | PASS | This feature directly improves AI agent discoverability by creating files agents auto-read. Uses existing MCP/agent detection infrastructure. |
| **VI. Local-First Execution** | PASS | All operations are local file writes. No cloud dependencies. |
| **VII. Observability & Documentation** | PASS | Created files reported in `files_created` list and `--json` output. Dry-run previews the file. |
| **VIII. Modularity & Composability** | PASS | Changes are scoped entirely to `VcsHooksModule`. No cross-module dependencies introduced. Module lifecycle (install/update/uninstall/verify) all handle the new file. |

**Gate result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/010-proactive-agent-instructions/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── agent-file-contract.md
└── tasks.md             # Phase 2 output (not created by /speckit.plan)
```

### Source Code (repository root)

```text
src/dev_stack/
├── config.py                      # detect_agent(), AgentInfo, AGENT_PRIORITY — READ ONLY
├── manifest.py                    # AgentConfig, StackManifest.to_dict() — READ ONLY
├── brownfield/
│   └── markers.py                 # write_managed_section() — READ ONLY
├── modules/
│   ├── base.py                    # ModuleBase, ModuleResult — READ ONLY
│   └── vcs_hooks.py               # MODIFIED: _create_agent_file(), _generate_constitutional_files(),
│                                  #   _get_agent_file_path(), uninstall() cleanup
└── templates/
    └── instructions.md            # Template content — READ ONLY

tests/
├── unit/
│   ├── test_vcs_hooks_module.py   # MODIFIED: add tests for proactive agent file creation
│   └── test_markers.py            # READ ONLY — existing marker tests
└── integration/
    └── test_hooks_lifecycle.py    # MODIFIED: add integration test for greenfield + agent
```

**Structure Decision**: Single-project layout. All changes are within the existing `vcs_hooks` module. No new modules or directories needed.

## Complexity Tracking

> No constitution violations. No complexity justifications needed.
