# dev-stack Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-10

## Active Technologies
- File-based -- `dev-stack.toml` manifest, `.dev-stack/` working directory, `.specify/` for Spec Ki (001-dev-stack-ecosystem)
- Python 3.11+ (project uses `requires-python = ">=3.11"`) + click, tomli-w, rich, pathspec (existing); uv CLI (external, v0.5+), sphinx + sphinx-autodoc-typehints + myst-parser (optional docs), mypy (optional dev) (002-init-pipeline-enhancements)
- TOML files (`dev-stack.toml` manifest, `pyproject.toml`); filesystem artifacts (002-init-pipeline-enhancements)
- Python 3.11+ + click (CLI), gitlint-core (commit linting), rich (output formatting), tomli-w (TOML writing), pathspec (file matching). Optional: git-cliff (changelog), python-semantic-release (release), gh/glab (PR creation). (004-vcs-best-practices)
- `.dev-stack/hooks-manifest.json` (JSON), `cliff.toml` (TOML config), `pyproject.toml` (existing) (004-vcs-best-practices)
- Python 3.11+ + click (CLI), tomllib (pyproject parsing), subprocess (stage execution), uv (package management) (006-init-pipeline-bugfixes)
- `dev-stack.toml` (TOML manifest), `.secrets.baseline` (JSON), `.dev-stack/pipeline/last-run.json` (006-init-pipeline-bugfixes)
- Python 3.11+ + click ≥8.1, detect-secrets ≥1.5, tomli-w ≥1.0, rich ≥13.7, pathspec ≥0.12, gitlint-core ≥0.19 (007-init-onboarding-fixes)
- Filesystem — `.secrets.baseline` (JSON), `dev-stack.toml` (TOML), `.dev-stack/hooks-manifest.json` (JSON) (007-init-onboarding-fixes)
- Python 3.11+ + click (CLI framework), tomli_w/tomllib (TOML read/write), uv (package manager) (008-greenfield-init-fixes)
- Filesystem — `dev-stack.toml` manifest, `pyproject.toml`, `.venv/` (008-greenfield-init-fixes)
- Python 3.12 (minimum 3.10+) + detect-secrets, sphinx, git CLI, Understand-Anything artifact policy checks (009-pipeline-commit-hygiene)
- JSON files (`.secrets.baseline`, pipeline state), filesystem (docs, `.understand-anything/`) (009-pipeline-commit-hygiene)
- Python 3.11+ + Click (CLI), tomli/tomli-w (TOML), pathlib (filesystem) (010-proactive-agent-instructions)
- Filesystem — repo-local files managed by brownfield markers (010-proactive-agent-instructions)
- Python 3.11+ (3.12.9 in development) + click >=8.1, gitlint-core >=0.19, rich >=13.7, pathspec >=0.12 (011-pipeline-commit-fixes)
- Filesystem (`.git/COMMIT_EDITMSG`, `.dev-stack/logs/`, `.dev-stack/pending-docs.md`) (011-pipeline-commit-fixes)
- Python 3.11+ + click, tomli_w, tomllib, gitlint-core, pathlib (012-universal-init-pipeline)
- TOML files (dev-stack.toml), YAML files (.pre-commit-config.yaml), git hooks (012-universal-init-pipeline)
- Python 3.12+ + click (CLI), tomli/tomllib (TOML parsing), subprocess (APM CLI invocation), shutil (which/PATH lookup), pyyaml or ruamel.yaml (apm.yml generation) (013-apm-module-swap)
- File-based — `apm.yml`, `apm.lock.yaml`, agent-native config dirs (`.claude/`, `.github/`, `.cursor/`, `.opencode/`) (013-apm-module-swap)
- Python 3.11+ (pyproject.toml: `requires-python = ">=3.11"`) + Click (CLI), PyYAML (apm.yml generation), `subprocess` (APM CLI invocation), `tomli-w` (TOML writing), `packaging` (version comparison) (014-apm-module-swap)
- File-based (`apm.yml`, `apm.lock.yaml`, `dev-stack.toml`) (014-apm-module-swap)
- Python 3.11+ + click, rich, packaging, tomli-w, yaml, gitlint-core, ruff (016-brownfield-init-bugs)
- File-based (pyproject.toml, apm.yml, .dev-stack/ marker files) (016-brownfield-init-bugs)
- Python 3.11+ + stdlib (`pathlib`, `tomllib`, `dataclasses`, `enum`, `logging`); existing `uv_project.scan_root_python_sources()` for repo-root scanning (017-package-layout-detection)
- N/A (filesystem detection only; no new persistence) (017-package-layout-detection)
- Python 3.11+ + stdlib (`pathlib`, `tomllib`, `subprocess`), `tomli_w` (init-time config write), existing pipeline/module infrastructure in `dev_stack` (018-soften-sphinx-warnings)
- Filesystem only (`pyproject.toml`, generated `docs/Makefile`) (018-soften-sphinx-warnings)
- Python 3.11+ + existing CLI/runtime stack (`click`, `rich`, `pathspec`, `PyYAML`, `gitlint-core`), stdlib (`json`, `pathlib`, `subprocess`, `hashlib`, `dataclasses`) (019-understand-anything-swap)
- Repository-tracked JSON artifacts under `.understand-anything/` plus internal state under `.dev-stack/viz/` and `.gitattributes` for LFS policy (019-understand-anything-swap)

- Python 3.11+ + `click` (CLI framework), `tomli`/`tomli-w` (TOML read/write), `rich` (terminal output), `d2` CLI (diagrams) (001-dev-stack-ecosystem)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 019-understand-anything-swap: Added Python 3.11+ + existing CLI/runtime stack (`click`, `rich`, `pathspec`, `PyYAML`, `gitlint-core`), stdlib (`json`, `pathlib`, `subprocess`, `hashlib`, `dataclasses`)
- 018-soften-sphinx-warnings: Added Python 3.11+ + stdlib (`pathlib`, `tomllib`, `subprocess`), `tomli_w` (init-time config write), existing pipeline/module infrastructure in `dev_stack`
- 017-package-layout-detection: Added Python 3.11+ + stdlib (`pathlib`, `tomllib`, `dataclasses`, `enum`, `logging`); existing `uv_project.scan_root_python_sources()` for repo-root scanning


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
