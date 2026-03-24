"""Custom gitlint rules for dev-stack commit message validation.

Exports all rule classes for use with gitlint's ``extra_path`` mechanism.
Point ``LintConfig.extra_path`` at this package to auto-discover rules.
"""
from __future__ import annotations

from dev_stack.rules.body_sections import BodySectionRule
from dev_stack.rules.conventional import ConventionalCommitRule
from dev_stack.rules.pipeline_warn import PipelineFailureWarningRule
from dev_stack.rules.trailers import TrailerPathRule, TrailerPresenceRule

__all__ = [
    "ConventionalCommitRule",
    "TrailerPresenceRule",
    "TrailerPathRule",
    "PipelineFailureWarningRule",
    "BodySectionRule",
]
