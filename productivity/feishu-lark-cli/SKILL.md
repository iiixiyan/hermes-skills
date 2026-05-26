---
name: feishu-lark-cli
description: Feishu/Lark CLI 操作 — 配置认证、读写文档、发送消息、管理知识库等。覆盖 lark-cli 的 auth binding、device-flow 授权、docs/wiki 操作。
---

# Feishu/Lark CLI 操作（lark-cli）

## 触发条件
需要在飞书（Feishu/Lark）中执行操作时加载 — 创建/更新/读取文档、配置授权、发送消息、管理知识库。

## 快速开始

### 1. 绑定 Hermes 上下文
在飞书对话中首次使用 `lark-cli` 前，必须绑定认证：
```bash
# 确认用户意图后执行
lark-cli config bind --source hermes --identity user-default

# identity 选项：
#   bot-only (安全默认) — 仅机器人身份，不能访问个人资源
#   user-default       — 模拟用户身份，可访问个人日历/邮箱/云盘
```

### 2. 用户授权（Device Flow）
绑定后需要用户授权：
```bash
# 方式A（推荐）：先获取 URL 发给用户，再轮询等待
lark-cli auth login --recommend --no-wait --json
```
返回 `verification_url` 和 `device_code`。**必须将 URL 原样发给用户（代码块包裹，不修改、不转义、不加空格或Markdown链接）**。用户在其浏览器中打开 URL 授权后，运行：
```bash
lark-cli auth login --device-code <code>
```

```bash
# 方式B（阻塞等待，需要长 timeout ≥600s）：
lark-cli auth login --recommend
# CLI 打印 URL 后阻塞等待用户授权
```

### 3. 验证状态
```bash
lark-cli auth status
# 查看 token 状态、过期时间、已授权 scopes
lark-cli auth scopes
# 查看应用已开启的 scopes
```

---

## ⚠️ 关键规则

### 授权链接处理
`lark-cli auth login` 返回的 `verification_url` 是 opaque string，必须：
- **原样逐字发送给用户**，不要做 URL 编码/解码
- 不要补 `%20`、空格或标点
- 不要改写成 Markdown 链接
- **推荐用只包含该 URL 的代码块单独输出**
- **不要用 `browser_navigate` 之类的工具自动打开** — 授权必须在用户的浏览器中完成

### ⚠️ 不要短 timeout 反复重试
每次重启 `auth login` 会作废上一轮的 device_code，导致用户已打开的授权链接失效。如果必须分段：
1. 用 `--no-wait --json` 拿到 device_code
2. 保存 device_code
3. 用户授权后，用 `--device-code <code>` 续上轮询

### Token 有效期
- Token 有效约 2 小时
- Refresh token 有效约 7 天
- 过期后重新 `lark-cli auth login` 即可

---

## 文档操作（docs）

### 读取文档
```bash
lark-cli docs +fetch --doc <文档URL或token> [--api-version v1]
# 返回 markdown 内容
```

### 写入/更新文档
```bash
# 追加内容
lark-cli docs +update --doc <token> --markdown "**标题**\n\`\`\`\n内容\n\`\`\`" --mode append

# 覆盖全部内容
lark-cli docs +update --doc <token> --markdown "新内容" --mode overwrite

# 替换指定标题下的内容
lark-cli docs +update --doc <token> --markdown "新段落" --mode replace_all --selection-by-title "## 原始标题"

# 可选参数
#   --api-version v1|v2   （v1 已废弃，优先用 v2 但需先更新技能）
#   --new-title "新标题"    同时修改文档标题
```

### Markdown 格式说明
- 支持标准 Markdown：标题 `##`、粗体 `**`、代码块 ` ``` `、列表等
- 原始数据用代码块包裹以保留格式：
  ```markdown
  **Tab名称**
  ```plaintext
  document.body.innerText 原始内容
  ```
  ```

### 文档媒体操作
```bash
# 上传并插入图片
lark-cli docs +media-insert --doc <token> --file /path/to/image.png

# 下载文档中的媒体
lark-cli docs +media-download --doc <token>
```

---

## 通用 API 调用

```bash
# GET 请求
lark-cli api GET /open-apis/drive/v1/files/<token>

# POST 请求
lark-cli api POST /open-apis/im/v1/messages \
  --data '{"receive_id":"ou_xxx","msg_type":"text","content":"{\"text\":\"你好\"}"}'

# 自动翻页（返回超过一页时）
lark-cli api GET /open-apis/... --page-all --page-limit 20
```

---

## 其他常用命令

```bash
# 知识库
lark-cli wiki --help

# 消息/群聊
lark-cli im --help

# 日历
lark-cli calendar --help

# 联系人
lark-cli contact --help

# 健康检查
lark-cli doctor
```

---

## 参考文件
- `references/auth-troubleshooting.md` — 认证常见问题
