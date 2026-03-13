"""Tests for _has_llm_api_key() in pipeline stages."""
from __future__ import annotations

from unittest.mock import patch

from dev_stack.pipeline.stages import LLM_API_KEY_VARS, _has_llm_api_key


def test_returns_true_when_key_is_set() -> None:
    """Any of the 5 keys set → True."""
    for key in LLM_API_KEY_VARS:
        with patch.dict("os.environ", {key: "sk-test-value"}, clear=False):
            assert _has_llm_api_key() is True, f"Expected True when {key} is set"


def test_returns_false_when_no_keys_set() -> None:
    """No keys set → False."""
    env = {k: "" for k in LLM_API_KEY_VARS}
    with patch.dict("os.environ", env, clear=False):
        # Also remove them entirely to test the get() path
        cleaned = {k: v for k, v in env.items()}
        with patch.dict("os.environ", cleaned, clear=True):
            assert _has_llm_api_key() is False


def test_returns_false_when_keys_are_empty_strings() -> None:
    """Empty string values are treated as unset."""
    env = {k: "" for k in LLM_API_KEY_VARS}
    with patch.dict("os.environ", env, clear=True):
        assert _has_llm_api_key() is False


def test_gemini_api_key_in_vars() -> None:
    """GEMINI_API_KEY should be recognized as a valid LLM key."""
    assert "GEMINI_API_KEY" in LLM_API_KEY_VARS


def test_returns_true_for_gemini_key() -> None:
    """GEMINI_API_KEY alone should make _has_llm_api_key() return True."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True):
        assert _has_llm_api_key() is True
