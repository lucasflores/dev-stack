#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Validate branch names and optionally enforce signed commits at push time."""
import sys

from dev_stack.vcs.hooks_runner import run_pre_push_hook

sys.exit(run_pre_push_hook(sys.stdin))
