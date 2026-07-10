# TencentDB Agent Memory 接入 Hermes 完整记录

> 版本: v0.3.6（npm）
> 接入时间: 2026-06-04
> 服务器: Linux x86_64, Node v22.22.2, Python 3.11

## 架构

```
Hermes Agent (Python)
  └─ MemoryTencentdbProvider (plugins/memory/memory_tencentdb/)
       ├─ GatewaySupervisor → subprocess Popen of Node.js sidecar
       └─ MemoryTencentdbSdkClient → POST /recall, /capture, /search
              │
              ▼ HTTP 127.0.0.1:8420
       Gateway (Node.js, tsx + src/gateway/server.ts)
          ├─ L0 Conversation store (SQLite + JSONL)
          ├─ L1 Episodic extraction (DeepSeek v4 Pro LLM)
          ├─ L2 Scene blocks (Markdown)
          └─ L3 Persona synthesis
```

## 完整安装步骤

### 1. 安装 npm 包

```bash
npm install @tencentdb-agent-memory/memory-tencentdb@latest
```

### 2. 创建路径结构（用于 Gateway 自动发现）

```bash
mkdir -p ~/.memory-tencentdb
ln -sf $(npm root)/@tencentdb-agent-memory/memory-tencentdb \
       ~/.memory-tencentdb/tdai-memory-openclaw-plugin
```

### 3. 安装 Gateway 的 Node 依赖

```bash
cd ~/.memory-tencentdb/tdai-memory-openclaw-plugin
npm install    # 约 548 个包，~1分钟
```

### 4. 复制 Hermes 记忆提供者插件

```bash
cp -r $(npm root)/@tencentdb-agent-memory/memory-tencentdb/hermes-plugin/memory/memory_tencentdb \
      /path/to/hermes-agent/plugins/memory/
```

### 5. 配置记忆提供者

```bash
hermes config set memory.provider memory_tencentdb
```

### 6. 配置环境变量

在 `~/.hermes/env.d/memory-tencentdb-llm.sh` 中写入：

```bash
# Gateway LLM 凭据（用于 L1/L2/L3 记忆提取）
export MEMORY_TENCENTDB_LLM_BASE_URL="https://api.deepseek.com/v1"
export MEMORY_TENCENTDB_LLM_MODEL="deepseek-v4-pro"
export MEMORY_TENCENTDB_LLM_API_KEY="sk-..."  # 你的 API Key

# 日志目录
export MEMORY_TENCENTDB_LOG_DIR="/root/.hermes/logs/memory_tencentdb"

# ⚠️ 重要：显式指定 Gateway 启动命令（覆盖自动发现中的 pnpm）
export MEMORY_TENCENTDB_GATEWAY_CMD="sh -c 'cd /root/.memory-tencentdb/tdai-memory-openclaw-plugin && exec npx tsx src/gateway/server.ts'"
```

### 7. 验证

```bash
source ~/.hermes/env.d/memory-tencentdb-llm.sh

# 检查 Gateway 自动发现
cd /path/to/hermes-agent
python3 -c "from plugins.memory.memory_tencentdb import _discover_gateway_cmd; print(_discover_gateway_cmd())"

# 检查提供者可用性
python3 -c "
from plugins.memory.memory_tencentdb import MemoryTencentdbProvider
p = MemoryTencentdbProvider()
print(f'Available: {p.is_available()}')
print(f'Tools: {[t[\"name\"] for t in p.get_tool_schemas()]}')
"
```

预期输出:
```
Auto-discovery: sh -c 'cd ... && exec pnpm exec tsx src/gateway/server.ts'
Available: True
Tools: ['memory_tencentdb_memory_search', 'memory_tencentdb_conversation_search']
```

## 陷阱与避坑

### ⚠️ pnpm vs npm 冲突
自动发现的 Gateway 启动命令使用 `pnpm exec tsx`。如果插件是用 `npm install` 部署的（不是 pnpm），pnpm 会试图把所有依赖移动到 `.ignored` 并重新下载，导致启动失败。

**解决方案:** 通过 `MEMORY_TENCENTDB_GATEWAY_CMD` 显式指定用 `npx tsx`。

