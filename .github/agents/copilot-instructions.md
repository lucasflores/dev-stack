# dev-stack Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-10

## Active Technologies
- File-based -- `dev-stack.toml` manifest, `.dev-stack/` working directory, `.specify/` for Spec Ki (001-dev-stack-ecosystem)
- Python 3.11+ (project uses `requires-python = ">=3.11"`) + click, tomli-w, rich, pathspec (existing); uv CLI (external, v0.5+), sphinx + sphinx-autodoc-typehints + myst-parser (optional docs), mypy (optional dev) (002-init-pipeline-enhancements)
- TOML files (`dev-stack.toml` manifest, `pyproject.toml`); filesystem artifacts (002-init-pipeline-enhancements)
- Python 3.11+ + click >=8.1, rich, pathspec (existing); CodeBoarding CLI (external subprocess, not imported) (003-codeboarding-viz)
- File-based JSON (.codeboarding/analysis.json, .codeboarding/injected-readmes.json, .dev-stack/viz/manifest.json) (003-codeboarding-viz)
- Python 3.11+ + click (CLI), gitlint-core (commit linting), rich (output formatting), tomli-w (TOML writing), pathspec (file matching). Optional: git-cliff (changelog), python-semantic-release (release), gh/glab (PR creation). (004-vcs-best-practices)
- `.dev-stack/hooks-manifest.json` (JSON), `cliff.toml` (TOML config), `pyproject.toml` (existing) (004-vcs-best-practices)
- Python 3.11+ + click (CLI), tomllib (pyproject parsing), subprocess (stage execution), uv (package management) (006-init-pipeline-bugfixes)
- `dev-stack.toml` (TOML manifest), `.secrets.baseline` (JSON), `.dev-stack/pipeline/last-run.json` (006-init-pipeline-bugfixes)

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
- 006-init-pipeline-bugfixes: Added Python 3.11+ + click (CLI), tomllib (pyproject parsing), subprocess (stage execution), uv (package management)
- 004-vcs-best-practices: Added Python 3.11+ + click (CLI), gitlint-core (commit linting), rich (output formatting), tomli-w (TOML writing), pathspec (file matching). Optional: git-cliff (changelog), python-semantic-release (release), gh/glab (PR creation).
- 003-codeboarding-viz: Added Python 3.11+ + click >=8.1, rich, pathspec (existing); CodeBoarding CLI (external subprocess, not imported)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
