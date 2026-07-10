# Gitee → GitHub 同步方案

## 背景

学习文档仓库 `huawei-od-learning` 的主仓库在 Gitee（https://gitee.com/iiixiyan/huawei-od-learning）。
GitHub 镜像仓库已存在（https://github.com/iiixiyan/huawei-od-learning），需要保持同步。

## 方案A：Gitee内置仓库镜像（推荐，零维护）

通过 Gitee 网页界面设置 Push Mirror，每次推送到 Gitee 自动同步到 GitHub。

**设置步骤：**
1. 登录 Gitee → 打开 https://gitee.com/iiixiyan/huawei-od-learning
2. 点「管理」→「仓库镜像管理」→「添加镜像」
3. 填写：
   - 镜像类型：GitHub
   - 镜像方向：Push（推送）
   - 目标地址：`https://github.com/iiixiyan/huawei-od-learning.git`
   - 用户名：`iiixiyan`
   - 密码/Token：GitHub Personal Access Token（需 `repo` 权限）
4. 保存后自动生效

**优势：** 一次设置，永不过期，零维护。

**注意：** Gitee 的 REST API（/api/v5）不公开镜像管理端点（返回405），不能通过代码自动配置。必须通过网页界面手动操作。

## 方案B：脚本双推（无依赖）

在 cron job 或脚本中，推送完 Gitee 后再推一份到 GitHub：

```python
import subprocess, re, os

# 读取 token
with open("/root/.hermes/.env") as f:
    env = f.read()
gitee_token = re.search(r"GITEE_TOKEN=(\S+)", env).group(1)
github_token = re.search(r"GITHUB_TOKEN=(\S+)", env).group(1)

LEARN_DIR = "/tmp/huawei-od-learning-push"

# 添加 GitHub remote 并推送
subprocess.run(
    ["git", "-C", LEARN_DIR, "remote", "add", "github",
     f"https://iiixiyan:{github_token}@github.com/iiixiyan/huawei-od-learning.git"],
    capture_output=True, timeout=10
)
subprocess.run(["git", "-C", LEARN_DIR, "push", "github", "master"],
               capture_output=True, timeout=60)
```

**优势：** 完全自动化，无需手动配置。
**劣势：** 每次都要加 remote（或持久化配置），多一步推送耗时。

### ⚠️ GitHub Token (GITHUB_TOKEN)

已在 `~/.hermes/.env` 中配置了 `GITHUB_TOKEN=github_pat_...`（93字符的Fine-grained PAT），拥有 `repo` 权限，可用于：
- GitHub API 调用（创建仓库、启用Pages等）
- HTTPS git 推送（`https://oauth2:{token}@github.com/{user}/{repo}.git`）
- GitHub Pages 管理

读token方式：
```python
import re
with open("/root/.hermes/.env") as f:
    env = f.read()
m = re.search(r'GITHUB_TOKEN=*** env)
token = m.group(1).strip("'\"")
```

---

## 当前状态

2026-07-07 状态：方案A未配置（需手动网页操作），方案B未集成。目前仅推送到 Gitee。
