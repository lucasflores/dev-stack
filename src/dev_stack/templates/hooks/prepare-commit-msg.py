#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Run stages 3-9 of the pipeline during prepare-commit-msg hook."""
import sys

from dev_stack.vcs.hooks_runner import run_prepare_commit_msg_hook

message_file = sys.argv[1] if len(sys.argv) > 1 else ""
source = sys.argv[2] if len(sys.argv) > 2 else None
commit_sha = sys.argv[3] if len(sys.argv) > 3 else None

sys.exit(run_prepare_commit_msg_hook(message_file, source, commit_sha))
