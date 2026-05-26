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
- ❌ 使用 `year_old` 作为用户名会收到 403 — 因为 `year_old` 与 `iiixiyan` 是不同账号
- ✅ 使用 `oauth2`（标准方式）或 `iiixiyan`（令牌所属用户名）均有效
- 令牌类型：Gitee Personal Access Token（个人访问令牌）

## 源仓库（课程原始内容）

| 项目 | 值 |
|------|-----|
| 仓库名 | `huawei-od-prep` |
| 地址 | https://gitee.com/year_old/huawei-od-prep |
| 所属用户 | `year_old` |
| 克隆URL | `https://oauth2:{GITEE_TOKEN}@gitee.com/year_old/huawei-od-prep.git` |

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
| 15-21 | 第3周 | 栈·队列·链表 | **`week-03-linkedlist-tree/`**（不是 stack-queue） | `week-03-linkedlist-tree/`（新文档）或 `week-03-stack-queue-linkedlist/`（旧文档） |
| 22-28 | 第4周 | 二叉树·图 | `week-04-tree-graph/` | 同上 |
| 29-35 | 第5周 | OD 100分·字符串/数组类 | `week-05-od-100-1/` | 同上 |
| 36-42 | 第6周 | OD 100分·树/图/矩阵类 | `week-06-od-100-2/` | 同上 |
| 43-49 | 第7周 | OD 200分题 | `week-07-od-200/` | 同上 |
| 50-56 | 第8周 | 模拟考冲刺 | `week-08-mock-review/` | 同上 |

### 文件搜索策略

硬编码周目录名可能导致文件找不到（如源仓库第3周是 `linkedlist-tree` 而非期望的 `stack-queue-linkedlist`）。**推荐使用路径通配**：

```python
from pathlib import Path

REPO_DIR = "/tmp/huawei-od-prep"
patterns = [f"day-{n:02d}*.md", f"day-{n}*.md", f"D{n:02d}*.md", f"D{n}*.md"]
for pat in patterns:
    for m in Path(REPO_DIR).rglob(pat):
        if "curriculum" not in m.name.lower() and "readme" not in m.name.lower():
            return str(m)
```

## 学习仓库目标准目录

学习文档应放入与源仓库同名的周目录中。Day16开始的第3周文档使用 `week-03-linkedlist-tree/`：

```
week-03-linkedlist-tree/
  Day15-栈基础-从零到精通.md    (已存在于 week-03-stack-queue-linkedlist/)
  Day16-栈进阶-从零到精通.md    (在 week-03-linkedlist-tree/)
  Day17-...                     (在 week-03-linkedlist-tree/)
  ...
```
