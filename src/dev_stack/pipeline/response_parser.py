"""Extract clean commit messages from raw agent stdout."""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExtractionMethod(str, Enum):
    """How the commit message was extracted from agent output."""

    CODE_FENCE = "code_fence"
    PLAIN_TEXT = "plain_text"


@dataclass(frozen=True)
class ParsedCommitMessage:
    """Extracted clean commit message after processing agent output."""

    subject: str
    body: str | None
    raw_content: str
    extraction_method: ExtractionMethod
    source_hash: str


# Patterns that indicate tool-use artifacts (not commit message content)
_TOOL_ARTIFACT_PATTERN = re.compile(
    r"^(Tool:|Running:|Result:|Searching:|Reading:|Executing:)\s",
    re.MULTILINE,
)

# Matches fenced code blocks: ```[lang]\n...\n``` or ~~~[lang]\n...\n~~~
_CODE_FENCE_PATTERN = re.compile(
    r"(?:^|\n)(`{3,}|~{3,})[^\n]*\n(.*?)\n\1",
    re.DOTALL,
)

_MAX_SUBJECT_LENGTH = 200


def extract_commit_message(raw: str) -> ParsedCommitMessage | None:
    """Extract a commit message from agent output.

    Algorithm:
    1. If ``raw`` is empty/whitespace, return ``None``.
    2. Scan for fenced code blocks (triple-backtick or triple-tilde).
    3. If found, extract content of the **last** fenced block.
    4. If no fenced blocks, use ``raw.strip()`` as-is.
    5. Validate: not empty, subject ≤ 200 chars, no tool-artifact lines.
    6. Split into subject + body (first line vs rest after blank line).
    7. Return ``ParsedCommitMessage``.

    Returns ``None`` if extraction fails validation.
    """
    if not raw or not raw.strip():
        logger.debug("response_parser: empty input, returning None")
        return None

    source_hash = hashlib.sha256(raw.encode()).hexdigest()

    # Try code fence extraction (last block wins)
    fenced_blocks = list(_CODE_FENCE_PATTERN.finditer(raw))
    if fenced_blocks:
        content = fenced_blocks[-1].group(2).strip()
        method = ExtractionMethod.CODE_FENCE
        logger.debug(
            "response_parser: extraction_method=%s blocks_found=%d source_hash=%s",
            method.value, len(fenced_blocks), source_hash[:12],
        )
    else:
        content = raw.strip()
        method = ExtractionMethod.PLAIN_TEXT
        logger.debug(
            "response_parser: extraction_method=%s source_hash=%s",
            method.value, source_hash[:12],
        )

    # Validate extracted content
    if not content:
        logger.debug(
            "response_parser: empty content after extraction, source_hash=%s",
            source_hash[:12],
        )
        return None

    lines = content.splitlines()
    subject = lines[0].strip()

    if not subject:
        logger.debug("response_parser: empty subject line, source_hash=%s", source_hash[:12])
        return None

    if len(subject) > _MAX_SUBJECT_LENGTH:
        logger.debug(
            "response_parser: subject too long (%d chars), source_hash=%s",
            len(subject), source_hash[:12],
        )
        return None

    if _TOOL_ARTIFACT_PATTERN.search(content):
        logger.debug("response_parser: tool artifact detected, source_hash=%s", source_hash[:12])
        return None

    # Split subject / body
    body: str | None = None
    if len(lines) > 1:
        rest = "\n".join(lines[1:]).strip()
        if rest:
            body = rest

    logger.debug(
        "response_parser: success extraction_method=%s subject_length=%d source_hash=%s",
        method.value, len(subject), source_hash[:12],
    )
    return ParsedCommitMessage(
        subject=subject,
        body=body,
        raw_content=content,
        extraction_method=method,
        source_hash=source_hash,
    )
