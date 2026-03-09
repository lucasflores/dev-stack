# Research: Version Control Best Practices Automation

**Feature**: `004-vcs-best-practices`  
**Date**: 2026-03-08  
**Status**: Complete

---

### Topic 1: gitlint Custom Rule API

**Decision**: Use `gitlint-core` (v0.19+) with custom `CommitRule` subclasses registered via `LintConfig.extra_path`, invoked programmatically through `GitLinter.lint()`. Do NOT use the gitlint CLI from hooks; instead, call the Python API directly from the hook script.

**Rationale**: The Python API gives dev-stack full control over config construction (bypassing any global `.gitlint` file), allows embedding custom rules as part of the `dev_stack` package, and avoids subprocess overhead. The `gitlint-core` package is the library-only distribution without CLI dependencies — lighter and appropriate for programmatic use.

**Alternatives Considered**:
- **gitlint CLI via subprocess**: Simpler but introduces a dependency on gitlint being on `$PATH`, makes config override harder (must write temp `.gitlint` file or pass many `-c` flags), and adds subprocess overhead on every commit.
- **commitlint (Node.js)**: Requires Node.js runtime, which dev-stack doesn't otherwise depend on.
- **Custom regex-only validation (no library)**: Would require reimplementing all of gitlint's built-in rules (title length, body formatting, etc.) and miss future upstream improvements.

**Key Details**:

**Base classes** (all in `gitlint.rules`):
- `CommitRule` — validates the entire commit object. Method: `validate(self, commit) -> list[RuleViolation] | None`. Best for trailer validation.
- `LineRule` — validates individual lines. Method: `validate(self, line, commit)`. Requires `target = CommitMessageTitle` or `target = CommitMessageBody`.
- `ConfigurationRule` — modifies config before other rules run. Method: `apply(self, config, commit)`. Useful for conditionally ignoring rules (e.g., skip body-is-missing for merge commits).

**Rule class requirements**:
- Must have `name` (str) and `id` (str) attributes.
- Optional `options_spec` list of `gitlint.options.*Option` objects.
- User rule IDs must NOT start with `R`, `T`, `B`, `M`, or `I` (reserved for built-in).
- Recommended prefixes: `UC` (user CommitRule), `UL` (user LineRule), `UCR` (user ConfigurationRule).

**Rule discovery/registration**:
- `config.extra_path = "/path/to/rules_dir_or_file.py"` — gitlint auto-discovers rule classes.
- Contrib rules enabled via `config.set_general_option("contrib", "contrib-title-conventional-commits")`.
- For dev-stack: point `extra_path` to the installed package path, e.g. `dev_stack.vcs.rules.__file__`.

**Programmatic invocation** (verified working with gitlint-core 0.19.1):

```python
from gitlint.git import GitContext
from gitlint.config import LintConfig
from gitlint.lint import GitLinter
from gitlint.rules import CommitRule, RuleViolation

# Build config programmatically — ignores any global .gitlint file
config = LintConfig()
config.set_general_option("contrib", "contrib-title-conventional-commits")
config.set_general_option("ignore", "body-is-missing")
config.extra_path = "/path/to/dev_stack/vcs/rules.py"

linter = GitLinter(config)

# Parse a commit message string into a context
ctx = GitContext.from_commit_msg("feat(cli): add new command\n\nBody here.")
# For staged commits with file info: GitContext.from_staged_commit(msg, repo_path)

for commit in ctx.commits:
    violations = linter.lint(commit)
    # violations is a list of RuleViolation objects
    for v in violations:
        print(f"{v.rule_id}: {v.message}")
```

**Commit object attributes** available in rules:
- `commit.message.title` — first line
- `commit.message.body` — list of body lines
- `commit.message.original` — raw message from git
- `commit.message.full` — full message without comments
- `commit.changed_files` — list of changed file paths (only available from `from_staged_commit` or `from_local_repository`)
- `commit.changed_files_stats` — dict of file → `{filepath, additions, deletions}`
- `commit.context.current_branch` — branch name
- `commit.author_name`, `commit.author_email`, `commit.date`
- `commit.is_merge_commit`, `commit.is_revert_commit`, `commit.is_fixup_commit`

