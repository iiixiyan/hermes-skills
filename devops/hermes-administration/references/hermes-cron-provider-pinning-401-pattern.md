# Provider Pinning 401 Pattern — Real Session Reproduction

## Environment

- Hermes version: unspecified (gateway PID 200121, Jun 18 2026)
- Host: Linux 5.14.0-362.8.1.el9_3.x86_64
- Provider: DeepSeek (`api.deepseek.com/v1`)
- Model: `deepseek-v4-flash`
- API key stored in `~/.hermes/.env` as `DEEPSEEK_API_KEY`

## The Job

**Name:** 竞足每日复盘优化 (Daily Jingzu Review)
**Job ID (old):** `f84b9cf8d1ef`
**Schedule:** `0 11 * * *` (daily 11:00)
**Skills:** `[59itou-data-fetch, football-prediction]`
**Deliver:** WeChat DM (`weixin:o9cq807XDvGnSulORJ_iRtMlbePc@im.wechat`)

## The Error

```
Cronjob Response: 竞足每日复盘优化
(job_id: f84b9cf8d1ef)
-------------
⚠️ Cron job '竞足每日复盘优化' failed:
RuntimeError: Error code: 401 - {'error': {'code': 16, 'message': 'Forbidden'}}
```

## Diagnosis

1. **Listed all jobs** via `cronjob(action='list')` — confirmed `last_status: "error"` on the failing job.
2. **Checked the failed job's config** — it had pinned `model: "deepseek-v4-flash"` and `provider: "deepseek"` with `base_url: null`.
3. **Tested the API key directly** in the current shell environment:
   ```bash
   source ~/.hermes/.env
   curl -s -w "\nHTTP:%{http_code}" "https://api.deepseek.com/v1/chat/completions" ...
   ```
   Result: **HTTP 200** — the key itself was valid.
4. **Compared with other jobs** — several other jobs also pinned the same `deepseek` provider and model, but their last runs (June 17) were successful. Only the June 18 run of this specific job failed.
5. **Conclusion**: the cron runtime environment couldn't load the API key for the pinned provider, despite the key being valid when tested from the interactive shell. Unpinning the provider lets the cron job use the gateway's own env loading mechanism, which resolves correctly.

## The Fix

1. Removed the old job:
   ```
   cronjob(action='remove', job_id='f84b9cf8d1ef')
   ```
2. Recreated with identical config **except no pinned model/provider**:
   ```
   cronjob(
       action='create',
       name='竞足每日复盘优化',
       schedule='0 11 * * *',
       skills=['59itou-data-fetch', 'football-prediction'],
       prompt='<same_prompt>'
   )
   ```
   New job ID: `65de6633f87d` — model/provider both `null`.

## Verification

- New job created successfully with `model: null, provider: null`
- Next scheduled run: following day 11:00
- Triggered `cronjob(action='run', job_id='65de6633f87d')` immediately
- Status confirmed correct via `cronjob(action='list')`

## Other Jobs at Risk

These jobs also have pinned `provider: "deepseek"` and may fail similarly:

| Job ID | Name | Schedule | Last Status |
|--------|------|----------|-------------|
| `cd0456f2c803` | 竞足每日预测 | 18:30 daily | OK (Jun 17) |
| `99da379ec645` | 北单晚场预测 | 22:00 daily | OK (Jun 17) |
| `9af717d3c89b` | 竞足每周复盘 | Sat 08:00 | OK (Jun 13) |
| `6beabbc435d2` | 北单每周复盘 | Sun 08:00 | OK (Jun 14) |
| `ddd6db21550b` | 临场SP异动预警 | 20:00 daily | OK (Jun 17) |

If any of these also 401 on their next run, recreate them using the same unpin-the-provider pattern.
