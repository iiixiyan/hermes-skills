# DeepSeek Official API

API endpoint: `https://api.deepseek.com/v1`
Auth: Bearer token (`Authorization: Bearer sk-xxx`)
Provider value in config: `custom` (OpenAI-compatible)

## Available Models (as of May 2026)

| Model ID | Type | Notes |
|----------|------|-------|
| `deepseek-v4-flash` | Text-only LLM | 262K context, tools/json_mode/reasoning |
| `deepseek-v4-pro` | Text-only LLM (premium) | Higher quality, slower |

## Config Example (as fallback provider)

```yaml
model:
  default: deepseek-v4-flash
  provider: custom
  base_url: https://token.sensenova.cn/v1
  api_key: sk-xxxxx

fallback_providers:
  - provider: custom
    model: sensenova-6.7-flash-lite
    base_url: https://token.sensenova.cn/v1
  - provider: custom
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key: sk-xxxxx
```

The same model (`deepseek-v4-flash`) is used via two different endpoints. API keys are independent — the SenseNova key and DeepSeek official key are separate credentials.

## Test Call

```bash
curl -s "https://api.deepseek.com/v1/chat/completions" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Hi"}]}'
```

## Discovery

```bash
curl -s "https://api.deepseek.com/v1/models" \
  -H "Authorization: Bearer $API_KEY"
```

## Notes

- Pricing varies by model; check [platform.deepseek.com](https://platform.deepseek.com) for current rates.
- Use `provider: custom` in Hermes config — there is no built-in DeepSeek adapter.
- The API key can be set inline in config.yaml or stored in `.env` as `DEEPSEEK_API_KEY` and referenced via `key_env: DEEPSEEK_API_KEY` in fallback entries.
