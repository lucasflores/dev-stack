"""Docker module implementation."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict

from ..brownfield.conflict import ConflictType, FileConflict
from ..errors import ConflictError
from .base import ModuleBase, ModuleResult, ModuleStatus

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "docker"
TEMPLATE_MAP: Dict[str, Path] = {
    "Dockerfile": TEMPLATE_DIR / "Dockerfile",
    "docker-compose.yml": TEMPLATE_DIR / "docker-compose.yml",
    ".dockerignore": TEMPLATE_DIR / ".dockerignore",
}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DockerModule(ModuleBase):
    NAME = "docker"
    VERSION = "0.1.2"
    MANAGED_FILES = tuple(TEMPLATE_MAP.keys())

    def install(self, *, force: bool = False) -> ModuleResult:
        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []
        conflicts: list[FileConflict] = []

        for rel_path, template_path in TEMPLATE_MAP.items():
            if not template_path.exists():
                warnings.append(f"Template missing: {template_path.name}")
                continue
            destination = self.repo_root / rel_path
            desired_text = template_path.read_text(encoding="utf-8")
            if destination.exists() and not force:
                current_text = destination.read_text(encoding="utf-8")
                if current_text == desired_text:
                    continue
                conflicts.append(
                    FileConflict(
                        path=destination,
                        conflict_type=ConflictType.MODIFIED,
                        current_hash=_hash_text(current_text),
                        proposed_hash=_hash_text(desired_text),
                    )
                )
                continue
            existed = destination.exists()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(desired_text, encoding="utf-8")
            destination.chmod(0o644)
            if existed:
                modified.append(destination)
            else:
                created.append(destination)

        if conflicts and not force:
            raise ConflictError(conflicts)

        message = "Docker assets installed"
        return ModuleResult(True, message, files_created=created, files_modified=modified, warnings=warnings)

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []
        for rel_path in self.MANAGED_FILES:
            target = self.repo_root / rel_path
            if target.exists():
                target.unlink()
                deleted.append(target)
        return ModuleResult(True, "Docker assets removed", files_deleted=deleted)

    def update(self) -> ModuleResult:
        return self.install(force=True)

    def verify(self) -> ModuleStatus:
        missing = [path for path in self.MANAGED_FILES if not (self.repo_root / path).exists()]
        issues: list[str] = []
        if missing:
            issues.append(f"Missing files: {', '.join(missing)}")
        dockerfile_path = self.repo_root / "Dockerfile"
        compose_path = self.repo_root / "docker-compose.yml"
        dockerignore_path = self.repo_root / ".dockerignore"
        if dockerfile_path.exists():
            dockerfile_text = dockerfile_path.read_text(encoding="utf-8")
            if "dev-stack" not in dockerfile_text:
                issues.append("Dockerfile missing dev-stack CLI instructions")
            if "uv pip install" not in dockerfile_text:
                issues.append("Dockerfile missing uv-based dependency installation")
        if compose_path.exists():
            compose_text = compose_path.read_text(encoding="utf-8")
            if "dev-stack" not in compose_text:
                issues.append("docker-compose.yml missing dev-stack service command")
        if dockerignore_path.exists():
            dockerignore_text = dockerignore_path.read_text(encoding="utf-8")
            required_patterns = (".dev-stack/", ".specify/", "node_modules/", "__pycache__/")
            for pattern in required_patterns:
                if pattern not in dockerignore_text:
                    issues.append(f".dockerignore missing pattern: {pattern}")
        healthy = not issues and not missing
        return ModuleStatus(
            name=self.NAME,
            installed=not missing,
            version=self.VERSION,
            healthy=healthy,
            issue="; ".join(issues) if issues else None,
            config={"files": list(self.MANAGED_FILES)},
        )

    def preview_files(self) -> dict[Path, str]:
        preview: dict[Path, str] = {}
        for rel_path, template_path in TEMPLATE_MAP.items():
            if not template_path.exists():
                continue
            preview[Path(rel_path)] = template_path.read_text(encoding="utf-8")
        return preview


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(DockerModule)
