# Internal Contract: Docs Strictness Policy

**Feature**: `018-soften-sphinx-warnings`  
**Scope**: `docs-api` pipeline stage + Sphinx Makefile generation

## Contracted Functions

### 1) Pipeline strictness resolver

```python
def _is_strict_docs(context: StageContext) -> bool:
    ...
```

**Contract**:
- Reads `[tool.dev-stack.pipeline].strict_docs` from `pyproject.toml`.
- Returns `True` when file is missing, unreadable, or key is absent.
- Returns explicit configured bool when present.

---

### 2) Module strictness resolver

```python
def _read_strict_docs(repo_root: Path) -> bool:
    ...
```

**Contract**:
- Mirrors `_is_strict_docs` semantics for Sphinx module generation paths.
- Uses strict fallback (`True`) for missing/unreadable config.

---

### 3) docs-api stage command assembly

```python
def _execute_docs_api_stage(context: StageContext) -> StageResult:
    ...
```

**Command contract**:
- Base command: `python3 -m sphinx -b html`.
- If `strict_docs` is `True`, append `-W --keep-going`.
- If `strict_docs` is `False`, append neither `-W` nor `--keep-going`.
- Always append source/output directories (`docs`, `docs/_build`).

**Canonical examples**:
- strict: `python3 -m sphinx -b html -W --keep-going docs docs/_build`
- non-strict: `python3 -m sphinx -b html docs docs/_build`

**Outcome contract**:
- Warnings are fatal only in strict mode.
- True build errors remain fatal in both modes.
- Existing skip behavior remains unchanged when Sphinx tool or `docs/` directory is missing.
- When non-strict docs build exits `0` (warnings-only output), pipeline proceeds to subsequent stages.
- When strict docs build exits non-zero due to warnings (`-W`), pipeline halts at `docs-api` (hard failure).

**Side-effect contract**:
- Does not modify `docs/Makefile` during pipeline execution.

---

### 4) Sphinx Makefile rendering

```python
def _render_makefile(
    pkg_name: str,
    layout: PackageLayout | None = None,
    *,
    strict_docs: bool = True,
) -> str:
    ...
```

**Rendering contract**:
- `strict_docs=True` -> `SPHINXOPTS  ?= -W --keep-going`
- `strict_docs=False` -> `SPHINXOPTS  ?= ` (empty)

**Application contract**:
- Applies during docs scaffold generation and explicit regeneration paths.
- No automatic migration of pre-existing Makefiles during normal pipeline runs.

**Canonical output examples**:
- strict: `SPHINXOPTS  ?= -W --keep-going`
- non-strict: `SPHINXOPTS  ?= `

---

### 5) Brownfield default injection

```python
def _set_brownfield_pipeline_defaults(repo_root: Path) -> None:
    ...
```

**Contract**:
- For brownfield init, sets `strict_docs = false` only if key is absent.
- Must preserve explicit user-configured strictness values.

## Non-Goals (Enforced by Contract)

- No new CLI flag for strictness control in this feature.
- No Sphinx extension or warning-category remediation changes.
- No package-layout logic changes.

## Verification Mapping

- Resolver parity and fallbacks:
    - `tests/contract/test_docs_strictness_contract.py::TestStrictnessResolverContract`
- docs-api command assembly strict vs non-strict:
    - `tests/contract/test_docs_strictness_contract.py::TestDocsApiCommandContract`
- Non-strict continuation and strict halt behavior:
    - `tests/integration/test_docs_strictness.py::test_non_strict_warnings_continue_to_subsequent_stage`
    - `tests/integration/test_docs_strictness.py::test_strict_warning_failure_stops_pipeline`
- Makefile rendering invariants:
    - `tests/contract/test_docs_strictness_contract.py::TestMakefileStrictnessContract`
    - `tests/unit/test_sphinx_docs.py`
- Legacy Makefile non-migration during normal pipeline execution:
    - `tests/integration/test_docs_strictness.py::test_existing_makefile_unchanged_during_pipeline_run`
