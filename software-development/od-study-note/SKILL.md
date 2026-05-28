---
name: od-study-note
description: "华为OD备考学习笔记 — 从算法题库源文档生成小白友好型详细学习文档，推送到Gitee学习仓库"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [huawei-od, algorithm, learning-doc, documentation, gitee]
    related_skills: [writing-plans, plan]
---

# 华为OD备考学习笔记

## 触发条件

需要从 `huawei-od-prep` 仓库的源内容生成学习文档时加载此技能。用户提到以下关键词时触发：
- "出一份学习文档"、"整理一下"、"写个笔记"、"存档"
- "Day N" + "学习" / "笔记" / "文档"
- 用户要求针对某天课程输出初学者友好的详细学习材料

## 背景

- **源仓库**：https://gitee.com/year_old/huawei-od-prep — 包含56天的算法题库与课程内容
- **学习仓库**：https://gitee.com/iiixiyan/huawei-od-learning — 存放整理后的学习文档（⚠️ 注意：不是 year_old 下的仓库，是 iiixiyan 下的）
- **课程周期**：5月11日(Day 1) ~ 7月5日(Day 56)，共56天
- **Git账号**：year_old / 炯炯吖，token存储在 `~/.hermes/.env` 中（key: `GITEE_TOKEN`）
- **终端工具存在bug**：不能直接用 `terminal` 工具，必须用 `execute_code` + Python `subprocess`
- **定时任务**：每天 09:30 自动执行完整流程（发送邮件 → 生成学习文档 → 推送仓库），详情见"定时任务集成"章节

## 定时任务集成（自动每日生成）

该技能已集成到每日 09:30 的 cron job（job_id: `364f0625ea03`，原名"华为OD每日推送+学习文档"）。执行流程：

### 定时任务工作流

```
第1步：运行 od_daily_push.py 脚本 → 发送今日OD题目邮件到 suijiong@huawei.com
第2步：确定今日Day编号（Day N = 今天 - 2026-05-11 + 1）
第3步：从 /tmp/huawei-od-prep/ 读取当日 raw 课程内容
第4步：生成「从零到精通」学习文档（LLM驱动）
第5步：推送到 https://gitee.com/iiixiyan/huawei-od-learning
第6步：通过微信发送总结给用户
```

### 关键细节

- **源仓库保持最新**：`git -C /tmp/huawei-od-prep pull`
- **目标仓库认证**：读取 `~/.hermes/.env` 中的 `GITEE_TOKEN`，构建带认证的 URL
- **README 维护**：每次推送前在 `README.md` 的学习文档表格中追加新的Day行。如果 README 中有 `🚧 待更新` 占位行则替换它，否则在最后一个Day之后插入新行（用 `patch` 工具或 `sed` 在最后一条Day行后追加）
- **邮件发送**：使用硬编码在 `od_daily_push.py` 中的 SMTP 配置（163.com）

### 从 no_agent 切换为 agent-driven 的注意事项

最初的定时任务设置为 `no_agent=true`（纯脚本执行，零token消耗）。升级为需要LLM生成文档的 agent-driven 模式时，**必须删除旧任务后重建新任务**——单纯 update `script=""` 不会清除 `no_agent` 标记。

```bash
# 正确做法
hermes cron remove <job_id>
hermes cron create "30 9 * * *" --prompt "..." --name "华为OD每日推送+学习文档"
```

## 执行流程

### 第 1 步：确定目标Day

确认用户要的是哪一天的内容。使用 `execute_code` + `subprocess` 计算：

```python
# Day 1 = 5月11日
from datetime import datetime, timedelta
day1 = datetime(2026, 5, 11)
target = day1 + timedelta(days=day_number - 1)
print(f"Day {day_number} = {target.strftime('%Y-%m-%d')}")
```

### 第 2 步：获取源内容

从Gitee克隆 `huawei-od-prep` 仓库（如果未克隆），读取对应Day的文件：

