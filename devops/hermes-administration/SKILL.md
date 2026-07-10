---
name: hermes-administration
description: "Administer Hermes Agent subsystems — cron job troubleshooting, memory provider setup, gateway configuration, and environment debugging. Covers 401 auth failures, provider pinning, post-upgrade migration, external memory provider integration, and common subsystem operations."
version: 1.0.0
author: Hermes Agent
tags: [hermes, cron, memory, troubleshooting, provider, auth, gateway]
---

# Hermes Agent Administration

> Umbrella skill for managing Hermes Agent subsystems: cron job troubleshooting, memory provider configuration, and common operational tasks.

This skill consolidates knowledge from narrower troubleshooting and setup skills into a single class-level reference. Each section covers one Hermes subsystem area.

---

## §1. Cron Job Troubleshooting

Diagnose and fix Hermes cron job failures — provider/model pinning issues, 401/403 auth errors, delivery failures, and environment mismatches between cron runtime and interactive sessions.

### 1.1 Triggers

- Cron job user receives an error report instead of the expected output
- `last_status: "error"` in `cronjob list`
- 401/403 errors: `{'error': {'code': 16, 'message': 'Forbidden'}}`
- Delivery errors without job errors (`last_status: "ok"` but `last_delivery_error` is set)

### 1.2 Why Cron Jobs Fail Differently

| Aspect | Interactive Session | Cron Runtime |
|--------|-------------------|--------------|
| `.env` loading | Loaded at startup, refreshed by `/reload` | Loaded at each run tick |
| API key access | Full session environment | Subprocess inherits gateway env |
| Provider pinning | Flexible — `model()` command | **Pinned at creation time** — model/provider are frozen |
| `base_url` resolution | From current config | From config at run time, but provider auth may differ |

**Critical gap:** when a cron job was pinned with a `provider` + `model`, and the provider's API key was later rotated or the env loading path changed, the cron session gets 401 even though interactive sessions still work.

### 1.3 Diagnosis Checklist

#### A. List jobs and check status

```bash
cronjob(action='list')
# Check: last_status, last_delivery_error, last_run_at
```

Check for:
- `last_status: "error"` — the job itself failed
- `last_delivery_error` set but `last_status: "ok"` — job ran, delivery failed
- `last_run_at` being old — job may be paused, stuck, or never ran

#### B. Diagnose 401/403 Provider Auth Errors

Error signature:
```
RuntimeError: Error code: 401 - {'error': {'code': 16, 'message': 'Forbidden'}}
```

**Key insight: null/null (unpinned) jobs can also 401.** Even without a pinned `model/provider`, the job inherits system defaults at runtime. If the default provider's auth is temporarily degraded or the gateway env doesn't match the interactive session, unpinned jobs fail identically to pinned ones. **Fix: pin explicitly to the working default.** Don't assume "unpinned = immune to 401."

**Test API key directly:**

```bash
source ~/.hermes/.env
curl -s -w "\nHTTP:%{http_code}" "https://api.deepseek.com/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}],"max_tokens":5}' | tail -3
```

- HTTP 200 → API key is valid. Problem is cron env vs interactive env mismatch.
- HTTP 401 → API key expired or invalid. Rotate key in `.env`.
- HTTP 429 → API key is valid but **out of quota** (insufficient_quota). Recharge or switch to a different provider. Distinguish from 401: a 429 can be temporary (daily quota refresh), a 401 is permanent until key rotation.

**Check which jobs have pinned providers:**

When a job was created with a `model`/`provider` override, it stores frozen values. Compare against system defaults:
```bash
hermes config show model
hermes config show provider
```

#### C. Read fallback chain from error log

When a job with `model: null, provider: null` still gets 401/403, read `errors.log` to see which providers were attempted:

```bash
grep "<failed_job_session_id>" /root/.hermes/logs/errors.log
```

Look for the **fallback chain exhaustion** pattern:

```log
WARNING [cron_<id>] agent.chat_completion_helpers: Fallback skip: chain entry <provider>/<model> matches current provider/model
WARNING [cron_<id>] agent.conversation_loop: API call failed (attempt 1/3) provider=<p1> model=<m1> summary=...
WARNING [cron_<id>] agent.conversation_loop: API call failed (attempt 1/3) provider=<p2> model=<m2> summary=...
ERROR [cron_<id>] agent.conversation_loop: Non-retryable client error: Error code: ...
```

