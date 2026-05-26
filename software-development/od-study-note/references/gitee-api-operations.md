# Gitee API 操作参考

## 认证

所有API调用需要 `access_token` 参数。Gitee Token 存储在 `~/.hermes/.env` 中。

```python
GITEE_TOKEN = "f5b4e45ce364dd9dcac7e9c20c6423f7"
```

## 仓库操作

### 创建仓库

⚠️ **已知问题**：传 `"private": False` 后，Gitee API 可能仍然创建为私有仓库。建议创建后立即查询并修正：

```python
import subprocess, json

result = subprocess.run(
    ["curl", "-s", "-X", "POST",
     "https://gitee.com/api/v5/user/repos",
     "-H", "Content-Type: application/json",
     "-d", json.dumps({
         "access_token": GITEE_TOKEN,
         "name": "repo-name",
         "description": "描述文字",
         "private": False  # 注意：此参数可能无效，创建后仍是私有
     })],
    capture_output=True, text=True, timeout=30
)
data = json.loads(result.stdout)
print(data.get("full_name"))      # year_old/repo-name
print(data.get("private"))        # 可能还是 True！

# 如果还是私有，立即用 PATCH 修改
if data.get("private") != False:
    result = subprocess.run(
        ["curl", "-s", "-X", "PATCH",
         "https://gitee.com/api/v5/repos/year_old/repo-name",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({
             "access_token": GITEE_TOKEN,
             "private": False
         })],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    assert data.get("private") == False, "设置公开失败！"
```

### 查询仓库信息

```python
result = subprocess.run(
    ["curl", "-s",
     f"https://gitee.com/api/v5/repos/year_old/repo-name?access_token={GITEE_TOKEN}"],
    capture_output=True, text=True, timeout=15
)
data = json.loads(result.stdout)
print(data.get("private"))   # True=私有, False=公开
print(data.get("html_url"))
```

### 修改仓库（设置公开/私有）

```python
result = subprocess.run(
    ["curl", "-s", "-X", "PATCH",
     "https://gitee.com/api/v5/repos/year_old/repo-name",
     "-H", "Content-Type: application/json",
     "-d", json.dumps({
         "access_token": GITEE_TOKEN,
         "name": "repo-name",          # 必须传name
         "private": False,
         "description": "描述（可选更新）"
     })],
    capture_output=True, text=True, timeout=15
)
data = json.loads(result.stdout)
# 访问 data["private"] 验证修改是否生效
```

### 删除仓库

```python
result = subprocess.run(
    ["curl", "-s", "-X", "DELETE",
     f"https://gitee.com/api/v5/repos/year_old/repo-name?access_token={GITEE_TOKEN}"],
    capture_output=True, text=True, timeout=15
)
# HTTP 204 = 成功
print(result.stdout)
```

## Git操作注意事项

- **默认分支**：Gitee新建仓库默认分支是 `master`（不是 `main`）
- **push前必须先commit**：检查 `git log --oneline` 确认有提交
- **token嵌入URL**：`https://oauth2:{GITEE_TOKEN}@gitee.com/iiixiyan/repo.git`（⚠️ 用户名必须是 `oauth2`，不是 Gitee 用户名 — 这是 Gitee API 的固定要求）
- **必须用subprocess**：`terminal` 工具有bug（报错"cd: y: No such file or directory"），所有Git命令用 `execute_code` + Python `subprocess`
