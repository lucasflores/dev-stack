# Data Model: Version Control Best Practices Automation

**Branch**: `004-vcs-best-practices` | **Date**: 2026-03-08

---

## Entity Relationship Overview

```
VcsHooksModule ──|> ModuleBase
VcsHooksModule 1──1 HookManifest
HookManifest 1──* HookEntry
VcsHooksModule 1──* HookTemplate
ConventionalCommitRule ──|> gitlint.rules.CommitRule
TrailerPresenceRule ──|> gitlint.rules.CommitRule
TrailerPathRule ──|> gitlint.rules.CommitRule
PipelineFailureWarningRule ──|> gitlint.rules.CommitRule
BranchConfig 1──1 VcsConfig
SigningConfig 1──1 VcsConfig
HooksConfig 1──1 VcsConfig
PRDescription 1──* CommitSummary
CommitSummary *──1 TrailerData (existing)
ReleaseContext 1──* CommitSummary
ScopeAdvisory 1──* StagedFilePath
```

---

## New Entities

### VcsHooksModule

Subclass of `ModuleBase`. Manages git hook installation/removal lifecycle, constitutional practices templates, and agent file injection.

| Field / Attr | Type | Value | Description |
|-------------|------|-------|-------------|
| NAME | str | `"vcs_hooks"` | Module identifier in registry |
| VERSION | str | `"0.1.0"` | Initial version |
| DEPENDS_ON | Sequence[str] | `()` | No module dependencies |
| MANAGED_FILES | Sequence[str] | See below | Hook scripts, manifest, templates |

**MANAGED_FILES**:
```python
(
    ".git/hooks/commit-msg",
    ".git/hooks/pre-push",
    ".dev-stack/hooks-manifest.json",
    ".dev-stack/instructions.md",
    "constitution-template.md",
    "cliff.toml",
)
```

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `install` | `(*, force: bool = False) -> ModuleResult` | Installs managed hooks, generates manifest, creates constitutional templates, injects agent instructions |
| `uninstall` | `() -> ModuleResult` | Removes managed hooks (checksum-matching only), clears manifest, removes managed sections from agent files |
| `update` | `() -> ModuleResult` | Re-installs hooks if checksum matches (FR-014a), updates managed sections in agent files |
| `verify` | `() -> ModuleStatus` | Validates hooks exist, checksums match manifest, templates present |

**Internal helpers**:

| Helper | Purpose |
|--------|---------|
| `_install_hook(hook_name: str, template: str, force: bool) -> bool` | Copies hook template to `.git/hooks/`, sets 0o755 permissions, records in manifest |
| `_is_managed_hook(hook_path: Path) -> bool` | Checks for `# managed by dev-stack` header comment |
| `_compute_checksum(path: Path) -> str` | SHA-256 hex digest of file content |
| `_load_manifest() -> HookManifest` | Reads `.dev-stack/hooks-manifest.json` |
| `_save_manifest(manifest: HookManifest) -> None` | Writes `.dev-stack/hooks-manifest.json` |
| `_detect_agent_files(repo_root: Path) -> list[Path]` | Scans for `.github/copilot-instructions.md`, `CLAUDE.md`, `.cursorrules`, `AGENTS.md` |
| `_inject_instructions(file_path: Path, content: str) -> bool` | Uses `write_managed_section()` with `DEV-STACK:INSTRUCTIONS` section ID |
| `_configure_signing(repo_root: Path, config: SigningConfig) -> ModuleResult` | Sets local git config for SSH signing (FR-039–FR-041) |

**Validation rules**:
- Git must be available on PATH
- `.git/` directory must exist at repo root
- Existing non-managed hooks are never overwritten (FR-013)
- SSH signing requires git >= 2.34 (FR-040a)

**State transitions**:
- `not-installed` → `installed` (via `install()`)
- `installed` → `not-installed` (via `uninstall()`)
- `installed` → `installed` (via `update()` — re-installs matching hooks)

---

### HookManifest

