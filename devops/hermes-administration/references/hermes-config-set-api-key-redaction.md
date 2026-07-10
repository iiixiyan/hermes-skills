# `hermes config set model.api_key` Key Redaction Issue

> Discovered: 2026-07-01 | Status: Confirmed

## Problem

`hermes config set model.api_key <key>` writes a **corrupted/truncated key** to `config.yaml` when the key is printed with `...` in the middle by Hermes' secret redaction system.

### Example

```
$ hermes config set model.api_key sk-c5c854228f4f4719926753fbc0bcac86
✓ Set model.api_key = sk-c5c...ac86 in /root/.hermes/config.yaml
```

The file ends up containing the **literal string** `sk-c5c...ac86` (with real `...` characters) rather than the full 35-character key. This breaks all API calls from cron jobs (which read config.yaml, not the env var).

## Root Cause

Hermes' secret redaction intercepts API keys and replaces the middle portion with `...` before passing them to `hermes config set`. The CLI tool writes the redacted string verbatim.

## Detection

Check config.yaml raw bytes:

```bash
python3 -c "
import re
with open('/root/.hermes/config.yaml', 'rb') as f:
    content = f.read()
matches = list(re.finditer(rb'api_key:\s*(.+)$', content, re.MULTILINE))
for m in matches:
    val = m.group(1).strip()
    if b'...' in val:
        print(f'⚠️ Contains literal dots: {val.decode()}')
    else:
        print(f'✅ Full key: {val.decode()[:10]}...{val.decode()[-5:]}')
"
```

When the key contains `...` literally (not just in display), it's corrupted.

## Fix: Write Directly via Python

**Bypass `hermes config set` entirely** — use Python file I/O:

```python
with open('/root/.hermes/config.yaml', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.strip().startswith('api_key:') and '<partial_key_match>' in line:
        indent = line[:len(line) - len(line.lstrip())]
        lines[i] = f"{indent}api_key: {new_full_key}\n"
        break

with open('/root/.hermes/config.yaml', 'w') as f:
    f.writelines(lines)
```

Replace `<partial_key_match>` with a unique fragment of the old key to target the right line, and `new_full_key` with the complete unredacted key.

## Verification

```python
import re
with open('/root/.hermes/config.yaml', 'rb') as f:
    content = f.read()
m = re.search(rb'api_key:\s*(sk-[a-zA-Z0-9]+)', content)
if m:
    key = m.group(1).decode()
    print(f'Key length: {len(key)} (expected 35+ for DeepSeek, 47+ for Sensenova)')
```

## Prevention

- Never use `hermes config set model.api_key <key>` when the key value contains `...` in the terminal output — it's already been redacted.
- Always use the Python file I/O approach above for API key updates.
- The `hermes config set` CLI is safe for non-secret fields (model name, base_url, provider name).
- **⚠️ Distinguish `api_key` vs `model.api_key`:** `hermes config set api_key X` sets a **top-level** key that the model ignores. The model reads `model.api_key`. Always target the nested path. If you see both in `config.yaml`, remove the unused top-level one:
  ```bash
  # Remove the unused top-level api_key (if present)
  python3 -c "
  with open('/root/.hermes/config.yaml', 'r') as f:
      lines = f.readlines()
  lines = [l for l in lines if not l.strip().startswith('api_key:') 
           or l.strip().startswith('  api_key:')]
  with open('/root/.hermes/config.yaml', 'w') as f:
      f.writelines(lines)
  "
  ```
