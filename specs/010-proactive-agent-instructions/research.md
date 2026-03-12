# Research: Proactive Agent Instruction File Creation

**Feature**: 010-proactive-agent-instructions  
**Date**: 2025-03-11  
**Status**: Complete — all unknowns resolved

## Research Tasks

### R1: How does VcsHooksModule access the detected agent at install time?

**Decision**: Use `self.manifest["agent"]["cli"]` to read the detected agent CLI name.

**Rationale**: The init flow in `init_cmd.py` (line 81) calls `detect_agent(manifest)`, stores the result in `manifest.agent = AgentConfig(cli=..., path=...)`, then passes `manifest.to_dict()` to module constructors. The `to_dict()` output includes `"agent": {"cli": "claude", "path": "/usr/local/bin/claude", "detected_at": "..."}`. All modules receive this dict as `self.manifest`. No new plumbing needed.

**Alternatives considered**:
- Pass `AgentInfo` as a separate argument to `_generate_constitutional_files()` — rejected because the manifest already carries this data and adding parameters changes the existing call signature.
- Call `detect_agent()` again inside the module — rejected because it would duplicate detection logic and could return a different result if environment changes between init and module install.

---

### R2: What is the correct agent-to-file mapping?

**Decision**: Maintain a constant mapping dict inside `VcsHooksModule`:

```python
AGENT_FILE_MAP: dict[str, str] = {
    "claude": "CLAUDE.md",
    "copilot": ".github/copilot-instructions.md",
    "cursor": ".cursorrules",
}
```

**Rationale**: The mapping is already implicit in `_detect_agent_files()` (which lists the same 3 files plus `AGENTS.md`). Making it an explicit `dict` keyed by agent CLI name enables both proactive creation and reverse lookup. `AGENTS.md` is excluded because it's an agent definition file, not a general instructions file.

**Alternatives considered**:
- Store the mapping in `config.py` alongside `AGENT_PRIORITY` — rejected because the mapping is module-specific (only `vcs_hooks` writes these files), not a global config concern.
- Use a more dynamic approach (e.g., agent plugins) — rejected as over-engineering for 3 static mappings.

---

### R3: How should `write_managed_section()` behave when the file doesn't exist?

**Decision**: Use `markers.write_managed_section()` as-is — it already handles file creation.

**Rationale**: Reading `markers.py` lines 42-45, when the file doesn't exist, `write_managed_section()` creates it with the managed block as content. For copilot's `.github/` directory, the parent directory must be created first via `file_path.parent.mkdir(parents=True, exist_ok=True)` before calling the marker function.

**Alternatives considered**:
- Create the file first with `Path.write_text()` then inject — rejected because `write_managed_section()` already handles creation atomically in one step.

---

### R4: How should MANAGED_FILES handle dynamically created agent files?

**Decision**: Keep `MANAGED_FILES` as a static class-level tuple (base files only). Handle the dynamic agent file via a separate `_get_agent_file_path()` instance method. Lifecycle methods (`update()`, `uninstall()`, `preview_files()`) reference the agent file through this helper rather than through `MANAGED_FILES`.

**Rationale**: `MANAGED_FILES` is currently a class-level `Sequence[str]` tuple accessed by `tests/contract/test_module_interface.py` via `getattr(cls, "MANAGED_FILES", ())` on the class (not an instance). Converting to `@property` would break this contract test since properties only resolve on instances. Keeping the static tuple intact and using a separate instance method preserves backward compatibility while still giving lifecycle methods access to the correct agent file path at runtime.

**Alternatives considered**:
- Convert `MANAGED_FILES` to a `@property` — rejected because the contract test in `test_module_interface.py` accesses it as a class attribute via `getattr(cls, "MANAGED_FILES", ())`, which doesn't trigger `@property`.
- Add all 3 agent files to `MANAGED_FILES` statically — rejected because `verify()` would report spurious "missing file" errors for agent files that shouldn't exist (only 1 of 3 is created).
- Track the created agent file in the manifest — rejected as unnecessary indirection when the manifest already contains the agent CLI, and the mapping is deterministic.

---

### R5: How should uninstall handle agent files it created vs. user-existing files?

**Decision**: On uninstall, always remove the managed section via `write_managed_section(path, section_id, "")`. If the file is then empty (whitespace-only), delete it. If it has other content, leave it.

**Rationale**: This matches the pattern used in existing `uninstall()` code (line 232-237) where `_detect_agent_files()` iterates and clears sections. The new wrinkle is that proactively created files should be deleted when empty. The emptiness check is `path.read_text().strip() == ""`.

**Alternatives considered**:
- Track a "created_by_devstack" flag per file — rejected as unnecessary state. The emptiness heuristic is sufficient and simpler.
- Always delete the file on uninstall — rejected because users may have added their own content after init.

---

### R6: How should update handle agent file refresh?

**Decision**: `update()` does NOT currently call `_generate_constitutional_files()` — it only updates hooks. A call to `_create_agent_file()` (or a broader call to `_generate_constitutional_files()`) must be wired into `update()` so the managed section is refreshed when the instructions template changes. Once wired, the re-injection is idempotent via `write_managed_section()`.

**Rationale**: `write_managed_section()` replaces existing sections in place (markers.py lines 46-50). Calling it again with updated content is the update mechanism. However, `update()` currently only handles hooks (checksum comparison + template re-write). The `_generate_constitutional_files()` call chain exists only in `install()`. Task T014 addresses this gap.

**Alternatives considered**:
- Call `_generate_constitutional_files()` from `update()` — viable but may have unintended side effects (re-generates constitution files on every update). Preferred approach: call only `_create_agent_file()` from `update()` to limit scope to agent file refresh.

---

### R7: Existing test patterns for agent mocking

**Decision**: Use `monkeypatch` and `tmp_path` fixtures to create isolated test repos with controlled agent manifests.

**Rationale**: `tests/unit/test_config.py` already demonstrates the pattern: `monkeypatch.setenv("DEV_STACK_AGENT", "claude")` for env-var testing, and `tmp_path / "dev-stack.toml"` for manifest-based testing. `tests/unit/test_vcs_hooks_module.py` creates `VcsHooksModule(tmp_path, manifest_dict)` with fixture manifests.

**Alternatives considered**: None — the existing patterns are well-established.