Key signals:
- `Fallback skip: chain entry X matches current` = cron is correctly using the default provider (no pinning issue)
- Each `API call failed` line = one fallback chain entry that was attempted
- If ALL providers fail (primary + all fallbacks) with `AuthenticationError`, **every API key needs rotation** — no config fix helps
- Distinguish 401 (invalid key) vs 429 (quota exceeded) in the summary field

#### D. Special case: post-upgrade 401 (config version mismatch)

After `hermes update`, all cron jobs may 401 — even unpinned `null/null` jobs.

**Root cause:** Upgrade introduces new config schema version. Old config incompatible with new provider adapter. Built-in providers may stop reading API key from `.env` and require explicit `model.api_key`.

```bash
# 1. Check config version
hermes config check | grep "Config version"

# 2. Run migration
hermes config migrate

# 3. Check if model.api_key is set
grep -A5 "^model:" ~/.hermes/config.yaml | grep api_key

# 4. If missing, set it
hermes config set model.api_key "$(grep DEEPSEEK_API_KEY ~/.hermes/.env | head -1 | cut -d'=' -f2-)"

# 🚨 Gotcha: config migrate + model.api_key may NOT fix null/null jobs.
# After steps 1-4, interactive sessions work, but cron jobs with null/null can still 401.
# Fix: explicitly pin model/provider on EACH affected job:
cronjob(action='update', job_id='<job_id>',
    model={'model': 'deepseek-v4-flash', 'provider': 'deepseek'})
```

#### E. Special case: no pinned provider but still 401s

A job with `model: null, provider: null` uses system defaults. If that provider's key expired, the job 401s.

**Fix options:**

| Fix | When to use | Method |
|:---|:-----------|:-------|
| A | Default key expired, fallback exists | `provider: 'custom:<model>'` |
| B | Default key valid, cron doesn't auto-resolve | `provider: '<plain_provider_name>'` |

### 1.4 Fix — Provider 401

#### Option A: Pin to working fallback (preferred when default key expired)

Find working fallbacks in `~/.hermes/config.yaml` under `fallback_providers`:

```yaml
fallback_providers:
  - provider: custom
    model: deepseek-v4-flash
    base_url: https://token.sensenova.cn/v1
    api_key: sk-...
```

Test and pin:
```bash
curl -s -w "\nHTTP:%{http_code}" "https://token.sensenova.cn/v1/chat/completions" \
  -H "Authorization: Bearer $SENSENOVA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"test"}],"max_tokens":10}' | tail -3
```

If HTTP 200:
```
cronjob(action='update', job_id='<job_id>',
    model={'model': 'deepseek-v4-flash', 'provider': 'custom:deepseek-v4-flash'})
```

Note: `provider` format for custom fallback = `custom:<modelID>`.

#### Option B: Pin to plain provider name

When `model=null, provider=null` defaults are failing but the default provider key is valid:
```
cronjob(action='update', job_id='<job_id>',
    model={'model': 'deepseek-v4-flash', 'provider': 'deepseek'})
# Note: provider='deepseek', NOT 'custom:deepseek-v4-flash'
```

#### Option C: Recreate without pinned provider

When the pinned provider's API key has expired and no fallback is available:

```
cronjob(action='remove', job_id='<old_job_id>')
cronjob(action='create', name='<same_name>', prompt='<same_prompt>',
    schedule='<same_schedule>', skills=['<skill1>', '<skill2>'])
```

Do NOT pass `model` — job inherits current system defaults.

#### Option D: All providers dead — report to user

After exhausting the full fallback chain (diagnosed via §1.3.C), every API key is expired or out of quota.

**Symptom in error.log:** every `API call failed` line shows 401 or 429 across all entries in the fallback_providers list. No config change or cron update will fix it — the keys themselves must be refreshed.

**Action:** tell the user which keys are dead and which are out of quota, so they know which provider to fix:
- 401 = expired/invalid → needs key rotation
- 429 = quota exhausted → needs recharge or rate-limit wait

### 1.6 Fix Delivery Failures

A job with `last_status: "ok"` but non-null `last_delivery_error`:

1. **Check output was produced:**
   ```bash
   ls ~/.hermes/cron/output/<job_id>/
   ```
2. **Re-run** — delivery retries on next run:
   ```
   cronjob(action='run', job_id='<job_id>')
   ```
3. **Dual-channel delivery** — have the prompt write to a file + send to email/Gitee in addition to default delivery.

### 1.8 Preferences and Pitfalls

