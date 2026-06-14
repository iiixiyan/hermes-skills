# CSDN 博客表格解析技巧

## 背景

CSDN 博客（blog.csdn.net）经常包含以 HTML `<table>` 格式呈现的技术题库/真题数据。CSDN 有较强的反爬机制，但解析表格数据是数据采集中常见的需求。

## 技术方案

### 第1步：获取HTML内容

CSDN 对桌面端浏览器 UA 会有 403 拦截。使用移动端 UA 可直接获取：

```bash
curl -s -L -H 'User-Agent: Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36' \
  "https://blog.csdn.net/USER_ID/article/details/ARTICLE_ID"
```

### 第2步：提取文章内容区域

CSDN 的文章正文在 `id="article_content"` 的 div 中：

```python
import re

html = result.stdout  # curl 返回内容

# 方法1：匹配 article_content
m = re.search(
    r'id="article_content"[^>]*>(.*?)</div>\s*<div[^>]*class="recommend',
    html, re.DOTALL
)

# 方法2：fallback（如果文章末尾没有recommend div）
if not m:
    m = re.search(r'id="article_content"[^>]*>(.*?)</div>', html, re.DOTALL)

# 方法3：进一步fallback
if not m:
    m = re.search(r'class="article_content"[^>]*>(.*?)</div>', html, re.DOTALL)

content = m.group(1)
```

### 第3步：提取所有HTML表格

```python
tables = re.findall(r'<table[^>]*>(.*?)</table>', content, re.DOTALL)
```

### 第4步：解析表格行和单元格

```python
for ti, table in enumerate(tables):
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
    
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        if len(cells) >= 2:  # 至少有序号和内容
            clean = []
            for cell in cells:
                # 清理HTML标签
                text = re.sub(r'<[^>]+>', '', cell)
                # 清理HTML实体
                text = re.sub(r'&nbsp;', ' ', text)
                text = re.sub(r'&lt;', '<', text)
                text = re.sub(r'&gt;', '>', text)
                text = re.sub(r'&amp;', '&', text)
                # 清理Unicode转义（&#xXXXX; 和 &#DDDD;）
                text = re.sub(r'&#xff0c;', ',', text)
                text = re.sub(r'&#x([0-9a-f]+);', lambda m: chr(int(m.group(1), 16)), text)
                text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
                text = text.strip()
                # 跳过无关文本
                if text and text != '点击去做题':
                    clean.append(text)
            
            if len(clean) >= 2:
                # 提取信息
                title = clean[1]  # 题目名通常在第二个单元格
                topic_str = clean[2] if len(clean) > 2 else ""  # 考点在第三个
                # 解析考点（以逗号/中文逗号/斜杠分隔）
                topics = [t.strip() for t in re.split(r'[,，/]', topic_str) if t.strip()]
```

### 第5步：积累统计

```python
from collections import Counter

all_topics = Counter()
all_questions = []

for questions in section_data.values():
    for q in questions:
        for topic in q['topics']:
            all_topics[topic] += 1
        all_questions.append(q)

# TOP30 考点
for rank, (topic, count) in enumerate(all_topics.most_common(30), 1):
    pct = count / len(all_questions) * 100
    print(f"{rank:2d}. {topic:10s} {count:3d}次 ({pct:.1f}%)")
```

## 注意事项

1. **CSDN 反爬**：移动端 UA 比桌面端 UA 更可靠，且不需要 Cookie
2. **表格结构**：CSDN 表格可能有表头行（`<th>`），需要用 `ti == 0` 判断跳过
3. **考点字段中有噪声**：如"考点 or 实现"等表头文本混入，需要在解析时过滤
4. **HTML实体处理**：CSDN 使用 `&#xff0c;`（全角逗号）等 Unicode 转义，需要单独处理
5. **多表格场景**：一篇文章可能包含多个不连续的表格，需分别解析后合并

## 适用平台

此技巧适用于以下类似中文技术博客：
- CSDN (blog.csdn.net) — 已验证
- 知乎专栏 (zhuanlan.zhihu.com) — 结构类似
- 简书 (jianshu.com) — 结构类似
- 掘金 (juejin.cn) — 结构不同，需调整选择器
