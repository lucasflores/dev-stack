#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Run lint and typecheck pipeline stages as a pre-commit check."""
import sys

from dev_stack.vcs.hooks_runner import run_pre_commit_hook

sys.exit(run_pre_commit_hook())
