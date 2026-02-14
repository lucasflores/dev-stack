"""Incremental visualization helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from .scanner import FileSnapshot


STATE_DIR = Path(".dev-stack/viz")


@dataclass(slots=True)
class FileEntry:
    hash: str
    lines: int


@dataclass(slots=True)
class VisualizationManifest:
    files: dict[str, FileEntry]
    generated_at: str | None = None

    @classmethod
    def empty(cls) -> "VisualizationManifest":
        return cls(files={})

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "files": {path: {"hash": entry.hash, "lines": entry.lines} for path, entry in self.files.items()},
        }


class ManifestStore:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self.state_dir = self.repo_root / STATE_DIR
        self.manifest_path = self.state_dir / "manifest.json"
        self.schema_path = self.state_dir / "overview.json"

    # ------------------------------------------------------------------
    # Manifest helpers
    def load_manifest(self) -> VisualizationManifest:
        if not self.manifest_path.exists():
            return VisualizationManifest.empty()
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        file_block = data.get("files") if isinstance(data, dict) else data
        files = {path: FileEntry(**entry) for path, entry in (file_block or {}).items()}
        generated_at = data.get("generated_at") if isinstance(data, dict) else None
        return VisualizationManifest(files=files, generated_at=generated_at)

    def save_manifest(self, manifest: VisualizationManifest) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")

    def build_manifest(self, snapshots: Iterable["FileSnapshot"]) -> VisualizationManifest:
        files: dict[str, FileEntry] = {}
        for snapshot in snapshots:
            rel = str(snapshot.relative_path)
            files[rel] = FileEntry(hash=snapshot.digest, lines=snapshot.line_count)
        timestamp = datetime.now(timezone.utc).isoformat()
        return VisualizationManifest(files=files, generated_at=timestamp)

    def changed_paths(
        self,
        previous: VisualizationManifest,
        current: VisualizationManifest,
    ) -> set[str]:
        changed: set[str] = set()
        for path, entry in current.files.items():
            prior = previous.files.get(path)
            if prior is None or prior.hash != entry.hash:
                changed.add(path)
        removed = set(previous.files.keys()) - set(current.files.keys())
        changed.update(removed)
        return changed

    # ------------------------------------------------------------------
    # Schema helpers
    def load_schema(self) -> dict | None:
        if not self.schema_path.exists():
            return None
        return json.loads(self.schema_path.read_text(encoding="utf-8"))

    def save_schema(self, schema: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")