```python
import subprocess, os

GITEE_TOKEN = "f5b4e45ce364dd9dcac7e9c20c6423f7"
REPO_URL = f"https://oauth2:{GITEE_TOKEN}@gitee.com/year_old/huawei-od-prep.git"
CLONE_DIR = "/tmp/huawei-od-prep"

# 克隆
if not os.path.exists(CLONE_DIR):
    subprocess.run(["git", "clone", REPO_URL, CLONE_DIR], capture_output=True, timeout=60)

# 读取文件
result = subprocess.run(["cat", f"{CLONE_DIR}/week-XX/day-XX-xxx.md"], capture_output=True, text=True)
print(result.stdout[:100])
```

源仓库的目录结构：
```
week-01-array-hash/               # 第1周：数组与哈希
  day-01-array-basics.md
  day-02-array-advanced.md
  ...
week-02-string-pointer/           # 第2周：字符串与双指针
  day-08-strings-basics.md        # ← Day8
  day-09-two-pointers.md
  day-10-palindrome-sliding-window.md
  ...
week-03-linkedlist-tree/          # 第3周：栈·队列·链表（注意目录名为linkedlist-tree而非stack-queue）
  D15-栈基础.md
  D16-栈进阶.md
  ...
```

⚠️ **目录名注意**：源仓库第3周的目录是 `week-03-linkedlist-tree`，但学习仓库（huawei-od-learning）中第3周的目标目录是 **`week-03-stack-queue-linkedlist`** 而非 `week-03-linkedlist-tree`。学习仓库没有 `week-03-linkedlist-tree` 目录，所有第3周的学习文档（Day15-21）都统一放入 `week-03-stack-queue-linkedlist`。

```python
# ✅ 正确：学习文档写入 week-03-stack-queue-linkedlist（与学习仓库实际目录一致）
WEEK_DIR = "week-03-stack-queue-linkedlist"

# ❌ 错误：学习仓库中不存在 week-03-linkedlist-tree 目录
# WEEK_DIR = "week-03-linkedlist-tree"  # 这是源仓库的目录，不是学习仓库的
```

搜索源仓库文件时使用 `rglob` 通配匹配，不要硬编码周目录名：

```python
from pathlib import Path
file = next(Path(REPO_DIR).rglob(f"D{day_num:02d}*.md"), None)  # 自动找到文件
```

### 第 3 步：批量并行生成（当有多篇文档时）

如果有多天内容需要生成（如补齐历史7天的文档），**不要一天一天先后生成**，使用 `delegate_task` 将任务拆分为2-3个子代理并行执行：

```python
# 推荐的分组策略
# 批1：Day 1-3（数组篇）
# 批2：Day 4-6（哈希/前缀和篇）
# 批3：Day 7（复习篇）
# 每批分配一个delegate_task，在context中传源文件路径
```

每个 `delegate_task` 的 `context` 中必须指定：
- **源文件路径**（完整绝对路径）
- **目标保存路径**（完整绝对路径）
- **文档结构要求**（引用下方的模板）
- **内容规格**（20KB+、从零讲起、代码模板、手把手推演等）
- **推荐分组**：不要在一批里放太多天。已验证的成功经验是：Day 1-3（数组篇）为一组、Day 4-6（哈希/前缀和篇）为一组、Day 7（复习/综合篇）为一组——每组的子代理都带着明确的源文件路径和目标路径，子代理内部自行 read_file 读取源内容后生成。

⚠️ 单文档生成大约需1-3分钟，并行生成3批约3-8分钟，串行约需15-25分钟。已实测验证：3个子代理并行生成7篇文档（Day1-7），每批各负责2-3篇，耗时约**7.5分钟**，总计**210KB+**内容（Day1 32KB、Day2 31KB、Day3 34KB、Day4 25KB、Day5 22KB、Day6 28KB、Day7 35KB，平均约30KB/篇）。

#### delegate_task context 编写规范

为子代理编写 context 时，必须包含以下**必要信息**：

