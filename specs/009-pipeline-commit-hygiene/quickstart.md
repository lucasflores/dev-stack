# Quickstart: Pipeline Commit Hygiene

**Feature Branch**: `009-pipeline-commit-hygiene`
**Date**: 2026-03-10

## Overview

This feature fixes 6 issues in the dev-stack pre-commit pipeline to ensure:
1. First commit succeeds on the first attempt (no multiple `git add && git commit` cycles)
2. Working tree stays clean after every commit (no perpetually dirty `.secrets.baseline`)
3. Soft-gate stages (visualize, commit-message) behave and report correctly

## Changes At a Glance

| File | Change |
|------|--------|
| `src/dev_stack/pipeline/stages.py` | Add `output_paths` to `StageResult`; baseline comparison in security stage; LLM key check in visualize stage; `-m` detection in commit-message stage |
| `src/dev_stack/pipeline/runner.py` | Add `hook_context` to `StageContext`; auto-staging logic after pipeline completes |
| `src/dev_stack/templates/hooks/pre-commit` | Export `DEV_STACK_HOOK_CONTEXT=pre-commit` |
| `README.md` | Document LLM API key requirement for visualize stage; document `-m` flag behavior for commit-message stage |

## Development Setup

```bash
# Checkout the feature branch
git checkout 009-pipeline-commit-hygiene

# Install dev dependencies
uv sync --extra dev --extra docs

# Run existing tests to establish baseline
python -m pytest tests/ -v
```

## Testing the Changes

### Unit Tests

```bash
# Run only pipeline unit tests
python -m pytest tests/unit/pipeline/ -v

# Key test areas:
# - _baseline_findings_changed() comparison logic
# - _has_llm_api_key() environment variable checking
# - _user_message_provided() COMMIT_EDITMSG detection
# - _auto_stage_outputs() staging behavior
# - StageResult.output_paths population by each stage executor
```

### Integration Test (Greenfield Flow)

```bash
# Create a fresh temp directory and run the full flow
cd /tmp && mkdir test-project && cd test-project
git init
uv init --package
dev-stack --json init
git add -A && git commit -m "Initial commit"

# Verify: commit succeeds on first attempt
# Verify: git status --porcelain produces empty output
git status --porcelain
```

### Manual Verification Checklist

- [ ] `git commit -m "test"` → commit-message stage reports "skip" (not "pass")
- [ ] After commit, `git status --porcelain` is empty
- [ ] Unset all LLM API keys → visualize stage reports "skip" with key list
- [ ] `dev-stack pipeline run` (standalone) → no auto-staging occurs
- [ ] `.secrets.baseline` timestamp unchanged when no findings change

## Architecture Notes

- **Auto-staging scope**: Only runs when `DEV_STACK_HOOK_CONTEXT=pre-commit` is set
- **Stage output tracking**: Each stage populates `StageResult.output_paths` with files it creates/modifies
- **Fail-safe**: Failed stages don't contribute to auto-staging (only "pass" and "skip" results)
- **Baseline comparison**: Security stage reads JSON before and after scan, compares `results` dict only
