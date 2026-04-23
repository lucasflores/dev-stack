# Data Model: Soften Sphinx `-W` for Brownfield Projects

**Feature**: `018-soften-sphinx-warnings`  
**Date**: 2026-04-21

## Entities

### DocsStrictnessPolicy

Resolved policy used by both docs-api runtime and docs scaffolding generation.

| Field | Type | Description |
|-------|------|-------------|
| `strict_docs` | `bool` | Effective strictness mode (`true` = warnings are fatal, `false` = warnings are non-fatal) |
| `source` | `StrictnessSource` | Where the effective value came from |
| `fallback_applied` | `bool` | Whether strict mode fallback was applied due to missing/unreadable config |

`StrictnessSource` enum values:
- `CONFIG_EXPLICIT`: `strict_docs` key exists in `pyproject.toml`
- `CONFIG_DEFAULT`: key missing in readable config; default applied
- `CONFIG_FALLBACK`: file missing/unreadable; default strict fallback applied

**Validation rules**:
- If `strict_docs` cannot be read, effective value must be `true`.
- Explicit configured values always win over inferred project provenance.

---

### DocsApiBuildConfig

Derived command-shaping state for docs-api stage.

| Field | Type | Description |
|-------|------|-------------|
| `include_warning_error_flag` | `bool` | Whether `-W` is included in Sphinx build command |
| `include_keep_going_flag` | `bool` | Whether `--keep-going` is included in Sphinx build command |
| `source_date_epoch` | `str` | Deterministic build env setting (`"0"`) |

**Validation rules**:
- `include_warning_error_flag` and `include_keep_going_flag` are both `true` only when `strict_docs = true`.
- Both are `false` when `strict_docs = false`.
- Build failure semantics are independent from strictness: non-zero Sphinx return code still fails the stage.

---

### DocsMakefileDefaults

Generated defaults for `docs/Makefile` strictness options.

| Field | Type | Description |
|-------|------|-------------|
| `sphinxopts_line` | `str` | Rendered `SPHINXOPTS` assignment line |
| `applies_on_generation` | `bool` | Indicates value is applied during generation/regeneration flows |
| `applies_on_pipeline_run` | `bool` | Indicates value is applied during pipeline runs |

**Validation rules**:
- When `strict_docs = false`, `sphinxopts_line` must be `SPHINXOPTS  ?= `.
- When `strict_docs = true`, `sphinxopts_line` must be `SPHINXOPTS  ?= -W --keep-going`.
- `applies_on_pipeline_run` is always `false` for legacy Makefile migration behavior.

---

### ExistingDocsMakefileState

Represents pre-existing `docs/Makefile` files that predate this feature.

| Field | Type | Description |
|-------|------|-------------|
| `exists` | `bool` | Whether a `docs/Makefile` is already present |
| `managed_by_current_generation` | `bool` | Whether current run is explicit generation/regeneration |
| `auto_migration_allowed` | `bool` | Whether pipeline may rewrite file automatically |

**Validation rules**:
- During normal pipeline execution, `auto_migration_allowed` is always `false`.
- Existing files remain unchanged unless user invokes generation/regeneration path.

## Relationships

- `DocsStrictnessPolicy` drives both `DocsApiBuildConfig` and `DocsMakefileDefaults`.
- `ExistingDocsMakefileState` gates whether `DocsMakefileDefaults` is applied immediately.
- Pipeline stage behavior consumes `DocsApiBuildConfig` and does not mutate existing Makefiles.

## State Transitions

1. Brownfield init writes `strict_docs = false` only when key is absent.
2. User may explicitly set `strict_docs` to `true` or `false`.
3. Runtime resolves `DocsStrictnessPolicy` from config (or strict fallback).
4. docs-api builds command from policy and executes without changing Makefile state.
5. docs scaffolding generation/regeneration uses the same policy to render `SPHINXOPTS`.