```python
# 推荐的 context 结构
context=f"""
你是华为OD备考文档作者。请阅读源材料并生成每篇20KB+的超详细小白文档。

## [Day N] 主题 (file: /path/to/source/day-xx-xxx.md)
涵盖：[列出该天涵盖的核心算法/题型]
核心套路：[列出2-4个核心套路]

## [Day N+1] 主题 (file: /path/to/source/day-xx-xxx.md)
...

## 要求（每篇文档）：
- 文件名：DayN-主题-从零到精通.md
- 从零讲起，用生活例子引入
- 每个套路配代码模板 + 手把手step-by-step推演 + 画图解释
- 每个算法题配完整解题思路 + 代码 + 复杂度分析 + 模拟推演
- 包含常见面试追问方向
- 包含OD机考建议
- 约15000-25000字（约20KB）
- 结构参考：目录→知识点→套路详解→高频题精讲→性能优化→OD实战→作业
- 保存路径：/target/path/DayN-主题-从零到精通.md
"""
```

子代理的 `toolsets` 应包含 `["file", "terminal"]`，确保能读取源文件和写目标文件。

### 第 3B 步：生成长文档

源内容通常比较简洁（题+代码+简短总结），需要扩展为**小白友好型详细文档**（每篇20KB+）。

#### 文档结构模板

```markdown
# 📘 Day N：[主题] — 从零到精通

> 🎯 **学习目标**：[一句话描述]
> 📅 **华为OD备考 · 第X周 · 第N天** | [返回目录](../README.md)

---

## 目录

- [一、XXX是什么？](#一xxx是什么)
- [二、核心知识点详解](#二核心知识点详解)
- [三、核心套路/模型](#三核心套路模型)
- [四、高频题精讲](#四高频题精讲)
- [五、性能优化与面试进阶](#五性能优化与面试进阶)
- [六、OD机考实战指南](#六od机考实战指南)
- [七、今日作业](#七今日作业)
```

#### 文档内容规范 — 必须达到以下详细程度

| 章节 | 要求 | 最低字数 |
|------|------|----------|
| **知识点详解** | 从零讲起，假设读者没有前置知识。每个概念配生活类比 + 具体代码示例 | 3000+字 |
| **操作速查表** | Python常用操作的表格形式（写法+示例+结果+易混淆对比） | 500+字 |
| **常见操作大全** | 完整汇总该主题所有常见操作/API，每个附：写法、示例、结果、复杂度、易混淆对比。用表格+代码示例呈现，让小白一眼看清所有工具。 | 2000+字 |
| **核心套路** | 归纳为2-4个核心模型/套路。每个套路配**代码模板**（可直接背诵）和**手把手推演**（逐行画图、展示每一步的变量变化） | 4000+字 |
| **高频题精讲** | 每道题包含：题目描述→思路→完整带注释代码→**手把手推演**（逐步执行、画图展示变量变化）→复杂度分析 | 5000+字 |
| **性能优化** | Python常见性能陷阱（如循环拼接O(n²)、频繁切片等），用 ❌ vs ✅ 对比示例，配复杂度分析 | 1000+字 |
| **面试追问** | 常见面试追问和进阶方向（5个以上Q&A） | 1000+字 |
| **OD实战指南** | 题型分布（哪类题在100分题/200分题中出现频率）、刷题优先级（⭐⭐⭐/⭐⭐/⭐三档）、考场技巧 | 1500+字 |
| **今日作业** | 必做/选做/挑战三级分类，标注预计时间，配自测方法 | 500+字 |

**文档总目标**：每篇不低于20KB（约10000字），推荐25-35KB（约13000-18000字）。已实测验证：Day1(32KB)、Day2(31KB)、Day3(34KB)、Day4(25KB)、Day5(22KB)、Day6(28KB)、Day7(35KB)，平均约30KB/篇。

#### 写作风格

- **语气**：友善、鼓励，像老师在教学生（"别急，我们一步步来"）
- **难度分级**：⭐/⭐⭐/⭐⭐⭐ 标注每道题的难度
- **代码**：Python，完整可运行，含注释
- **推演**：用ASCII画图或步骤编号展示变量变化过程
- **强调**：⚠️ 标注常见的坑，💡 标注小技巧，✅ ❌ 对比好坏写法

#### 避免的内容

- ❌ 不要假设读者有算法基础
- ❌ 不要写"显然"、"易知"等跳过步骤的表述
- ❌ 不要只写思路不给完整代码
- ❌ 不要长篇理论知识不结合实际例题

