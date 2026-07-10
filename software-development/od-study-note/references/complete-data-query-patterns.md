# complete-data.json 查询模式与问题选择策略

## 数据结构

`/tmp/huawei-od-new-system/complete-data.json` 是 **dict[str, list[dict]]** 结构：

```json
{
  "新系统真题 (2026.4~6月)": [
    {"title": "题名", "topics": ["标签1", "标签2"]},
    ...
  ],
  "双机位C卷-100分": [...],
  "双机位C卷-200分": [...],
  "双机位B卷-100分": [...],
  "双机位B卷-200分": [...],
  "双机位A卷-100分": [...],
  "双机位A卷-200分": [...],
  "2025C卷-100分": [...],
  "2025C卷-200分": [...],
  "2025B卷-100分": [...],
  "2025B卷-200分": [...],
  "2025A卷-100分": [...],
  "2025A卷-200分": [...],
  "E卷-100分": [...],
  "E卷-200分": [...],
  "A卷-100分": [...],
  "A卷-200分": [...]
}
```

**注意**：每个题目的 `topics` 字段可能是 `list[str]` 或 `str`，访问时必须统一处理。

## 基础查询模式（terminal inline Python）

由于 `execute_code` 在 cron 模式下被阻止，所有 JSON 查询必须通过 `terminal` 中运行 inline Python 完成：

```bash
# 查询某标签的所有题目
python3 -c "
import json
data = json.load(open('/tmp/huawei-od-new-system/complete-data.json'))
query = '二分'
results = []
for cat, problems in data.items():
    for p in problems:
        tags = p.get('topics', [])
        if isinstance(tags, str): tags = [tags]
        if query in ' '.join(tags):
            results.append((cat, p['title'], tags))

print(f'找到 {len(results)} 道 [{query}] 题:')
for cat, title, tags in results:
    print(f'  [{cat}] {title}')
    print(f'    标签: {tags}')
"
```

为避免 shell 反引号/引号冲突，使用**双引号包 python 代码、单引号括字符串**：

```bash
# ✅ 安全写法
python3 -c "
tags = p.get('topics', [])
if isinstance(tags, str):
    tags = [tags]
if '二分' in ' '.join(tags):
    ...
"
```

## 问题选择策略（核心新增！）

**每天优化 Day 文件时，选择 5-8 道 OD 真题。选择标准：**

### 1. 来源多样性（必须覆盖 ≥3 个来源）

不要全从同一个来源选。一个好的分布：

| 来源 | 推荐题目数 | 原因 |
|------|-----------|------|
| 新系统真题 (2026.4~6月) | 0-1道 | 最新真题，优先选 |
| 双机位C卷 (100+200) | 2-3道 | 主力真题库 |
| 双机位A/B卷 | 1-2道 | 补充验证 |
| 2025C/B/A卷 | 2-3道 | 历史高频题 |
| E卷 | 1道 | 低频但灵活的题 |

### 2. 难度平衡（100分+200分混排）

| 分值 | 推荐数量 | 说明 |
|------|---------|------|
| 100分题 | 2-3道 | 基础分，必须拿满 |
| 200分题 | 3-5道 | 拉开差距的核心 |

**排序建议**：先放 100分题（小白友好），再放 200分题。

### 3. 次要标签多样性

同一个大主题下，选择不同次要标签的题目，展示该知识点的不同应用场景：

| 主题 | 次要标签组合示例 |
|------|----------------|
| 二分 | 二分+双指针、二分+DFS、二分+数学原理、纯二分（二分答案） |
| 动态规划 | DP+贪心、DP+字符串、DP+哈希表、DP+二分 |
| DFS | DFS+回溯、DFS+记忆化、DFS+剪枝、DFS+二分 |
| BFS | BFS+层序、BFS+多源、BFS+拓扑、BFS+二分 |
| 双指针 | 双指针+排序、双指针+滑动窗口、双指针+二分 |

