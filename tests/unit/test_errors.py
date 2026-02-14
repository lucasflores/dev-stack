"""Smoke tests for custom exceptions."""
from __future__ import annotations

from dev_stack.errors import DependencyError, RollbackError


def test_dependency_error_message() -> None:
    error = DependencyError("demo", ["hooks", "speckit"])
    assert "demo" in str(error)
    assert "hooks" in str(error)


def test_rollback_error_message() -> None:
    error = RollbackError("dev-stack/rollback/demo", "failed")
    assert "rollback" in str(error)
    assert error.ref == "dev-stack/rollback/demo"