### 第 4 步：推送到Gitee学习仓库

⚠️ **Gitee个人访问令牌认证细节**：Gitee的HTTP Basic Auth接受两种用户名格式：
- `oauth2` — 官方推荐的标准方式（适用于所有Gitee个人访问令牌）
- 实际Gitee用户名 — 如 `iiixiyan`（取决于令牌所属的账号）

两种方式都有效。但注意**不要使用不相关的用户名**（如 `year_old` 是针对不同的Gitee账号）。

```python
import subprocess, os

GITEE_TOKEN = "f5b4e45ce364dd9dcac7e9c20c6423f7"  # 从 ~/.hermes/.env 读取
TOKEN_FILE = "/root/.hermes/.env"

with open(TOKEN_FILE) as f:
    for line in f:
        if line.startswith("GITEE_TOKEN="):
            GITEE_TOKEN = line.strip().split("=", 1)[1].strip("'\"")

# ✅ 两种有效的认证方式：
AUTH_URL_1 = f"https://oauth2:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git"
AUTH_URL_2 = f"https://iiixiyan:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git"

# ❌ 错误的认证方式（不同账号）：
# AUTH_URL_BAD = f"https://year_old:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git"
# → 403: "The token username invalid"
```

如果学习仓库**不存在**，先通过Gitee API创建：

```python
import subprocess, json

# 创建公开仓库
result = subprocess.run(
    ["curl", "-s", "-X", "POST",
     "https://gitee.com/api/v5/user/repos",
     "-H", "Content-Type: application/json",
     "-d", json.dumps({
         "access_token": GITEE_TOKEN,
         "name": "huawei-od-learning",
         "description": "华为OD备考学习笔记 — 从零开始，每日一讲",
         "private": False  # 用户要求公开
     })],
    capture_output=True, text=True, timeout=30
)
data = json.loads(result.stdout)
print(data.get("full_name", data.get("message")))
```

**⚠️ 已知问题**：通过Gitee API创建仓库时，即使设置 `"private": False`，返回的状态有时仍然是私有。创建后必须**主动查询并确认**，必要时执行PATCH修正。

如果仓库已创建但**是私有的**，通过PATCH设为公开：

```python
# 查询仓库信息
result = subprocess.run(
    ["curl", "-s",
     f"https://gitee.com/api/v5/repos/iiixiyan/huawei-od-learning?access_token={GITEE_TOKEN}"],
    capture_output=True, text=True, timeout=15
)
data = json.loads(result.stdout)
if data.get("private") == True:
    result = subprocess.run(
        ["curl", "-s", "-X", "PATCH",
         "https://gitee.com/api/v5/repos/iiixiyan/huawei-od-learning",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"access_token": GITEE_TOKEN, "private": False})],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    print("设为公开:", "成功" if data.get("private") == False else "失败")
```

然后拉取/推送文档：

```python
LEARN_DIR = "/tmp/huawei-od-learning-push"

# 克隆或更新
if not os.path.exists(LEARN_DIR):
    subprocess.run(["git", "clone", AUTH_URL, LEARN_DIR], capture_output=True, timeout=60)
else:
    subprocess.run(["git", "-C", LEARN_DIR, "pull"], capture_output=True, text=True, timeout=30)

# 写入文档（用 write_file 或复制）
# ... 生成文档到对应周目录 ...

# 提交推送
subprocess.run(["git", "-C", LEARN_DIR, "add", "-A"], capture_output=True, timeout=30)
subprocess.run(["git", "-C", LEARN_DIR, "commit", "-m", "📘 Day N: 主题"], capture_output=True, timeout=30)
subprocess.run(["git", "-C", LEARN_DIR, "push"], capture_output=True, timeout=60)
```

### 第 5 步：发送链接给用户

生成后通过微信发送：
```
仓库链接：https://gitee.com/iiixiyan/huawei-od-learning
文件路径：week-XX/DayN-主题-副标题.md
```

同时告知用户文档中包含的内容概览（让用户知道新写的文档有哪些亮点）。

## 目录命名规范