**Config override approach**: By constructing `LintConfig()` in code and never calling `set_from_config_file()`, any global `~/.gitlint` or project `.gitlint` is completely ignored. The `LintConfigBuilder` class can also be used: `builder.set_option("general", "key", "value")` then `builder.build()`.

**Package name**: `gitlint-core` (PyPI). Install with `pip install gitlint-core`. The `gitlint` package is the full distribution including CLI entry points; `gitlint-core` is library-only. Both provide the same `gitlint.*` import namespace.

---

### Topic 2: git-cliff Configuration for Custom Trailers

**Decision**: Use git-cliff's built-in conventional commit footer parsing (the `footers` array in the template context) to access custom trailers like `Spec-Ref`, `Task-Ref`, `Agent`, `Pipeline`, and `Edited`. Render AI provenance markers via Tera template conditionals on footer values. Configure via `cliff.toml` at repo root (generated by `dev-stack init`).

**Rationale**: git-cliff natively parses conventional commit footers into structured `{token, separator, value, breaking}` objects. No custom regex is needed to extract trailers — they are automatically available in the Tera template context as `commit.footers`. The `commit_parsers` section handles type-based grouping, while the Tera template handles rendering.

**Alternatives Considered**:
- **Custom Python changelog generator**: Full control but massive effort to replicate git-cliff's release range detection, tag handling, and template rendering.
- **towncrier**: Fragment-file based, not commit-message based. Would require maintaining separate changelog fragments, which conflicts with the trailer-driven workflow.
- **Embedding config in pyproject.toml**: git-cliff supports `[tool.git-cliff.*]` sections in `pyproject.toml`, but a separate `cliff.toml` is clearer and avoids bloating `pyproject.toml`.

**Key Details**:

**Trailer access in templates**: git-cliff parses footers compliant with the Conventional Commits / git-trailer spec. Each footer becomes:
```json
{
  "token": "Agent",
  "separator": ": ",
  "value": "claude-sonnet-4-20250514",
  "breaking": false
}
```

**cliff.toml configuration**:

```toml
[changelog]
header = """# Changelog\n
All notable changes to this project will be documented in this file.\n"""

body = """
{% if version -%}
    ## [{{ version | trim_start_matches(pat="v") }}] - {{ timestamp | date(format="%Y-%m-%d") }}
{% else -%}
    ## [Unreleased]
{% endif %}
{% for group, commits in commits | group_by(attribute="group") %}
    ### {{ group | upper_first }}
    {% for commit in commits %}
        {# --- AI provenance markers --- #}
        {%- set is_agent = false -%}
        {%- set is_edited = false -%}
        {%- for footer in commit.footers -%}
            {%- if footer.token == "Agent" -%}
                {%- set_global is_agent = true -%}
            {%- endif -%}
            {%- if footer.token == "Edited" and footer.value == "true" -%}
                {%- set_global is_edited = true -%}
            {%- endif -%}
        {%- endfor -%}
        - {% if is_agent %}🤖 {% endif %}{% if is_edited %}✏️ {% endif %}\
          {{ commit.message | upper_first | trim }}\
          {% if commit.scope %} *({{ commit.scope }})*{% endif %}\
          {%- for footer in commit.footers %}
            {%- if footer.token == "Spec-Ref" %} [`{{ footer.value }}`]({{ footer.value }}){% endif -%}
          {%- endfor %}
    {% endfor %}
{% endfor %}
"""

footer = """<!-- generated by git-cliff -->"""
trim = true

[git]
conventional_commits = true
filter_unconventional = false
split_commits = false
protect_breaking_commits = true

commit_parsers = [
    { message = "^feat", group = "🚀 Features" },
    { message = "^fix", group = "🐛 Bug Fixes" },
    { message = "^docs", group = "📚 Documentation" },
    { message = "^perf", group = "⚡ Performance" },
    { message = "^refactor", group = "🔧 Refactoring" },
    { message = "^style", group = "🎨 Style" },
    { message = "^test", group = "🧪 Tests" },
    { message = "^build", group = "📦 Build" },
    { message = "^ci", group = "⚙️ CI" },
    { message = "^chore\\(release\\)", skip = true },
    { message = "^chore", group = "🔨 Chores" },
    { message = "^revert", group = "⏪ Reverts" },
]

tag_pattern = "v[0-9]*"
sort_commits = "oldest"
```

