---
name: od-study-note
description: "华为OD备考学习笔记 — 从算法题库源文档生成小白友好型详细学习文档，推送到Gitee学习仓库"
version: 1.4.0
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
第4步：如果当日学习文档已存在，跳过生成（保持幂等），直接进入第5步
第5步：推送到 https://gitee.com/iiixiyan/huawei-od-learning
第6步：通过微信发送总结给用户
```

### 🔍 每日cron自查清单

每次cron运行时，除了生成/推送新文档，还应快速执行以下自查：

1. **README链接验证**：扫描README中所有指向当前周目录的链接，确认目标目录存在。如果发现损坏链接（如指向 `week-03-linkedlist-tree/` 而实际目录为 `week-03-stack-queue-linkedlist/`），自动修复。
2. **文档幂等性检查**：如果当日文档已存在且内容完整（>5KB），跳过生成，直接推送总结。
3. **源仓库同步**：运行 `git pull` 检查源仓库是否有更新（如果原始课程内容被修正过，老文档可能需要重新生成）。

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

### ⚠️ 已知问题：源仓库工作目录损坏

**每次cron运行前必须执行** `git -C /tmp/huawei-od-prep restore .`，因为 `/tmp/huawei-od-prep` 仓库存在一个重复出现的问题：跟踪的文件会从工作目录中消失（`git status` 显示所有文件为 "deleted"），但文件的 blob 仍在 git 历史中完好。

如果不执行 restore，`find_day_file()` 会找不到任何课程文件，导致邮件发送失败。

修复示例：
```python
import subprocess
# 恢复源仓库工作目录
subprocess.run(["git", "-C", "/tmp/huawei-od-prep", "restore", "."],
               capture_output=True, text=True, timeout=30)
```

建议在 `ensure_repo()` 函数或邮件脚本执行前加入此步骤。

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
week-04-dp-review/                # 第4周：二叉树（注意目录名为dp-review，内容却是树，不含DP）
  D22-二叉树遍历.md
  D23-树的构建.md
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

### 第 3C 步：代码示例质量检查 ⚠️ 生成后必做

生成文档后、推送前，**必须对文档中所有 Python 代码块进行快速静态检查**。历史Bug教训：已多次出现可运行但实际有错的代码示例。

#### 自检清单（逐项排查）

```python
import re

with open("/path/to/generated/DayN-xxx.md") as f:
    content = f.read()

# 提取所有 python 代码块
blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)

for i, code in enumerate(blocks):
    # 1️⃣ 检查 BFS/队列相关代码是否有 root=None 保护
    if 'deque(' in code and 'if not root' not in code.split('def ')[-1][:200]:
        print(f"⚠️  代码块{i+1}: BFS缺少 None 检查")
    
    # 2️⃣ 检查是否用了 Optional 但没导入 typing
    if 'Optional[' in code and 'from typing import Optional' not in code:
        print(f"⚠️  代码块{i+1}: 使用了 Optional 但缺少 import")
    
    # 3️⃣ 检查是否用了未定义的变量/函数
    # （简单启发：找函数调用中第一个单词+括号模式，排除内置函数）
    calls = re.findall(r'([a-z_][a-z_0-9]*)\\(', code)
    defined = set(re.findall(r'def ([a-z_][a-z_0-9]*)', code))
    defined.update({'print', 'len', 'range', 'max', 'min', 'abs', 'sum',
                     'int', 'str', 'list', 'dict', 'set', 'tuple',
                     'sorted', 'reversed', 'enumerate', 'zip', 'map', 'filter',
                     'type', 'isinstance', 'hasattr', 'getattr',
                     'open', 'input', 'super', 'property', 'classmethod',
                     'append', 'pop', 'extend', 'insert', 'remove', 'clear',
                     'popleft', 'appendleft', 'deque', 'defaultdict', 'Counter',
                     'Optional', 'List', 'TreeNode'})
    for call in calls:
        if call not in defined and call.islower() and len(call) > 2:
            print(f"⚠️  代码块{i+1}: 可能使用了未定义函数 '{call}'")
