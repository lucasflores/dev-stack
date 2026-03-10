# Data Model: Init Onboarding Fixes

**Feature**: 007-init-onboarding-fixes  
**Date**: 2026-03-10

---

## Entity: FileConflict

Represents a file that init would create or overwrite.

| Field | Type | Description |
|-------|------|-------------|
| `path` | `Path` | Absolute path to the conflicting file |
| `current_hash` | `str \| None` | SHA-256 of existing file on disk; `None` if file is new |
| `expected_hash` | `str \| None` | SHA-256 of the file dev-stack would write |
| `resolution` | `str` | One of: `"pending"`, `"greenfield_predecessor"`, `"accepted"`, `"skipped"`, `"merged"`, `"overwritten"` |

**Resolution states** (state machine):

```
pending ──┬── greenfield_predecessor  (auto-resolved by predecessor detection)
           ├── accepted               (user accepted overwrite)
           ├── skipped                 (user chose to skip)
           ├── merged                  (user merged content)
           └── overwritten             (--force applied)
```

**Changed behavior** (FR-005):
- `has_existing_conflicts()` now filters on `resolution == "pending"` — only unresolved conflicts block init.

---

## Entity: ConflictReport

Collection of file conflicts for a single init run.

| Field | Type | Description |
|-------|------|-------------|
| `conflicts` | `list[FileConflict]` | All detected file conflicts |
| `all_resolved` | `bool` (property) | `True` if no conflict has `resolution == "pending"` |

**Invariant**: After predecessor detection, `all_resolved` can return `True` even when `len(conflicts) > 0`.

---

## Entity: AgentInfo

Result of agent detection.

| Field | Type | Description |
|-------|------|-------------|
| `cli` | `str` | Agent CLI identifier: `"claude"`, `"copilot"`, `"cursor"`, or `"none"` |
| `path` | `str \| None` | Filesystem path to the agent binary; `None` when `cli == "none"` |

**Changed behavior** (FR-006):
- When `DEV_STACK_AGENT=none`, detection short-circuits to `AgentInfo(cli="none", path=None)` without resolving binaries.

---

## Entity: Secrets Baseline (`.secrets.baseline`)

JSON file managed by `detect-secrets`.

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | `str` | ISO timestamp of generation |
| `plugins_used` | `list[dict]` | Active detection plugins |
| `filters_used` | `list[dict]` | Active filters including `--exclude-files` patterns |
| `results` | `dict[str, list[Finding]]` | Map of file path → list of findings |

**Finding** (nested):

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Plugin that detected it (e.g., `"Hex High Entropy String"`) |
| `hashed_secret` | `str` | SHA-1 of the detected secret value |
| `is_secret` | `bool \| absent` | Audit status: `true` (confirmed), `false` (false positive), or absent (unaudited) |
| `line_number` | `int` | Line where finding was detected |

**Changed behavior** (FR-001/FR-002):
- `filters_used` now includes `--exclude-files` pattern `\.dev-stack/|\.secrets\.baseline`.
- `results` will never contain keys matching `.dev-stack/*` or `.secrets.baseline`.

---

## Entity: Init Mode

Classification string stored in `dev-stack.toml`.

| Value | Condition |
|-------|-----------|
| `"greenfield"` | Not previously initialized AND no pending conflicts (predecessors don't count) |
| `"brownfield"` | Not previously initialized AND has pending conflicts |
| `"reinit"` | Already initialized (manifest exists) |

**Changed behavior** (FR-012):
- `_determine_mode()` receives `has_conflicts=False` when all conflicts are resolved as `greenfield_predecessor`, resulting in `"greenfield"` instead of `"brownfield"`.

---

## Entity: Constitution Template

Managed markdown file for project governance practices.

| Attribute | Value |
|-----------|-------|
| Location | `.specify/templates/constitution-template.md` |
| Content source | `src/dev_stack/templates/constitution-template.md` (baseline practices) |
| Injection method | Append managed content to speckit scaffold template |
| Condition | Only when speckit module is installed (`.specify/templates/` directory exists) |

**Changed behavior** (FR-009/FR-010):
- No longer placed at repo root.
- Content injected into speckit's template, not as standalone file.
- Skipped entirely when speckit is not installed.

---

## Relationships

```
ConflictReport 1──* FileConflict
    └── has_existing_conflicts() filters on resolution=="pending"
    └── _determine_mode() uses filtered result

AgentInfo
    └── detect_agent() short-circuits on DEV_STACK_AGENT=none

Secrets Baseline
    └── _generate_secrets_baseline() creates with --exclude-files
    └── _execute_security_stage() updates with --exclude-files
    └── has_unaudited_secrets() evaluates findings

Constitution Template
    └── vcs_hooks._generate_constitutional_files() injects into speckit template
    └── speckit.install() creates the scaffold first (reordered)
```