**Footer filtering in commit_parsers**: The `footer = "regex"` field matches against the raw footer text, useful for skip rules:
```toml
{ footer = "^changelog: ?ignore", skip = true }
```

**Tera template features used**:
- `commits | group_by(attribute="group")` — groups by parser-assigned group
- `commit.footers` — array of footer objects with `.token`, `.separator`, `.value`, `.breaking`
- `set_global` — required (not `set`) to mutate variables inside `for` loops in Tera
- `trim_start_matches(pat="v")` — strips version prefix from tag

**pyproject.toml alternative** (if desired, instead of standalone `cliff.toml`):
```toml
[tool.git-cliff.changelog]
body = "..."

[tool.git-cliff.git]
conventional_commits = true
commit_parsers = [...]
```

---

### Topic 3: python-semantic-release Integration

**Decision**: Use python-semantic-release (PSR) as an optional external tool invoked via CLI subprocess (`semantic-release version --print`, `semantic-release version --no-push`), with a built-in fallback implementation for version inference and `pyproject.toml` bumping when PSR is not installed.

**Rationale**: PSR's Python internals are not designed as a stable public API — the documented interface is the CLI. Shelling out to the CLI is the supported approach. However, since PSR is a heavyweight optional dependency, dev-stack needs a zero-dependency fallback that can parse conventional commits and bump versions in `pyproject.toml` directly.

**Alternatives Considered**:
- **PSR Python API (private internals)**: The `RuntimeContext` and command classes exist but are undocumented, tightly coupled to CLI entry points, and may change between versions. Not suitable for library use.
- **commitizen**: Another commit-convention tool with version bumping, but it's opinionated about the commit format and doesn't handle trailers. Adding it would be a competing convention.
- **Built-in only (no PSR support)**: Would miss PSR's robust tag handling, changelog integration, and VCS release creation. Better to support it when available.

**Key Details**:

**PSR Configuration** (in `pyproject.toml`):
```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
commit_parser = "conventional"
tag_format = "v{version}"
major_on_zero = false

[tool.semantic_release.commit_parser_options]
minor_tags = ["feat"]
patch_tags = ["fix", "perf"]
parse_squash_commits = true
ignore_merge_commits = true

[tool.semantic_release.branches.main]
match = "main"
prerelease = false
```

**How PSR infers version bumps**:
1. Finds the last release tag matching `tag_format`.
2. Parses all commits since that tag using the configured `commit_parser`.
3. Commit type → bump level mapping: `feat` → minor, `fix`/`perf` → patch.
4. A `BREAKING CHANGE:` paragraph in the commit body → major (override).
5. `major_on_zero = false` means breaking changes only bump minor when version is `0.x.x`.
6. The highest bump level wins across all commits in the range.

**How PSR writes to pyproject.toml**: The `version_toml` config specifies dot-notation paths. PSR reads the TOML, navigates to `project.version`, replaces the value string, and writes back. Supports multiple stamp locations.

**CLI invocation patterns for dev-stack integration**:
```bash
# Dry-run: just print next version
semantic-release version --print

# Print next tag
semantic-release version --print-tag

# Bump version, update changelog, commit, tag — but don't push
semantic-release version --no-push --no-vcs-release

# Force a specific bump
semantic-release version --patch --no-push
semantic-release version --minor --no-push
semantic-release version --major --no-push
```

**Fallback built-in implementation** (minimal logic needed):
```python
import re, subprocess, tomli, tomli_w
from packaging.version import Version

def infer_bump(commits: list[str]) -> str | None:
    """Parse conventional commit subjects to determine bump level."""
    bump = None
    for msg in commits:
        if "BREAKING CHANGE:" in msg or re.match(r"^\w+(\(.*\))?!:", msg):
            return "major"
        match = re.match(r"^(\w+)(\(.*\))?: ", msg)
        if match:
            ctype = match.group(1)
            if ctype == "feat" and bump != "major":
                bump = "minor"
            elif ctype in ("fix", "perf") and bump is None:
                bump = "patch"
    return bump

def bump_version(current: str, level: str) -> str:
    v = Version(current)
    if level == "major":
        return f"{v.major + 1}.0.0"
    elif level == "minor":
        return f"{v.major}.{v.minor + 1}.0"
    else:
        return f"{v.major}.{v.minor}.{v.micro + 1}"

def get_commits_since_tag(tag: str) -> list[str]:
    result = subprocess.run(
        ["git", "log", f"{tag}..HEAD", "--pretty=%B---COMMIT_SEP---"],
        capture_output=True, text=True
    )
    return [c.strip() for c in result.stdout.split("---COMMIT_SEP---") if c.strip()]
```

