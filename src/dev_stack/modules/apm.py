"""APM module — delegates MCP server management to Microsoft's Agent Package Manager CLI."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Sequence

import yaml
from packaging.version import Version

from .base import ModuleBase, ModuleResult, ModuleStatus

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "apm"
DEFAULT_TEMPLATE = TEMPLATE_DIR / "default-apm.yml"

# APM manifest and lockfile names
MANIFEST_FILE = "apm.yml"
LOCKFILE = "apm.lock.yaml"


class APMModule(ModuleBase):
    """Manage MCP servers via the APM CLI."""

    NAME = "apm"
    VERSION = "0.1.0"
    DEPENDS_ON: Sequence[str] = ()
    MANAGED_FILES: Sequence[str] = (MANIFEST_FILE, LOCKFILE)
    MIN_APM_VERSION = "0.8.0"
    DEFAULT_SERVERS: tuple[str, ...] = (
        "io.github.upstash/context7",
        "io.github.github/github-mcp-server",
        "huggingface/hf-mcp-server",
    )
    DEFAULT_APM_PACKAGES: tuple[str, ...] = (
        "lucasflores/agent-skills",
    )

    def __init__(self, repo_root: Path, manifest: dict[str, Any] | None = None) -> None:
        super().__init__(repo_root, manifest)

    # ── Public API (ModuleBase) ──────────────────────────────────────

    def install(self, *, force: bool = False) -> ModuleResult:
        """Bootstrap apm.yml and run ``apm install``."""
        ok, msg = self._check_apm_cli()
        if not ok:
            return ModuleResult(
                success=False,
                message=msg,
                warnings=[msg],
            )

        manifest_path = self._bootstrap_manifest(force=force)
        result = self._run_apm(["install"])
        return self._parse_install_result(result, manifest_path)

    def uninstall(self) -> ModuleResult:
        """Remove apm.yml and apm.lock.yaml."""
        deleted: list[Path] = []
        for name in (MANIFEST_FILE, LOCKFILE):
            target = self.repo_root / name
            if target.exists():
                target.unlink()
                deleted.append(target)
        return ModuleResult(True, "Removed APM manifest and lockfile", files_deleted=deleted)

    def update(self) -> ModuleResult:
        """Re-run apm install against existing manifest."""
        return self.install(force=True)

    def verify(self) -> ModuleStatus:
        """Check APM CLI, manifest, and lockfile health."""
        issues: list[str] = []

        # 1. APM CLI on PATH
        ok, version_msg = self._check_apm_cli()
        if not ok:
            return ModuleStatus(
                name=self.NAME,
                installed=False,
                version=self.VERSION,
                healthy=False,
                issue=version_msg,
            )

        # 2. apm.yml exists
        manifest_path = self.repo_root / MANIFEST_FILE
        installed = manifest_path.exists()
        if not installed:
            return ModuleStatus(
                name=self.NAME,
                installed=False,
                version=self.VERSION,
                healthy=False,
                issue=f"{MANIFEST_FILE} not found",
            )

        # 3. apm.lock.yaml exists and staleness check
        lockfile_path = self.repo_root / LOCKFILE
        if not lockfile_path.exists():
            issues.append(f"{LOCKFILE} missing — run 'dev-stack apm install'")
        elif lockfile_path.stat().st_mtime < manifest_path.stat().st_mtime:
            issues.append(
                f"{LOCKFILE} is stale — {MANIFEST_FILE} was modified after last install"
            )

        healthy = len(issues) == 0
        issue = "; ".join(issues) if issues else None
        return ModuleStatus(
            name=self.NAME,
            installed=True,
            version=self.VERSION,
            healthy=healthy,
            issue=issue,
        )

    def preview_files(self) -> dict[Path, str]:
        """Return the default apm.yml template content.

        Returns an empty dict when the APM CLI is unavailable, since
        install() will early-return without writing any files in that case.
        This prevents false conflict reports for apm.yml.
        """
        ok, _ = self._check_apm_cli()
        if not ok:
            return {}
        project_name = self.repo_root.name
        content = self._render_template(project_name)
        return {Path(MANIFEST_FILE): content}

    def audit(
        self, *, fmt: str = "text", output: Path | None = None
    ) -> ModuleResult:
        """Run ``apm audit`` with the given format and optional output file."""
        ok, msg = self._check_apm_cli()
        if not ok:
            return ModuleResult(success=False, message=msg, warnings=[msg])

        args = ["audit", "-f", fmt]
        if output is not None:
            args.extend(["-o", str(output)])
        result = self._run_apm(args)

        if result.returncode == 0:
            return ModuleResult(
                success=True,
                message="Audit clean — no findings",
            )
        # Non-zero: findings or error
        stderr_text = result.stderr.strip()
        stdout_text = result.stdout.strip()
        report = stderr_text or stdout_text
        return ModuleResult(
            success=False,
            message=f"Audit found issues (exit {result.returncode})",
            warnings=[report] if report else [],
        )

    # ── Private helpers ──────────────────────────────────────────────

    def _check_apm_cli(self) -> tuple[bool, str]:
        """Verify APM binary exists on PATH and meets minimum version."""
        import re as _re

        apm_path = shutil.which("apm")
        if apm_path is None:
            return False, "APM CLI not found on PATH — install from https://github.com/microsoft/apm"

        try:
            result = subprocess.run(
                ["apm", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            raw = result.stdout.strip()
            if not raw:
                return False, "Could not determine APM CLI version"
            # FR-003: Strip ANSI escape sequences, then extract semver pattern
            stripped = _re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw)
            match = _re.search(r'\d+\.\d+\.\d+', stripped)
            if not match:
                return False, f"Could not parse version from APM output: {raw!r}"
            version_str = match.group(0)
            detected = Version(version_str)
            minimum = Version(self.MIN_APM_VERSION)
            if detected < minimum:
                return (
                    False,
                    f"APM CLI {detected} is below minimum {self.MIN_APM_VERSION}",
                )
            return True, f"APM CLI v{detected} detected"
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as exc:
            return False, f"APM CLI version check failed: {exc}"

    def _bootstrap_manifest(self, *, force: bool = False, strategy: str | None = None) -> Path:
        """Create or update apm.yml at repo root.

        If apm.yml already exists and ``force`` is False, prompt user for action.
        ``strategy`` can be "skip", "merge", or "overwrite" to bypass the prompt.
        """
        import click

        manifest_path = self.repo_root / MANIFEST_FILE
        project_name = self.repo_root.name

        if not manifest_path.exists() or force:
            content = self._render_template(project_name)
            manifest_path.write_text(content, encoding="utf-8")
            return manifest_path

        # Existing file — determine strategy
        if strategy is None:
            if not click.get_text_stream("stdin").isatty():
                # Non-interactive (CI) — default to skip
                strategy = "skip"
            else:
                strategy = click.prompt(
                    f"{MANIFEST_FILE} already exists. Choose action",
                    type=click.Choice(["skip", "merge", "overwrite"]),
                    default="skip",
                )

        if strategy == "skip":
            return manifest_path
        elif strategy == "overwrite":
            content = self._render_template(project_name)
            manifest_path.write_text(content, encoding="utf-8")
            return manifest_path
        elif strategy == "merge":
            self._merge_manifest(manifest_path)
            return manifest_path

        return manifest_path

    def _merge_manifest(self, manifest_path: Path) -> None:
        """Additively merge default servers and packages into an existing apm.yml."""
        existing_text = manifest_path.read_text(encoding="utf-8")
        existing = yaml.safe_load(existing_text) or {}

        deps = existing.setdefault("dependencies", {})

        # Merge MCP servers
        mcp_list: list[str | dict] = deps.get("mcp", [])
        existing_mcp_names: set[str] = set()
        for entry in mcp_list:
            if isinstance(entry, str):
                existing_mcp_names.add(entry)
            elif isinstance(entry, dict) and "name" in entry:
                existing_mcp_names.add(entry["name"])
        for server in self.DEFAULT_SERVERS:
            if server not in existing_mcp_names:
                mcp_list.append(server)
        deps["mcp"] = mcp_list

        # Merge APM packages
        apm_list: list[str | dict] = deps.get("apm", [])
        existing_apm_names: set[str] = set()
        for entry in apm_list:
            name = entry if isinstance(entry, str) else entry.get("name", "")
            # Strip pinning suffix for deduplication (e.g., "owner/repo#tag" → "owner/repo")
            existing_apm_names.add(name.split("#")[0])
        for pkg in self.DEFAULT_APM_PACKAGES:
            if pkg.split("#")[0] not in existing_apm_names:
                apm_list.append(pkg)
        deps["apm"] = apm_list

        manifest_path.write_text(
            yaml.dump(existing, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

    def _run_apm(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Execute APM CLI as a subprocess.

        Timeouts are treated as install failures (non-zero return code) rather
        than raising, so callers can surface warnings without aborting init.
        """
        timeout_seconds = self._apm_timeout_seconds()
        command = ["apm", *args]
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(
                errors="replace"
            )
            stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(
                errors="replace"
            )
            timeout_msg = (
                f"APM command timed out after {timeout_seconds}s: {' '.join(command)}"
            )
            combined_stderr = f"{stderr}\n{timeout_msg}".strip() if stderr else timeout_msg
            return subprocess.CompletedProcess(
                args=command,
                returncode=124,
                stdout=stdout,
                stderr=combined_stderr,
            )

    def _apm_timeout_seconds(self) -> int:
        raw = os.environ.get("DEV_STACK_APM_TIMEOUT_SECONDS") or os.environ.get("DEV_STACK_APM_TIMEOUT")
        if raw:
            try:
                value = int(raw)
                if value > 0:
                    return value
            except ValueError:
                pass
        # Keep init responsive when APM registry/network is slow.
        return 45

    def _parse_install_result(
        self,
        result: subprocess.CompletedProcess[str],
        manifest_path: Path,
    ) -> ModuleResult:
        """Parse apm install output for per-server success/failure."""
        files_created: list[Path] = []
        warnings: list[str] = []

        if manifest_path.exists():
            files_created.append(manifest_path)

        lockfile_path = self.repo_root / LOCKFILE
        if lockfile_path.exists():
            files_created.append(lockfile_path)

        if result.returncode == 0:
            return ModuleResult(
                success=True,
                message="All MCP servers installed successfully",
                files_created=files_created,
            )

        # Partial or full failure — parse stderr for details
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        output = stderr or stdout

        if output:
            for line in output.splitlines():
                line = line.strip()
                if line:
                    warnings.append(line)

        return ModuleResult(
            success=False,
            message=f"APM install failed (exit {result.returncode})",
            files_created=files_created,
            warnings=warnings,
        )

    def _render_template(self, project_name: str) -> str:
        """Load and render the default apm.yml template."""
        template = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
        return template.replace("{{ PROJECT_NAME }}", project_name)


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(APMModule)
