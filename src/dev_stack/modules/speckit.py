"""Spec Kit module implementation."""
from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .base import ModuleBase, ModuleResult, ModuleStatus

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "speckit"
LAZYSPECKIT_TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "lazyspeckit"
SPECIFY_DIR_NAME = ".specify"
SPEC_KIT_VERSION = "0.1.0"
SHIM_RELATIVE_PATH = Path(".dev-stack") / "bin" / "specify"
LAZYSPECKIT_PROMPT_RELATIVE_PATH = Path(".github") / "prompts" / "LazySpecKit.prompt.md"
LAZYSPECKIT_REVIEWERS_DIR_NAME = ".lazyspeckit"
PRESERVE_FILES = {Path("memory") / "constitution.md"}

# Agency reviewer mapping: (remote path in Agency repo) -> (installed filename)
_AGENCY_REPO = "msitarzewski/agency-agents"
_AGENCY_REF = "main"
_AGENCY_REVIEWER_MAP: dict[str, str] = {
    "testing/testing-reality-checker.md": "spec-compliance.md",
    "engineering/engineering-security-engineer.md": "security.md",
    "testing/testing-performance-benchmarker.md": "performance.md",
    "testing/testing-accessibility-auditor.md": "accessibility.md",
    "engineering/engineering-backend-architect.md": "architecture.md",
}

_NO_INTERACTION_HEADER = (
    "**You are a REVIEWER, not a coder.** You MUST NOT write or generate code. "
    "You MUST NOT ask the user any questions. Your role is strictly to review "
    "code, plans, tasks, and architecture — then report findings. If something "
    "is ambiguous, make a reasonable judgment call based on the spec, constitution, "
    "and codebase conventions — do not ask for clarification."
)


@dataclass(slots=True)
class _SyncResult:
    created: list[Path]
    modified: list[Path]


