"""Repository scanner for visualization inputs."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import pathspec

DEFAULT_IGNORE = (
    ".git/",
    ".dev-stack/",
    "node_modules/",
    "dist/",
    "build/",
    "venv/",
    ".venv/",
    "__pycache__/",
)


@dataclass(slots=True)
class FileSnapshot:
    path: Path
    relative_path: Path
    digest: str
    line_count: int


@dataclass(slots=True)
class ScanResult:
    snapshots: list[FileSnapshot]
    destination: Path
    skipped: list[Path]


class SourceScanner:
    """Scan the repository and emit a noodles-style combined file."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def scan(self, *, extra_ignores: Iterable[str] | None = None) -> ScanResult:
        ignore_patterns = list(DEFAULT_IGNORE)
        if extra_ignores:
            ignore_patterns.extend(extra_ignores)
        gitignore = self.repo_root / ".gitignore"
        if gitignore.exists():
            ignore_patterns.extend(
                line.strip()
                for line in gitignore.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            )
        spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)
        destination = self.repo_root / ".dev-stack" / "viz" / "scan.txt"
        destination.parent.mkdir(parents=True, exist_ok=True)
        snapshots: list[FileSnapshot] = []
        skipped: list[Path] = []
        with destination.open("w", encoding="utf-8") as buffer:
            for path in self._iter_files(spec):
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    skipped.append(path)
                    continue
                rel_path = path.relative_to(self.repo_root)
                lines = text.splitlines()
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                snapshots.append(
                    FileSnapshot(
                        path=path,
                        relative_path=rel_path,
                        digest=digest,
                        line_count=len(lines),
                    )
                )
                buffer.write(f"### FILE: {rel_path}\n")
                for idx, line in enumerate(lines, 1):
                    buffer.write(f"[{idx:04d}] {line}\n")
                buffer.write("\n")
        return ScanResult(snapshots=snapshots, destination=destination, skipped=skipped)

    def _iter_files(self, spec: pathspec.PathSpec) -> Iterator[Path]:
        for path in sorted(self.repo_root.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(self.repo_root)
            if spec.match_file(str(rel)):
                continue
            yield path