### 4. 题名独特性

不要选同名跨卷的题（如「智能驾驶」同时出现在 4 个来源），只保留最新来源的那一道。使用去重：

```python
seen = set()
unique = []
for cat, title, tags in results:
    # 提取题名末尾的中文核心名（去掉卷名前缀）
    core_name = title.split(' - ')[-1] if ' - ' in title else title
    if core_name not in seen:
        seen.add(core_name)
        unique.append((cat, title, tags))
```

### 5. 考点匹配

确保选中的题目**确实展示了该主题的核心思想**。例如，二分专题应优先选：
- 体现「二分答案」思想的（占OD二分题的70%）：爱吃蟠桃的孙悟空、最佳植树距离
- 体现「标准二分」的：部门人力分配
- 体现「二分+复杂约束」的：员工派遣、智能驾驶
- 体现「最大化最小值/最小化最大值」两种方向的都有

## 完整查询示例（二分专题，含去重和精选）

```bash
python3 -c "
import json
data = json.load(open('/tmp/huawei-od-new-system/complete-data.json'))

# 1. 查询所有二分标签的题目
query = '二分'
results = []
for cat, problems in data.items():
    for p in problems:
        tags = p.get('topics', [])
        if isinstance(tags, str): tags = [tags]
        if query in ' '.join(tags):
            results.append((cat, p['title'], tags))

# 2. 按来源分类统计
from collections import Counter
source_counts = Counter()
for cat, _, _ in results:
    source = cat.split('-')[0]  # 取来源前缀
    source_counts[source] += 1
print('来源分布:', dict(source_counts))

# 3. 去重（保留核心题名）
seen = set()
unique = []
for cat, title, tags in results:
    core = title.split(' - ')[-1] if ' - ' in title else title
    # 策略：新系统真题 > 双机位 > 2025卷 > E卷
    priority = 0
    if '新系统' in cat: priority = 4
    elif '双机位' in cat: priority = 3
    elif '2025' in cat or 'E卷' in cat: priority = 2
    else: priority = 1

    if core not in seen:
        seen.add(core)
        unique.append((priority, cat, title, tags, core))
    else:
        # 已有同名题，保留更高优先级的
        for i, (p, c, t, tg, cn) in enumerate(unique):
            if cn == core and priority > p:
                unique[i] = (priority, cat, title, tags, core)

# 4. 按标签多样性优选
tag_groups = {}
for p, cat, title, tags, core in unique:
    for tag in tags if isinstance(tags, list) else [tags]:
        if tag != '二分':
            tag_groups.setdefault(tag, []).append((cat, title))

print()
print('按次要标签分组:')
for tag, items in sorted(tag_groups.items()):
    print(f'  {tag}: {[t for _,t in items]}')

# 5. 输出精选列表
print()
print(f'去重后共 {len(unique)} 道题')
"
```

## 查看所有可用标签

```bash
python3 -c "
import json
data = json.load(open('/tmp/huawei-od-new-system/complete-data.json'))
tags = set()
for cat, problems in data.items():
    for p in problems:
        t = p.get('topics', [])
        if isinstance(t, str): tags.add(t)
        elif isinstance(t, list): tags.update(t)
print(sorted(tags))
"
```

## 标签与考频对照（1208道题全量统计）

