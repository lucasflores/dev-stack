# Contract: Agent File Creation

**Feature**: 010-proactive-agent-instructions  
**Scope**: Internal module contract — `VcsHooksModule._generate_constitutional_files()`

## Overview

This contract defines the behavior of the proactive agent file creation flow within `_generate_constitutional_files()`. There is no external API surface change — the existing `dev-stack init`, `update`, and `uninstall` CLI commands are the entry points.

## Internal Contract: `_create_agent_file()`

### Signature

```python
def _create_agent_file(
    self,
    created: list[Path],
    modified: list[Path],
    warnings: list[str],
) -> None:
```

### Preconditions

- `self.manifest` contains an `"agent"` key with at least `"cli"` field.
- `self.repo_root` is a valid directory.
- The instructions template exists at `TEMPLATE_DIR / "instructions.md"`.

### Behavior

1. Read `self.manifest["agent"]["cli"]`.
2. If `cli` is `"none"` or not in `AGENT_FILE_MAP`, return (no-op).
3. Resolve the target file path: `self.repo_root / AGENT_FILE_MAP[cli]`.
4. Create parent directories if needed: `target.parent.mkdir(parents=True, exist_ok=True)`.
5. Read instructions template content.
6. Call `markers.write_managed_section(target, "DEV-STACK:INSTRUCTIONS", content)`.
7. If the file was newly created, append `target` to `created`.
8. If the file existed and the section was updated, append `target` to `modified`.
9. On exception, append warning message to `warnings`.

### Postconditions

- If agent is detected: the canonical agent file exists and contains exactly one managed section with the instructions content.
- If no agent is detected: no agent file is created or modified.
- The `created` or `modified` list is updated to reflect the operation.

## Internal Contract: `AGENT_FILE_MAP`

### Definition

```python
AGENT_FILE_MAP: dict[str, str] = {
    "claude": "CLAUDE.md",
    "copilot": ".github/copilot-instructions.md",
    "cursor": ".cursorrules",
}
```

### Invariants

- Keys are a subset of `config.AGENT_PRIORITY`.
- Values are relative paths from repo root.
- No key maps to `AGENTS.md` (excluded by design).

## Internal Contract: Dynamic `MANAGED_FILES`

### Current (static)

```python
MANAGED_FILES: Sequence[str] = (
    ".git/hooks/commit-msg",
    ".git/hooks/pre-push",
    ".dev-stack/hooks-manifest.json",
    ".dev-stack/instructions.md",
    ".specify/templates/constitution-template.md",
    "cliff.toml",
)
```

### New (static — no change to class attribute)

`MANAGED_FILES` remains the same static 6-entry tuple. The agent file is resolved at runtime via `_get_agent_file_path()` and handled explicitly in `_create_agent_file()`, `uninstall()`, and `preview_files()`.

### Invariant

- `MANAGED_FILES` class attribute always returns exactly the 6 base files.
- `getattr(cls, "MANAGED_FILES", ())` on the class (not instance) must return a sequence of strings — this is a contract test requirement.
- The agent file is NOT in `MANAGED_FILES`. Lifecycle methods handle it via `_get_agent_file_path()`.

## Uninstall Contract

### Agent File Cleanup

When `uninstall()` runs:

1. Determine the agent file from `AGENT_FILE_MAP[self.manifest["agent"]["cli"]]`.
2. If the file exists, clear the managed section: `markers.write_managed_section(path, "DEV-STACK:INSTRUCTIONS", "")`.
3. If the file is now empty (`path.read_text().strip() == ""`), delete it and add to `files_deleted`.
4. If the file still has content, add to `files_modified`.

## JSON Output Contract

The `--json` output for `init` includes the agent file in the appropriate list:

```json
{
  "modules": {
    "vcs_hooks": {
      "success": true,
      "message": "VCS hooks installed",
      "files_created": [
        ".git/hooks/commit-msg",
        ".git/hooks/pre-push",
        ".dev-stack/hooks-manifest.json",
        ".dev-stack/instructions.md",
        ".specify/templates/constitution-template.md",
        "cliff.toml",
        "CLAUDE.md"
      ],
      "files_modified": [],
      "warnings": []
    }
  }
}
```
