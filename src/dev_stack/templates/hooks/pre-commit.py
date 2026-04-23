#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Run pre-commit quality gates including graph freshness validation."""
import os
import sys

if os.environ.get("DEV_STACK_NO_HOOKS") == "1":
    sys.exit(0)

try:
    from dev_stack.vcs.hooks_runner import run_pre_commit_hook
except ImportError:
    sys.exit(0)

sys.exit(run_pre_commit_hook())