JSON ledger tracking all managed hooks. Stored at `.dev-stack/hooks-manifest.json`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | str | yes | Manifest schema version (e.g., `"1.0"`) |
| created | str (ISO 8601) | yes | When manifest was first created |
| updated | str (ISO 8601) | yes | When manifest was last modified |
| hooks | dict[str, HookEntry] | yes | Map of hook name → entry |

**JSON schema**:
```json
{
  "version": "1.0",
  "created": "2026-03-08T12:00:00Z",
  "updated": "2026-03-08T12:00:00Z",
  "hooks": {
    "commit-msg": {
      "checksum": "a1b2c3d4e5f6...",
      "installed_at": "2026-03-08T12:00:00Z",
      "template_version": "0.1.0"
    },
    "pre-push": {
      "checksum": "f6e5d4c3b2a1...",
      "installed_at": "2026-03-08T12:00:00Z",
      "template_version": "0.1.0"
    }
  }
}
```

**Validation rules**:
- `version` must be a recognized schema version
- Each hook entry in `hooks` must have a valid checksum and timestamp
- Hook names must be valid git hook names

---

### HookEntry

A single managed hook record within the manifest.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| checksum | str | yes | SHA-256 hex digest of the installed hook file |
| installed_at | str (ISO 8601) | yes | Timestamp of installation |
| template_version | str | yes | Version of the hook template used |

**Usage**:
- Compared against current file checksum to detect manual modifications
- If `current_checksum == manifest_checksum`: hook is unmodified → safe to update/remove
- If `current_checksum != manifest_checksum`: hook was manually edited → skip with warning

---

### HookTemplate

Template for a thin Python hook wrapper installed to `.git/hooks/`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| hook_name | str | yes | Git hook name (`commit-msg`, `pre-push`, `pre-commit`) |
| shebang | str | yes | Always `#!/usr/bin/env python3` |
| header | str | yes | `# managed by dev-stack — do not edit manually` |
| import_target | str | yes | Python module path to import (e.g., `dev_stack.rules`) |

**commit-msg template structure**:
```python
#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Validate commit messages against conventional commit format and trailer rules."""
import sys
from dev_stack.vcs.hooks_runner import run_commit_msg_hook

sys.exit(run_commit_msg_hook(sys.argv[1]))
```

**pre-push template structure**:
```python
#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Validate branch names and optionally enforce signed commits at push time."""
import sys
from dev_stack.vcs.hooks_runner import run_pre_push_hook

sys.exit(run_pre_push_hook(sys.stdin))
```

---

### VcsConfig

Configuration read from `pyproject.toml` under `[tool.dev-stack.*]`. Aggregates all VCS-related settings.

| Section | Type | Description |
|---------|------|-------------|
| hooks | HooksConfig | Which hooks to install |
| branch | BranchConfig | Branch naming rules |
| signing | SigningConfig | SSH signing settings |

**pyproject.toml location**: `[tool.dev-stack]`

---

### HooksConfig

Configuration for which git hooks to install.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| commit-msg | bool | `true` | Install commit-msg hook |
| pre-push | bool | `true` | Install pre-push hook |
| pre-commit | bool | `false` | Install pre-commit hook (runs lint + typecheck stages) |

**pyproject.toml example**:
```toml
[tool.dev-stack.hooks]
commit-msg = true
pre-push = true
pre-commit = false
```

---

### BranchConfig

Configuration for branch naming enforcement.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| pattern | str | `"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)/[a-z0-9._-]+$"` | Regex pattern for valid branch names |
| exempt | list[str] | `["main", "master", "develop", "staging", "production"]` | Branch names exempt from validation |

**pyproject.toml example**:
```toml
[tool.dev-stack.branch]
pattern = "^(feat|fix|docs|chore)/[a-z0-9._-]+$"
exempt = ["main", "master", "develop"]
```

**Validation rules**:
- `pattern` must be a valid Python regex (compiled at load time)
- `exempt` entries are matched exactly (not as regex)
- Enforcement applies only at push time (FR-009)

