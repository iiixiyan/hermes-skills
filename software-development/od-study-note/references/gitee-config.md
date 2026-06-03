# Gitee仓库配置（华为OD学习笔记）

## 学习仓库（归档学习文档）

| 项目 | 值 |
|------|-----|
| 仓库名 | `huawei-od-learning` |
| 地址 | https://gitee.com/iiixiyan/huawei-od-learning |
| 所属用户 | `iiixiyan`（而非 `year_old`） |
| 默认分支 | `master` |
| Token | `f5b4e45ce364dd9dcac7e9c20c6423f7`（存于 `~/.hermes/.env`） |
| 有效认证URL | `https://oauth2:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git` |
| 备选认证URL | `https://iiixiyan:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git` |

⚠️ **认证注意事项**：
- Gitee Personal Access Token 的 HTTP Basic Auth 行为：**username 字段可以被 Gitee 忽略**，token 本身决定权限。实测 `year_old:{GITEE_TOKEN}` 也可以成功推送到 `iiixiyan/huawei-od-learning`，因为 Gitee 仅校验 token 值，不校验用户名是否匹配仓库所属账号。
- ✅ **推荐**使用 `oauth2`（Gitee官方标准方式）：`https://oauth2:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git`
- ✅ 也可以使用 `iiixiyan`（令牌所属用户名）或 `year_old`（实测有效）
- ❌ 仅当 token 被撤销/过期时才会收到 403，与 URL 中的用户名无关

## 源仓库（课程原始内容）

| 项目 | 值 |
|------|-----|
| 仓库名 | `huawei-od-prep` |
| 地址 | https://gitee.com/year_old/huawei-od-prep |
| 所属用户 | `year_old` |
| 克隆URL | `https://oauth2:{GITEE_TOKEN}@gitee.com/year_old/huawei-od-prep.git` |

⚠️ **源仓库工作目录损坏（常见Bug）**：该仓库的文件会在会话之间从工作目录中消失（`git status` 显示全部文件为"deleted"），但 git 历史完好。每次使用前必须运行 `git -C /tmp/huawei-od-prep restore .` 恢复。详见 SKILL.md 的「已知问题」章节。

## 课程时间线

- Day 1 = 2026-05-11
- 每过1天 +1
- 共56天（至2026-07-05）

```python
from datetime import datetime, timedelta
day1 = datetime(2026, 5, 11)
target = day1 + timedelta(days=day_number - 1)
```

## 目录结构对照

⚠️ **注意**：源仓库（huawei-od-prep）的周目录名与主题不完全对应。

| Day | 周次 | 主题 | 源仓库目录 | 学习仓库目录 |
|-----|------|------|-----------|-------------|
| 1-7 | 第1周 | 数组与哈希表 | `week-01-array-hash/` | 同上 |
| 8-14 | 第2周 | 字符串与双指针 | `week-02-string-pointer/` | 同上 |
| 15-21 | 第3周 | 栈·队列·链表 | `week-03-linkedlist-tree/`（源仓库）→ `week-03-stack-queue-linkedlist/`（学习仓库） |
| 22-28 | 第4周 | 二叉树·图 | `week-04-dp-review/`（源仓库，名不符实但内容确实是树）→ `week-04-tree-graph/`（学习仓库） |
| 29-35 | 第5周 | OD 100分·字符串/数组类 | `week-05-od-100-1/` |
| 36-42 | 第6周 | OD 100分·树/图/矩阵类 | `week-06-od-100-2/` |
| 43-49 | 第7周 | OD 200分题 | `week-07-od-200/` |
| 50-56 | 第8周 | 模拟考冲刺 | `week-08-mock-review/` |

⚠️ **源仓库目录名与主题不匹配的两个例子**：
1. **第3周**：源仓库目录 `week-03-linkedlist-tree/` 但内容包含栈和队列（不含链表专项），学习仓库用 `week-03-stack-queue-linkedlist/`
2. **第4周**：源仓库目录 `week-04-dp-review/` 但内容完全是二叉树（不含DP），学习仓库用 `week-04-tree-graph/`

### 静态站点

学习笔记可在 Web 站点浏览（详见 SKILL.md 静态站点部署章节）：
- **URL**: http://106.12.76.187:8765/
- **数据**：通过代理实时从 Gitee API 拉取，无需手动同步

### 文件搜索策略

硬编码周目录名可能导致文件找不到（源仓库目录名与预期不匹配）。**推荐使用路径通配**：

```python
from pathlib import Path

REPO_DIR = "/tmp/huawei-od-prep"
patterns = [f"day-{n:02d}*.md", f"day-{n}*.md", f"D{n:02d}*.md", f"D{n}*.md"]
for pat in patterns:
    for m in Path(REPO_DIR).rglob(pat):
        if "curriculum" not in m.name.lower() and "readme" not in m.name.lower():
            return str(m)
```

注意 Day 22+ 的文件使用 `D{22..56}` 命名格式（大写D，无连词符），而早期 Day 1-21 使用 `day-{01..21}` 格式（小写day，有连词符）。`rglob` 搜索时用 `D{n:02d}*.md` 和 `day-{n:02d}*.md` 两种模式覆盖两种命名风格。

## 学习仓库目标准目录

所有学习文档统一放入与学习仓库实际目录名一致的周目录中。**不以源仓库目录名为准**：

| 周次 | 学习仓库目录 |
|------|-------------|
| 第1周 | `week-01-array-hash/` |
| 第2周 | `week-02-string-pointer/` |
| 第3周 | `week-03-stack-queue-linkedlist/`（⚠️ 注意非源仓库的 `linkedlist-tree`） |
| 第4周 | `week-04-tree-graph/`（⚠️ 注意非源仓库的 `dp-review`） |
| 第5周 | `week-05-od-100-1/` |
| 第6周 | `week-06-od-100-2/` |
| 第7周 | `week-07-od-200/` |
| 第8周 | `week-08-mock-review/` |

生成文档时，直接写入对应目录即可，无需关心源仓库的目录名差异。
