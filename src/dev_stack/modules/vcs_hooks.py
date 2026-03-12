"""VcsHooksModule — git hook lifecycle management for dev-stack."""

from __future__ import annotations

import hashlib
import json
import shutil
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import tomli_w

from ..brownfield import markers
from ..brownfield.conflict import ConflictType, FileConflict
from ..errors import ConflictError, DevStackError
from ..modules.base import ModuleBase, ModuleResult, ModuleStatus
from ..vcs import load_vcs_config

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates"
HOOK_TEMPLATE_DIR = TEMPLATE_DIR / "hooks"

# Agent CLI → canonical instruction file (relative to repo root)
AGENT_FILE_MAP: dict[str, str] = {
    "claude": "CLAUDE.md",
    "copilot": ".github/copilot-instructions.md",
    "cursor": ".cursorrules",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class HookEntry:
    """Single hook record in the manifest."""

    checksum: str  # SHA-256 hex digest
    installed_at: str  # ISO 8601 timestamp
    template_version: str  # Version of the hook template


@dataclass
class HookManifest:
    """JSON ledger tracking all managed hooks."""

    version: str  # Schema version ("1.0")
    created: str  # ISO 8601
    updated: str  # ISO 8601
    hooks: dict[str, HookEntry] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "version": self.version,
            "created": self.created,
            "updated": self.updated,
            "hooks": {},
        }
        for name, entry in self.hooks.items():
            result["hooks"][name] = asdict(entry)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookManifest:
        hooks: dict[str, HookEntry] = {}
        for name, raw in data.get("hooks", {}).items():
            hooks[name] = HookEntry(
                checksum=raw["checksum"],
                installed_at=raw["installed_at"],
                template_version=raw["template_version"],
            )
        return cls(
            version=data["version"],
            created=data["created"],
            updated=data["updated"],
            hooks=hooks,
        )


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


_DEFAULT_DS_CONFIG: dict[str, Any] = {
    "hooks": {
        "commit-msg": True,
        "pre-push": True,
        "pre-commit": True,
    },
    "branch": {
        "pattern": "^(main|master|develop|feature/.+|bugfix/.+|hotfix/.+|release/.+)$",
        "exempt": ["main", "master"],
    },
    "signing": {
        "required": False,
    },
    "pipeline": {
        "visualize": True,
    },
}


def _ensure_devstack_config(pyproject_path: Path) -> bool:
    """Write default ``[tool.dev-stack.*]`` sections if missing. Returns True if modified."""
    if not pyproject_path.exists():
        return False
    with open(pyproject_path, "rb") as fh:
        data = tomllib.load(fh)

    tool = data.setdefault("tool", {})
    ds = tool.setdefault("dev-stack", {})

    modified = False
    for section, defaults in _DEFAULT_DS_CONFIG.items():
        if section not in ds:
            ds[section] = defaults
            modified = True

    if modified:
        with open(pyproject_path, "wb") as fh:
            tomli_w.dump(data, fh)
    return modified


