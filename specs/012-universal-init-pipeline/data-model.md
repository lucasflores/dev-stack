# Data Model: Universal Init Pipeline

**Feature**: 012-universal-init-pipeline  
**Date**: 2026-03-24

## New Entities

### StackProfile

Characterizes the target repository's language stack. Used by modules to adapt their output.

```python
@dataclass(frozen=True, slots=True)
class StackProfile:
    """Characterization of a repository's language/tooling stack."""
    has_python: bool          # True if any *.py file found in repo
    # Future extensibility: has_javascript, has_rust, etc.
```

**Location**: `src/dev_stack/config.py`

**Relationships**:
- Consumed by `HooksModule.install()` to decide which hooks to generate
- Produced by `detect_stack_profile(repo_root)` function
- Passed through `init_command` → `HooksModule`

**Validation**:
- `has_python` is derived from filesystem scan; not user-configurable
- Immutable (frozen dataclass) — computed once per init invocation

### HookEntry

Represents a single hook in the generated `.pre-commit-config.yaml`.

```python
@dataclass(frozen=True, slots=True)
class HookEntry:
    """A single pre-commit hook definition."""
    id: str               # e.g., "dev-stack-pipeline"
    name: str             # Human-readable name
    entry: str            # Command to execute
    language: str         # Always "system" for dev-stack hooks
    pass_filenames: bool  # Whether filenames are passed to the command
    types: list[str] | None = None   # File type filter (e.g., ["python"])
    stages: list[str] | None = None  # Hook stages (e.g., ["commit"])
```

**Location**: `src/dev_stack/modules/hooks.py`

**Relationships**:
- Assembled by `HooksModule._build_hook_list(profile: StackProfile)`
- Rendered into YAML string for `.pre-commit-config.yaml`

## Modified Entities

### AgentConfig (manifest.py)

**Current state**:
```python
@dataclass
class AgentConfig:
    cli: str = "none"
    path: str | None = None        # ← REMOVE from serialization
    detected_at: datetime = ...
```

**New state** — serialization change only:
```python
class AgentConfig:
    cli: str = "none"
    path: str | None = None        # Kept as transient runtime field
    detected_at: datetime = ...

    def to_dict(self) -> dict[str, Any]:
        # CHANGED: no longer includes 'path'
        return {
            "cli": self.cli,
            "detected_at": self.detected_at.strftime(ISO_FORMAT),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentConfig":
        # Backward compat: ignores 'path' if present in old manifests
        return cls(
            cli=data.get("cli", "none"),
            path=None,  # Never read from disk
            detected_at=...
        )
```

**Impact**: Existing `dev-stack.toml` files with `path` field will have it silently dropped on next `dev-stack init --force`.

### HooksModule (modules/hooks.py)

**Current state**: Copies static `pre-commit-config.yaml` template containing Python hooks.

**New state**: 
- Constructor accepts optional `StackProfile` 
- `install()` detects stack profile and generates conditional hook config
- `_build_hook_list(profile)` returns base hooks + conditional Python hooks
- `_render_pre_commit_config(hooks)` generates YAML string
- Uses managed section markers for brownfield safety (FR-012)

### init_command (cli/init_cmd.py)

**Changes**:
1. `uv sync` call guarded by `"uv_project" in module_names`
2. `_generate_secrets_baseline()` removed (or guarded by secrets module check)
3. New call to `_ensure_gitignore_managed_section(repo_root)` after module install
4. `manifest.agent = AgentConfig(cli=agent_info.cli)` — no `path=` kwarg

## Entity Relationship Diagram

```
┌─────────────────────┐     produces      ┌──────────────────┐
│  detect_stack_      │──────────────────→│  StackProfile     │
│  profile()          │                   │  - has_python     │
└─────────────────────┘                   └────────┬─────────┘
                                                   │ consumed by
                                                   ▼
┌─────────────────────┐                   ┌──────────────────┐
│   init_command()    │──── instantiates ─→│  HooksModule     │
│   - gate uv sync   │                   │  - install()     │
│   - gate secrets   │                   │  - _build_hooks()│
│   - gitignore mgmt │                   └──────────────────┘
└─────────┬───────────┘                            │
          │ writes                                  │ generates
          ▼                                        ▼
┌─────────────────────┐                   ┌──────────────────┐
│  dev-stack.toml     │                   │ .pre-commit-     │
│  (AgentConfig:      │                   │  config.yaml     │
│   cli only, no path)│                   │  (stack-aware)   │
└─────────────────────┘                   └──────────────────┘

┌─────────────────────┐     validates     ┌──────────────────┐
│  commit-msg hook    │──────────────────→│ BodySectionRule  │
│  (gitlint runner)   │                   │  UC5             │
└─────────────────────┘                   │ - agent only     │
                                          │ - 4 sections req │
                                          └──────────────────┘
```

## State Transitions

### .pre-commit-config.yaml Generation

```
Repo scan → StackProfile(has_python=True/False)
    │
    ├─ has_python=True  → base hooks + Python hooks (ruff, pytest, mypy)
    │
    └─ has_python=False → base hooks only (dev-stack-pipeline)
```

### Agent Commit Validation (commit-msg hook)

```
Commit message received
    │
    ├─ Has Agent: trailer → Check ## Intent, ## Reasoning, ## Scope, ## Narrative
    │   ├─ All present → PASS
    │   └─ Missing any → REJECT with list of missing sections
    │
    └─ No Agent: trailer (human) → PASS (no body section enforcement)
```
