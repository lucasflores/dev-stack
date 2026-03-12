"""Unit tests for dev_stack.pipeline.response_parser."""
from __future__ import annotations

import pytest

from dev_stack.pipeline.response_parser import (
    ExtractionMethod,
    ParsedCommitMessage,
    extract_commit_message,
)


class TestExtractCommitMessage:
    """Tests for extract_commit_message()."""

    def test_empty_string_returns_none(self) -> None:
        assert extract_commit_message("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert extract_commit_message("   \n\n  ") is None

    def test_plain_text_extraction(self) -> None:
        raw = "feat(pipeline): add sandbox mode\n\nPrevents agents from modifying staged content."
        result = extract_commit_message(raw)
        assert result is not None
        assert result.subject == "feat(pipeline): add sandbox mode"
        assert result.body == "Prevents agents from modifying staged content."
        assert result.extraction_method == ExtractionMethod.PLAIN_TEXT

    def test_code_fence_extraction(self) -> None:
        raw = """Here is your commit message:

```
feat(pipeline): add sandbox mode

Prevents agents from modifying staged content during git hooks.
```

This follows conventional commits format.
"""
        result = extract_commit_message(raw)
        assert result is not None
        assert result.subject == "feat(pipeline): add sandbox mode"
        assert result.body == "Prevents agents from modifying staged content during git hooks."
        assert result.extraction_method == ExtractionMethod.CODE_FENCE

    def test_code_fence_with_language_tag(self) -> None:
        raw = """```text
fix(hooks): correct pre-commit stage filtering
```"""
        result = extract_commit_message(raw)
        assert result is not None
        assert result.subject == "fix(hooks): correct pre-commit stage filtering"
        assert result.extraction_method == ExtractionMethod.CODE_FENCE

    def test_multi_fence_selects_last_block(self) -> None:
        raw = """I used these tools:

```bash
git diff --cached
```

Here's the commit message:

```
feat: add response parser module

Extracts clean commit messages from agent output.
```
"""
        result = extract_commit_message(raw)
        assert result is not None
        assert result.subject == "feat: add response parser module"
        assert result.body == "Extracts clean commit messages from agent output."
        assert result.extraction_method == ExtractionMethod.CODE_FENCE

    def test_tilde_fence_extraction(self) -> None:
        raw = """~~~
fix: handle empty responses
~~~"""
        result = extract_commit_message(raw)
        assert result is not None
        assert result.subject == "fix: handle empty responses"
        assert result.extraction_method == ExtractionMethod.CODE_FENCE

    def test_subject_only_no_body(self) -> None:
        raw = "fix: correct typo"
        result = extract_commit_message(raw)
        assert result is not None
        assert result.subject == "fix: correct typo"
        assert result.body is None

    def test_tool_artifact_rejection(self) -> None:
        raw = "Tool: searching for files\nRunning: git diff\nResult: no changes"
        assert extract_commit_message(raw) is None

    def test_subject_too_long_returns_none(self) -> None:
        raw = "x" * 201
        assert extract_commit_message(raw) is None

    def test_subject_at_max_length(self) -> None:
        raw = "x" * 200
        result = extract_commit_message(raw)
        assert result is not None
        assert result.subject == "x" * 200

    def test_source_hash_is_consistent(self) -> None:
        raw = "feat: add feature"
        r1 = extract_commit_message(raw)
        r2 = extract_commit_message(raw)
        assert r1 is not None and r2 is not None
        assert r1.source_hash == r2.source_hash

    def test_source_hash_differs_for_different_input(self) -> None:
        r1 = extract_commit_message("feat: one")
        r2 = extract_commit_message("feat: two")
        assert r1 is not None and r2 is not None
        assert r1.source_hash != r2.source_hash

    def test_frozen_dataclass(self) -> None:
        result = extract_commit_message("feat: test")
        assert result is not None
        with pytest.raises(AttributeError):
            result.subject = "modified"  # type: ignore[misc]

    def test_empty_code_fence_returns_none(self) -> None:
        raw = """```

```"""
        assert extract_commit_message(raw) is None

    def test_body_with_blank_line_separator(self) -> None:
        raw = """feat: add hook

This commit adds a new prepare-commit-msg hook
that runs stages 3-9 of the pipeline.

Closes #42"""
        result = extract_commit_message(raw)
        assert result is not None
        assert result.subject == "feat: add hook"
        assert "Closes #42" in result.body