The fallback reads `pyproject.toml` version via `tomli`, infers the bump, computes the new version, and writes it back with `tomli_w`. This covers FR-033/FR-034 without PSR.

---

### Topic 4: Git Hook Script Portability

**Decision**: Generate hook scripts as thin Python-shebang scripts that import and call functions from the installed `dev_stack` package. Use `#!/usr/bin/env python3` as the shebang. The hook script itself is minimal (~10 lines) and delegates all logic to the library.

**Rationale**: Since dev-stack is always installed as a Python package (it's a `pip install`-able tool), the hooks can reliably import from `dev_stack`. Using `#!/usr/bin/env python3` is the most portable shebang — it finds whichever `python3` is on the PATH, which will be the activated venv's Python if a venv is active. The thin-wrapper approach means hook logic is testable as normal Python code, and hook templates only change when the interface changes (reducing unnecessary re-installs).

**Alternatives Considered**:
- **Shell scripts that call `dev-stack` CLI**: Adds subprocess overhead and requires `dev-stack` to be on `$PATH` (may not be true in all venv setups). Also harder to get structured error output.
- **Absolute venv python path in shebang**: Fragile — breaks if venv is moved, recreated, or the user switches Python versions. `#!/usr/bin/env python3` is the standard portable approach.
- **Pre-commit framework**: Powerful but heavyweight. Requires `.pre-commit-config.yaml`, a separate tool installation, and runs hooks in isolated environments that may not have `dev_stack` installed. Conflicts with dev-stack's own hook management.

**Key Details**:

**commit-msg hook** — receives the commit message file path as `$1`:
```python
#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Commit message validation hook."""
import sys

def main():
    commit_msg_file = sys.argv[1]
    with open(commit_msg_file) as f:
        message = f.read()

    # Import from installed package
    from dev_stack.vcs.hooks import validate_commit_message
    errors = validate_commit_message(message)
    if errors:
        print("❌ Commit message validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  • {err}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**pre-push hook** — receives input on stdin:
```python
#!/usr/bin/env python3
# managed by dev-stack — do not edit manually
"""Pre-push validation hook (branch naming, signing)."""
import sys

def main():
    # stdin format: <local ref> <local sha> <remote ref> <remote sha>\n
    # One line per ref being pushed
    lines = sys.stdin.read().strip().splitlines()

    from dev_stack.vcs.hooks import validate_pre_push
    errors = validate_pre_push(lines)
    if errors:
        print("❌ Pre-push validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  • {err}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Shebang considerations**:
- `#!/usr/bin/env python3` — **recommended**. Respects `$PATH`, works with venvs, pyenv, conda.
- `#!/path/to/venv/bin/python` — fragile, breaks on venv recreation.
- `#!/usr/bin/python3` — may point to system Python, which won't have dev-stack installed.
- On Windows git-for-windows, `#!/usr/bin/env python3` works because git-bash maps it correctly.

**Detecting the commit message file** in commit-msg hook:
- Git passes it as the first positional argument: `sys.argv[1]`
- Typically `.git/COMMIT_EDITMSG`
- The hook can read it, validate, and optionally modify it (write back to the same file)

**pre-push stdin format**:
```
refs/heads/feat/my-feature <local-sha> refs/heads/feat/my-feature <remote-sha>
```
- One line per ref being pushed
- `<remote-sha>` is all zeros for new branches
- Parse with: `local_ref, local_sha, remote_ref, remote_sha = line.split()`

**Verifying commit signatures** (for pre-push signing enforcement):
```python
import subprocess

def is_commit_signed(sha: str) -> bool:
    result = subprocess.run(
        ["git", "verify-commit", sha],
        capture_output=True, text=True
    )
    return result.returncode == 0

# For a range of commits:
def get_unsigned_commits(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "log", f"{base}..{head}", "--pretty=%H"],
        capture_output=True, text=True
    )
    shas = result.stdout.strip().splitlines()
    return [sha for sha in shas if not is_commit_signed(sha)]
```

**File permissions**: Hook scripts must be executable (`chmod +x`). dev-stack's hook installer must set `os.chmod(hook_path, 0o755)`.

---

### Topic 5: SSH Signing with Git

**Decision**: Configure SSH signing via local git config (`git config --local`) during `dev-stack init` when the user opts in. Auto-detect the preferred SSH public key (preferring ed25519 over RSA). Require git ≥ 2.34 and skip with a warning if the version is too old.

**Rationale**: SSH signing (introduced in git 2.34) is simpler than GPG signing — no separate keyring, no key servers, no gpg-agent. Most developers already have SSH keys for GitHub/GitLab. Setting config locally (not globally) ensures dev-stack doesn't modify the user's global git config. The version check prevents cryptic errors on older git versions.

**Alternatives Considered**:
- **GPG signing**: More established but significantly more complex setup (GPG keyring, key generation, gpg-agent). SSH signing is the modern replacement recommended by GitHub.
- **No signing support**: Would miss a key provenance feature for AI-generated commits. Since the feature is opt-in, the cost of including it is low.
- **Global git config**: Would affect all repositories, not just the dev-stack project. Local config is scoped correctly.

**Key Details**:

**Git config keys for SSH signing** (all set with `--local`):
```bash
# Enable commit signing
git config --local commit.gpgsign true

# Use SSH format instead of GPG
git config --local gpg.format ssh

# Path to the SSH public key used for signing
git config --local user.signingkey ~/.ssh/id_ed25519.pub

# Optional: allowed signers file for verification
git config --local gpg.ssh.allowedSignersFile .dev-stack/allowed_signers
```

**Allowed signers file format** (`.dev-stack/allowed_signers`):
```
user@example.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...
```
Format: `<email> <key-type> <public-key-data>`

**Auto-detecting SSH public keys** (Python):
```python
from pathlib import Path

SSH_KEY_PREFERENCE = [
    "id_ed25519.pub",    # Preferred: modern, fast
    "id_ecdsa.pub",      # Good alternative
    "id_rsa.pub",        # Legacy but common
]

def find_ssh_public_key() -> Path | None:
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.is_dir():
        return None
    for key_name in SSH_KEY_PREFERENCE:
        key_path = ssh_dir / key_name
        if key_path.is_file():
            return key_path
    # Fallback: any .pub file
    pub_files = sorted(ssh_dir.glob("*.pub"))
    return pub_files[0] if pub_files else None
```

**Git version check** (Python):
```python
import subprocess, re

def get_git_version() -> tuple[int, ...]:
    result = subprocess.run(["git", "--version"], capture_output=True, text=True)
    match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
    if match:
        return tuple(int(x) for x in match.group(1).split("."))
    return (0, 0, 0)

def supports_ssh_signing() -> bool:
    return get_git_version() >= (2, 34, 0)
```

**Verifying signed commits**:
```bash
# Verify a specific commit
git verify-commit HEAD
# Exit code 0 = valid signature, non-zero = unsigned or invalid

# Show signatures in log
git log --show-signature -1

# Check signature via format
git log --pretty=format:"%H %G?" -1
# %G? outputs: G (good), B (bad), U (untrusted), N (none), E (error)
```

**Python verification**:
```python
def verify_commit_signature(sha: str) -> str:
    """Returns signature status: 'G' (good), 'N' (none), 'B' (bad), etc."""
    result = subprocess.run(
        ["git", "log", "--pretty=format:%G?", "-1", sha],
        capture_output=True, text=True
    )
    return result.stdout.strip()
```

**Minimum git version**: 2.34 (released November 2021). SSH signing was introduced in this version. Key features by version:
- 2.34: `gpg.format = ssh` support, basic SSH signing
- 2.34.1: Bug fixes for SSH signing
- 2.39+: Widely distributed on macOS (Apple Git)

**Current environment**: git 2.39.3 (Apple Git-145) — fully supports SSH signing.

**Configuration in pyproject.toml** (dev-stack reads this):
```toml
[tool.dev-stack.signing]
enabled = true
enforcement = "warn"  # or "block"
# key = "~/.ssh/id_ed25519.pub"  # optional: auto-detected if omitted
```