- **Do not pin model/provider in cron jobs unless necessary.** Unpinned jobs inherit system config and adapt gracefully when keys are rotated. If you must pin, verify auth works by running the job immediately after creation.
- **When ALL fallback providers also fail**, do NOT keep recreating the cron job — the problem is upstream (expired keys, exhausted quota), not in the config.
- **Model listing API (GET /v1/models) may work even when chat completions (POST /v1/chat/completions) fail with 429.** Test the actual chat endpoint, not the models endpoint, when verifying a fallback provider.
- **After rotating API keys**, check all pinned cron jobs. Recreate unpinned ones if they were previously pinned — the old pin still references the dead key.
- **⚠️ `hermes config set model.api_key` can CORRUPT the key.** When the key value shown in terminal contains `...` (e.g. `sk-57a...be2e`), Hermes secret redaction replaces the middle of the key with literal dots before writing to config.yaml. The resulting key is `sk-57a...be2e` (containing real `...` characters), not the full 35-char key. **Workaround:** write the key directly via Python file I/O (see `references/hermes-config-set-api-key-redaction.md`).
- **⚠️ `api_key` vs `model.api_key` — DIFFERENT config paths.** `hermes config set api_key X` creates a **top-level** `api_key` key in config.yaml, not `model.api_key`. The model reads from `model.api_key` (the nested path), so the top-level key has no effect. Always use `hermes config set model.api_key <key>` (with the `model.` prefix) to update the main DeepSeek/similar provider key. To check which was set:
  ```bash
  grep -A5 "^model:" ~/.hermes/config.yaml | grep api_key  # the real one
  grep "^api_key:" ~/.hermes/config.yaml                    # the top-level one (likely unused)
  ```
- **⚠️ `cronjob(action='run')` may not reliably execute for jobs with existing schedules.** Calling `run` schedules a one-shot tick but the job may not actually trigger if the scheduler skips ticks. The job's `next_run_at` returns to the regular schedule, `last_status` stays unchanged, and no output is produced. **Workaround:** remove and recreate the job as a one-shot, or run the prompt manually via `skill_view` + `delegate_task` to verify key validity.
- **`curl` test with the actual full key is the only reliable verification** that a new API key works. `hermes config set` and `cronjob run` can both mask success/failure. Always test with a direct chat completion call:
  ```bash
  curl -s https://api.deepseek.com/v1/chat/completions \
    -H "Authorization: Bearer <actual_full_key>" \
    -H "Content-Type: application/json" \
    -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"test"}],"max_tokens":5}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'choices' in d else 'FAIL: '+str(d))"
  ```
- **⚠️ Cron jobs with a previously-pinned provider CANNOT be fully un-pinned via `cronjob(action='update')`.** When a job was created with `model={'model': 'X', 'provider': 'Y'}`, and later updated by passing only `model={'model': 'X'}` (omitting provider), the response still shows the old provider. The provider lock persists even after update. **Workaround:** remove and recreate the job without the model parameter to let it inherit system defaults fully:
  ```python
  cronjob(action='remove', job_id='<old_job_id>')
  cronjob(action='create', name='<same_name>', prompt='<same_prompt>',
      schedule='<same_schedule>', skills=['<skill1>', '<skill2>'])
  # Do NOT pass model — inherits current system defaults and keys
  ```

### 1.8.5 Key rotation recipe — user-provided new key

When the user messages a fresh API key in chat (e.g. "this is my new DeepSeek key"), the workflow is:

```bash
# 1. Test the raw key immediately (before touching config)
curl -s https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer <actua...r>" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"test"}],"max_tokens":5}'

# 2. Set the key at the CORRECT path
hermes config set model.api_key "<full_key>"
# NOT: hermes config set api_key "<key>"  — this sets top-level, not model.api_key

# 3. Verify the write took effect
head -6 ~/.hermes/config.yaml  # confirm api_key under model:

# 4. Verify the key works end-to-end with a chat completion
curl -s https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer $(grep -A5 '^model:' ~/.hermes/config.yaml | grep api_key | awk '{print $NF}')" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"测试"}],"max_tokens":5}'
```

**Key insight: cron jobs with pinned `model`/`provider` inherit the API key from config AT RUN TIME, not at creation time.** After updating `model.api_key`, the next scheduled tick automatically picks up the new key — no need to recreate or repin the job. Verify by checking `~/.hermes/cron/output/<job_id>/` after the next run.

**If `cronjob(action='run')` schedules a one-shot but produces no output:** the one-shot may be silently skipped by the scheduler. Wait for the next regular schedule tick — it uses the same updated config and always fires. Do NOT keep calling `run` — it only crowds the scheduler queue.

