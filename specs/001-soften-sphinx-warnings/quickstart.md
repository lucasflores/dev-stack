# Quickstart: Soften Sphinx `-W` for Brownfield Projects

**Feature**: `001-soften-sphinx-warnings`

## What This Validates

- Docs strictness is controlled by `[tool.dev-stack.pipeline].strict_docs`.
- Non-strict mode omits `-W` and does not fail on warnings alone.
- Strict mode preserves `-W --keep-going` behavior.
- Existing `docs/Makefile` files are not auto-migrated during normal pipeline execution.

## Prerequisites

- Python 3.11+
- `uv` installed
- Development dependencies synced:

```bash
uv sync --extra dev --extra docs
```

## 1) Run Targeted Regression Tests

```bash
/Users/lucasflores/dev-stack/.venv/bin/python -m pytest -o addopts='' tests/contract/test_docs_strictness_contract.py tests/integration/test_docs_strictness.py -q
/Users/lucasflores/dev-stack/.venv/bin/python -m pytest -o addopts='' tests/unit/test_pipeline_stages.py -k 'TestIsStrictDocs or TestDocsApiStrictDocs' -q
/Users/lucasflores/dev-stack/.venv/bin/python -m pytest -o addopts='' tests/unit/test_sphinx_docs.py -k 'strict_docs or BrownfieldMakefile' -q
/Users/lucasflores/dev-stack/.venv/bin/python -m pytest -o addopts='' tests/unit/test_init_cmd.py -k 'BrownfieldPipelineDefaults' -q
```

Expected results:
- All selected tests pass.
- Pipeline tests show `-W` present in strict mode and absent in non-strict mode.
- Sphinx docs module tests show Makefile `SPHINXOPTS` is empty in non-strict mode.
- Init tests confirm brownfield defaults inject `strict_docs = false` without overwriting explicit values.

Latest verification snapshot (`2026-04-22T04:31:48Z`):
- `tests/contract/test_docs_strictness_contract.py` + `tests/integration/test_docs_strictness.py`: `11 passed`
- `tests/unit/test_pipeline_stages.py -k 'TestIsStrictDocs or TestDocsApiStrictDocs'`: `10 passed, 22 deselected`
- `tests/unit/test_sphinx_docs.py -k 'strict_docs or BrownfieldMakefile'`: `8 passed, 26 deselected`
- `tests/unit/test_init_cmd.py -k 'BrownfieldPipelineDefaults'`: `5 passed, 10 deselected`

## 2) Manual Config Smoke Check (Optional)

1. Set `strict_docs = false` in a test `pyproject.toml` under `[tool.dev-stack.pipeline]`.
2. Trigger docs Makefile generation (install/preview path) and verify:
   - `SPHINXOPTS  ?= ` appears in generated output.
3. Set `strict_docs = true` and verify:
   - `SPHINXOPTS  ?= -W --keep-going` appears in generated output.

## 3) Manual Pipeline Smoke Check (Optional)

- Run docs-api stage through the existing pipeline entrypoint in a repository with docs warnings.
- Verify:
  - `strict_docs = false`: warnings are reported, stage does not hard-fail on warnings alone.
  - `strict_docs = true`: warnings produce failure via `-W` behavior.
  - Build-breaking errors fail in both modes.

Automated integration coverage now also validates this behavior via:
- `tests/integration/test_docs_strictness.py::test_non_strict_warnings_continue_to_subsequent_stage`
- `tests/integration/test_docs_strictness.py::test_strict_warning_failure_stops_pipeline`

## 4) Legacy Makefile Safety Check (Optional)

- Keep an existing `docs/Makefile` that predates this feature.
- Run normal pipeline execution.
- Verify file contents remain unchanged unless explicit regeneration is invoked.

Automated integration coverage validates this boundary with:
- `tests/integration/test_docs_strictness.py::test_existing_makefile_unchanged_during_pipeline_run`

## 5) Non-Doc Pipeline Regression Subset

Run unchanged non-doc stage regressions to confirm lint/typecheck/test/security/runner behavior is unaffected:

```bash
/Users/lucasflores/dev-stack/.venv/bin/python -m pytest -o addopts='' tests/unit/test_pipeline.py tests/unit/test_pipeline_stages.py::TestRemediationHints::test_lint_skip_includes_remediation_hint tests/unit/test_pipeline_stages.py::TestRemediationHints::test_test_skip_includes_remediation_hint tests/unit/test_pipeline_stages.py::TestRemediationHints::test_typecheck_skip_includes_remediation_hint tests/unit/test_pipeline_stages.py::test_typecheck_skip_when_src_missing tests/unit/test_pipeline_stages.py::test_security_scan_does_not_exclude_lazyspeckit tests/unit/test_pipeline_stages.py::test_execute_infra_sync_stage_detects_drift tests/unit/test_pipeline_stages.py::test_infra_sync_ignores_pre_commit_config_yaml -q
```

Observed result (`2026-04-22T04:31:48Z`):
- `20 passed`
- No regressions in non-doc stage orchestration or skip/hint behavior.
