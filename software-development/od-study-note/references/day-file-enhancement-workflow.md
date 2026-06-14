# 20天冲刺计划 Day文件增强工作流

## 仓库

- **GitHub/Gitee**: https://gitee.com/iiixiyan/huawei-od-new-system-questions
- **本地路径**: `/tmp/huawei-od-new-system/`
- **20天计划目录**: `/tmp/huawei-od-new-system/20天计划/`
- **题库数据**: `/tmp/huawei-od-new-system/complete-data.json`（1208道题元数据）
- **认证**: `https://oauth2:{GITEE_TOKEN}@gitee.com/iiixiyan/huawei-od-new-system-questions.git`

## 触发条件

当用户提到以下内容时，加载此工作流：
- "优化Day N"、"增强Day N"、"丰富Day N"
- "给OD真题加链接"、"加CSDN链接"
- "20天计划" / "冲刺计划"

## Day文件增强标准

### 每道OD真题必须包含：

```
1. 题目描述 — 完整的问题场景和规则说明
2. 输入格式 — 第一行/后续行的格式定义
3. 输出格式 — 输出内容说明
4. 示例输入/输出 — 至少1个完整示例
5. 完整代码 — Python可运行代码（包含 solve() 函数 + `if __name__`）
6. 手把手推演 — 变量状态追踪表/ASCII推演
7. 多case演练（可选）— 第二个示例的完整推演
8. 复杂度分析 — 时间O() + 空间O()
9. 考点分析 — 核心知识点、易错点、变形题方向
10. CSDN题解链接 — 从博主目录页获取（见 references/csdn-od-problem-sourcing.md）
```

### 文档总大小目标

- **首次生成**: ≥ 20KB
- **增强版**: ≥ 30KB（Day01已达到30KB）
- **结构完整性**: 目录 → 知识点 → 模型/套路 → LeetCode精讲 → OD真题精讲 → 常见坑 → 今日自测

### OD真题数量

- 模拟/高频考点: 8道
- 其他考点: 5-8道（按考点频率分配）
- 来源：新系统真题、双机位C/B/A卷、2025C/B/A卷、E卷

## 增强工作流

### 第1步：读取当前内容，评估每道题缺失项

```python
import re
with open(f"{REPO}/20天计划/DayNN-主题.md") as f:
    content = f.read()

problems = re.findall(r'### 真题\d.*?(?=### 真题|\Z)', content, re.DOTALL)
for p in problems:
    has_code = '```python' in p
    has_deduction = '手把手' in p or '推演' in p
    has_complexity = '复杂度' in p
    has_example = '示例' in p or '输入' in p
    has_link = 'blog.csdn.net' in p
    print(f"代码:{has_code} 推演:{has_deduction} 复杂度:{has_complexity} 示例:{has_example} 链接:{has_link}")
```

### 第1.5步（可选）：按考点筛选OD真题

使用 `scripts/query-od-problems.py` 查询 complete-data.json 按考点筛选真题：

```bash
# 查询某考点相关真题（含来源分布统计）
python3 scripts/query-od-problems.py 排序
python3 scripts/query-od-problems.py 区间合并 贪心

# 以 Markdown 表格输出（直接粘贴到 Day 文档）
python3 scripts/query-od-problems.py 排序 --markdown --limit 10

# 按标题关键词过滤
python3 scripts/query-od-problems.py --title 日志 --source "双机位"
```

这比手动翻阅 complete-data.json 更快，且能直观看到各来源的题目分布，帮助决定从哪些卷选取真题。

### 第2步：获取CSDN链接

从博主目录页 `https://blog.csdn.net/qq_45776114/article/details/145076776` 抓取（详见 `references/csdn-od-problem-sourcing.md`）

### 第3步：生成增强内容

使用 `execute_code` 直接生成并写文件（注意三重引号冲突）。每道题增强到500-2500字符。

### 第4步：推送到Gitee

```bash
git -C /tmp/huawei-od-new-system add -A
git -C /tmp/huawei-od-new-system commit -m "📘 增强DayNN：详细推演+考点+CSDN链接（XXKB）"
git -C /tmp/huawei-od-new-system push
```

## 已知CSDN链接（已采集）

见 `references/csdn-od-problem-sourcing.md` 中的已知链接表。
