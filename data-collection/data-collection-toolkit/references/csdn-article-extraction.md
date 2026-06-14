# CSDN 文章内容提取方法（含付费墙绕过）

## 适用场景

需要从CSDN博客获取文章内容，但：
- 文章有付费墙（"订阅专栏 解锁全文"）
- 全文被截断，但**问题描述部分在付费墙之前**
- 需要提取题目描述、输入输出格式、示例等**问题陈述部分**
- 解题思路和代码在付费墙后不可见

## 核心原理

CSDN文章通过`<div id="article_content">`包含原始HTML内容（含付费墙前全部文本）。**问题陈述（题目描述、输入格式、输出格式、示例）始终在付费墙之前**，因此即使不付费也能提取。

## 提取步骤

### 第1步：获取原始HTML

```python
import subprocess, re, html as html_mod

result = subprocess.run([
    "curl", "-s", "-L", "--max-time", "15",
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120",
    url
], capture_output=True, text=True, timeout=15)
h = result.stdout
```

关键：使用桌面版Chrome UA，CSDN对curl+桌面UA不拦截。

### 第2步：提取article_content div

```python
m = re.search(r'id="article_content"[^>]*>(.*?)</div>\s*<div[^>]*class="recommend', h, re.DOTALL)
if not m:
    m = re.search(r'id="article_content"[^>]*>(.*?)</div>', h, re.DOTALL)
content = m.group(1)
content = html_mod.unescape(content)
```

两种模式：
- 优先用`recommend`结尾（更精确，排除文末推荐内容）
- 回退用通用`</div>`结尾（包含全文）

### 第3步：清理HTML标签（保留代码块）

```python
# 1. 移除脚本和样式
content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
content = re.sub(r'<svg[^>]*>.*?</svg>', '', content, flags=re.DOTALL)

# 2. 保护代码块（先提取pre/code，再清理）
def protect_code(m):
    code = re.sub(r'<[^>]+>', '', m.group(1))
    code = html_mod.unescape(code)
    return f'\n```\n{code}\n```\n'

content = re.sub(r'<pre[^>]*>(?:<code[^>]*>)?(.*?)(?:</code>)?</pre>', protect_code, content, flags=re.DOTALL)

# 3. 块级标签转换行
for tag in ['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'br', 
            'table', 'tr', 'th', 'td', 'blockquote', 'ul', 'ol']:
    content = re.sub(f'</?{tag}[^>]*>', '\n', content)

# 4. 清理剩余HTML标签和空白
content = re.sub(r'<[^>]+>', '', content)
content = re.sub(r'[ \t]+', ' ', content)
content = re.sub(r'\n{4,}', '\n\n', content)
```

### 第4步：截断付费墙后内容

```python
for marker in ['解题思路', '核心思想', '订阅专栏', '解锁全文']:
    pos = content.find(marker)
    if pos > 0:
        content = content[:pos]
```

### 第5步：清理广告行

```python
content = re.sub(r'\n点击查看华为 OD.*?\n', '\n', content)
content = re.sub(r'\n了解本专栏.*', '', content, flags=re.DOTALL)
```

## 完整函数

```python
import subprocess, re, html as html_mod

def fetch_csdn_problem_statement(url):
    """提取CSDN文章的问题描述（付费墙前内容）"""
    result = subprocess.run([
        "curl", "-s", "-L", "--max-time", "15",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120",
        url
    ], capture_output=True, text=True, timeout=15)
    h = result.stdout

    m = re.search(r'id="article_content"[^>]*>(.*?)</div>\s*<div[^>]*class="recommend', h, re.DOTALL)
    if not m:
        m = re.search(r'id="article_content"[^>]*>(.*?)</div>', h, re.DOTALL)
    if not m:
        return None

    content = m.group(1)
    content = html_mod.unescape(content)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
    content = re.sub(r'<svg[^>]*>.*?</svg>', '', content, flags=re.DOTALL)

    def protect_code(m):
        code = re.sub(r'<[^>]+>', '', m.group(1))
        return f'\n```\n{code}\n```\n'
    content = re.sub(r'<pre[^>]*>(?:<code[^>]*>)?(.*?)(?:</code>)?</pre>', protect_code, content, flags=re.DOTALL)

    for tag in ['div', 'p', 'h[1-6]', 'li', 'br', 'table', 'tr', 'td', 'th', 'blockquote']:
        content = re.sub(f'</?{tag}[^>]*>', '\n', content)
    content = re.sub(r'<[^>]+>', '', content)
    content = re.sub(r'[ \t]+', ' ', content)
    content = re.sub(r'\n{4,}', '\n\n', content)

    for marker in ['解题思路', '核心思想', '订阅专栏', '解锁全文']:
        pos = content.find(marker)
        if pos > 0:
            content = content[:pos]

    return content.strip()
```

## 局限与注意事项

1. **付费墙后内容不可得**：解题代码、完整题解在"订阅专栏"之后，curl拿不到
2. **JS渲染内容不可得**：CSDN文章的数学公式、流程图等依赖JS渲染的内容无法提取
3. **CSDN可能更新反爬策略**：若curl返回内容<500字，检查是否需要更新UA
4. **部分文章整篇付费**：问题描述也在付费墙后，这时只能用文章标题

## 与`csdn-blog-table-parsing.md`的区别

| 文件 | 用途 |
|:----|:------|
| `csdn-blog-table-parsing.md` | 提取CSDN博客中的表格数据（题库/排行榜） |
| `csdn-article-extraction.md` | 提取CSDN文章的文本内容（问题描述/题目） |
