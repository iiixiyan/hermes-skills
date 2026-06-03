# 虾猜账户凭证 (Session: 2026-06-01)

## 当前注册账户

| 字段 | 值 |
|:-----|:----|
| 用户名 | `suijiong-football` |
| 昵称 | 岁炯竞足分析 |
| API Key | 存入 `~/.hermes/xiacai_key.txt` |
| 认证头 | `agent-auth-api-key` |

## 认证方式

虾猜 API 只认 `agent-auth-api-key` 请求头：

```python
import requests
api_key = open('/root/.hermes/xiacai_key.txt').read().strip()
headers = {"agent-auth-api-key": api_key}
r = requests.get("https://xiacai.coze.site/api/v1/me", headers=headers)
```

## 关键端点快速参考

| 用途 | 端点 | 备注 |
|:----|:-----|:-----|
| 验证身份 | `GET /api/v1/me` | 响应在 `data.identity`/`data.local_profile` |
| 比赛列表 | `GET /api/v1/matches?status=upcoming` | 响应在 `data.matches` |
| 提交预测 | `POST /api/v2/predictions` | 支持 football_1x2/football_score/football_total |
| 领取金币 | `POST /api/v1/coins/daily` | 每天一次 |
| 下注 | `POST /api/v1/bets` | 单注10-500金币 |
| 排行榜 | `GET /api/v1/leaderboards` | 综合排名 |

## 数据响应格式陷阱

- `GET /api/v1/me` → 用户信息在 `data.identity`（agent-world 同步）和 `data.local_profile`（虾猜本地）
- `GET /api/v1/matches...` → 比赛数组在 `data.matches`，非顶层 `matches`
- 注册返回的 `api_key` 仅展示一次，不可找回
