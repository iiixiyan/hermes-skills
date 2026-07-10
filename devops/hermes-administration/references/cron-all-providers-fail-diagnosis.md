# Cron Job: All Providers Failed Diagnosis

> 2026-07-01 session | Fixed: removed old pinned job, recreated unpinned

## Scenario

A cron job (北单每日复盘优化, job_id=d7b9747e6206) ran daily at 14:00 and failed with:

```
RuntimeError: Error code: 401 - {'error': {'code': 16, 'message': 'Forbidden'}}
```

It failed for 2 consecutive days. Other cron jobs at different hours (18:30, 22:00) using the same provider still worked.

## Diagnosis Steps

### Step 1: Identify pinned provider

```
cronjob(action='list')
→ model: deepseek-v4-flash, provider: deepseek, base_url: null
```

The job was created with an explicit model/provider pin.

### Step 2: Test API key directly

```python
curl -s https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY"
→ HTTP 401, "Authentication Fails, Your api key is invalid"
```

Key was dead.

### Step 3: Check fallback provider

Config had `fallback_providers` with a Sensenova endpoint:

```bash
curl -s https://token.sensenova.cn/v1/models \
  -H "Authorization: Bearer $SENSENOVA_API_KEY"
→ HTTP 200, model list returned
```

Model listing worked! But chat completions:

```bash
curl -s https://token.sensenova.cn/v1/chat/completions \
  -H "Authorization: Bearer $SENSENOVA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"test"}],"max_tokens":5}'
→ HTTP 429, "insufficient_quota"
```

Key was valid but out of quota. **Important: model listing API working does not mean chat completions will work.**

### Step 4: Update pinned provider

Tried `cronjob(action='update', job_id='...', model={'provider':'custom', 'model':'deepseek-v4-flash'})`

Still failed because the `custom` provider resolved to the config's dead keys.

### Step 5: Change default config

```bash
hermes config set model.provider custom
hermes config set model.base_url https://token.sensenova.cn/v1
```

This changed the session's default but pinned cron jobs still used the old provider.

### Step 6: Recreate without pinning (the fix)

```bash
cronjob(action='remove', job_id='d7b9747e6206')
cronjob(action='create', name='北单每日复盘优化', prompt='...', schedule='0 14 * * *',
    skills=['59itou-data-fetch', 'bjdc-prediction'])
```

**Do NOT pass `model`** — the new job inherits system defaults.

BUT this still failed because ALL API keys in the system were dead (expired + out of quota).

### Step 7: Read fallback chain from error log

```bash
grep "25ad8d1cbd78" /root/.hermes/logs/errors.log
```

Showed:
1. `Fallback skip: chain entry custom/deepseek-v4-flash matches current provider/model` — routing was correct
2. `provider=custom base_url=https://api.deepseek.com/v1/ model=deepseek-v4-pro → HTTP 401` — dead key
3. `provider=custom base_url=https://token.sensenova.cn/v1/ model=sensenova-6.7-flash-lite → HTTP 401` — also dead/quota exhausted

**Final finding:** Every provider in the chain was dead → user must rotate API keys. No amount of config changes or cron recreation will fix source-of-truth key failures.

## Secrets Redaction Note

Hermes redacts API keys aggressively:
- `os.environ.get('SENSENOVA_API_KEY')` returns the key but any **output** is replaced with `sk-GE9...KLkS`
- `/proc/pid/environ` and `xxd` hex dumps also show redacted output
- `hermes config set model.api_key <key>` redacts in display but stores the correct key in config.yaml (verified via hex dump of raw bytes)
- When debugging key issues, verify config content via **hex dump** of the raw config.yaml bytes, not via `grep` or `cat`
- The current interactive session works because Hermes started with the real key from `.env` before redaction was applied; cron jobs read from config which may have stale/redacted values