### 1.9 References

- `references/cron-provider-pinning-401-pattern.md` — Full reproduction and fix transcript
- `references/cron-401-fallback-provider-fix.md` — Alternative fix: pinning to working fallback
- `references/post-upgrade-401-config-migration.md` — Post-upgrade config migration walkthrough
- `references/cron-all-providers-fail-diagnosis.md` — Fallback chain exhaustion: every API key dead

---

## §2. Memory Provider Setup

Configure and troubleshoot external memory providers for Hermes Agent. Covers installation, plugin linking, Gateway sidecars, env vars, and verification.

**Architecture:**
```
Hermes Agent (Python)
  └─ MemoryManager
       └─ <MemoryProvider> (plugin at plugins/memory/<name>/)
            ├─ SDK Client → HTTP API
            └─ (optional) Supervisor — auto-starts provider's sidecar
                    │
                    ▼ HTTP (usually localhost)
            Provider Gateway (sidecar process)
               └─ Storage backend (SQLite, vector DB, etc.)
```

### 2.1 General Setup Workflow

**Step 1 — Install the provider package:**
```bash
npm install @vendor/provider-package    # Node-based
pip install provider-package            # Python-based
```

**Step 2 — Set up the backing service:**

Auto-discovery or explicit path:
```bash
mkdir -p ~/.memory-provider
ln -sf $(npm root)/@vendor/provider-package ~/.memory-provider/example
```

**Step 3 — Install Node dependencies:**
```bash
cd ~/.memory-provider/example && npm install
```

**Step 4 — Copy/link the Hermes plugin:**
```bash
cp -r path/to/hermes-plugin/memory/<provider_name> /path/to/hermes-agent/plugins/memory/
```

Directory name MUST match `plugin.yaml::name` (underscores, not hyphens).

**Step 5 — Configure config.yaml:**
```bash
hermes config set memory.provider <provider_name>
```
Never edit config.yaml directly — always use `hermes config set`.

**Step 6 — Set environment variables:**

Create env files in `~/.hermes/env.d/`:
```bash
cat > ~/.hermes/env.d/memory-provider-llm.sh << 'EOF'
export PROVIDER_API_KEY="sk-..."
export PROVIDER_BASE_URL="https://api.example.com/v1"
export PROVIDER_MODEL="deepseek-v4-pro"
EOF
```

Common env vars:
- `PROVIDER_API_KEY` — Gateway LLM API key (for memory extraction)
- `PROVIDER_BASE_URL` — Gateway LLM endpoint
- `PROVIDER_MODEL` — Gateway LLM model name
- `PROVIDER_GATEWAY_CMD` — Explicit start command (overrides auto-discovery)

**Step 7 — Verify provider discovery:**
```bash
cd /path/to/hermes-agent
python3 -c "
from plugins.memory import discover_memory_providers
for name, is_available, _ in discover_memory_providers():
    print(f'{name}: {is_available}')
"
```

### 2.2 Pitfalls

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Direct config editing blocked** | Hermes blocks direct writes to `config.yaml` | Always use `hermes config set memory.provider <name>` |
| **Directory naming** | Plugin not found | Directory name (underscore) MUST match `plugin.yaml::name` AND `memory.provider` value |
| **Package manager conflicts** | npm vs pnpm auto-discovery | Set `PROVIDER_GATEWAY_CMD` explicitly |
| **env.d timing** | Vars not available mid-session | `source ~/.hermes/env.d/*.sh` before testing manually |
| **Gateway port conflicts** | Sidecar fails to start | Check port availability (`lsof -i :8420`) |

### 2.3 Specific Providers

#### TencentDB Agent Memory (`memory_tencentdb`)

A 4-tier memory system (L0 raw → L1 episodic → L2 scene → L3 persona) as a Node.js Gateway sidecar on `localhost:8420`.

**Quick setup:**
```bash
npm install @tencentdb-agent-memory/memory-tencentdb@latest
mkdir -p ~/.memory-tencentdb
ln -sf $(npm root)/@tencentdb-agent-memory/memory-tencentdb ~/.memory-tencentdb/tdai-memory-openclaw-plugin
cd ~/.memory-tencentdb/tdai-memory-openclaw-plugin && npm install
cp -r $(npm root)/@tencentdb-agent-memory/memory-tencentdb/hermes-plugin/memory/memory_tencentdb /path/to/hermes-agent/plugins/memory/
hermes config set memory.provider memory_tencentdb
```

