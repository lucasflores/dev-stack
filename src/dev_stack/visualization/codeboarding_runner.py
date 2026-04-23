"""Legacy compatibility wrapper for visualization runner APIs.

Active visualization flows now use Understand-Anything artifacts. This module
keeps the historical import path available for callers and tests that still
reference ``dev_stack.visualization.codeboarding_runner``.
"""
from __future__ import annotations

from .understand_runner import RunResult, check_cli_available, run

__all__ = ["RunResult", "check_cli_available", "run"]