| 标签 | 次数 | 占比 | 100分/200分 |
|------|------|------|------------|
| 模拟 | 265 | 21.9% | 以100分为主（送分题） |
| 逻辑分析 | 134 | 11.1% | 以100分为主 |
| 贪心 | 104 | 8.6% | 兼有 |
| DFS | 86 | 7.1% | 200分偏多 |
| BFS | 76 | 6.3% | 兼有 |
| 双指针 | 74 | 6.1% | 100分偏多 |
| 排序 | 70 | 5.8% | 兼有 |
| 递归回溯 | 59 | 4.9% | 200分偏多 |
| **二分** | **55** | **4.6%** | **兼有（70%二分答案）** |
| 数学原理 | 52 | 4.3% | 兼有 |
| 动态规划 | 48 | 4.0% | 200分偏多（区分度题） |
| 哈希表 | 47 | 3.9% | 100分偏多 |
| 滑动窗口 | 34 | 2.8% | 以100分为主 |
| 栈 | 28 | 2.3% | 兼有 |
| 前缀和 | 25 | 2.1% | 兼有 |
| 字符串 | 22 | 1.8% | 以100分为主 |
| 并查集 | 20 | 1.7% | 200分偏多 |
| 区间合并 | 19 | 1.6% | 以100分为主 |
| 单调栈 | 15 | 1.2% | 兼有 |
| 二叉树 | 14 | 1.2% | 兼有 |

## 快速选题模板

每次优化 Day 文件时，按以下步骤选题：

```bash
# 1. 查标签
python3 -c "
import json
data = json.load(open('/tmp/huawei-od-new-system/complete-data.json'))
Q = '二分'  # ← 替换为目标主题标签
results = []
for cat, problems in data.items():
    for p in problems:
        tags = p.get('topics', [])
        if isinstance(tags, str): tags = [tags]
        if Q in ' '.join(tags):
            results.append((cat, p['title'], tags))
print(f'备选: {len(results)} 道')
# 去重
seen = set()
for cat, title, tags in results:
    core = title.split(' - ')[-1] if ' - ' in title else title
    if core not in seen:
        seen.add(core)
        print(f'  [{cat}] {title}')
        print(f'    标签: {tags}')
"
```

**选择原则**：优先选"去重后列表"中次要标签种类最多、覆盖不同来源的 5-8 道题。

## DP子类型关键词过滤（Day10/11/14分配用）

当标签='动态规划'的题目需要进一步分配到Day10（一维DP）/ Day11（二维DP+背包）/ Day14（背包）/ Day15（树状DP）时，使用标题关键词+标签双重过滤：

```bash
cd /tmp/huawei-od-new-system && python3 -c "
import json
data = json.load(open('complete-data.json'))

# DP子类型关键词
one_d_titles = ['猴子爬山','抢7','找终点','跳格子','最佳对手',
                '工作安排','限流','调度','充电桩','过河']
two_d_titles = ['查找重复','公共子串','字符串','最短路径','园区参观',
                '会议接待','矩阵的和','大炮攻城','攻城站']
knap_titles = ['MELON','报酬','磁盘','背包','书籍叠放','构建数列','构造数列']
tree_titles = ['WonderLand','士兵过河','伐木','快递员的烦恼','路测路线']

counts = {'一维DP':0,'二维DP':0,'背包DP':0,'树状DP':0,'其他':0}

for category, problems in data.items():
    for p in problems:
        title = p['title']
        tags = p.get('topics', [])
        if isinstance(tags, str): tags = [tags]
        if '动态规划' not in ' '.join(tags):
            continue
        if any(t in title for t in one_d_titles):
            counts['一维DP'] += 1
            print(f'[Day10-一维] [{category}] {title}')
        elif any(t in title for t in two_d_titles):
            counts['二维DP'] += 1
            print(f'[Day11-二维] [{category}] {title}')
        elif any(t in title for t in knap_titles):
            counts['背包DP'] += 1
            print(f'[Day11/14-背包] [{category}] {title}')
        elif any(t in title for t in tree_titles):
            counts['树状DP'] += 1
            print(f'[Day15-树状] [{category}] {title}')
        else:
            counts['其他'] += 1
            print(f'[未知分配] [{category}] {title}')

print(f'\\n=== 分配统计 ===')
for k, v in counts.items():
    print(f'{k}: {v}道')
"
```

**注**：书籍叠放（LIS变体）同时出现在二维和背包组中，按Day11内容结构放在\"变型排序+DP\"模型下更合适。