### ⚠️ 环境变量的生效时机
`env.d/*.sh` 中的变量只有在 Hermes 启动时 source 后才可用。在单独测试时需手动 source。

### ⚠️ 目录名称必须用下划线
- 正确: `memory_tencentdb`
- 错误: `memory-tencentdb`（这是 config alias，不是目录名）

### ⚠️ npm install 国内网络慢
npm 镜像（registry.npmmirror.com）下载速度较慢（~20-50 KiB/s），约需 1-5 分钟。

## 命令行工具

npm 包附带了一些 CLI 工具（通过 `npm bin` 注册）:

```bash
read-local-memory       # 读取本地记忆
migrate-sqlite-to-tcvdb # 迁移 SQLite → 腾讯云向量数据库
export-tencent-vdb      # 导出到腾讯云向量数据库
```

运维脚本位于 `scripts/memory-tencentdb-ctl.sh`:
```bash
# 接线启动
memory-tencentdb-ctl start

# 查看状态
memory-tencentdb-ctl status

# 停止
memory-tencentdb-ctl stop
```

## 配置参考

日常调参（在 `~/.memory-tencentdb/memory-tdai/tdai-gateway.json` 或环境变量中配置）:

| 参数 | 默认值 | 说明 |
|:----|:------|:----|
| `recall.strategy` | `hybrid` | 召回策略: keyword/embedding/hybrid |
| `recall.maxResults` | 5 | 每次召回条数 |
| `pipeline.everyNConversations` | 5 | 每 N 轮触发 L1 提取 |
| `persona.triggerEveryN` | 50 | 每 N 条新记忆触发画像生成 |
| `offload.enabled` | false | 是否启用短期记忆压缩 |
| `llm.model` | gpt-4o | 提取用模型 |
| `embedding.dimensions` | 1536 | 向量维度 |

## 自带 LLM 工具

提供者注册了两个工具供模型调用:

- `memory_tencentdb_memory_search` — 搜索 L1 结构化长期记忆
  - 参数: `query`（必填）, `limit`（1-20, 默认5）, `type`（persona/episodic/instruction）
- `memory_tencentdb_conversation_search` — 搜索 L0 原始对话
  - 参数: `query`（必填）, `limit`（1-20, 默认5）

## 推荐的生产配置

对于阿里云/国内服务器，推荐以下配置以避免网络问题:

1. 使用 `npm install` 而非 `pnpm`（npm flat install 更稳定）
2. 设置 `MEMORY_TENCENTDB_GATEWAY_CMD` 显式路径（绕过自动发现）
3. Gateway LLM 使用 DeepSeek（国内可达，速度快）
4. 存储后端用本地 SQLite（无需额外服务）

## 分层记忆金字塔

| 层级 | 内容 | 存储 | 触发频率 |
|:----|:-----|:----|:---------|
| L0 | 原始对话日志 | SQLite + JSONL | 每轮自动 |
| L1 | 结构化事实提取 | SQLite + 向量 | 每5轮 |
| L2 | 场景块归纳 | Markdown | 每N轮 |
| L3 | 用户画像 | persona.md | 每50条记忆 |

## 运维检查

```bash
# 检查 Gateway 是否运行
curl http://127.0.0.1:8420/health
# 预期: {"status":"ok"} 或 {"status":"degraded"}

# 查看 Gateway 日志
tail -f ~/.hermes/logs/memory_tencentdb/gateway.stderr.log

# 查看记忆数据目录
ls -la ~/.memory-tencentdb/memory-tdai/

# 验证 provider 已注册
python3 -c "from plugins.memory import discover_memory_providers; [print(n, a) for n, _, a in discover_memory_providers() if 'tencent' in n]"
```

## 故障排除

| 症状 | 原因 | 修复 |
|:----|:-----|:-----|
| `is_available(): False` | Gateway 未启动 | 检查 env.d 文件，重启 Hermes |
| 工具不显示 | `get_tool_schemas()` 返回 `[]` | 设置 `MEMORY_TENCENTDB_GATEWAY_CMD` 环境变量 |
| Gateway 启动失败 | 端口被占 / node 找不到 | 检查 `8420` 端口，检查 `npx tsx` 是否可用 |
| 记忆为空 | 需等 pipeline 触发 | 默认每5轮触发 L1 提取，继续对话即可 |
