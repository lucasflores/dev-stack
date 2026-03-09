# CLI Contract: VCS Best Practices Commands

**Branch**: `004-vcs-best-practices` | **Date**: 2026-03-08

---

## Global Conventions

All new commands follow existing dev-stack CLI conventions:

- `--json` flag for machine-readable JSON output
- `--verbose` flag for debug-level logging
- `--dry-run` flag where applicable
- Exit codes follow POSIX conventions (see existing CLI contract, spec 001)
- Human output to stdout; diagnostics to stderr
- Colors auto-disabled when stdout is not a TTY

### Additional Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (invalid commit message, missing tool, etc.) |
| 2 | Invalid arguments or usage |
| 6 | Release gate failure (hard pipeline failures in commit range) |
| 7 | Branch naming violation (pre-push rejection) |

---

## Commands

### `dev-stack hooks status [--json] [--verbose]`

Show the status of all managed git hooks.

**Behavior**:
1. Load `.dev-stack/hooks-manifest.json`
2. For each hook in manifest:
   a. Check if file exists at `.git/hooks/<name>`
   b. Compute current file checksum
   c. Compare against manifest checksum
   d. Report: installed, expected checksum, actual checksum, modified status
3. Report hooks configured but not installed (from pyproject.toml config)

**JSON output schema** (`--json`):
```json
{
  "status": "healthy" | "degraded" | "not_installed",
  "manifest_path": ".dev-stack/hooks-manifest.json",
  "hooks": [
    {
      "name": "commit-msg",
      "installed": true,
      "path": ".git/hooks/commit-msg",
      "checksum_expected": "a1b2c3d4e5f6...",
      "checksum_actual": "a1b2c3d4e5f6...",
      "modified": false,
      "installed_at": "2026-03-08T12:00:00Z",
      "template_version": "0.1.0"
    },
    {
      "name": "pre-push",
      "installed": true,
      "path": ".git/hooks/pre-push",
      "checksum_expected": "f6e5d4c3b2a1...",
      "checksum_actual": "deadbeef1234...",
      "modified": true,
      "installed_at": "2026-03-08T12:00:00Z",
      "template_version": "0.1.0"
    },
    {
      "name": "pre-commit",
      "installed": false,
      "configured": false
    }
  ],
  "signing": {
    "enabled": true,
    "enforcement": "warn",
    "key": "~/.ssh/id_ed25519.pub",
    "git_version": "2.39.3",
    "ssh_signing_supported": true
  }
}
```

**Human output** (default):
```
Hook Status
───────────────────────────────────────────
  commit-msg   ✓ installed  (unmodified)
  pre-push     ⚠ installed  (manually modified)
  pre-commit   ○ not installed (disabled in config)

Signing: enabled (warn mode, key: ~/.ssh/id_ed25519.pub)
```

---

### `dev-stack pr [--dry-run] [--base BRANCH] [--json] [--verbose]`

Generate a PR description from branch commits and optionally create the PR.

**Arguments**:
- `--base BRANCH`: Base branch for comparison (default: `main`)
- `--dry-run`: Print rendered Markdown without creating PR

**Behavior**:
1. Determine current branch name
2. Get commits between `--base` and HEAD
3. If no commits: exit 1 with message "No changes to create a PR for"
4. Parse each commit: extract conventional type, scope, trailers
5. Aggregate trailer data into PRDescription
6. Render Markdown from PR template
7. If `--dry-run`: print Markdown to stdout, exit 0
8. Detect PR CLI tool:
   a. If `gh` available and remote is GitHub: `gh pr create`
   b. If `glab` available and remote is GitLab: `glab mr create`
   c. Otherwise: print Markdown to stdout with message about missing CLI

**JSON output schema** (`--json`):
```json
{
  "status": "created" | "dry_run" | "printed" | "error",
  "branch": "feat/004-vcs-best-practices",
  "base": "main",
  "total_commits": 12,
  "ai_commits": 8,
  "human_commits": 4,
  "edited_commits": 3,
  "spec_refs": ["specs/004-vcs-best-practices/spec.md"],
  "task_refs": ["specs/004-vcs-best-practices/tasks.md#task-4.1"],
  "agents": ["claude"],
  "pipeline_status": {
    "lint": "pass",
    "typecheck": "pass",
    "test": "pass",
    "security": "pass",
    "docs-api": "pass",
    "docs-narrative": "pass",
    "infra-sync": "pass",
    "commit-message": "pass"
  },
  "pr_url": "https://github.com/user/repo/pull/42",
  "description_md": "## Summary\n..."
}
```

**Rendered Markdown template**:
```markdown
## Summary

{summary}

## Spec References

{spec_refs_list}

## Task References

{task_refs_list}

## AI Provenance

- **Total commits**: {total_commits}
- **AI-authored**: {ai_commits} ({ai_percentage}%)
- **Human-edited**: {edited_commits}
- **Agents used**: {agents_list}

## Pipeline Status

| Stage | Status |
|-------|--------|
{pipeline_rows}

## Commits

{commit_list}
```

---

### `dev-stack changelog [--unreleased] [--full] [--output FILE] [--json] [--verbose]`

