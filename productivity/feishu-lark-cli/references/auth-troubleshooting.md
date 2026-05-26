# lark-cli 认证常见问题

## "hermes context detected but lark-cli is not bound to it"

**错误信息**：
```
"hermes context detected but lark-cli is not bound to it",
"hint": "read lark-cli config bind --help"
```

**解决**：先绑定 Hermes 上下文：
```bash
lark-cli config bind --source hermes --identity user-default
```

**注意**：绑定前必须先让用户确认（身份预设：bot-only 或 user-default）。

## "please specify the scopes to authorize"

**错误信息**：
```
"please specify the scopes to authorize"
```

**解决**：使用 `--recommend` 标志自动选择推荐权限：
```bash
lark-cli auth login --recommend
# 或分段执行：
lark-cli auth login --recommend --no-wait --json
```

## Token 过期

Token 有效期约 2 小时。过期后：
```bash
lark-cli auth login --recommend
# 重新走 Device Flow
```

Refresh token 有效期约 7 天，过期后需重新绑定并授权。

## 授权链接失效

用户拿到链接后如果授权页报错/过期：
1. 用 `--no-wait --json` 重新获取新的 device_code
2. 把新的 `verification_url` 发给用户

**不要用旧的 device_code 重试** — 每次 `auth login` 重新执行会作废上一轮的 device_code。

## 身份策略切换

如果已绑定 bot-only，想切到 user-default：
```bash
# 先确认用户意图，再执行
lark-cli config bind --source hermes --identity user-default --force
```

**⚠️ 切换到 user-default 后，AI 将以用户的名义在飞书中执行所有操作（读写文档、搜索消息、修改日程等）。切勿将机器人分享给他人或拉入群聊。**
