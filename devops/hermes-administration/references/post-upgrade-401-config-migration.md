# Post-Upgrade 401: Config Version Mismatch

**Encountered:** 2026-06-26, Hermes v0.16.0→v0.17.0  
**Symptom:** All cron jobs returning 401 `{'error': {'code': 16, 'message': 'Forbidden'}}`  
**Scope:** Jobs with `model: null, provider: null` (inherit defaults) AND pinned jobs

## Root Cause

`hermes update` from v0.16.0→v0.17.0 introduced config schema version 30. The running config was still v26. The DeepSeek built-in provider adapter in v0.17.0 changed how it resolves the API key:

- **Old (v0.16.0):** `provider: deepseek` silently reads `DEEPSEEK_API_KEY` from `.env`
- **New (v0.17.0):** `provider: deepseek` requires `model.api_key` to be set in `config.yaml`. If empty, the adapter returns 401.

## Fix Sequence

```bash
# 1. Check current config version
hermes config check | grep "Config version"

# 2. Run migration (v26→v30)
hermes config migrate

# 3. Check if model.api_key is set
grep -A5 "^model:" ~/.hermes/config.yaml | grep api_key

# 4. If missing, copy key from .env into config
hermes config set model.api_key "$(grep DEEPSEEK_API_KEY ~/.hermes/.env | head -1 | cut -d'=' -f2-)"

# 5. Verify API key works
curl -s https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $(grep DEEPSEEK_API_KEY ~/.hermes/.env | head -1 | cut -d'=' -f2-)" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('OK' if 'data' in d else 'FAIL')"

# 6. Re-run the failed cron job
cronjob(action='run', job_id='<job_id>')
```

## 🚨 Gotcha: config migrate + model.api_key may NOT fix null/null jobs

After steps 1-5, **interactive sessions and `hermes chat -q` work fine**, but cron jobs with `model: null, provider: null` can **still 401**. This happened because the cron scheduler's provider resolution path differs from the interactive path even when the default config is correct.

**Don't assume `config migrate` + `model.api_key` is sufficient.** You must also:

```
# Explicitly pin model/provider on EACH affected job
cronjob(action='update', job_id='<job_id>',
    model={'model': 'deepseek-v4-flash', 'provider': 'deepseek'})
```

This applies to ANY cron job that was created before the upgrade, regardless of whether it previously had model/provider pinned.

## 🚨 Gotcha: Baidu pip mirror may not have latest version

`hermes update` uses the system pip which hits Baidu mirrors (`http://mirrors.baidubce.com/pypi/simple/`). These mirrors may lag behind PyPI by days. If `hermes update` times out or reports "already up to date" when you know a newer version exists:

```bash
# Check latest version on Tsinghua mirror (faster than official PyPI for China)
pip index versions hermes-agent -i https://pypi.tuna.tsinghua.edu.cn/simple/

# Upgrade with Tsinghua mirror
cd ~/.hermes/hermes-agent && source venv/bin/activate
pip install --upgrade hermes-agent -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

## Prevention

After any `hermes update`:
1. Always run `hermes config migrate`
2. Check `hermes config check` for version mismatch warnings
3. Verify `model.api_key` is set for built-in providers
4. **Explicitly pin model/provider on ALL cron jobs** — even those with `null/null`
5. Test: trigger a cron run immediately: `cronjob(action='run', job_id='<job_id>')`
6. If `hermes update` timed out, use pip with Tsinghua mirror directly
