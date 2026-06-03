# SenseNova (商汤) Custom Provider

API endpoint: `https://token.sensenova.cn/v1`
Auth: Bearer token (`Authorization: Bearer sk-xxx`)
Provider value in config: `custom`

## Available Models (as of June 2026)

| Model ID | Type | Context | Status | Notes |
|----------|------|---------|--------|-------|
| `deepseek-v4-flash` | Text-only LLM | 262K | ✅ Working | Supports tools, json_mode, reasoning. Produces thinking + output by default. |
| `sensenova-6.7-flash-lite` | Multimodal (text+image) | 262K | ⚠️ Needs thinking:disabled | See **Pitfalls** below — default mode dumps thinking tokens only with no output. |
| `sensenova-u1-fast` | Image gen (infographics) | 262K | ❌ NOT FOUND | Returns "model is not found" on chat/completions endpoint. Skip entirely. |

## Config Example (YAML list format, preferred)

```yaml
model:
  default: deepseek-v4-flash
  provider: custom
  base_url: https://api.deepseek.com/v1
  api_key: sk-xxxxx

fallback_providers:
  - provider: custom
    model: deepseek-v4-flash
    base_url: https://token.sensenova.cn/v1
    api_key: sk-xxxxx
  - provider: custom
    model: deepseek-v4-pro
    base_url: https://api.deepseek.com/v1
    api_key: sk-xxxxx
  - provider: custom
    model: sensenova-6.7-flash-lite
    base_url: https://token.sensenova.cn/v1
    api_key: sk-xxxxx
```

> **Tip**: YAML list format (`fallback_providers:` + indented `- provider:` items) is cleaner and avoids escaping issues. The JSON-string format (`fallback_providers: '[...]'`) also works but is harder to read and edit.

## Pitfalls

### 1. sensenova-6.7-flash-lite: thinking mode must be disabled

This model defaults to reasoning/thinking mode. Without disabling it, the API returns HTTP 200 but the response `content` is empty — all token budget is consumed by `reasoning_content` with no final output.

**Test evidence**:
- Without `thinking: disabled`: finish=length, tok=242, content=(empty)
- With `thinking: {"type": "disabled"}`: finish=stop, tok=51, content="Hello! How can I assist you today?"

**Fix**: Pass `"thinking": {"type": "disabled"}` in the request body.

```bash
curl -s "https://token.sensenova.cn/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"sensenova-6.7-flash-lite","thinking":{"type":"disabled"},"messages":[{"role":"user","content":"Say hello"}]}'
```

In Hermes config, if `fallback_providers` supports `extra_body`, include it:
```yaml
  - provider: custom
    model: sensenova-6.7-flash-lite
    base_url: https://token.sensenova.cn/v1
    api_key: sk-xxxxx
    # Ideally: extra_body: {"thinking": {"type": "disabled"}}
```

### 2. sensenova-u1-fast is unavailable

Returns HTTP 404 / "model is not found" on the standard chat completions endpoint. Despite being listed in Sensenova's model catalog, it does not work for general chat. Skip it.

### 3. deepseek-v4-flash works on both lines

This model works identically on DeepSeek official (`api.deepseek.com`) and Sensenova (`token.sensenova.cn`). Configuring both as primary + fallback provides redundancy without quality degradation.

### 4. YAML file corruption risk

When editing `config.yaml` via Python `execute_code` (which rewrites the entire file), complex YAML structures (personalities with Unicode escape sequences, multi-line strings) can be corrupted. **Use `patch` for targeted edits on YAML files** rather than rewriting the whole file.

## Discovery

```bash
curl -s "https://token.sensenova.cn/v1/models" \
  -H "Authorization: Bearer $API_KEY"
```

## Test Call (verified working)

```bash
# deepseek-v4-flash — basic
curl -s "https://token.sensenova.cn/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Hi"}]}'

# sensenova-6.7-flash-lite — MUST include thinking:disabled
curl -s "https://token.sensenova.cn/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"sensenova-6.7-flash-lite","thinking":{"type":"disabled"},"messages":[{"role":"user","content":"Hi"}]}'
```

## Notes

- Pricing appears to be free (all models show `pricing: { prompt: "0", completion: "0" }`) — check current status.
- Datacenter: CN only.
- Use `provider: custom` in Hermes config — there is no built-in SenseNova adapter.
- For Hermes, the API key can be set inline in config.yaml or stored in `.env` and referenced via `key_env` in `fallback_providers`.
