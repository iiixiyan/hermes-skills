# Cron 401 Fix by Pinning to Fallback Provider

## Environment
- **Host:** Linux 5.14.0-362.8.1.el9_3.x86_64
- **Default provider:** deepseek (`api.deepseek.com/v1`) — key expired
- **Fallback:** custom (`token.sensenova.cn/v1`) — key valid (SENSENOVA_API_KEY)
- **Model:** deepseek-v4-flash

## The Failing Job
- **Job ID:** `65de6633f87d` — 竞足每日复盘优化 (Daily Jingzu Review)
- **Schedule:** `0 11 * * *` (daily 11:00)
- **Skills:** `[59itou-data-fetch, football-prediction]`
- **Model:** `null`, **Provider:** `null` (no pinned provider)

## The Error
```
RuntimeError: Error code: 401 - {'error': {'code': 16, 'message': 'Forbidden'}}
```

## Diagnosis

1. **Listed jobs** → `last_status: "error"` on job `65de6633f87d`
2. **Checked job config** → `model: null, provider: null` — no pinned provider
3. **Tested default provider key** (deepseek) → HTTP 401, key expired
4. **Checked `~/.hermes/config.yaml`** → found working fallback providers:
   ```yaml
   fallback_providers:
     - provider: custom
       model: deepseek-v4-flash
       base_url: https://token.sensenova.cn/v1
       api_key: sk-GE9...KLkS
   ```
5. **Tested fallback** → HTTP 200 ✅

## Fix

Pinned the job to the working fallback provider:
```
cronjob(action='update', job_id='65de6633f87d',
    model={'model': 'deepseek-v4-flash', 'provider': 'custom:deepseek-v4-flash'})
```

Key insight: `provider` format for custom fallback = `custom:<model>`

## Key Difference from Previous Fix

| Previous fix (f84b9cf8d1ef) | This fix (65de6633f87d) |
|----------------------------|------------------------|
| Job had pinned deepseek provider → **unpinned** it | Job had NO pinned provider → **pinned** to working fallback |
| Fix: remove pinned model so it inherits system default | Fix: cannot inherit system default (key expired), so pin to alternate |
| Root cause: env mismatch | Root cause: expired key |

## Other Jobs at Risk

These jobs also pin `provider: deepseek` with the expired key:
- `cd0456f2c803` (竞足每日预测)
- `99da379ec645` (北单晚场预测)
- `9af717d3c89b` (竞足每周复盘)
- `6beabbc435d2` (北单每周复盘)
- `ddd6db21550b` (SP预警)