**Key env vars:**
```bash
export MEMORY_TENCENTDB_LLM_BASE_URL="https://api.deepseek.com/v1"
export MEMORY_TENCENTDB_LLM_MODEL="deepseek-v4-pro"
export MEMORY_TENCENTDB_LLM_API_KEY="sk-..."
export MEMORY_TENCENTDB_GATEWAY_CMD="sh -c 'cd /root/.memory-tencentdb/tdai-memory-openclaw-plugin && exec npx tsx src/gateway/server.ts'"
```

**Provider tools:**
- `memory_tencentdb_memory_search` — Search L1 structured long-term memory
- `memory_tencentdb_conversation_search` — Search L0 raw conversation

**Gateway health check:**
```bash
curl http://127.0.0.1:8420/health
# Expected: {"status":"ok"}
```

**Verification:**
```bash
source ~/.hermes/env.d/memory-tencentdb-llm.sh
cd /path/to/hermes-agent
python3 -c "
from plugins.memory.memory_tencentdb import MemoryTencentdbProvider
p = MemoryTencentdbProvider()
print(f'Available: {p.is_available()}')
print(f'Tools: {[t[\"name\"] for t in p.get_tool_schemas()]}')
"
```

See `references/tencentdb-integration.md` for complete setup walkthrough.

### 2.4 References

- `references/tencentdb-integration.md` — Full TencentDB setup with architecture, env config, troubleshooting table

---

## §3. General Hermes Operations

### 3.1 `hermes update` Timeout (China Networks)

The built-in `hermes update` may timeout (120s+) when hitting Baidu mirrors with stale packages:

```bash
# Check latest version on Tsinghua mirror
pip index versions hermes-agent -i https://pypi.tuna.tsinghua.edu.cn/simple/

# Upgrade with Tsinghua mirror
cd ~/.hermes/hermes-agent && source venv/bin/activate
pip install --upgrade hermes-agent -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 3.2 Cron Prompt Design Principles

- Keep prompts under ~700 chars. Longer prompts cause agent context stalls.
- Reference skill files via `skill_view('name')` — don't inline their content.
- Include structured output templates in the prompt.
- Test with `cronjob(action='run', job_id='<job_id>')` after creating or editing.
- One-shot, never interactive — cron sessions run with no user present.

### 3.3 Installing Community Skills (ClawHub / External Sources)

Install skills from ClawHub (or direct SKILL.md URLs) using:

```bash
hermes skills install https://clawhub.ai/<user>/skills/<skill-name>    # ClawHub URL
hermes skills install @<user>/<skill>                                  # Hub identifier
hermes skills install https://raw.githubusercontent.com/.../SKILL.md    # Raw GitHub URL
```

#### BOM Security Scan Block

Community skills (especially from ClawHub) often trigger a **CAUTION** verdict because the README contains a **U+FEFF (BOM/zero-width no-break space)** at line 1. This is flagged as HIGH severity "injection" risk:

```
Scan: wechat-publisher-pro (wechat-publisher-pro/community)  Verdict: CAUTION
  HIGH     injection      README.md:1                    "U+FEFF (BOM/zero-width
no-break space)"

Decision: BLOCKED — Blocked (community source + caution verdict, 1 findings).
Use --force to override.
```

**Fix:** Use `--force` to bypass:

```bash
hermes skills install <url> --force
```

The BOM is harmless (UTF-8 BOM from Windows editors or content management systems). After forced install, the skill works normally. Verify with:

```bash
hermes skills list | grep <skill-name>
```

#### Pitfalls

- **Inspect first** — `hermes skills inspect <id>` shows a preview without installing. May timeout if the hub is slow (GitHub API latency). Use `curl` to check the raw SKILL.md directly instead.
- **`--force` only needed for non-bundled, community-source skills.** Hermes-bundled skills and official hub skills pass the security scan without flags.
- **The BOM is in README.md, not SKILL.md.** The skill logic itself is unaffected — only the README triggers the scanner.
- **After install**, the skill lives under `~/.hermes/skills/<skill-name>/` as a read-only hub install. Do not modify its files directly — edits will be lost on update. Changes belong in user-created umbrella skills.
- **Uninstall:** `hermes skills uninstall <skill-name>`

### 3.4 Gateway Service Management

```bash
# Check gateway status
hermes gateway status

# Restart gateway
hermes gateway restart

# Check gateway logs
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20

# Enable linger (prevent gateway death on SSH logout)
sudo loginctl enable-linger $USER

# Reset failed state (gateway crash loop)
systemctl --user reset-failed hermes-gateway
```