```

#### 常见问题速查

| 症状 | 原因 | 修复 |
|------|------|------|
| `deque([None])` → `AttributeError` | BFS 没写 `if not root: return []` | 补上空根检查 |
| `NameError: name 'Optional' is not defined` | 用了类型注解没导入 | 加 `from typing import Optional` |
| `NameError: name 'update_state' is not defined` | 模板代码用了占位符函数 | 替换为真实示例或加注释 |
| `NameError: name 'initial_state' is not defined` | 模板代码用了占位符变量 | 替换为 `[]` 或 `0` |

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

# 三种认证方式均可（Gitee忽略username，仅校验token）：
AUTH_URL_1 = f"https://oauth2:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git"
AUTH_URL_2 = f"https://iiixiyan:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git"
AUTH_URL_3 = f"https://year_old:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git"
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

## 🔄 回退策略：源仓库缺少某天课程内容

### 场景描述

源仓库 (`huawei-od-prep`) 的 git 历史中包含全部 56 天的课程文件，但存在一个已知Bug：**工作目录中的文件会在会话之间被清空**（`git status` 显示所有文件为 "deleted"）。这导致初次运行时看似缺少内容。

**必须先执行** `git -C /tmp/huawei-od-prep restore .` **恢复所有文件后再查找，而不是直接认定内容缺失。**

### 兜底策略

当 `git restore` 后仍然找不到当天内容时，才执行以下兜底：

### 后果

- `od_daily_push.py` 脚本中 `find_day_file(day_num)` 返回 `None`，脚本打印 `❌ 未找到 Day N 的课程文件` 并以 exit code 1 退出 → **邮件不会发送**
- 后续步骤（生成学习文档、推送仓库）需要**自行兜底**

### 兜底策略

当源仓库缺少当天课程内容时：

1. **记录邮件失败**：在最终输出中明确指出「⚠️ 邮件发送失败 — 源仓库未更新Day N内容」
2. **判断当天在周中的位置**：
   - 如果是**第1-5天（周一至周五）**：该天是新知识点日，无法从空源内容生成文档 → 生成一份「本周进度小结」或标注「文档待补充」
   - 如果是**第6天（周六）**：参考 Day 7 和 Day 14 的模式，生成**本周综合复习文档**（Review），覆盖本周已学全部主题
   - 如果是**第7天（周日）**：生成限时测验/综合练习文档
3. **复习文档的内容结构**：不要写具体题解（因为没有源内容），而是：
   - 本周知识点总览表格（列出已学的 Day 15-19 主题及核心内容）
   - 本周四大核心套路总结（每个套路配通用模板代码）
   - 高频易错点 & 性能优化
   - OD机考实战指南
   - 综合限时测验（5道典型题 + 答案折叠）
   - 今日作业（分级练习题，指向 LeetCode 原题）
   - 下周预告
4. **文档命名**：使用 `Day{NN}-{主题}综合复习-从零到精通.md`（如 `Day20-栈队列链表综合复习-从零到精通.md`）
5. **照常更新 README 并推送**：即使邮件失败，学习文档推送仍然执行

```python
# 兜底检查示例
from pathlib import Path
REPO_DIR = "/tmp/huawei-od-prep"
file = next(Path(REPO_DIR).rglob(f"D{day_num:02d}*.md"), None)
if not file:
    file = next(Path(REPO_DIR).rglob(f"day-{day_num:02d}*.md"), None)

if not file:
    print(f"⚠️ 源仓库未包含 Day {day_num} 内容，将生成周复习文档")
    generate_review_document = True
```

## 🔄 Git推送冲突处理

当 `git push` 被远程拒绝时（`! [rejected] master -> master (fetch first)`），说明远程仓库已有本地分支落后的新提交。这种情况可能是由于：
- 其他会话（同时运行的cron任务、手动修改等）已向远程推送过
- 上次会话的提交由于认证问题未能推送到远程

### 处理步骤

```python
import subprocess

LEARN_DIR = "/tmp/huawei-od-learning-push"
AUTH_URL = f"https://oauth2:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-learning.git"

# 1. 重新设置远程URL（确保认证正确）
subprocess.run(["git", "-C", LEARN_DIR, "remote", "set-url", "origin", AUTH_URL])

# 2. 先拉取并rebase（不要用merge，避免产生多余的merge commit）
result = subprocess.run(["git", "-C", LEARN_DIR, "pull", "--rebase"],
                        capture_output=True, text=True, timeout=60)
if result.returncode != 0:
    print(f"⚠️ Rebase失败: {result.stderr}")
    # 如果rebase失败，尝试stash + rebase
    subprocess.run(["git", "-C", LEARN_DIR, "stash"], capture_output=True)
    subprocess.run(["git", "-C", LEARN_DIR, "pull", "--rebase"], capture_output=True, timeout=60)
    subprocess.run(["git", "-C", LEARN_DIR, "stash", "pop"], capture_output=True)

# 3. 检查状态 — rebase后staged changes可能被清除
# 如果Day N文件仍存在于磁盘但未被staged
result = subprocess.run(["git", "-C", LEARN_DIR, "status", "--short"],
                        capture_output=True, text=True)
if result.stdout.strip():
    # 有未staged的变更，需要重新add + commit
    subprocess.run(["git", "-C", LEARN_DIR, "add", "-A"], capture_output=True, timeout=30)
    subprocess.run(["git", "-C", LEARN_DIR, "commit", "-m", "📚 Day N: ..."],
                   capture_output=True, timeout=30)

# 4. 推送
result = subprocess.run(["git", "-C", LEARN_DIR, "push"],
                        capture_output=True, text=True, timeout=60)
