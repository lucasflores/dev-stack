"""Tests for conflict detection."""
from __future__ import annotations

from dev_stack.brownfield import conflict


def test_detects_new_and_modified_files(tmp_path) -> None:
    repo = tmp_path
    existing = repo / "existing.txt"
    existing.write_text("original", encoding="utf-8")

    proposed = {
        "existing.txt": "changed",
        "new.txt": "fresh",
    }

    conflicts = conflict.detect_conflicts(repo, proposed)

    kinds = {c.conflict_type for c in conflicts}
    assert conflict.ConflictType.MODIFIED in kinds
    assert conflict.ConflictType.NEW in kinds
    paths = {c.path.name for c in conflicts}
    assert paths == {"existing.txt", "new.txt"}


def test_detects_deletion(tmp_path) -> None:
    repo = tmp_path
    doomed = repo / "remove.me"
    doomed.write_text("bye", encoding="utf-8")

    conflicts = conflict.detect_conflicts(repo, {"remove.me": None})

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == conflict.ConflictType.DELETED


def test_serialize_conflicts_returns_relative_paths(tmp_path) -> None:
    repo = tmp_path
    target = repo / "nested" / "file.txt"
    file_conflict = conflict.FileConflict(
        path=target,
        conflict_type=conflict.ConflictType.NEW,
        proposed_hash="abc",
    )
    report = conflict.ConflictReport(operation="init", conflicts=[file_conflict])

    payload = conflict.serialize_conflicts(report, repo)

    assert payload == [
        {"path": "nested/file.txt", "type": "new", "resolution": "pending"}
    ]


def test_resolve_conflicts_accepts_overwrite(monkeypatch, tmp_path) -> None:
    file_path = tmp_path / "conflict.txt"
    file_path.write_text("current", encoding="utf-8")
    file_conflict = conflict.FileConflict(
        path=file_path,
        conflict_type=conflict.ConflictType.MODIFIED,
        proposed_hash="deadbeef",
        current_hash="oldhash",
    )
    report = conflict.ConflictReport("init", [file_conflict])
    monkeypatch.setattr(conflict, "_prompt_choice", lambda: "a")

    skip_map, merge_map = conflict.resolve_conflicts_interactively(report, tmp_path, {file_path: "next"})

    assert not skip_map
    assert not merge_map
    assert file_conflict.resolution == "accepted"


def test_resolve_conflicts_skips_and_snapshots(monkeypatch, tmp_path) -> None:
    file_path = tmp_path / "skip.txt"
    file_path.write_text("preserve", encoding="utf-8")
    blocking = conflict.FileConflict(
        path=file_path,
        conflict_type=conflict.ConflictType.MODIFIED,
        proposed_hash="deadbeef",
        current_hash="oldhash",
    )
    report = conflict.ConflictReport("init", [blocking])
    monkeypatch.setattr(conflict, "_prompt_choice", lambda: "s")

    skip_map, merge_map = conflict.resolve_conflicts_interactively(report, tmp_path, {file_path: "next"})

    assert file_path in skip_map
    snapshot, mode = skip_map[file_path]
    assert snapshot == b"preserve"
    assert isinstance(mode, int)
    assert not merge_map
    assert blocking.resolution == "skipped"


def test_resolve_conflicts_merges_with_editor(monkeypatch, tmp_path) -> None:
    file_path = tmp_path / "merge.txt"
    file_path.write_text("current", encoding="utf-8")
    blocking = conflict.FileConflict(
        path=file_path,
        conflict_type=conflict.ConflictType.MODIFIED,
        proposed_hash="deadbeef",
        current_hash="oldhash",
    )
    report = conflict.ConflictReport("init", [blocking])
    monkeypatch.setattr(conflict, "_prompt_choice", lambda: "m")
    monkeypatch.setattr(conflict.click, "edit", lambda *args, **kwargs: "# note\nmerged content")

    skip_map, merge_map = conflict.resolve_conflicts_interactively(report, tmp_path, {file_path: "new text"})

    assert not skip_map
    assert merge_map[file_path] == "merged content"
    assert blocking.resolution == "merged"


def test_resolve_conflicts_merge_cancelled(monkeypatch, tmp_path) -> None:
    file_path = tmp_path / "merge-cancel.txt"
    file_path.write_text("current", encoding="utf-8")
    blocking = conflict.FileConflict(
        path=file_path,
        conflict_type=conflict.ConflictType.MODIFIED,
        proposed_hash="deadbeef",
        current_hash="oldhash",
    )
    report = conflict.ConflictReport("init", [blocking])
    monkeypatch.setattr(conflict, "_prompt_choice", lambda: "m")
    monkeypatch.setattr(conflict.click, "edit", lambda *args, **kwargs: None)

    skip_map, merge_map = conflict.resolve_conflicts_interactively(report, tmp_path, {file_path: "new"})

    assert file_path in skip_map
    assert not merge_map
    assert blocking.resolution == "skipped"
