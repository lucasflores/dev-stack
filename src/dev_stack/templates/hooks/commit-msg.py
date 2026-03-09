#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Validate commit messages against conventional commit format and trailer rules."""
import sys

from dev_stack.vcs.hooks_runner import run_commit_msg_hook

sys.exit(run_commit_msg_hook(sys.argv[1]))
