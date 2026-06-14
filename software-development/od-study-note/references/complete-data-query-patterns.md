# complete-data.json 查询模式

## 数据结构

`/tmp/huawei-od-new-system/complete-data.json` 是 **dict[str, list[dict]]** 结构：

```json
{
  "新系统真题 (2026.4~6月)": [
    {"title": "题名", "topics": ["标签1", "标签2"], "difficulty": "?"},
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
  ...
}
```

## 按标签查询（已验证的常用模式）

```python
import json

data = json.load(open('/tmp/huawei-od-new-system/complete-data.json'))

# 按标签过滤所有题目
results = []
for cat, problems in data.items():
    for p in problems:
        tags = p.get('topics', [])
        if isinstance(tags, str):
            tags = [tags]
        tag_str = ' '.join(tags)
        if '双指针' in tag_str:  # 替换为目标标签
            results.append((cat, p.get('title','?'), tags))

print(f"找到 {len(results)} 道题")
for cat, title, tags in results:
    print(f"  [{cat}] {title} | 标签: {tags}")
```

## 查看所有可用标签

```python
tags = set()
for cat, problems in data.items():
    for p in problems:
        t = p.get('topics', [])
        if isinstance(t, str):
            tags.add(t)
        elif isinstance(t, list):
            tags.update(t)
print(sorted(tags))
```

## 标签与考频对照（1208道题全量统计）

| 标签 | 次数 | 占比 |
|------|------|------|
| 模拟 | 265 | 21.9% |
| 逻辑分析 | 134 | 11.1% |
| 贪心 | 104 | 8.6% |
| DFS | 86 | 7.1% |
| BFS | 76 | 6.3% |
| 双指针 | 74 | 6.1% |
| 排序 | 70 | 5.8% |
| 递归回溯 | 59 | 4.9% |
| 二分 | 55 | 4.6% |
| 数学原理 | 52 | 4.3% |
| 动态规划 | 48 | 4.0% |
| 哈希表 | 47 | 3.9% |
| 滑动窗口 | 34 | 2.8% |
| 栈 | 28 | 2.3% |
| 前缀和 | 25 | 2.1% |
| 字符串 | 22 | 1.8% |
| 并查集 | 20 | 1.7% |
| 区间合并 | 19 | 1.6% |
| 单调栈 | 15 | 1.2% |
| 二叉树 | 14 | 1.2% |
