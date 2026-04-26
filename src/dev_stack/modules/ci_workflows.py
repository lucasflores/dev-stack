"""CI workflows module implementation."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict


from ..brownfield.conflict import ConflictType, FileConflict
from ..errors import ConflictError
from .base import ModuleBase, ModuleResult, ModuleStatus

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "ci"
WORKFLOWS_DIR = Path(".github") / "workflows"
WORKFLOW_TEMPLATES: Dict[str, Path] = {
    "dev-stack-tests.yml": TEMPLATE_DIR / "dev-stack-tests.yml",
    "dev-stack-deploy.yml": TEMPLATE_DIR / "dev-stack-deploy.yml",
    "dev-stack-vuln-scan.yml": TEMPLATE_DIR / "dev-stack-vuln-scan.yml",
}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class CIWorkflowsModule(ModuleBase):
    NAME = "ci-workflows"
    MANAGED_FILES = tuple(str(WORKFLOWS_DIR / name) for name in WORKFLOW_TEMPLATES)

    def install(self, *, force: bool = False) -> ModuleResult:
        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []
        target_dir = self.repo_root / WORKFLOWS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        for filename, template_path in WORKFLOW_TEMPLATES.items():
            if not template_path.exists():
                warnings.append(f"Template missing: {template_path.name}")
                continue
            destination = target_dir / filename
            desired_text = template_path.read_text(encoding="utf-8")
            if destination.exists() and not force:
                current_text = destination.read_text(encoding="utf-8")
                if current_text == desired_text:
                    continue
                raise ConflictError(
                    [
                        FileConflict(
                            path=destination,
                            conflict_type=ConflictType.MODIFIED,
                            current_hash=_hash_text(current_text),
                            proposed_hash=_hash_text(desired_text),
                        )
                    ]
                )
            existed = destination.exists()
            destination.write_text(desired_text, encoding="utf-8")
            destination.chmod(0o644)
            if existed:
                modified.append(destination)
            else:
                created.append(destination)

        message = "CI workflows installed"
        return ModuleResult(True, message, files_created=created, files_modified=modified, warnings=warnings)

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []
        for filename in WORKFLOW_TEMPLATES:
            target = self.repo_root / WORKFLOWS_DIR / filename
            if target.exists():
                target.unlink()
                deleted.append(target)
        return ModuleResult(True, "CI workflows removed", files_deleted=deleted)

    def update(self) -> ModuleResult:
        return self.install(force=True)

    def verify(self) -> ModuleStatus:
        missing: list[str] = []
        justification_issues: list[str] = []
        freshness_check_issues: list[str] = []
        for filename in WORKFLOW_TEMPLATES:
            target = self.repo_root / WORKFLOWS_DIR / filename
            if not target.exists():
                missing.append(filename)
                continue
            contents = target.read_text(encoding="utf-8")
            if "Cloud justification" not in contents:
                justification_issues.append(filename)
            if filename == "dev-stack-tests.yml" and "dev-stack-graph-freshness" not in contents:
                freshness_check_issues.append(filename)
        healthy = not missing and not justification_issues and not freshness_check_issues
        issues: list[str] = []
        if missing:
            issues.append(f"Missing workflows: {', '.join(missing)}")
        if justification_issues:
            issues.append(f"Missing justification comments: {', '.join(justification_issues)}")
        if freshness_check_issues:
            issues.append(
                "Missing required graph freshness check job 'dev-stack-graph-freshness' in: "
                + ", ".join(freshness_check_issues)
            )
        return ModuleStatus(
            name=self.NAME,
            installed=not missing,
            version=self.version,
            healthy=healthy,
            issue="; ".join(issues) if issues else None,
            config={"workflows": list(WORKFLOW_TEMPLATES.keys())},
        )

    def preview_files(self) -> dict[Path, str]:
        preview: dict[Path, str] = {}
        for filename, template_path in WORKFLOW_TEMPLATES.items():
            if not template_path.exists():
                continue
            preview[WORKFLOWS_DIR / filename] = template_path.read_text(encoding="utf-8")
        return preview


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(CIWorkflowsModule)
