# OD新系统真题数据分析

> 采集自CSDN博客，2026年新系统双机位C卷，47道真题
> 仓库：https://gitee.com/iiixiyan/huawei-od-new-system-questions

## 采集方式

CSDN文章有反爬限制，浏览器返回403。使用 `curl` 带手机端User-Agent直接获取HTML：

```bash
curl -s -L -H 'User-Agent: Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36' <url>
```

## 提取文章内容

CSDN正文在 `class="article_content"` 或 `id="content_views"` 的div中：

```python
import re
m = re.search(r'class="article_content"[^>]*>(.*?)</div>\s*<div', html, re.DOTALL)
content = m.group(1)
```

表格数据每4个字段一行：日期 | 分值 | 题目 | 考点

## 考点频率统计（47道真题）

| 排名 | 考点 | 出现次数 |
|------|------|:--------:|
| 1 | 模拟 | 17 |
| 2 | BFS | 6 |
| 3 | 逻辑分析 | 6 |
| 4 | 递归回溯 | 5 |
| 5 | 贪心 | 3 |
| 5 | 单调栈 | 3 |
| 5 | 动态规划 | 3 |
| 5 | 自定义排序 | 3 |
| 9 | 双指针 | 2 |
| 9 | 前缀和 | 2 |

## 20天冲刺计划结构

基于频率排序，每天配：
1. 知识点讲解 + 代码模板（可背诵）
2. LeetCode必刷题（带原题链接）
3. OD新系统真题（标注日期和分值）
4. 自测清单

详细计划见仓库中的 `20天冲刺计划.md`