学习仓库目录结构与源仓库保持一致，但文件名改为中文+描述性：

```patch
- 源仓库：day-01-array-basics.md
+ 学习仓库：Day01-数组基础操作-从零到精通.md
```

**命名规则**：
- 格式：`DayN-主题-副标题.md`
- 单个数字（1-9）用前导零 `Day01` ~ `Day09`，保持排序美观
- 双数字（10-56）直接用 `Day10` ~ `Day56`
- 全部使用中文字符，不需要英文字段名
- 描述性后缀建议用「从零到精通」或更具体的关键词

```patch
week-02-string-pointer/
  Day08-字符串基础-从零到精通.md
  Day09-双指针进阶-从零到精通.md
  Day10-回文串与滑动窗口-从零到精通.md
  ...
README.md
```

## README维护

每次添加新文档后，更新 `README.md` 中的学习文档表格。

### 实际条目格式

```markdown
| Day N | **主题关键词** — 子主题1、子主题2、子主题3 | ⭐⭐⭐ | [📖 查看](week-XX/DayN-xxx.md) |
```

### 添加方式（两种场景）

**场景A：README中有 `🚧 待更新` 占位行**…
搜索 `🚧 待更新` 标记所在行，整行替换为实际链接。

**场景B：README按顺序增长（无占位行）—— 日更场景下的常见情况**…
在最后一个已存在的Day行之后插入新行。推荐以下两种方法：

### 🔍 README 链接验证（重要！）

每次追加新行后，**验证所有指向当前周目录的链接**是否真实存在：

```python
import os
LEARN_DIR = "/tmp/huawei-od-learning-push"
with open(f"{LEARN_DIR}/README.md") as f:
    for line in f:
        if '查看]' in line:
            start = line.find('(')
            end = line.find(')', start)
            if start > 0 and end > start:
                path = line[start+1:end]
                full = os.path.join(LEARN_DIR, path)
                dir_path = os.path.dirname(full)
                if not os.path.exists(dir_path):
                    print(f"⚠️  BROKEN LINK: {path} — directory {dir_path} does not exist!")
```

如果发现旧会话遗留的**错误链接**（如指向 `week-03-linkedlist-tree/` 但实际目录是 `week-03-stack-queue-linkedlist/`），用 Python 替换修复：

```python
with open(README_PATH) as f:
    content = f.read()
content = content.replace(
    "week-03-linkedlist-tree/Day16-栈进阶-从零到精通.md",
    "week-03-stack-queue-linkedlist/Day16-栈进阶-从零到精通.md"
)
with open(README_PATH, 'w') as f:
    f.write(content)
```

修复后在 commit message 中注明 `(fixed broken README link)`。

#### 方法1（推荐）：用 Python 通过 `execute_code` 重写 README

最可控的方式——用Python读取、修改、写回，**完全避免 `patch` 工具的格式化问题**：

```python
import subprocess

LEARN_DIR = "/tmp/huawei-od-learning-push"
README_PATH = f"{LEARN_DIR}/README.md"

with open(README_PATH) as f:
    content = f.read()

# 找到最后一条 "| Day" 行的位置
lines = content.split('\n')
last_day_idx = -1
for i, line in enumerate(lines):
    if line.startswith('| Day '):
        last_day_idx = i

if last_day_idx >= 0:
    new_row = '| Day N | **主题** — 子主题1、子主题2 | ⭐⭐⭐ | [📖 查看](week-XX/DayN-xxx.md) |'
    lines.insert(last_day_idx + 1, new_row)
    with open(README_PATH, 'w') as f:
        f.write('\n'.join(lines))
    print(f"✅ Day N 行已追加到 README")
```

#### 方法2（备选）：用 `patch` 工具追加

用 `patch` 工具将最后一条Day行替换为「自身 + 换行 + 新Day行」。

⚠️ **`patch`工具已知陷阱**：如果 `old_string` 与原文**不完全匹配**（如多了一个 `|`），`patch` 会应用替换但**注入多余的 `|` 前缀**，导致整行解析异常。必须：
1. 从 `read_file` 输出中**精确复制**要替换的行内容（含前后空格）
2. 编辑后**检查表格管道符 `|` 数量是否一致**
3. 万不得已时，再发一个 `patch` 修复多余的 `|`

