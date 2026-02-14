"""Marker helpers for stack-managed file sections."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

BLOCK_COMMENT_EXTS = {".html", ".htm", ".md", ".xml"}
SLASH_COMMENT_EXTS = {".js", ".ts", ".tsx", ".jsx", ".c", ".cpp", ".java", ".go"}
DEFAULT_PREFIX = "#"


def read_managed_section(file_path: Path, section_id: str) -> str | None:
    """Return the content between dev-stack markers in the given file."""

    if not file_path.exists():
        return None
    text = file_path.read_text(encoding="utf-8")
    start_marker, end_marker = _marker_pair(file_path, section_id)
    start_index = text.find(start_marker)
    if start_index == -1:
        return None
    start_index += len(start_marker)
    end_index = text.find(end_marker, start_index)
    if end_index == -1:
        return None
    return text[start_index:end_index].strip("\n")


def write_managed_section(file_path: Path, section_id: str, content: str) -> bool:
    """Write managed content, creating or replacing marker sections."""

    file_path.parent.mkdir(parents=True, exist_ok=True)
    existing_text = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    start_marker, end_marker = _marker_pair(file_path, section_id)
    managed_block = f"{start_marker}\n{content.rstrip()}\n{end_marker}"

    start_index = existing_text.find(start_marker)
    search_from = start_index + len(start_marker) if start_index != -1 else 0
    end_index = existing_text.find(end_marker, search_from)
    if start_index != -1 and end_index != -1 and end_index > start_index:
        end_index += len(end_marker)
        new_text = existing_text[:start_index] + managed_block + existing_text[end_index:]
    else:
        prefix = existing_text
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        new_text = prefix + managed_block + "\n"

    if new_text == existing_text:
        return False

    file_path.write_text(new_text, encoding="utf-8")
    return True


def _marker_pair(file_path: Path, section_id: str) -> Tuple[str, str]:
    start_token, end_token = _comment_tokens(file_path.suffix.lower())
    begin = f"{start_token} === DEV-STACK:BEGIN:{section_id} ==={end_token}"
    end = f"{start_token} === DEV-STACK:END:{section_id} ==={end_token}"
    return begin, end


def _comment_tokens(suffix: str) -> tuple[str, str]:
    if suffix in BLOCK_COMMENT_EXTS:
        return "<!--", " -->"
    if suffix in SLASH_COMMENT_EXTS:
        return "//", ""
    return DEFAULT_PREFIX, ""
