# Quickstart: Verify Feature 020-update-apm-defaults

**Purpose**: Steps a developer can run to verify the implementation is correct after making the changes.

---

## Prerequisites

- APM CLI `>= 0.8.0` installed and on `PATH`
- Python 3.11+ with dev-stack installed in editable mode (`uv pip install -e .`)
- On branch `020-update-apm-defaults`

---

## Step 1: Verify template content

```bash
cat src/dev_stack/templates/apm/default-apm.yml
```

Expected output:
```yaml
name: "{{ PROJECT_NAME }}"
version: "2.0.0"
dependencies:
  apm:
    - lucasflores/agent-skills/agents/idea-to-speckit.agent.md
    - lucasflores/agent-skills/prompts/AutoSpecKit.prompt.md
    - lucasflores/agent-skills/skills/commit-pipeline
    - lucasflores/agent-skills/skills/dev-stack-update
```

**Check**: No `mcp` key present. Version is `"2.0.0"`. Exactly 4 `apm` entries.

---

## Step 2: Verify module constants

```bash
python -c "
from dev_stack.modules.apm import APMModule
print('DEFAULT_SERVERS:', APMModule.DEFAULT_SERVERS)
print('DEFAULT_APM_PACKAGES:', APMModule.DEFAULT_APM_PACKAGES)
print('Docstring:', APMModule.__doc__)
"
```

Expected output:
```
DEFAULT_SERVERS: ()
DEFAULT_APM_PACKAGES: ('lucasflores/agent-skills/agents/idea-to-speckit.agent.md', 'lucasflores/agent-skills/prompts/AutoSpecKit.prompt.md', 'lucasflores/agent-skills/skills/commit-pipeline', 'lucasflores/agent-skills/skills/dev-stack-update')
Docstring: Manage APM packages and agent skills via the APM CLI.
```

---

## Step 3: Verify fresh install produces correct manifest

```bash
TMP=$(mktemp -d)
python -c "
from pathlib import Path
from dev_stack.modules.apm import APMModule
import yaml
m = APMModule(Path('$TMP'))
m._bootstrap_manifest(force=True)
content = yaml.safe_load((Path('$TMP') / 'apm.yml').read_text())
print('version:', content['version'])
print('mcp present:', 'mcp' in content.get('dependencies', {}))
print('apm entries:', len(content['dependencies']['apm']))
for e in content['dependencies']['apm']:
    print(' -', e)
"
```

Expected output:
```
version: 2.0.0
mcp present: False
apm entries: 4
 - lucasflores/agent-skills/agents/idea-to-speckit.agent.md
 - lucasflores/agent-skills/prompts/AutoSpecKit.prompt.md
 - lucasflores/agent-skills/skills/commit-pipeline
 - lucasflores/agent-skills/skills/dev-stack-update
```

---

## Step 4: Verify merge does not add MCP key

```bash
TMP=$(mktemp -d)
python -c "
from pathlib import Path
from dev_stack.modules.apm import APMModule
import yaml

manifest = Path('$TMP') / 'apm.yml'
manifest.write_text(yaml.dump({'name': 'test', 'version': '1.0.0', 'dependencies': {}}))

m = APMModule(Path('$TMP'))
m._merge_manifest(manifest)
content = yaml.safe_load(manifest.read_text())
print('mcp in deps:', 'mcp' in content.get('dependencies', {}))
print('apm entries:', len(content.get('dependencies', {}).get('apm', [])))
"
```

Expected output:
```
mcp in deps: False
apm entries: 4
```

---

## Step 5: Verify `apm install` exits 0 on generated manifest

```bash
TMP=$(mktemp -d)
python -c "
from pathlib import Path
from dev_stack.modules.apm import APMModule
m = APMModule(Path('$TMP'))
m._bootstrap_manifest(force=True)
"
cd $TMP && apm install
echo "Exit code: $?"
```

Expected: `Exit code: 0` with 4 dependencies reported as installed.

---

## Step 6: Run the test suite

```bash
# Unit tests for APM module only (fast)
python -m pytest tests/unit/test_apm_module.py tests/contract/test_apm_contract.py -v -o addopts=''

# Integration tests
python -m pytest tests/integration/test_apm_install.py -v -o addopts=''
```

Expected: All tests pass (no failures, no errors).
