# dev-stack Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-10

## Active Technologies
- File-based -- `dev-stack.toml` manifest, `.dev-stack/` working directory, `.specify/` for Spec Ki (001-dev-stack-ecosystem)
- Python 3.11+ (project uses `requires-python = ">=3.11"`) + click, tomli-w, rich, pathspec (existing); uv CLI (external, v0.5+), sphinx + sphinx-autodoc-typehints + myst-parser (optional docs), mypy (optional dev) (002-init-pipeline-enhancements)
- TOML files (`dev-stack.toml` manifest, `pyproject.toml`); filesystem artifacts (002-init-pipeline-enhancements)

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
- 002-init-pipeline-enhancements: Added Python 3.11+ (project uses `requires-python = ">=3.11"`) + click, tomli-w, rich, pathspec (existing); uv CLI (external, v0.5+), sphinx + sphinx-autodoc-typehints + myst-parser (optional docs), mypy (optional dev)
- 001-dev-stack-ecosystem: Added Python 3.11+ + `click` (CLI framework), `tomli`/`tomli-w` (TOML read/write), `rich` (terminal output), `d2` CLI (diagrams)

- 001-dev-stack-ecosystem: Added Python 3.11+ + `click` (CLI framework), `tomli`/`tomli-w` (TOML read/write), `rich` (terminal output), `d2` CLI (diagrams)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