## ⚠️ 常见错误

### ❌ Gitee认证使用错误的用户名

使用 `year_old:{TOKEN}` 向 `iiixiyan/huawei-od-learning` 仓库推送会收到 403 "The token username invalid"。因为 `year_old` 与 `iiixiyan` 是不同Gitee账号。应使用：
- `oauth2:{TOKEN}`（官方标准方式，适用于所有令牌）
- `iiixiyan:{TOKEN}`（令牌所属账号的用户名）

### ❌ 使用terminal工具执行Git命令
terminal工具存在bug（所有命令报错"cd: y: No such file or directory" exit_code=126），必须用 `execute_code` + Python `subprocess` 执行所有系统命令。

### ❌ 文档太简短
用户明确要求"内容详细一点"。必须确保每道题有代码+手把手推演，每个套路有模板。20KB左右的详细文档比5KB的简洁版更符合用户期望。

### ❌ 忘记更新README
添加新文档后必须同步更新README.md中的目录，否则用户无法从首页导航。

### ❌ 使用 `patch` 工具添加额外管道符 `|`

当使用 `patch` 工具在 Markdown 表格末尾追加新行时，如果 `old_string` 与原文**不完全匹配**（如原文是 `| Day 12` 但传入了 `|| Day 12`），`patch` 仍然可能应用替换但**注入多余的 `|` 前缀**。

**根本预防**：从 `read_file` 输出中**精确复制**要替换的行内容（含前后空格）。或者使用上述的 Python/sed 方法完全避免此问题。

### ❌ README Markdown表格格式错误

手动编辑 README 时注意检查 pipes（`|`）数量是否正确。常见错误：
- **多余的前导 pipe**：`|| Day 9 | ...` → 应该为 `| Day 9 | ...`（多了个 `|` 会破坏整行解析）
- **多余的空格或缺失分隔符**：确保表格每行的列数一致
- 编辑后建议**肉眼预览**表格对齐情况，或检查文档是否排版异常

### ❌ README 中存在指向不存在目录的链接（来自旧会话）

历史会话生成的 README 行可能指向了错误的周目录。常见问题：
- 第3周：有些旧行指向 `week-03-linkedlist-tree/`（源仓库目录名），但学习仓库实际使用 `week-03-stack-queue-linkedlist/`
- 后果：用户在首页点击链接会 404

**修复方法**：每次更新 README 时，顺手检查所有指向当前周目录的行，确保路径与仓库实际目录一致。可以快速扫描：

```python
import os
LEARN_DIR = "/tmp/huawei-od-learning-push"
# 检查所有 README 中的链接是否指向真实存在的目录
with open(f"{LEARN_DIR}/README.md") as f:
    for line in f:
        if '查看]' in line:
            # 提取 (week-XX/...) 路径
            start = line.find('(')
            end = line.find(')', start)
            if start > 0 and end > start:
                path = line[start+1:end]
                full = os.path.join(LEARN_DIR, path)
                if not os.path.exists(os.path.dirname(full)):
                    print(f"⚠️  链接指向不存在的目录: {path}")
```

### ❌ 文件名不统一
使用 `DayN-主题-副标题.md` 格式，全部用中文字符，不要混用英文字母和中文数字。

### ❌ 源仓库周目录名与预期不符
源仓库 `huawei-od-prep` 的第3周目录名是 `week-03-linkedlist-tree` 而非 `week-03-stack-queue-linkedlist`。使用 `rglob` 搜索文件而不是硬编码周目录名，避免因命名不一致导致文件找不到。

## 参考

- 源仓库：https://gitee.com/year_old/huawei-od-prep
- 学习仓库：https://gitee.com/iiixiyan/huawei-od-learning
- 课程时间线：Day 1 = 2026-05-11，每天递增
- Gitee API操作参考：`references/gitee-api-operations.md`（仓库创建/查询/修改/删除）
- Gitee仓库配置：`references/gitee-config.md`（URL/Token/目录结构）
- 文档模板：`templates/study-note-template.md`
