# Implementation Plan: Version Control Best Practices Automation

**Branch**: `004-vcs-best-practices` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-vcs-best-practices/spec.md`

## Summary

Add a comprehensive VCS best practices automation layer to dev-stack: commit message linting (gitlint-core), branch naming enforcement, git hook lifecycle management, PR auto-description generation, changelog generation (git-cliff), semantic release versioning, SSH signed commit enforcement, and constitutional agent practices. All capabilities follow the existing ModuleBase pattern and integrate with the 8-stage pipeline.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click (CLI), gitlint-core (commit linting), rich (output formatting), tomli-w (TOML writing), pathspec (file matching). Optional: git-cliff (changelog), python-semantic-release (release), gh/glab (PR creation).
**Storage**: `.dev-stack/hooks-manifest.json` (JSON), `cliff.toml` (TOML config), `pyproject.toml` (existing)
**Testing**: pytest (unit + integration + contract tests)
**Target Platform**: macOS / Linux (any platform with git >= 2.20; SSH signing requires >= 2.34)
**Project Type**: Single project (existing `src/dev_stack/` layout)
**Performance Goals**: Hook execution < 500ms, scope advisory < 500ms, `hooks status` < 2s
**Constraints**: No network calls at commit time, no global git config mutations, all hooks must be thin Python wrappers
**Scale/Scope**: ~15 new source files, 4 new CLI commands, 1 new module, 1 new package (`rules/`), modifications to `pipeline/stages.py`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | CLI-First Interface | PASS | 4 new CLI commands (`hooks`, `pr`, `changelog`, `release`) with `--json`, `--dry-run`, `--verbose` support |
| II | Spec-Driven Development | PASS | Full spec.md with 46 FRs, 9 user stories, 10 success criteria, clarifications session |
| III | Automation by Default | PASS | commit-msg, pre-push hooks run automatically; scope advisory integrates into pipeline stage 8 |
| IV | Brownfield Safety | PASS | Never overwrites unmanaged hooks (FR-013); checksum-based manifest (FR-012); managed section markers for agent files (FR-019) |
| V | AI-Native Architecture | PASS | Constitutional practices injected into agent instruction files; PR descriptions include AI provenance; changelog annotates AI-authored commits |
| VI | Local-First Execution | PASS | All hooks and validation run locally; no network calls at commit time; git-cliff/PSR are local tools |
| VII | Observability & Documentation | PASS | `hooks status` command; hook manifest with checksums/timestamps; structured Pipeline trailer output |
| VIII | Modularity & Composability | PASS | New VcsHooksModule follows ModuleBase ABC; independently installable/removable; no implicit coupling to other modules |

No violations — Complexity Tracking table not needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-vcs-best-practices/
├── plan.md              # This file
├── research.md          # Phase 0 output (complete)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── cli-contract.md
│   └── module-contract.md
├── checklists/
│   └── requirements.md  # Quality checklist (complete)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/dev_stack/
├── modules/
│   ├── base.py              # ModuleBase ABC (existing, unchanged)
│   ├── hooks.py             # Existing HooksModule (pre-commit; unchanged)
│   ├── vcs_hooks.py         # NEW — VcsHooksModule (commit-msg, pre-push, hook lifecycle)
│   └── __init__.py          # Updated — register VcsHooksModule
├── rules/                   # NEW package — gitlint custom rules
│   ├── __init__.py
│   ├── conventional.py      # ConventionalCommitRule (subject format)
│   ├── trailers.py          # TrailerPresenceRule, TrailerPathRule
│   └── pipeline_warn.py     # PipelineFailureWarningRule
├── vcs/                     # NEW package — VCS automation utilities
│   ├── __init__.py
│   ├── hooks_runner.py      # Hook runner functions (commit-msg, pre-push, pre-commit)
│   ├── commit_parser.py     # CommitSummary + git log parsing utility
│   ├── branch.py            # Branch name validation
│   ├── signing.py           # SSH signing config & verification
│   ├── pr.py                # PR description generation
│   ├── changelog.py         # Changelog generation (git-cliff wrapper)
│   ├── release.py           # Semantic release (PSR wrapper + fallback)
│   └── scope.py             # Scope advisory heuristic
├── cli/
│   ├── hooks_cmd.py         # NEW — `dev-stack hooks status`
│   ├── pr_cmd.py            # NEW — `dev-stack pr`
│   ├── changelog_cmd.py     # NEW — `dev-stack changelog`
│   ├── release_cmd.py       # NEW — `dev-stack release`
│   └── main.py              # Updated — import new *_cmd modules
├── pipeline/
│   ├── stages.py            # Updated — add scope advisory to _execute_commit_stage
│   └── commit_format.py     # Existing (unchanged)
├── templates/               # NEW templates
│   ├── hooks/
│   │   ├── commit-msg.py    # Thin hook wrapper
│   │   ├── pre-push.py      # Thin hook wrapper
│   │   └── pre-commit.py    # Thin hook wrapper (lint + typecheck stages)
│   ├── constitution-template.md
│   ├── instructions.md
│   ├── cliff.toml           # git-cliff config template
│   └── pr-template.md       # PR description Markdown template
└── brownfield/
    └── markers.py           # Existing (unchanged, reused for agent file injection)

tests/
├── unit/
│   ├── test_vcs_hooks_module.py    # VcsHooksModule lifecycle
│   ├── test_rules_conventional.py  # gitlint rule tests
│   ├── test_rules_trailers.py      # Trailer validation rules
│   ├── test_branch.py              # Branch naming validation
│   ├── test_signing.py             # SSH signing config
│   ├── test_pr.py                  # PR description generation
│   ├── test_changelog.py           # Changelog generation
│   ├── test_release.py             # Release versioning
│   └── test_scope.py               # Scope advisory heuristic
├── integration/
│   ├── test_hooks_lifecycle.py     # Install/update/uninstall hooks
│   ├── test_commit_linting.py      # End-to-end commit-msg hook
│   └── test_pre_push.py            # End-to-end pre-push hook
└── contract/
    ├── test_cli_hooks.py           # `hooks status` JSON schema
    ├── test_cli_pr.py              # `pr` JSON schema
    ├── test_cli_changelog.py       # `changelog` JSON schema
    └── test_cli_release.py         # `release` JSON schema
```

**Structure Decision**: Extends the existing single-project `src/dev_stack/` layout. Two new packages (`rules/`, `vcs/`) keep VCS-specific logic separated from existing modules. Templates go into the existing `templates/` directory. All new CLI commands follow the existing `*_cmd.py` pattern.
