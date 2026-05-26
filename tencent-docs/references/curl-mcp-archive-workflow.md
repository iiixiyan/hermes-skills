# curl 方式调用 MCP API & 按日期归档工作流

## 适用场景

- 无法使用 `mcporter` 或 Hermes 原生 MCP 客户端（如 cron 任务环境）
- 需要在终端/脚本中直接调用 MCP 工具
- 需要按「根分类 → 日期子文件夹 → 文档」的结构组织归档

---

## 一、基础调用模板

### 通用函数

```python
import subprocess, json

TOKEN = "YOUR_TENCENT_DOCS_TOKEN"
MCP_URL = "https://docs.qq.com/openapi/mcp"

def mcp_call_tool(tool_name, args):
    """调用 Tencent Docs MCP 工具"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": args
        }
    }
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", MCP_URL,
         "-H", f"Authorization: Bearer {TOKEN}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True, timeout=30
    )
    resp = json.loads(result.stdout)
    text = resp.get("result", {}).get("content", [{}])[0].get("text", "")
    try:
        return json.loads(text)
    except:
        return {"error": "parse_failed", "raw": text[:200]}
```

### curl 直接调用

```bash
curl -s -X POST "https://docs.qq.com/openapi/mcp" \
  -H "Authorization: Bearer $TENCENT_DOCS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"manage.folder_list","arguments":{}}}'
```

---

## 二、按日期归档工作流

### 目录结构

```
📁 竞足预测          ← 根分类文件夹
  └── 📁 2026-05-18  ← 日期子文件夹 (YYYY-MM-DD)
       ├── 📄 2026-05-18 11:00 首次预测
       ├── 📄 2026-05-18 17:00 修正预测
       └── 📄 2026-05-18 20:30 综合复盘
```

### 步骤

#### 1. 创建/查找根分类文件夹

```python
# 查根目录
resp = mcp_call_tool("manage.folder_list", {})
# 找 "竞足预测" 文件夹ID
folder_id = None
for item in resp.get("list", []):
    if item.get("title") == "竞足预测" and item.get("is_folder"):
        folder_id = item["id"]
        break

# 没有则创建
if not folder_id:
    resp = mcp_call_tool("manage.create_file", {
        "title": "竞足预测",
        "file_type": "folder"
    })
    folder_id = resp.get("file_id")
```

#### 2. 创建/查找日期子文件夹

```python
today = "2026-05-18"  # 动态计算

# 查子文件夹
resp = mcp_call_tool("manage.folder_list", {"folder_id": folder_id})
date_folder_id = None
for item in resp.get("list", []):
    if item.get("title") == today and item.get("is_folder"):
        date_folder_id = item["id"]
        break

# 没有则创建
if not date_folder_id:
    resp = mcp_call_tool("manage.create_file", {
        "title": today,
        "file_type": "folder",
        "parent_id": folder_id
    })
    date_folder_id = resp.get("file_id")
```

#### 3. 创建带内容的文档

> ⚠️ **不要用 `smartcanvas.edit` 写入内容**——它可能返回空结果导致文档空白。
> ✅ **正确方式**：用 `create_smartcanvas_by_mdx` 创建时直接传入内容，然后 `manage.move_file` 移到目标文件夹。

```python
# 创建带内容的文档（create_smartcanvas_by_mdx 不支持 parent_id）
resp = mcp_call_tool("create_smartcanvas_by_mdx", {
    "title": "2026-05-18 11:00 首次预测",
    "mdx": "# 预测内容\n\nMarkdown 格式内容..."
})
file_id = resp.get("file_id")

# 移到日期文件夹
mcp_call_tool("manage.move_file", {
    "file_id": file_id,
    "target_folder_id": date_folder_id
})

# 设置权限（所有人可读）
mcp_call_tool("manage.set_privilege", {
    "file_id": file_id,
    "policy": 2  # 2=所有人可读
})
```

#### 4. 读取已有文档内容

```python
# 查文件夹下的文件列表
resp = mcp_call_tool("manage.folder_list", {"folder_id": date_folder_id})
for item in resp.get("list", []):
    print(f"{item['title']}: {item['url']}")

# 读取文档内容
resp = mcp_call_tool("smartcanvas.read", {"file_id": "文档ID"})
content = resp.get("content", "")
```

---

## 三、工具名速查

| 用途 | MCP 工具名 | 关键参数 |
|------|-----------|---------|
| 列目录 | `manage.folder_list` | `folder_id`（空=根目录） |
| 创建文件夹/文件 | `manage.create_file` | `title`, `file_type`, `parent_id` |
| 创建智能文档（带内容） | `create_smartcanvas_by_mdx` | `title`, `mdx`（不支持 `parent_id`） |
| 移动文件 | `manage.move_file` | `file_id`, `target_folder_id` |
| 设置权限 | `manage.set_privilege` | `file_id`, `policy` (2=可读, 3=可编辑) |
| 读取文档 | `smartcanvas.read` | `file_id` |
| 读取通用内容 | `get_content` | `file_id` |
| 删除文件 | `manage.delete_file` | `file_id`, `delete_type` |
| 搜索文件 | `manage.search_file` | `search_key` |

---

## 四、已知坑

1. **`smartcanvas.edit` 写入可能返回空**：文档创建后写入内容，`smartcanvas.edit` 返回空结果，内容实际未写入。应使用 `create_smartcanvas_by_mdx` 创建时直接带内容，再 `move_file` 到目标目录。

2. **`create_smartcanvas_by_mdx` 不支持 `parent_id`**：创建后的文档在根目录，需要用 `manage.move_file` 移动到目标文件夹。

3. **文件标题限 36 字符**：`manage.create_file` 的 `title` 参数长度不超过 36 字符。

4. **Token 环境变量**：建议从环境变量 `TENCENT_DOCS_TOKEN` 读取 Token，不要硬编码。