---

### SigningConfig

Configuration for SSH commit signing.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| enabled | bool | `false` | Whether SSH signing is configured |
| enforcement | str | `"warn"` | `"warn"` or `"block"` for unsigned agent commits at push time |
| key | str or None | `None` | Path to SSH public key; auto-detected if omitted |

**pyproject.toml example**:
```toml
[tool.dev-stack.signing]
enabled = true
enforcement = "warn"
# key = "~/.ssh/id_ed25519.pub"  # optional: auto-detected if omitted
```

**Validation rules**:
- `enforcement` must be one of `"warn"` or `"block"`
- If `key` is specified, the path must exist and be a `.pub` file
- SSH signing requires git >= 2.34 (checked at install time, not config load)

---

### ConventionalCommitRule

Custom gitlint rule validating commit message subject format. Extends `gitlint.rules.CommitRule`.

| Field | Type | Description |
|-------|------|-------------|
| name | str | `"dev-stack-conventional-commit"` |
| id | str | `"UC1"` (User Commit rule 1) |
| TYPES | tuple[str, ...] | `("feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert")` |
| PATTERN | re.Pattern | `r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_-]+\))?: .{1,72}$"` |

**Method**: `validate(commit: gitlint.Commit) -> list[RuleViolation]`
- Validates subject matches PATTERN
- Returns `RuleViolation` with actionable error message on failure

---

### TrailerPresenceRule

Custom gitlint rule requiring trailers on agent-generated commits. Extends `gitlint.rules.CommitRule`.

| Field | Type | Description |
|-------|------|-------------|
| name | str | `"dev-stack-trailer-presence"` |
| id | str | `"UC2"` |
| REQUIRED_TRAILERS | tuple[str, ...] | `("Spec-Ref", "Task-Ref", "Agent", "Pipeline", "Edited")` |

