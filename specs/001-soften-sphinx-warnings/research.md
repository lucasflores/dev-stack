# Research: Soften Sphinx `-W` for Brownfield Projects

**Feature**: `001-soften-sphinx-warnings`  
**Date**: 2026-04-21

## R-001: Canonical Docs Strictness Source

**Decision**: Use `[tool.dev-stack.pipeline] strict_docs` in `pyproject.toml` as the single runtime source of truth for docs strictness.

**Rationale**: This signal is persistent, already consumed in both pipeline and Sphinx module flows, survives first-commit marker cleanup, and naturally defaults to strict behavior when absent/unreadable.

**Alternatives considered**:
- `.dev-stack/brownfield-init` marker only: rejected because it is transient and intentionally removed.
- Manifest mode only (`stack.mode`): rejected as an indirect source for this behavior and less explicit than pipeline config.
- Dual-source resolution (marker + manifest + pyproject): rejected due to unnecessary precedence complexity.

---

## R-002: Non-Strict Docs-API Command Composition

**Decision**: In non-strict mode (`strict_docs = false`), omit both `-W` and `--keep-going` from the `python3 -m sphinx -b html ...` invocation.

**Rationale**: This aligns with spec clarification and existing expected behavior: warnings should not become fatal in brownfield mode, while true build errors still return non-zero and fail the stage.

**Alternatives considered**:
- Keep `--keep-going` while dropping only `-W`: rejected by clarified requirement for empty non-strict defaults.
- Always include `-W --keep-going`: rejected because it preserves the brownfield hard-fail problem.

---

## R-003: Non-Strict Makefile Default

**Decision**: Emit `SPHINXOPTS ?=` (empty) when `strict_docs = false`; emit `SPHINXOPTS ?= -W --keep-going` when `strict_docs = true`.

**Rationale**: This keeps generated docs scaffolding consistent with runtime stage behavior and avoids requiring users to manually edit generated files after initialization.

**Alternatives considered**:
- `SPHINXOPTS ?= --keep-going` for non-strict: rejected by clarification.
- Leave historical default unchanged: rejected because it contradicts non-strict brownfield behavior.

---

## R-004: Brownfield Persistence Strategy

**Decision**: Persist brownfield docs behavior through `strict_docs = false` injection during brownfield init, only when no explicit strictness value is already configured.

**Rationale**: This preserves user intent, avoids overwriting explicit config, and ensures behavior remains stable after transient markers are removed.

**Alternatives considered**:
- Force overwrite `strict_docs` on every init/update: rejected because it would violate explicit user configuration.
- Recompute strictness dynamically from provenance each run: rejected because explicit config precedence is clearer and already implemented.

---

## R-005: Existing Makefile Migration Policy

**Decision**: Do not auto-migrate pre-existing `docs/Makefile` files during normal pipeline runs; apply new defaults only during new generation or explicit regeneration.

**Rationale**: This is safer for brownfield repositories, avoids surprise rewrites, and keeps this feature narrowly scoped to strictness behavior.

**Alternatives considered**:
- Auto-rewrite Makefile during pipeline: rejected due to hidden file mutation in a validation path.
- Warn-only migration reminders in this feature: deferred to follow-up if needed.

---

## R-006: Verification Strategy

**Decision**: Use targeted unit regression coverage across three existing suites:
- `tests/unit/test_pipeline_stages.py` for docs-api command flags, strict fallback, and skip behavior invariants
- `tests/unit/test_sphinx_docs.py` for Makefile rendering/install/preview outputs
- `tests/unit/test_init_cmd.py` for brownfield `strict_docs=false` injection and non-overwrite semantics

**Rationale**: These suites already exercise the exact boundaries touched by the feature and provide fast feedback without adding new test infrastructure.

**Alternatives considered**:
- Add broad integration test harness for full init + commit pipeline: rejected for this scoped change; unit suites already cover behavior contracts.
- Rely solely on manual smoke validation: rejected as insufficient for regression safety.
