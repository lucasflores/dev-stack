# Quickstart: Init & Pipeline Bugfixes

**Branch**: `006-init-pipeline-bugfixes` | **Date**: 2026-03-10

## Overview

This feature fixes 14 bugs across 7 source files and 1 doc file. All changes are surgical modifications to existing functions — no new modules, no architectural changes, no new dependencies.

## Files Changed (by FR)

| File | FRs | Changes |
|---|---|---|
| `src/dev_stack/pipeline/stages.py` | FR-001, FR-008, FR-012 | Add `_tool_available_in_venv()`, update typecheck stage to check venv, update security stage to use `.secrets.baseline`, ensure all stages use venv Python |
| `src/dev_stack/cli/init_cmd.py` | FR-002, FR-003, FR-004, FR-005, FR-007, FR-013 | Add `uv sync --all-extras`, greenfield fingerprint filtering, dry-run delegation on initialized repos, rollback tag in greenfield |
| `src/dev_stack/pipeline/runner.py` | FR-006 | Fix `success` calculation: `not has_hard_failures` instead of `aborted_stage is None or force` |
| `src/dev_stack/cli/pipeline_cmd.py` | FR-006 | Add `"completed_with_failures"` status to `_serialize_run` |
| `src/dev_stack/cli/main.py` | FR-009 | Add `@click.version_option()` to CLI group with `importlib.metadata` version |
| `src/dev_stack/cli/update_cmd.py` | FR-010 | Add `help=` text to `@cli.command("update")` |
| `src/dev_stack/brownfield/conflict.py` | FR-004 | Add `is_greenfield_uv_package()` fingerprint function |
| `README.md` | FR-011 | Fix flag positions in validation checklist (global flags before subcommand) |

## Implementation Order

### Phase 1: Foundation (no dependencies between these)

1. **FR-009**: `--version` flag → `main.py` (1 file, isolated)
2. **FR-010**: Update help text → `update_cmd.py` (1 line change, isolated)
3. **FR-011**: README flag positions → `README.md` (text-only, isolated)

### Phase 2: Pipeline accuracy

4. **FR-006**: Pipeline success/status → `runner.py` + `pipeline_cmd.py` (2 files, linked)
5. **FR-001**: Venv-aware mypy detection → `stages.py` (1 function + 1 helper)
6. **FR-008**: Venv Python for all stages → `stages.py` (consistency with FR-001)

### Phase 3: Init flow

7. **FR-004/FR-005**: Greenfield fingerprint → `conflict.py` + `init_cmd.py` (2 files, linked)
8. **FR-002/FR-003**: `uv sync --all-extras` → `init_cmd.py` (1 file, depends on FR-004 for greenfield flow)
9. **FR-007**: Dry-run delegation → `init_cmd.py` (1 function mod)
10. **FR-013**: Rollback tag in greenfield → `init_cmd.py` (1 guard removal)

### Phase 4: Security

11. **FR-012**: Secrets baseline → `stages.py` + init baseline generation in `init_cmd.py`

## Test Strategy

| Test Type | Scope | Location |
|---|---|---|
| Unit | `_tool_available_in_venv`, `is_greenfield_uv_package`, `has_unaudited_secrets`, success calculation, `_serialize_run` | `tests/unit/` |
| Integration | Full greenfield flow, `--force` pipeline with failures, dry-run on initialized repos | `tests/integration/` |
| Contract | CLI JSON schema (new `completed_with_failures` status, `--version` output) | `tests/contract/` |

## Dev Setup

```bash
git checkout 006-init-pipeline-bugfixes
uv sync --all-extras
pytest tests/ -x
```

## Verification Commands (post-implementation)

```bash
# FR-009: Version flag
dev-stack --version

# FR-010: Update help text
dev-stack --help | grep update

# FR-001: Venv-aware mypy skip
# (with mypy NOT in venv, system mypy present)
dev-stack --json pipeline run --stage typecheck
# Expected: stage skips with "mypy not installed in project venv"

# FR-006: Force + failure = completed_with_failures
dev-stack --json pipeline run --force
# Expected: "completed_with_failures" status when hard gates fail

# FR-004/FR-005: Greenfield mode after uv init
mkdir /tmp/test-gf && cd /tmp/test-gf && git init && uv init --package
dev-stack --json init
# Expected: "mode": "greenfield", no conflicts

# FR-002/FR-003: .venv created with dev deps
ls .venv/bin/ruff .venv/bin/pytest .venv/bin/mypy

# FR-012: Security baseline
cat .secrets.baseline | python -m json.tool | head
```
