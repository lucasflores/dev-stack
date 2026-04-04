#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Validate commit messages against conventional commit format and trailer rules."""
import os
import sys

if os.environ.get("DEV_STACK_NO_HOOKS") == "1":
    sys.exit(0)

try:
    from dev_stack.vcs.hooks_runner import run_commit_msg_hook
except ImportError:
    sys.exit(0)

sys.exit(run_commit_msg_hook(sys.argv[1]))