print(f"Push: {result.returncode} - {result.stderr[:200]}")
```

### 注意事项

- **rebase 不会删除已存在的文件**：即使 rebase 清空了 staged changes，只要 Day N 文件已经保存在磁盘上，`git status` 仍然会看到它作为 untracked 或 modified 文件
- **如果 pull --rebase 后 status --short 为空**：说明其他会话的提交已经包含了相同的文件或更改，无需额外操作
- **认证失败 vs 推送冲突**：先确认 403 认证问题再执行 pull。如果认证失败（403 "The token username invalid"），fix remote URL 后再尝试

## ⚠️ 常见错误

### ❌ 误解：Gitee认证必须使用正确的用户名

早期经验认为 `year_old:{TOKEN}` 向 `iiixiyan/huawei-od-learning` 推送会收到 403。但实测表明 **Gitee Personal Access Token 的 HTTP Basic Auth 会忽略 username 字段**，仅校验 token 值。`year_old:{TOKEN}`、`oauth2:{TOKEN}`、`iiixiyan:{TOKEN}` 均可正常工作。

**推荐方案**：
- 首选 `oauth2:{TOKEN}`（Gitee官方标准方式）
- 备选 `{任意用户名}:{TOKEN}` 均可（实测 `year_old` 也能成功推送）
- 403 的唯一原因是 token 本身已过期或无效，与 URL 中的用户名无关

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

源仓库 `huawei-od-prep` 的周目录名与学习仓库的目录名不一致，目前已确认两个差异：
- **第3周**：源仓库 `week-03-linkedlist-tree` vs 学习仓库 `week-03-stack-queue-linkedlist`
- **第4周**：源仓库 `week-04-dp-review` vs 学习仓库 `week-04-tree-graph`（源仓库目录名含"dp"但内容完全是二叉树，与DP无关）

使用 `rglob` 搜索文件而不是硬编码周目录名，避免因命名不一致导致文件找不到。详见 `references/gitee-config.md` 的目录结构对照表。

## 静态站点部署（Web查看层）

学习笔记除了直接用 Gitee 仓库浏览外，还有一个 **静态HTML站点** 部署在服务器上，提供更好的阅读体验。

### 站点信息

| 项目 | 值 |
|------|-----|
| **URL** | `http://106.12.76.187:8765/` |
| **站点目录** | `/tmp/site/` |
| **组件** | `index.html`（前端页面）+ `server.py`（Python代理服务） |
| **端口** | 8765 |
| **数据源** | 通过 `/api/gitee/contents/` 代理实时拉取 Gitee API 内容 |

### 站点功能

- **深色/浅色主题切换**：Header 右侧 🌙/☀️ 按钮，偏好保存到 `localStorage`
- **左侧目录树**：按周分组，可折叠，自动高亮当前文档
- **Markdown 渲染**：使用 `marked.js` 在前端渲染
- **代码复制按钮**：鼠标悬停在代码块上显示 📋 复制按钮
- **手机自适应**：侧栏自动隐藏，点击 ☰ 展开
- **进度条**：每周显示完成进度
- **首页统计**：已学天数、完成周数等概览

### 更新站点

生成新的学习文档后，如果需要更新站点（目前站点已内置完整的目录结构和数据代理，**无需手动更新**，因为前端通过 `<yourdomain>/api/gitee/contents/` 代理实时从 Gitee API 拉取最新内容）。

但如果需要修改前端样式或功能，按以下步骤操作：

```bash
# 1. 编辑 index.html 或 server.py
vim /tmp/site/index.html

# 2. 重启服务器
pkill -f "python3 server.py"
cd /tmp/site && python3 server.py &
```

### 代理服务器说明

`server.py` 注册了 `/api/gitee/contents/<path>` 路由，它会：

1. 代理 Gitee API v5 `repos/iiixiyan/huawei-od-learning/contents/<path>`
2. 解码 Base64 内容，返回 `Content-Type: text/markdown`
3. 添加 CORS 头（`Access-Control-Allow-Origin: *`）

这解决了 Gitee raw 直链返回 `text/plain` 导致浏览器无法正确渲染 HTML 的问题。

### 主题切换实现

- CSS 变量驱动：`.light-theme` class 覆盖所有颜色变量
- 暗色默认为深蓝色系（#0f0f1a背景）
- 亮色为白底蓝字（#f5f7fa背景，#2563eb强调色）
- 包含滚动条、强文本、行内代码颜色的同步适配
- 切换后自动持久化到 `localStorage`（key: `od-theme`）

## 参考

- 源仓库：https://gitee.com/year_old/huawei-od-prep
- 学习仓库：https://gitee.com/iiixiyan/huawei-od-learning
- 课程时间线：Day 1 = 2026-05-11，每天递增
- Gitee API操作参考：`references/gitee-api-operations.md`（仓库创建/查询/修改/删除）
- Gitee仓库配置：`references/gitee-config.md`（URL/Token/目录结构）
- Gitee→GitHub同步：`references/gitee-github-sync.md`（镜像/双推方案）
- **代码示例Bug模式参考**：`references/generated-code-bug-patterns.md`（生成文档后必查的常见Python错误，缺少None检查/Optional缺导入/未定义函数等）
- 文档模板：`templates/study-note-template.md`