class VcsHooksModule(ModuleBase):
    """Manages git hooks, constitutional practices, and signing config."""

    NAME: str = "vcs_hooks"
    VERSION: str = "0.1.0"
    DEPENDS_ON: Sequence[str] = ()
    MANAGED_FILES: Sequence[str] = (
        ".git/hooks/commit-msg",
        ".git/hooks/pre-push",
        ".dev-stack/hooks-manifest.json",
        ".dev-stack/instructions.md",
        ".specify/templates/constitution-template.md",
        "cliff.toml",
    )

    MANAGED_HEADER: str = "# managed by dev-stack — do not edit manually"

    # -- Lifecycle ----------------------------------------------------------

    def install(self, *, force: bool = False) -> ModuleResult:
        """Install managed hooks, constitutional templates, and optionally configure signing."""
        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []

        self._ensure_git(warnings)

        config = load_vcs_config(self.repo_root)

        # Determine which hooks to install based on config
        hooks_to_install: list[tuple[str, str]] = []
        if config.hooks.commit_msg:
            hooks_to_install.append(("commit-msg", "commit-msg.py"))
        if config.hooks.pre_push:
            hooks_to_install.append(("pre-push", "pre-push.py"))
        if config.hooks.pre_commit:
            hooks_to_install.append(("pre-commit", "pre-commit.py"))

        # Install each hook
        for hook_name, template_name in hooks_to_install:
            installed = self._install_hook(
                hook_name, template_name, force, created, modified, warnings
            )

        # Write manifest
        now = datetime.now(timezone.utc).isoformat()
        manifest = self._load_manifest()
        if manifest is None:
            manifest = HookManifest(version="1.0", created=now, updated=now)
        manifest.updated = now

        # Record installed hooks in manifest
        for hook_name, _ in hooks_to_install:
            hook_path = self.repo_root / ".git" / "hooks" / hook_name
            if hook_path.exists():
                manifest.hooks[hook_name] = HookEntry(
                    checksum=self._compute_checksum(hook_path),
                    installed_at=now,
                    template_version=self.VERSION,
                )

        self._save_manifest(manifest, created, modified)

        # Generate constitutional templates & agent instructions (US4)
        self._generate_constitutional_files(created, modified, warnings)

        # Write default [tool.dev-stack.*] sections to pyproject.toml
        pyproject = self.repo_root / "pyproject.toml"
        if _ensure_devstack_config(pyproject):
            if pyproject not in modified:
                modified.append(pyproject)

        # Configure SSH signing if enabled (US8)
        self._configure_signing(warnings)

        return ModuleResult(
            success=True,
            message="VCS hooks installed",
            files_created=created,
            files_modified=modified,
            warnings=warnings,
        )

    def uninstall(self) -> ModuleResult:
        """Remove managed hooks and clear manifest."""
        deleted: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []

        manifest = self._load_manifest()
        if manifest is not None:
            for hook_name, entry in manifest.hooks.items():
                hook_path = self.repo_root / ".git" / "hooks" / hook_name
                if hook_path.exists():
                    current_checksum = self._compute_checksum(hook_path)
                    if current_checksum == entry.checksum:
                        hook_path.unlink()
                        deleted.append(hook_path)
                    else:
                        warnings.append(
                            f"Hook '{hook_name}' was manually modified — skipping removal"
                        )

        # Delete manifest file
        manifest_path = self.repo_root / ".dev-stack" / "hooks-manifest.json"
        if manifest_path.exists():
            manifest_path.unlink()
            deleted.append(manifest_path)

        # Remove managed sections from agent files
        for agent_file in self._detect_agent_files():
            try:
                markers.write_managed_section(agent_file, "DEV-STACK:INSTRUCTIONS", "")
            except Exception:
                pass  # Best effort

        # Clean up proactively-created agent file (FR-010)
        agent_target = self._get_agent_file_path()
        if agent_target is not None and agent_target.exists():
            try:
                # Remove the entire managed block (markers + content)
                text = agent_target.read_text(encoding="utf-8")
                start_marker = markers._marker_pair(agent_target, "DEV-STACK:INSTRUCTIONS")[0]
                end_marker = markers._marker_pair(agent_target, "DEV-STACK:INSTRUCTIONS")[1]
                start_idx = text.find(start_marker)
                end_idx = text.find(end_marker, start_idx + len(start_marker)) if start_idx != -1 else -1
                if start_idx != -1 and end_idx != -1:
                    end_idx += len(end_marker)
                    # Strip trailing newline left by marker block
                    if end_idx < len(text) and text[end_idx] == "\n":
                        end_idx += 1
                    cleaned = text[:start_idx] + text[end_idx:]
                    remaining = cleaned.strip()
                    if not remaining:
                        agent_target.unlink()
                        deleted.append(agent_target)
                    else:
                        agent_target.write_text(cleaned, encoding="utf-8")
                        modified.append(agent_target)
            except OSError:
                pass  # Best effort

        # Remove constitutional files
        for fname in ("constitution-template.md",):
            p = self.repo_root / fname
            if p.exists():
                p.unlink()
                deleted.append(p)
        inst_path = self.repo_root / ".dev-stack" / "instructions.md"
        if inst_path.exists():
            inst_path.unlink()
            deleted.append(inst_path)

        return ModuleResult(
            success=True,
            message="VCS hooks removed",
            files_deleted=deleted,
            files_modified=modified,
            warnings=warnings,
        )

    def update(self) -> ModuleResult:
        """Update managed hooks if templates have changed."""
        modified: list[Path] = []
        warnings: list[str] = []

        manifest = self._load_manifest()
        if manifest is None:
            return ModuleResult(
                success=False,
                message="No hooks manifest found — run install first",
                warnings=["hooks-manifest.json not found"],
            )

        config = load_vcs_config(self.repo_root)

        for hook_name, entry in list(manifest.hooks.items()):
            hook_path = self.repo_root / ".git" / "hooks" / hook_name
            if not hook_path.exists():
                warnings.append(f"Hook '{hook_name}' missing from .git/hooks/ — skipping")
                continue

            current_checksum = self._compute_checksum(hook_path)
            if current_checksum == entry.checksum:
                # Unmodified — safe to update with new template
                template_name = f"{hook_name}.py"
                template_path = HOOK_TEMPLATE_DIR / template_name
                if template_path.exists():
                    template_content = template_path.read_text(encoding="utf-8")
                    hook_path.write_text(template_content, encoding="utf-8")
                    hook_path.chmod(0o755)
                    now = datetime.now(timezone.utc).isoformat()
                    manifest.hooks[hook_name] = HookEntry(
                        checksum=self._compute_checksum(hook_path),
                        installed_at=now,
                        template_version=self.VERSION,
                    )
                    modified.append(hook_path)
            else:
                warnings.append(f"Hook '{hook_name}' was manually modified — skipping update")

        manifest.updated = datetime.now(timezone.utc).isoformat()
        self._save_manifest(manifest, [], modified)

        # Refresh agent instruction file managed section on update
        created: list[Path] = []
        self._create_agent_file(created, modified, warnings)

        return ModuleResult(
            success=True,
            message="VCS hooks updated",
            files_modified=modified,
            files_created=created,
            warnings=warnings,
        )

    def verify(self) -> ModuleStatus:
        """Verify hooks are correctly installed and healthy."""
        issues: list[str] = []

        manifest = self._load_manifest()
        if manifest is None:
            return ModuleStatus(
                name=self.NAME,
                installed=False,
                version=self.VERSION,
                healthy=False,
                issue="hooks-manifest.json not found",
            )

        for hook_name, entry in manifest.hooks.items():
            hook_path = self.repo_root / ".git" / "hooks" / hook_name
            if not hook_path.exists():
                issues.append(f"Hook '{hook_name}' missing from .git/hooks/")
                continue

            # Check managed header
            first_lines = hook_path.read_text(encoding="utf-8").split("\n", 2)
            if len(first_lines) < 2 or first_lines[1].strip() != self.MANAGED_HEADER:
                issues.append(f"Hook '{hook_name}' missing managed header")

            # Checksum validation
            current_checksum = self._compute_checksum(hook_path)
            if current_checksum != entry.checksum:
                issues.append(
                    f"Hook '{hook_name}' checksum mismatch — "
                    "may have been manually modified or needs re-sync after rollback"
                )

        # Check support files
        speckit_templates_dir = self.repo_root / ".specify" / "templates"
        if speckit_templates_dir.is_dir():
            constitution = speckit_templates_dir / "constitution-template.md"
            if not constitution.exists():
                issues.append(".specify/templates/constitution-template.md missing")

        instructions = self.repo_root / ".dev-stack" / "instructions.md"
        if not instructions.exists():
            issues.append(".dev-stack/instructions.md missing")

        healthy = len(issues) == 0
        return ModuleStatus(
            name=self.NAME,
            installed=True,
            version=self.VERSION,
            healthy=healthy,
            issue="; ".join(issues) if issues else None,
        )

    # -- Internal helpers ---------------------------------------------------

    def _ensure_git(self, warnings: list[str]) -> None:
        """Verify git is available and .git/ exists."""
        if not shutil.which("git"):
            raise DevStackError("git is not available on PATH")
        git_dir = self.repo_root / ".git"
        if not git_dir.is_dir():
            raise DevStackError(f".git/ directory not found at {self.repo_root}")

    def _install_hook(
        self,
        hook_name: str,
        template_name: str,
        force: bool,
        created: list[Path],
        modified: list[Path],
        warnings: list[str],
    ) -> bool:
        """Copy a hook template to ``.git/hooks/``, set permissions, return success."""
        template_path = HOOK_TEMPLATE_DIR / template_name
        if not template_path.exists():
            warnings.append(f"Template '{template_name}' not found — skipping hook '{hook_name}'")
            return False

        hook_dest = self.repo_root / ".git" / "hooks" / hook_name
        hook_dest.parent.mkdir(parents=True, exist_ok=True)

        if hook_dest.exists():
            if self._is_managed_hook(hook_dest):
                # Overwrite managed hooks
                pass
            elif force:
                warnings.append(f"Overwriting unmanaged hook '{hook_name}' (--force)")
            else:
                raise ConflictError(
                    [
                        FileConflict(
                            path=hook_dest,
                            conflict_type=ConflictType.MODIFIED,
                            proposed_hash="",
                            current_hash="",
                        )
                    ]
                )

        template_content = template_path.read_text(encoding="utf-8")
        existed = hook_dest.exists()
        hook_dest.write_text(template_content, encoding="utf-8")
        hook_dest.chmod(0o755)

        if existed:
            modified.append(hook_dest)
        else:
            created.append(hook_dest)
        return True

    def _is_managed_hook(self, hook_path: Path) -> bool:
        """Check if a hook file has the ``# managed by dev-stack`` header."""
        try:
            content = hook_path.read_text(encoding="utf-8")
            return self.MANAGED_HEADER in content.split("\n", 3)[1] if "\n" in content else False
        except (OSError, UnicodeDecodeError):
            return False

    @staticmethod
    def _compute_checksum(path: Path) -> str:
        """SHA-256 hex digest of file content."""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _load_manifest(self) -> HookManifest | None:
        """Read ``.dev-stack/hooks-manifest.json``."""
        manifest_path = self.repo_root / ".dev-stack" / "hooks-manifest.json"
        if not manifest_path.exists():
            return None
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return HookManifest.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def _save_manifest(
        self,
        manifest: HookManifest,
        created: list[Path],
        modified: list[Path],
    ) -> None:
        """Write ``.dev-stack/hooks-manifest.json``."""
        manifest_path = self.repo_root / ".dev-stack" / "hooks-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        existed = manifest_path.exists()
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        if existed:
            modified.append(manifest_path)
        else:
            created.append(manifest_path)

    def _detect_agent_files(self) -> list[Path]:
        """Scan for known agent instruction files at repo root."""
        candidates = [
            ".github/copilot-instructions.md",
            "CLAUDE.md",
            ".cursorrules",
            "AGENTS.md",
        ]
        found: list[Path] = []
        for name in candidates:
            path = self.repo_root / name
            if path.exists():
                found.append(path)
        return found

    def _get_agent_file_path(self) -> Path | None:
        """Return absolute path for the detected agent's instruction file, or None."""
        cli = self.manifest.get("agent", {}).get("cli", "none") if self.manifest else "none"
        rel = AGENT_FILE_MAP.get(cli)
        if rel is None:
            return None
        return self.repo_root / rel

    def _create_agent_file(
        self,
        created: list[Path],
        modified: list[Path],
        warnings: list[str],
    ) -> None:
        """Proactively create the detected agent's instruction file with managed section."""
        target = self._get_agent_file_path()
        if target is None:
            return

        instructions_template = TEMPLATE_DIR / "instructions.md"
        if not instructions_template.exists():
            return

        content = instructions_template.read_text(encoding="utf-8")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            existed = target.exists()
            changed = markers.write_managed_section(target, "DEV-STACK:INSTRUCTIONS", content)
            if changed:
                if existed:
                    modified.append(target)
                else:
                    created.append(target)
        except OSError as exc:
            warnings.append(f"Could not create agent file {target.name}: {exc}")

    def _generate_constitutional_files(
        self,
        created: list[Path],
        modified: list[Path],
        warnings: list[str],
    ) -> None:
        """Generate constitution content, instructions.md, and inject into agent files.

        Implements FR-017, FR-018, FR-019 (US4) and FR-009, FR-010, FR-011 (US5).
        """
        # FR-009/FR-010: Inject baseline practices into speckit template
        constitution_template = TEMPLATE_DIR / "constitution-template.md"
        speckit_templates_dir = self.repo_root / ".specify" / "templates"
        constitution_dest = speckit_templates_dir / "constitution-template.md"
        root_constitution = self.repo_root / "constitution-template.md"

        if constitution_template.exists() and speckit_templates_dir.is_dir():
            content = constitution_template.read_text(encoding="utf-8")

            # FR-011: Reinit migration — move root constitution to speckit template
            if root_constitution.exists():
                root_text = root_constitution.read_text(encoding="utf-8")
                if root_text.lstrip().startswith("# Dev-Stack Baseline Practices"):
                    user_content = ""
                    marker = "## User-Defined Requirements"
                    marker_idx = root_text.find(marker)
                    if marker_idx != -1:
                        after_marker = root_text[marker_idx + len(marker):]
                        user_content = after_marker.strip()
                    if user_content:
                        content = content.rstrip() + "\n\n" + user_content + "\n"
                    root_constitution.unlink()

            existed = constitution_dest.exists()
            changed = markers.write_managed_section(
                constitution_dest, "DEV-STACK:CONSTITUTION", content
            )
            if changed:
                if existed:
                    modified.append(constitution_dest)
                else:
                    created.append(constitution_dest)

        # FR-018: Generate .dev-stack/instructions.md
        instructions_template = TEMPLATE_DIR / "instructions.md"
        instructions_dest = self.repo_root / ".dev-stack" / "instructions.md"
        if instructions_template.exists():
            instructions_content = instructions_template.read_text(encoding="utf-8")
            instructions_dest.parent.mkdir(parents=True, exist_ok=True)
            existed = instructions_dest.exists()
            instructions_dest.write_text(instructions_content, encoding="utf-8")
            if existed:
                modified.append(instructions_dest)
            else:
                created.append(instructions_dest)

        # FR-019: Inject managed section into detected agent files
        agent_files = self._detect_agent_files()
        if agent_files and instructions_template.exists():
            inject_content = instructions_template.read_text(encoding="utf-8")
            for agent_file in agent_files:
                try:
                    changed = self._inject_instructions(agent_file, inject_content)
                    if changed:
                        modified.append(agent_file)
                except Exception as exc:
                    warnings.append(f"Could not inject instructions into {agent_file.name}: {exc}")

        # Proactive agent file creation (010-proactive-agent-instructions)
        self._create_agent_file(created, modified, warnings)

        # FR-032: Generate cliff.toml from template
        cliff_template = TEMPLATE_DIR / "cliff.toml"
        cliff_dest = self.repo_root / "cliff.toml"
        if cliff_template.exists():
            cliff_content = cliff_template.read_text(encoding="utf-8")
            existed = cliff_dest.exists()
            cliff_dest.write_text(cliff_content, encoding="utf-8")
            if existed:
                modified.append(cliff_dest)
            else:
                created.append(cliff_dest)

    def _inject_instructions(self, file_path: Path, content: str) -> bool:
        """Inject managed section into an agent instructions file."""
        return markers.write_managed_section(file_path, "DEV-STACK:INSTRUCTIONS", content)

    def preview_files(self) -> dict[Path, str]:
        """Return proposed file contents for conflict detection."""
        result: dict[Path, str] = {}
        for template_name, hook_name in [
            ("commit-msg.py", "commit-msg"),
            ("pre-push.py", "pre-push"),
        ]:
            template_path = HOOK_TEMPLATE_DIR / template_name
            if template_path.exists():
                result[Path(f".git/hooks/{hook_name}")] = template_path.read_text(encoding="utf-8")

        # Include agent instruction file if an agent is configured
        agent_path = self._get_agent_file_path()
        if agent_path is not None:
            instructions_template = TEMPLATE_DIR / "instructions.md"
            if instructions_template.exists():
                result[agent_path.relative_to(self.repo_root)] = instructions_template.read_text(encoding="utf-8")

        return result

    def _configure_signing(self, warnings: list[str]) -> None:
        """Configure SSH signing if enabled in VcsConfig (FR-039 to FR-041)."""
        from dev_stack.vcs import load_vcs_config
        from dev_stack.vcs.signing import configure_ssh_signing

        config = load_vcs_config(self.repo_root)
        if not config.signing.enabled:
            return

        success, message = configure_ssh_signing(self.repo_root, config.signing)
        if not success:
            warnings.append(f"Signing: {message}")


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(VcsHooksModule)