class SpecKitModule(ModuleBase):
    NAME = "speckit"
    VERSION = SPEC_KIT_VERSION
    MANAGED_FILES = (
        str(Path(SPECIFY_DIR_NAME)),
        str(SHIM_RELATIVE_PATH),
        str(LAZYSPECKIT_PROMPT_RELATIVE_PATH),
        str(Path(LAZYSPECKIT_REVIEWERS_DIR_NAME)),
    )

    def install(self, *, force: bool = False) -> ModuleResult:
        target_dir = self.repo_root / SPECIFY_DIR_NAME
        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []

        sync_result = self._sync_specify_tree(target_dir, overwrite=force, preserve_existing=not force)
        created.extend(sync_result.created)
        modified.extend(sync_result.modified)

        shim_created, shim_modified = self._ensure_cli_shim()
        created.extend(shim_created)
        modified.extend(shim_modified)

        prompt_created, prompt_modified = self._ensure_lazyspeckit_prompt(overwrite=force)
        created.extend(prompt_created)
        modified.extend(prompt_modified)

        reviewer_created, reviewer_modified, reviewer_warnings = self._ensure_reviewers(overwrite=force)
        created.extend(reviewer_created)
        modified.extend(reviewer_modified)
        warnings.extend(reviewer_warnings)

        warning = self._maybe_install_cli_with_uv()
        if warning:
            warnings.append(warning)

        return ModuleResult(True, "Spec Kit scaffold installed", created, modified, warnings=warnings)

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []
        specify_dir = self.repo_root / SPECIFY_DIR_NAME
        if specify_dir.exists():
            shutil.rmtree(specify_dir)
            deleted.append(specify_dir)
        shim_path = self.repo_root / SHIM_RELATIVE_PATH
        if shim_path.exists():
            shim_path.unlink()
            deleted.append(shim_path)
        prompt_path = self.repo_root / LAZYSPECKIT_PROMPT_RELATIVE_PATH
        if prompt_path.exists():
            prompt_path.unlink()
            deleted.append(prompt_path)
        reviewers_dir = self.repo_root / LAZYSPECKIT_REVIEWERS_DIR_NAME
        if reviewers_dir.exists():
            shutil.rmtree(reviewers_dir)
            deleted.append(reviewers_dir)
        return ModuleResult(True, "Spec Kit scaffold removed", files_deleted=deleted)

    def update(self) -> ModuleResult:
        target_dir = self.repo_root / SPECIFY_DIR_NAME
        warnings: list[str] = []
        sync_result = self._sync_specify_tree(target_dir, overwrite=True, preserve_existing=True)
        shim_created, shim_modified = self._ensure_cli_shim()
        prompt_created, prompt_modified = self._ensure_lazyspeckit_prompt(overwrite=True)
        reviewer_created, reviewer_modified, reviewer_warnings = self._ensure_reviewers(overwrite=True)
        warnings.extend(reviewer_warnings)
        warning = self._maybe_install_cli_with_uv()
        if warning:
            warnings.append(warning)
        created = sync_result.created + shim_created + prompt_created + reviewer_created
        modified = sync_result.modified + shim_modified + prompt_modified + reviewer_modified
        return ModuleResult(True, "Spec Kit scaffold updated", created, modified, warnings=warnings)

    def verify(self) -> ModuleStatus:
        specify_dir = self.repo_root / SPECIFY_DIR_NAME
        constitution = specify_dir / "memory/constitution.md"
        scripts_dir = specify_dir / "scripts" / "bash"
        shim_path = self.repo_root / SHIM_RELATIVE_PATH
        prompt_path = self.repo_root / LAZYSPECKIT_PROMPT_RELATIVE_PATH
        reviewers_dir = self.repo_root / LAZYSPECKIT_REVIEWERS_DIR_NAME / "reviewers"

        healthy = (
            specify_dir.exists()
            and constitution.exists()
            and scripts_dir.exists()
            and shim_path.exists()
            and prompt_path.exists()
            and reviewers_dir.exists()
        )
        issue = None
        if not specify_dir.exists():
            issue = ".specify/ directory missing"
        elif not constitution.exists():
            issue = "constitution not found"
        elif not scripts_dir.exists():
            issue = "Spec Kit scripts missing"
        elif not shim_path.exists():
            issue = "specify shim missing"
        elif not prompt_path.exists():
            issue = "LazySpecKit prompt missing"
        elif not reviewers_dir.exists():
            issue = "LazySpecKit reviewers directory missing"

        return ModuleStatus(
            name=self.NAME,
            installed=specify_dir.exists(),
            version=self.VERSION,
            healthy=healthy,
            issue=issue,
        )

    def preview_files(self) -> dict[Path, str]:
        preview: dict[Path, str] = {}
        if TEMPLATE_DIR.exists():
            for path in TEMPLATE_DIR.rglob("*"):
                if path.is_dir():
                    continue
                rel = path.relative_to(TEMPLATE_DIR)
                target = Path(SPECIFY_DIR_NAME) / rel
                preview[target] = path.read_text(encoding="utf-8")
        preview[SHIM_RELATIVE_PATH] = self._cli_shim_contents()
        prompt_src = LAZYSPECKIT_TEMPLATE_DIR / "prompts" / "LazySpecKit.prompt.md"
        if prompt_src.exists():
            preview[LAZYSPECKIT_PROMPT_RELATIVE_PATH] = prompt_src.read_text(encoding="utf-8")
        if LAZYSPECKIT_TEMPLATE_DIR.exists():
            reviewers_src = LAZYSPECKIT_TEMPLATE_DIR / "reviewers"
            if reviewers_src.exists():
                for path in reviewers_src.rglob("*"):
                    if path.is_dir():
                        continue
                    rel = path.relative_to(reviewers_src)
                    target = Path(LAZYSPECKIT_REVIEWERS_DIR_NAME) / "reviewers" / rel
                    preview[target] = path.read_text(encoding="utf-8")
        for remote_path, installed_name in _AGENCY_REVIEWER_MAP.items():
            target = Path(LAZYSPECKIT_REVIEWERS_DIR_NAME) / "reviewers" / installed_name
            preview[target] = f"(downloaded from {_AGENCY_REPO}/{remote_path} at install time)"
        return preview

    # ------------------------------------------------------------------
    def _sync_specify_tree(self, target_dir: Path, *, overwrite: bool, preserve_existing: bool) -> _SyncResult:
        created: list[Path] = []
        modified: list[Path] = []
        if not TEMPLATE_DIR.exists():
            return _SyncResult(created, modified)
        target_dir.mkdir(parents=True, exist_ok=True)
        for source_path in TEMPLATE_DIR.rglob("*"):
            if source_path.is_dir():
                (target_dir / source_path.relative_to(TEMPLATE_DIR)).mkdir(parents=True, exist_ok=True)
                continue
            rel_path = source_path.relative_to(TEMPLATE_DIR)
            destination = target_dir / rel_path
            if preserve_existing and rel_path in PRESERVE_FILES and destination.exists():
                continue
            if destination.exists():
                if not overwrite:
                    continue
                shutil.copy2(source_path, destination)
                modified.append(destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
                created.append(destination)
        return _SyncResult(created, modified)

    def _ensure_cli_shim(self) -> tuple[list[Path], list[Path]]:
        created: list[Path] = []
        modified: list[Path] = []
        shim_path = self.repo_root / SHIM_RELATIVE_PATH
        shim_path.parent.mkdir(parents=True, exist_ok=True)
        contents = self._cli_shim_contents()
        if shim_path.exists():
            current = shim_path.read_text(encoding="utf-8")
            if current == contents:
                return created, modified
            modified.append(shim_path)
        else:
            created.append(shim_path)
        shim_path.write_text(contents, encoding="utf-8")
        shim_path.chmod(0o755)
        return created, modified

    def _cli_shim_contents(self) -> str:
        return """#!/usr/bin/env bash
set -e
if command -v uv >/dev/null 2>&1; then
    exec uv tool run spec-kit -- "$@"
fi
cat <<'EOF' 1>&2
Spec Kit CLI requires the uv tool. Install uv from https://docs.astral.sh/uv/ \
then run `uv tool install spec-kit`.
EOF
exit 1
"""

    def _maybe_install_cli_with_uv(self) -> str | None:
        uv_path = shutil.which("uv")
        if not uv_path:
            return "uv CLI not found; install uv to enable Spec Kit commands"
        process = subprocess.run(
            [uv_path, "tool", "install", "spec-kit"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            cwd=self.repo_root,
            check=False,
        )
        if process.returncode != 0:
            details = process.stderr.strip() or process.stdout.strip() or "unknown error"
            return f"Failed to install Spec Kit CLI via uv: {details}"
        return None

    # ------------------------------------------------------------------
    # LazySpecKit helpers
    # ------------------------------------------------------------------

    def _ensure_lazyspeckit_prompt(self, *, overwrite: bool) -> tuple[list[Path], list[Path]]:
        """Copy the vendored LazySpecKit prompt to .github/prompts/."""
        created: list[Path] = []
        modified: list[Path] = []
        source = LAZYSPECKIT_TEMPLATE_DIR / "prompts" / "LazySpecKit.prompt.md"
        if not source.exists():
            return created, modified
        dest = self.repo_root / LAZYSPECKIT_PROMPT_RELATIVE_PATH
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if not overwrite:
                return created, modified
            if dest.read_bytes() == source.read_bytes():
                return created, modified
            shutil.copy2(source, dest)
            modified.append(dest)
        else:
            shutil.copy2(source, dest)
            created.append(dest)
        return created, modified

    def _ensure_reviewers(self, *, overwrite: bool) -> tuple[list[Path], list[Path], list[str]]:
        """Install vendored + Agency reviewer files into .lazyspeckit/reviewers/."""
        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []
        dest_dir = self.repo_root / LAZYSPECKIT_REVIEWERS_DIR_NAME / "reviewers"
        dest_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy vendored reviewers (code-quality.md, test.md)
        vendored_dir = LAZYSPECKIT_TEMPLATE_DIR / "reviewers"
        if vendored_dir.exists():
            for source in vendored_dir.iterdir():
                if source.is_dir():
                    continue
                dest = dest_dir / source.name
                if dest.exists():
                    if not overwrite:
                        continue
                    if dest.read_bytes() == source.read_bytes():
                        continue
                    shutil.copy2(source, dest)
                    modified.append(dest)
                else:
                    shutil.copy2(source, dest)
                    created.append(dest)

        # 2. Download Agency reviewers
        for remote_path, installed_name in _AGENCY_REVIEWER_MAP.items():
            dest = dest_dir / installed_name
            if dest.exists() and not overwrite:
                continue
            warning = self._download_agency_reviewer(remote_path, dest)
            if warning:
                warnings.append(warning)
            elif dest.exists():
                # File was just written by _download_agency_reviewer
                if dest in created or dest in modified:
                    continue
                # If it existed before the download, count as modified; otherwise created
                # Since we write-then-track, just add to created
                created.append(dest)

        return created, modified, warnings

    def _download_agency_reviewer(self, remote_path: str, dest: Path) -> str | None:
        """Download a single reviewer from the Agency repo and inject the no-interaction header."""
        url = f"https://raw.githubusercontent.com/{_AGENCY_REPO}/{_AGENCY_REF}/{remote_path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dev-stack"})  # noqa: S310
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                content = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            return f"Failed to download {remote_path}: {exc}"
        content = self._inject_no_interaction_header(content)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return None

    @staticmethod
    def _inject_no_interaction_header(content: str) -> str:
        """Insert the no-interaction header after the YAML front-matter closing ``---``."""
        lines = content.split("\n")
        # Find the closing --- of YAML frontmatter (second ---)
        fence_count = 0
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip() == "---":
                fence_count += 1
                if fence_count == 2:
                    insert_idx = i + 1
                    break
        if insert_idx:
            lines.insert(insert_idx, "")
            lines.insert(insert_idx + 1, f"> {_NO_INTERACTION_HEADER}")
            lines.insert(insert_idx + 2, "")
        return "\n".join(lines)


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(SpecKitModule)