Generate or update CHANGELOG.md from conventional commit history.

**Arguments**:
- `--unreleased`: Only changes since last tag (default)
- `--full`: Complete history from all tags
- `--output FILE`: Output file path (default: `CHANGELOG.md`)

**Behavior**:
1. Check if `git-cliff` is installed (`shutil.which("git-cliff")`)
2. If not installed: exit 1 with installation instructions
3. Verify `cliff.toml` exists at repo root
4. If `--unreleased`: run `git-cliff --unreleased`
5. If `--full`: run `git-cliff`
6. Post-process output to add AI/human-edited markers based on trailers
7. Write to output file

**JSON output schema** (`--json`):
```json
{
  "status": "success" | "error",
  "output_file": "CHANGELOG.md",
  "mode": "unreleased" | "full",
  "versions_rendered": 3,
  "total_commits_processed": 45,
  "ai_commits_annotated": 20,
  "human_edited_annotated": 8,
  "git_cliff_version": "2.4.0"
}
```

**Error case** (git-cliff not installed):
```json
{
  "status": "error",
  "error": "git-cliff is not installed",
  "help": "Install git-cliff: cargo install git-cliff, or brew install git-cliff"
}
```

---

### `dev-stack release [--dry-run] [--bump {major,minor,patch}] [--no-tag] [--json] [--verbose]`

Infer next version, bump pyproject.toml, update changelog, and tag release.

**Arguments**:
- `--dry-run`: Show inferred version and actions without executing
- `--bump {major,minor,patch}`: Override inferred bump type
- `--no-tag`: Skip creating git tag

**Behavior**:
1. Find latest version tag matching `v*` pattern
2. Collect commits since that tag
3. Parse each commit for conventional type, breaking changes, pipeline trailers
4. **Release gate check** (FR-036):
   a. For each commit, parse `Pipeline` trailer
   b. If any hard-failure stage (`lint`, `typecheck`, `test`, `security`, `docs-api`) has `=fail`: refuse
   c. Exit 6 with list of offending commits
5. If `--bump`: use override; else: infer from commit types
6. Compute next version
7. If `--dry-run`: print summary, exit 0
8. Update `[project] version` in `pyproject.toml`
9. Generate changelog entry (via `dev-stack changelog --unreleased`)
10. If not `--no-tag`: create annotated tag `v{version}`
11. If PSR installed: delegate to `semantic-release version`; else: use built-in

**JSON output schema** (`--json`):
```json
{
  "status": "success" | "dry_run" | "blocked" | "error",
  "current_version": "1.2.0",
  "next_version": "1.3.0",
  "bump_type": "minor",
  "commits_analyzed": 8,
  "breaking_changes": 0,
  "tag_created": "v1.3.0",
  "pyproject_updated": true,
  "changelog_updated": true,
  "hard_failures": []
}
```

**Blocked output** (exit code 6):
```json
{
  "status": "blocked",
  "reason": "Hard pipeline failures detected in commit range",
  "hard_failures": [
    {
      "sha": "abc1234",
      "subject": "feat(cli): add pr command",
      "failed_stages": ["typecheck"]
    }
  ]
}
```

**Dry-run human output**:
```
Release Summary
───────────────────────────────────────────
  Current version:  1.2.0
  Next version:     1.3.0
  Bump type:        minor
  Commits:          8 (5 feat, 2 fix, 1 docs)
  Breaking changes: 0
  Hard failures:    0

Actions (--dry-run, no changes made):
  • Update pyproject.toml version → 1.3.0
  • Update CHANGELOG.md
  • Create tag v1.3.0
```

---

### `dev-stack release --fallback` (Built-in Implementation)

When python-semantic-release is not installed, the built-in fallback handles:

1. **Version inference**: Regex parse conventional commit subjects
2. **pyproject.toml bump**: Read with `tomllib`, write with `tomli_w`
3. **Tag creation**: `git tag -a v{version} -m "Release v{version}"`

The fallback does NOT handle:
- Publishing to PyPI
- GitHub release creation
- Complex branching strategies

These require PSR and are documented in the help output.

---

## Interaction with Existing Commands

### `dev-stack init`

The existing `init` command triggers `VcsHooksModule.install()` as part of the standard module installation pipeline. No changes to `init_cmd.py` are needed — the module registry handles it.

### `dev-stack status`

The existing `status` command should include VcsHooksModule verification in its output. This is handled by the standard `verify()` call on all installed modules.

### `dev-stack update`

The existing `update` command triggers `VcsHooksModule.update()` via the module lifecycle. Hook auto-update (FR-014a) is handled within the module's `update()` method.

### `dev-stack rollback`

The existing `rollback` command restores managed files. Hook files in `.git/hooks/` are NOT in the git tree (they're in `.git/`), so rollback only affects:
- `.dev-stack/hooks-manifest.json` (restored)
- `constitution-template.md` (restored)
- `cliff.toml` (restored)
- `.dev-stack/instructions.md` (restored)

Post-rollback, `VcsHooksModule.verify()` will detect hook/manifest mismatch and recommend `dev-stack init --modules vcs_hooks` to re-sync.
