"""Implementation of the `dev-stack init` command."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Sequence

import click

from ..brownfield.conflict import (
    ConflictReport,
    ConflictType,
    build_conflict_report,
    echo_conflict_summary,
    is_greenfield_uv_package,
    resolve_conflicts_interactively,
    serialize_conflicts,
)
from ..brownfield.rollback import create_rollback_tag
from ..brownfield.markers import write_managed_section
from ..config import AgentInfo, detect_agent
from ..errors import ManifestError
from ..manifest import AgentConfig, StackManifest, create_default, read_manifest, write_manifest
from ..modules import instantiate_modules, resolve_module_names
from ..modules.base import ModuleBase
from ._constants import MANIFEST_FILENAME
from ._shared import (
    apply_post_install_overrides,
    collect_proposed_files,
    emit_manifest_error,
    ensure_git_repo,
    has_existing_conflicts,
    parse_modules,
)
from .main import CLIContext, ExitCode, cli


@cli.command("init")
@click.option("--modules", "modules_csv", help="Comma-separated list of modules to install")
@click.option("--force", is_flag=True, help="Overwrite existing files managed by dev-stack")
@click.pass_obj
def init_command(ctx: CLIContext, modules_csv: str | None, force: bool) -> None:
    """Initialize a repository with dev-stack automation."""

    repo_root = Path.cwd()

    ensure_git_repo(repo_root)

    manifest_path = repo_root / MANIFEST_FILENAME
    already_initialized = manifest_path.exists()
    existing_manifest: StackManifest | None = None
    if already_initialized:
        try:
            existing_manifest = read_manifest(manifest_path)
        except ManifestError as exc:
            emit_manifest_error(
                ctx, f"Unable to read existing manifest: {exc}", exit_code=ExitCode.GENERAL_ERROR
            )
            return
    if already_initialized and not force and not ctx.dry_run:
        _report_already_initialized(ctx)
        raise SystemExit(ExitCode.GENERAL_ERROR)

    requested_modules = parse_modules(modules_csv)
    if requested_modules:
        module_names = resolve_module_names(requested_modules, include_defaults=False)
    elif existing_manifest:
        module_names = list(existing_manifest.modules.keys())
    else:
        module_names = resolve_module_names(include_defaults=True)

    if existing_manifest and not requested_modules:
        manifest = existing_manifest
    else:
        manifest = create_default(module_names)

    should_write_manifest = not already_initialized or bool(requested_modules)
    should_create_rollback = not ctx.dry_run and should_write_manifest

    agent_info = detect_agent(manifest)
    manifest.agent = AgentConfig(cli=agent_info.cli)

    module_instances = instantiate_modules(repo_root, manifest, module_names)
    detection_map, preview_lookup = collect_proposed_files(module_instances)
    conflict_report = build_conflict_report("init", repo_root, detection_map)

    # FR-004/FR-005: Mark uv init --package files as greenfield predecessors
    is_greenfield = is_greenfield_uv_package(repo_root / "pyproject.toml")
    if is_greenfield:
        from ..layout import detect_package_layout

        layout = detect_package_layout(repo_root)
        pkg_names = layout.package_names
        predecessor_suffixes = {"pyproject.toml", ".python-version", "README.md"}
        for pkg_name in pkg_names:
            init_rel = str(layout.package_root / pkg_name / "__init__.py")
            predecessor_suffixes.add(init_rel)
        for conflict in conflict_report.conflicts:
            try:
                rel = str(conflict.path.relative_to(repo_root))
            except ValueError:
                continue
            if rel in predecessor_suffixes and conflict.resolution == "pending":
                conflict.resolution = "greenfield_predecessor"

    existing_conflicts = has_existing_conflicts(conflict_report)
    mode = _determine_mode(already_initialized, existing_conflicts)
    manifest.mode = mode

    if ctx.dry_run:
        _emit_dry_run_summary(ctx, repo_root, manifest_path, mode, module_names, conflict_report)
        return

    skip_map: dict[Path, tuple[bytes, int | None]] = {}
    merge_map: dict[Path, str] = {}
    conflicts_payload = serialize_conflicts(conflict_report, repo_root)

    if existing_conflicts and force:
        for conflict in conflict_report.conflicts:
            if conflict.resolution == "pending":
                conflict.resolution = "overwritten"
        conflicts_payload = serialize_conflicts(conflict_report, repo_root)

    if existing_conflicts and not force:
        if ctx.json_output:
            payload = {
                "status": "conflict",
                "mode": mode,
                "manifest_path": str(manifest_path),
                "modules": module_names,
                "conflicts": conflicts_payload,
                "hint": "Re-run with --force to overwrite conflicting files, "
                        "or resolve conflicts interactively without --json.",
            }
            click.echo(json.dumps(payload))
            raise SystemExit(ExitCode.CONFLICT)
        echo_conflict_summary(conflict_report, repo_root)
        skip_map, merge_map = resolve_conflicts_interactively(
            conflict_report, repo_root, preview_lookup
        )
        conflicts_payload = serialize_conflicts(conflict_report, repo_root)

    rollback_ref = manifest.rollback_ref
    if should_create_rollback:
        _ensure_initial_commit(repo_root)
        rollback_ref = create_rollback_tag(repo_root)
    if not ctx.dry_run:
        effective_force = force or existing_conflicts or is_greenfield
        _install_modules(module_instances, force=effective_force)
        apply_post_install_overrides(skip_map, merge_map)
        if "uv_project" in module_names:
            try:
                subprocess.run(["uv", "sync", "--all-extras"], cwd=str(repo_root), check=True)
            except subprocess.CalledProcessError as exc:
                msg = (
                    f"uv sync --all-extras failed (exit code {exc.returncode}). "
                    "Retry with: uv sync --extra dev --extra docs"
                )
                if ctx.json_output:
                    click.echo(json.dumps({"warning": msg}), err=True)
                else:
                    click.echo(f"Warning: {msg}", err=True)
        # TODO(012): Re-enable when a dedicated secrets module is added to _MODULE_REGISTRY
        _ensure_gitignore_managed_section(repo_root)
        # FR-004: Write brownfield-init marker for first-commit auto-format
        if not is_greenfield:
            marker_dir = repo_root / ".dev-stack"
            marker_dir.mkdir(parents=True, exist_ok=True)
            (marker_dir / "brownfield-init").touch()
            _set_brownfield_pipeline_defaults(repo_root)
        # FR-005: Detect and offer to migrate requirements.txt
        if not is_greenfield and not ctx.json_output:
            _detect_and_migrate_requirements(
                repo_root, interactive=not ctx.json_output, json_output=ctx.json_output
            )
        # FR-006: Detect root-level packages and recommend src/ layout
        if not is_greenfield and not ctx.json_output:
            _detect_root_packages(repo_root, json_output=ctx.json_output)
        if should_write_manifest:
            manifest.rollback_ref = rollback_ref
            write_manifest(manifest, manifest_path)

    _emit_init_result(
        ctx,
        mode=mode,
        modules_installed=module_names,
        manifest_path=str(manifest_path),
        rollback_ref=rollback_ref,
        agent=agent_info,
        conflicts=conflicts_payload,
    )


def _install_modules(modules: Sequence[ModuleBase], force: bool) -> None:
    for module in modules:
        module.install(force=force)


def _set_brownfield_pipeline_defaults(repo_root: Path) -> None:
    """Set ``[tool.dev-stack.pipeline] strict_docs = false`` for brownfield repos.

    Brownfield projects typically have pre-existing Sphinx warnings that
    should not be treated as fatal errors.  This writes the flag into
    ``pyproject.toml`` so the docs-api pipeline stage and generated
    Makefiles omit ``-W``.
    """
    import tomllib

    import tomli_w

    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return
    with open(pyproject, "rb") as fh:
        data = tomllib.load(fh)

    pipeline = data.setdefault("tool", {}).setdefault("dev-stack", {}).setdefault("pipeline", {})
    if "strict_docs" not in pipeline:
        pipeline["strict_docs"] = False
        with open(pyproject, "wb") as fh:
            tomli_w.dump(data, fh)


def _detect_and_migrate_requirements(repo_root: Path, interactive: bool, json_output: bool) -> None:
    """FR-005: Detect requirements.txt and offer to merge into pyproject.toml."""
    import tomllib

    import tomli_w
    from packaging.requirements import InvalidRequirement, Requirement

    req_path = repo_root / "requirements.txt"
    if not req_path.exists():
        return

    deps: list[str] = []
    for raw_line in req_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-e") or "://" in line:
            continue
        try:
            Requirement(line)
            deps.append(line)
        except InvalidRequirement:
            continue

    if not deps:
        return

    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        return

    if json_output:
        click.echo(json.dumps({"info": "requirements_detected", "dependencies": deps}))
    else:
        click.echo(f"Found {len(deps)} dependencies in requirements.txt:")
        for dep in deps:
            click.echo(f"  - {dep}")

    if not interactive:
        msg = "Non-interactive mode — skipping requirements.txt merge. Merge manually with: uv add " + " ".join(deps)
        if json_output:
            click.echo(json.dumps({"warning": msg}))
        else:
            click.echo(f"Warning: {msg}", err=True)
        return

    if not click.confirm("Merge these into pyproject.toml [project.dependencies]?", default=True):
        return

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project = data.setdefault("project", {})
    existing = project.get("dependencies", [])
    if not isinstance(existing, list):
        existing = [existing] if isinstance(existing, str) else []
    existing_names: set[str] = set()
    for d in existing:
        try:
            existing_names.add(Requirement(d).name.lower())
        except InvalidRequirement:
            continue
    added = []
    for dep in deps:
        if Requirement(dep).name.lower() not in existing_names:
            existing.append(dep)
            added.append(dep)
            existing_names.add(Requirement(dep).name.lower())
    project["dependencies"] = existing

    with open(pyproject_path, "wb") as f:
        tomli_w.dump(data, f)

    if json_output:
        click.echo(json.dumps({"info": "requirements_merged", "added": added}))
    else:
        click.echo(f"Merged {len(added)} new dependencies into pyproject.toml")


def _detect_root_packages(repo_root: Path, json_output: bool) -> None:
    """FR-006: Detect root-level Python packages and recommend src/ layout migration."""
    from ..modules.uv_project import scan_root_python_sources

    has_python, packages = scan_root_python_sources(repo_root)
    if not has_python or not packages:
        return

    if json_output:
        click.echo(json.dumps({
            "info": "root_packages_detected",
            "packages": packages,
            "recommendation": "Consider migrating to src/ layout",
        }))
    else:
        click.echo(f"Detected {len(packages)} root-level Python package(s):")
        for pkg in packages:
            click.echo(f"  - {pkg}  →  mv {pkg}/ src/{pkg}/")
        click.echo("Recommendation: migrate to src/ layout for proper uv/mypy integration.")


def _generate_secrets_baseline(repo_root: Path) -> None:
    """Generate .secrets.baseline if detect-secrets is available."""
    import shutil

    if not shutil.which("detect-secrets"):
        return
    baseline_path = repo_root / ".secrets.baseline"
    if baseline_path.exists():
        return
    with open(baseline_path, "w") as f:
        subprocess.run(
            ["detect-secrets", "scan", "--exclude-files", r"\.dev-stack/|\.secrets\.baseline"],
            cwd=str(repo_root),
            stdout=f,
            check=False,
        )


# Files under .dev-stack/ that modules expect to be tracked.
_TRACKED_DEVSTACK_FILES = ("hooks-manifest.json", "instructions.md")


def _ensure_gitignore_managed_section(repo_root: Path) -> None:
    """Ensure untracked .dev-stack/ artifacts are gitignored via a managed section.

    Ignores runtime/generated subdirs but preserves tracked files like
    hooks-manifest.json and instructions.md via negation patterns.
    """
    lines = [
        ".dev-stack/pipeline/",
        ".dev-stack/viz/",
        ".dev-stack/pipeline-skipped",
    ]
    for name in _TRACKED_DEVSTACK_FILES:
        lines.append(f"!.dev-stack/{name}")
    write_managed_section(repo_root / ".gitignore", "GITIGNORE", "\n".join(lines))


def _ensure_initial_commit(repo_root: Path) -> None:
    """Create an initial commit if the repository has no commits yet."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return  # already has commits
    subprocess.run(
        ["git", "-C", str(repo_root), "add", "-A"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-m", "chore: initial commit for dev-stack init", "--allow-empty"],
        check=True,
    )


def _emit_init_result(
    ctx: CLIContext,
    *,
    mode: str,
    modules_installed: Sequence[str],
    manifest_path: str,
    rollback_ref: str | None,
    agent: AgentInfo,
    conflicts: list[dict[str, str | None]] | None = None,
) -> None:
    payload = {
        "status": "success",
        "mode": mode,
        "manifest_path": manifest_path,
        "modules_installed": list(modules_installed),
        "rollback_ref": rollback_ref,
        "agent": {"cli": agent.cli},
    }
    payload["conflicts"] = conflicts or []
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo(
            f"dev-stack init ({mode})\n- manifest: {manifest_path}\n- modules: {', '.join(modules_installed) or 'none'}"
        )


def _determine_mode(already_initialized: bool, has_conflicts: bool) -> str:
    if already_initialized:
        return "reinit"
    if has_conflicts:
        return "brownfield"
    return "greenfield"


def _emit_dry_run_summary(
    ctx: CLIContext,
    repo_root: Path,
    manifest_path: Path,
    mode: str,
    modules: Sequence[str],
    report: ConflictReport,
) -> None:
    conflicts_payload = serialize_conflicts(report, repo_root)
    new_files: list[str] = []
    for conflict in report.conflicts:
        if conflict.conflict_type != ConflictType.NEW:
            continue
        try:
            rel = conflict.path.relative_to(repo_root)
        except ValueError:
            rel = conflict.path
        new_files.append(str(rel))
    payload = {
        "status": "dry-run",
        "mode": mode,
        "manifest_path": str(manifest_path),
        "modules": list(modules),
        "conflicts": conflicts_payload,
        "new_files": new_files,
    }
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo("Dry run summary:")
        click.echo(f" - Mode: {mode}")
        click.echo(f" - Manifest: {manifest_path}")
        click.echo(f" - Modules: {', '.join(modules) or 'none'}")
        echo_conflict_summary(report, repo_root)
        if new_files:
            click.echo("Files to be created:")
            for path in new_files:
                click.echo(f" - {path}")


def _report_already_initialized(ctx: CLIContext) -> None:
    message = "Repository already has dev-stack.toml. Use --force to reinitialize or run 'dev-stack update'."
    if ctx.json_output:
        payload = {"status": "error", "message": message}
        click.echo(json.dumps(payload))
    else:
        click.echo(message, err=True)
