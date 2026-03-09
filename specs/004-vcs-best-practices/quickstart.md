# Quickstart: Version Control Best Practices Automation

**Branch**: `004-vcs-best-practices` | **Date**: 2026-03-08

---

## Prerequisites

- Python 3.11+
- git >= 2.20 (>= 2.34 for SSH signing)
- dev-stack installed (`pip install -e .` from repo root)

### Optional Tools

| Tool | Required For | Install |
|------|-------------|---------|
| gitlint-core | Commit message linting | `pip install gitlint-core` |
| git-cliff | Changelog generation | `cargo install git-cliff` or `brew install git-cliff` |
| python-semantic-release | Full release automation | `pip install python-semantic-release` |
| gh | PR creation on GitHub | `brew install gh` |
| glab | MR creation on GitLab | `brew install glab` |

---

## 1. Initialize VCS Best Practices

```bash
# In a git repository with pyproject.toml:
dev-stack init

# Or add VCS hooks to an existing dev-stack project:
dev-stack update --modules vcs_hooks
```

This installs:
- `.git/hooks/commit-msg` — validates commit messages
- `.git/hooks/pre-push` — validates branch names, checks signatures
- `.dev-stack/hooks-manifest.json` — tracks hook state
- `.dev-stack/instructions.md` — agent behavioral practices
- `constitution-template.md` — for spec-kit users
- `cliff.toml` — changelog configuration

## 2. Commit Message Validation

After installation, every `git commit` is automatically validated:

```bash
# Valid commit — passes
git commit -m "feat(cli): add pr command"

# Invalid commit — rejected with helpful error
git commit -m "added stuff"
# ERROR: Commit message does not follow conventional commit format.
# Expected: type(scope): description
# Valid types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

# Agent-generated commit must include trailers:
git commit -m "feat(cli): add pr command

Spec-Ref: specs/004-vcs-best-practices/spec.md
Task-Ref: specs/004-vcs-best-practices/tasks.md#task-5.1
Agent: claude
Pipeline: lint=pass,typecheck=pass,test=pass
Edited: false"
```

## 3. Branch Naming Enforcement

Branch names are validated at push time (never blocks local work):

```bash
# Valid branch names:
git checkout -b feat/004-vcs-best-practices   # OK
git checkout -b fix/broken-hook-install         # OK

# Pushing an invalid branch name:
git push origin my-random-branch
# ERROR: Branch name 'my-random-branch' does not match required pattern.
# Expected: {type}/{slug} (e.g., feat/my-feature, fix/bug-description)

# Exempt branches push freely:
git push origin main  # Always allowed
```

### Customize Branch Pattern

```toml
# pyproject.toml
[tool.dev-stack.branch]
pattern = "^(feat|fix|docs|chore)/[a-z0-9._-]+$"
exempt = ["main", "master", "develop"]
```

## 4. Check Hook Status

```bash
dev-stack hooks status
# Hook Status
# ───────────────────────────────────────────
#   commit-msg   ✓ installed  (unmodified)
#   pre-push     ✓ installed  (unmodified)
#   pre-commit   ○ not installed (disabled in config)
#
# Signing: disabled

# JSON output for CI:
dev-stack hooks status --json
```

## 5. Generate PR Description

```bash
# Preview the PR description:
dev-stack pr --dry-run

# Create PR on GitHub (requires `gh` CLI):
dev-stack pr

# Use a different base branch:
dev-stack pr --base develop
```

## 6. Generate Changelog

```bash
# Requires git-cliff to be installed

# Changes since last tag:
dev-stack changelog --unreleased

# Full changelog:
dev-stack changelog --full

# Custom output file:
dev-stack changelog --output docs/CHANGELOG.md
```

## 7. Create a Release

```bash
# Dry-run to see what would happen:
dev-stack release --dry-run
# Release Summary
#   Current version:  0.1.0
#   Next version:     0.2.0
#   Bump type:        minor
#   Commits:          12

# Execute the release:
dev-stack release

# Override the bump type:
dev-stack release --bump patch

# Skip tag creation:
dev-stack release --no-tag
```

## 8. Enable SSH Signing (Optional)

```toml
# pyproject.toml
[tool.dev-stack.signing]
enabled = true
enforcement = "warn"   # or "block"
# key = "~/.ssh/id_ed25519.pub"  # auto-detected if omitted
```

Then re-run init to configure git:

```bash
dev-stack init
# Configures: commit.gpgsign=true, gpg.format=ssh, user.signingkey=...
```

## 9. Configure Hooks

```toml
# pyproject.toml
[tool.dev-stack.hooks]
commit-msg = true   # default: true
pre-push = true     # default: true
pre-commit = false  # default: false — enable to run lint+typecheck on commit
```

---

## Development Workflow

### Implementing a New Feature

```bash
# 1. Create correctly named branch
git checkout -b feat/my-feature

# 2. Write code, tests pass locally
pytest

# 3. Commit — hook validates message automatically
git commit -m "feat(module): add new capability"

# 4. Push — hook validates branch name
git push origin feat/my-feature

# 5. Create PR with auto-description
dev-stack pr

# 6. When ready to release
dev-stack release --dry-run
dev-stack release
```

### Scope Advisory in Pipeline

When you stage changes across many directories, the pipeline warns you:

```bash
# Staging changes across 3+ source packages triggers advisory:
git add src/dev_stack/cli/new_cmd.py src/dev_stack/modules/new_mod.py src/dev_stack/pipeline/new_stage.py
# During commit pipeline: "scope-check=warn" appears in Pipeline trailer
# This is informational only — your commit is NOT blocked
```

---

## Troubleshooting

### Hook not running
```bash
# Check hook status:
dev-stack hooks status

# Re-install hooks:
dev-stack update --modules vcs_hooks
```

### Hook was manually modified
```bash
# dev-stack will detect the modification:
dev-stack hooks status
#   commit-msg   ⚠ installed  (manually modified)

# Force re-install:
dev-stack init --modules vcs_hooks --force
```

### git-cliff or PSR not found
```bash
dev-stack changelog
# ERROR: git-cliff is not installed.
# Install: cargo install git-cliff, or brew install git-cliff

dev-stack release
# Using built-in release implementation (python-semantic-release not found).
# For full release features, install: pip install python-semantic-release
```

### SSH signing requires newer git
```bash
dev-stack init
# WARNING: SSH signing requires git >= 2.34 (current: 2.30.1).
# Signing configuration skipped. Upgrade git to enable signing.
```