**Method**: `validate(commit: gitlint.Commit) -> list[RuleViolation]`
- If commit body contains `Agent:` trailer → require all REQUIRED_TRAILERS
- If no `Agent:` trailer → skip (manual commits don't need trailers)
- Returns one `RuleViolation` per missing trailer

---

### TrailerPathRule

Custom gitlint rule validating that `Spec-Ref` and `Task-Ref` trailer values reference existing paths. Extends `gitlint.rules.CommitRule`.

| Field | Type | Description |
|-------|------|-------------|
| name | str | `"dev-stack-trailer-path"` |
| id | str | `"UC3"` |
| PATH_TRAILERS | tuple[str, ...] | `("Spec-Ref", "Task-Ref")` |

**Method**: `validate(commit: gitlint.Commit) -> list[RuleViolation]`
- For each PATH_TRAILER present: check if the referenced path exists relative to repo root
- Returns `RuleViolation` for each non-existent path

**Context requirement**: Needs repo root path. Passed via gitlint's `extra-path` mechanism or `LintConfig` options.

---

### PipelineFailureWarningRule

Custom gitlint rule emitting warnings for `=fail` entries in the `Pipeline` trailer. Extends `gitlint.rules.CommitRule`.

| Field | Type | Description |
|-------|------|-------------|
| name | str | `"dev-stack-pipeline-warning"` |
| id | str | `"UC4"` |

**Method**: `validate(commit: gitlint.Commit) -> list[RuleViolation]`
- Parses `Pipeline:` trailer value (comma-separated `key=value` pairs)
- Emits a warning-level `RuleViolation` for each `=fail` entry
- Non-blocking (FR-004)

---

### PRDescription

Aggregated PR description generated from branch commits.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | str | yes | PR title (from branch name or first commit) |
| summary | str | yes | Multi-line summary of changes |
| spec_refs | list[str] | no | Unique `Spec-Ref` values across all commits |
| task_refs | list[str] | no | Unique `Task-Ref` values across all commits |
| agents | list[str] | no | Unique `Agent` values |
| pipeline_status | dict[str, str] | no | Aggregated pipeline results (stage → worst status) |
| edited_count | int | yes | Number of commits with `Edited: true` |
| total_commits | int | yes | Total commits in the branch |
| ai_commits | int | yes | Commits with `Agent` trailer |
| commits | list[CommitSummary] | yes | Per-commit summaries |

**Rendering**: Uses Jinja2-style Markdown template at `src/dev_stack/templates/pr-template.md`.

---

### CommitSummary

Parsed representation of a single commit for PR/changelog/release aggregation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| sha | str | yes | Full commit hash |
| short_sha | str | yes | First 7 characters of hash |
| subject | str | yes | First line of commit message |
| type | str | yes | Conventional commit type (parsed from subject) |
| scope | str or None | no | Conventional commit scope |
| description | str | yes | Conventional commit description (after `: `) |
| trailers | dict[str, str] | no | Parsed trailers (key → value) |
| is_breaking | bool | yes | Contains `BREAKING CHANGE` footer |
| is_ai_authored | bool | yes | Has `Agent` trailer |
| is_human_edited | bool | yes | Has `Edited: true` trailer |
| is_signed | bool | yes | Commit has valid signature |

**Derivation rules**:
- `type`, `scope`, `description` parsed from subject via regex
- `is_breaking` = `True` if body contains `BREAKING CHANGE:` or subject contains `!` after type
- `is_ai_authored` = `True` if `Agent` key exists in trailers
- `is_human_edited` = `True` if `Edited` trailer value is `true`
- `is_signed` = `True` if `git log --pretty=format:%G? -1 <sha>` returns `G`

---

### ReleaseContext

Context gathered for a semantic release operation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| current_version | str | yes | Current version from `pyproject.toml` |
| next_version | str | yes | Inferred next version |
| bump_type | str | yes | `"major"`, `"minor"`, or `"patch"` |
| commits | list[CommitSummary] | yes | All commits since last tag |
| has_breaking | bool | yes | Any commit is breaking |
| hard_failures | list[str] | no | Commit SHAs with hard pipeline failures |
| tag_name | str | yes | `v{next_version}` |

**Version inference rules** (FR-033):
- Any `BREAKING CHANGE` → major bump
- Any `feat` type → minor bump (if no breaking)
- Only `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` → patch bump
- `--bump` flag overrides inference

**Release gate** (FR-036):
- If `hard_failures` is non-empty → refuse to release
- Hard failure = any `Pipeline` trailer entry where the stage has `FailureMode.HARD` and value is `fail`
- Hard stages: `lint`, `typecheck`, `test`, `security`, `docs-api`

---

### ScopeAdvisory

Result of the scope heuristic check during the commit-message pipeline stage.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| triggered | bool | yes | Whether the advisory was triggered |
| reason | str or None | no | Human-readable explanation |
| root_dirs_touched | list[str] | yes | Repo-root directories in staged files |
| subpackages_touched | list[str] | yes | Source subpackages in staged files |
| rule_triggered | str or None | no | Which rule fired: `"root_dirs"`, `"subpackages"`, `"specs_and_src"` |

**Trigger rules** (FR-044, FR-045):
1. `root_dirs` — staged files touch >= 3 repo-root directories (e.g., `src/`, `tests/`, `specs/`)
2. `subpackages` — staged files touch >= 3 source subpackages (e.g., `cli/`, `modules/`, `pipeline/`)
3. `specs_and_src` — staged files include both `specs/` and `src/` changes

**Pipeline integration**:
- If `triggered` is `True`: append `scope-check=warn` to `Pipeline` trailer
- Never blocks the commit (FR-046)

---

### ChangelogConfig

Configuration for git-cliff rendering. Stored as `cliff.toml` at repo root.

| Field | Type | Description |
|-------|------|-------------|
| changelog.header | str | Changelog file header text |
| changelog.body | str | Tera template for rendering commit groups |
| changelog.footer | str | Footer text |
| git.conventional_commits | bool | Always `true` |
| git.commit_parsers | list[dict] | Maps commit types to changelog groups |
| git.filter_commits | bool | Whether to filter non-conventional commits |

**Template features** (from research):
- Groups commits by type (`feat` → "Features", `fix` → "Bug Fixes", etc.)
- Annotates AI-authored commits with 🤖 marker (from `Agent` trailer via `commit.footers`)
- Annotates human-edited commits with ✏️ marker (from `Edited: true` footer)
- Links to specs when `Spec-Ref` footer is present

**Commit parsers**:
```toml
[git]
conventional_commits = true
commit_parsers = [
    { message = "^feat", group = "Features" },
    { message = "^fix", group = "Bug Fixes" },
    { message = "^docs", group = "Documentation" },
    { message = "^perf", group = "Performance" },
    { message = "^refactor", group = "Refactoring" },
    { message = "^style", group = "Styling" },
    { message = "^test", group = "Testing" },
    { message = "^build", group = "Build" },
    { message = "^ci", group = "CI" },
    { message = "^chore", skip = true },
    { message = "^revert", group = "Reverted" },
]
```

---

### ConstitutionTemplate

Markdown template generated during `dev-stack init` for spec-kit users.

| Section | Required | Editable | Description |
|---------|----------|----------|-------------|
| Dev-Stack Baseline Practices | yes | no | Non-removable section header |
| Atomic Commits | yes | no | Defines logical unit of work; smallest set implementing single task with passing tests |
| Test-Driven Development | yes | no | Red-Green-Refactor cycle: failing test → minimal pass → refactor |
| User-Defined Requirements | yes | yes | Empty section for user customization |

**File path**: `constitution-template.md` (repo root)

---

### AgentInstructionsFile

Generated instructions file for non-spec-kit workflows.

| Field | Type | Description |
|-------|------|-------------|
| path | str | `.dev-stack/instructions.md` |
| content | str | Same atomic commit + TDD clauses as ConstitutionTemplate |
| managed_section_id | str | `DEV-STACK:INSTRUCTIONS` |

**Agent file injection targets** (FR-019):
- `.github/copilot-instructions.md` — GitHub Copilot
- `CLAUDE.md` — Claude Code
- `.cursorrules` — Cursor
- `AGENTS.md` — Generic agent instructions

**Injection method**: `write_managed_section()` from `brownfield/markers.py` with markers:
```markdown
<!-- === DEV-STACK:INSTRUCTIONS:BEGIN === -->
[atomic commit + TDD content]
<!-- === DEV-STACK:INSTRUCTIONS:END === -->
```

---

## Modified Entities

### PipelineStage (stage 8 — commit-message)

The `_execute_commit_stage()` function in `pipeline/stages.py` is extended to include the scope advisory check before generating the commit message.

**New behavior in `_execute_commit_stage()`**:
1. (Existing) Read staged diff and file list
2. **NEW**: Run `ScopeAdvisory` check against staged files
3. **NEW**: If advisory triggered, include `scope-check=warn` in pipeline results
4. (Existing) Invoke agent for commit message generation
5. (Existing) Upsert trailers via `commit_format.upsert_trailers()`

**No changes to**: `PipelineStage` dataclass, `build_pipeline_stages()`, other stage executors, `TrailerData`, `TRAILER_ORDER`.

### Module Registry (`modules/__init__.py`)

**New registration**:
```python
from dev_stack.modules.vcs_hooks import VcsHooksModule
register_module(VcsHooksModule)
```

**Updated DEFAULT_GREENFIELD_MODULES**:
```python
DEFAULT_GREENFIELD_MODULES = ("uv_project", "sphinx_docs", "hooks", "vcs_hooks", "speckit")
```

**Module resolution order** (updated):
```
1. uv_project     (no deps)
2. sphinx_docs    (depends on: uv_project)
3. hooks          (no deps)
4. vcs_hooks      (no deps)
5. speckit        (no deps)
6. ci-workflows   (no deps)
7. docker         (no deps)
8. mcp-servers    (no deps)
9. visualization  (depends on: hooks)
```
