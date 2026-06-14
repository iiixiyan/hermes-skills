# OD真题CSDN题解链接获取

## 博主目录页（主入口）

### 首选（新系统真题）：banxia_frontend 目录页
**URL**: https://blog.csdn.net/banxia_frontend/article/details/160346662

这是博主 `banxia_frontend` 整理的**2026年新系统OD真题**目录，包含全部新系统题解链接。**当用户提到"用这个目录的链接"时，必须使用此目录**。该目录收录的题目命名格式：`4.1 空间占用计算`、`4.19 8位LED控制器`、`5.24 简单表达式运算`等。

### 备选（全量题库）：qq_45776114 目录页
**URL**: https://blog.csdn.net/qq_45776114/article/details/145076776

这是博主 `qq_45776114` 整理的华为OD机试真题题库目录，包含 **1200+ 道题**的CSDN题解链接，涵盖：
- 新系统真题 (2026.4~6月)
- 双机位C卷/B卷/A卷
- 2025C卷/B卷/A卷
- E卷

### 用户偏好
- ⭐ 新系统真题优先使用 `banxia_frontend` 目录的链接
- ⭐ 用户要求"只需要获取原文题目，你来解答和讲解" — 只提取题目描述，代码和讲解自己写
- ⭐ 题目内容必须"原文不动" — 保留CSDN原题描述，不做改写/简化

## 获取方法

### 方法1：从目录页提取文章链接

```python
import subprocess, re

# 从 banxia_frontend 目录页提取（新系统真题首选）
url = "https://blog.csdn.net/banxia_frontend/article/details/160346662"
result = subprocess.run([
    "curl", "-s", "-L", "--max-time", "15",
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120",
    url
], capture_output=True, text=True, timeout=15)

html = result.stdout
# 提取文章正文
m = re.search(r'id="article_content"[^>]*>(.*?)</div>', html, re.DOTALL)
if m:
    content = m.group(1)
    # 提取所有链接
    all_links = re.findall(r'<a[^>]*href="(https?://blog\\.csdn\\.net/[^"]*)"[^>]*>(.*?)</a>', content, re.DOTALL)
    for url, text in all_links:
        title = re.sub(r'<[^>]+>', '', text).strip()
        if '新系统' in title:
            print(f"{title} -> {url.split('?')[0]}")
```

### 方法1b：从 qq_45776114 目录页提取（全量题库）
```python
url = "https://blog.csdn.net/qq_45776114/article/details/145076776"
# 同上
```

### ⭐ 方法2：从单篇文章提取题目描述（只取原题，不取解答）

用户要求：**只需要获取原文题目，你来解答和讲解**

CSDN文章大多数有付费墙（`订阅专栏 解锁全文`），但**题目描述部分可见**。提取方法：

```python
import subprocess, re, html as html_mod

def fetch_problem_statement(url):
    result = subprocess.run([
        "curl", "-s", "-L", "--max-time", "15",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120",
        url
    ], capture_output=True, text=True, timeout=15)
    h = result.stdout
    m = re.search(r'<div[^>]*id="content_views"[^>]*>(.*?)</div>\s*</div>', h, re.DOTALL)
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
        return '\n```\n' + re.sub(r'<[^>]+>', '', m.group(1)) + '\n```\n'
    content = re.sub(r'<pre[^>]*>(?:<code[^>]*>)?(.*?)(?:</code>)?</pre>', protect_code, content, flags=re.DOTALL)
    for tag in ['div', 'p', 'h1', 'h2', 'h3', 'li', 'br', 'table', 'tr', 'td', 'th', 'blockquote', 'ul', 'ol']:
        content = re.sub(f'</?{tag}[^>]*>', '\n', content)
    content = re.sub(r'<[^>]+>', '', content)
    content = re.sub(r'[ \t]+', ' ', content)
    content = re.sub(r'\n{4,}', '\n\n', content)
    for marker in ['解题思路', '核心思想', '订阅专栏', '解锁全文']:
        pos = content.find(marker)
        if pos > 0: content = content[:pos]
    content = re.sub(r'\n点击查看华为 OD.*?\n', '\n', content)
    return content.strip()
```

### ⚠️ 目录页链接提取不可靠（JS渲染限制）

banxia_frontend 目录页（`/article/details/160346662`）使用 JavaScript 懒加载文章标题，**在 curl 返回的原始 HTML 中，所有链接的可见文本都是统一的"点击去刷题"**，无法通过简单的 `re.findall` 提取题目名称到链接的对应关系。

**替代方案**（当链接提取不可靠时）：
1. **直接访问已知排序/区间合并等主题文章** — 根据 complete-data.json 中的题目命名，猜测博主可能使用的标题格式，在浏览器中手动查找
2. **使用 CSDN 搜索功能**：`https://blog.csdn.net/banxia_frontend/search?q=排序`
3. **从 qq_45776114 目录页提取**（该页面可能使用不同的渲染方式）：`https://blog.csdn.net/qq_45776114/article/details/145076776`
4. **如果完全无法获取题目描述** — 根据 OD 真题的常见题型，自己编写合理的题目描述（注明为复述而非原文）

### ⚠️ 关键差异：CSDN原题 vs Day文件中的题

CSDN文章标题可能与Day文件中的题名相同，但**题目内容可能完全不同**。

| Day文件中的旧题 | CSDN原题实际内容 |
|:-------------|:----------------|
| alloc/free 内存管理 | 目录空间统计（解析路径+计算子目录大小） |
| 多行LED命令 | 单串指令(L0L1D2T1)返回整数 |
| write/undo/redo 双栈 | 双向链表execute/undo/redo |
| n×n螺旋矩阵 | n个数m行螺旋+*占位 |
| create/delete 文件 | add_rule/mod_rule/del_rule 配置规则 |
| 相邻交换排序 | 最长非递增连续子数组 |
| IPv4/IPv6分类 | IPv4 A/B/C/D/E/R/L类 |
| 四则运算 | 多进制数+范围限制+十六进制取反 |

**必须从CSDN获取原题描述替换Day文件中的旧内容。**

### 方法2：从 complete-data.json 匹配

本地仓库 `/tmp/huawei-od-new-system/complete-data.json` 包含题目元数据（标题+分类），但不含CSDN链接。需要结合方法1获取。

### 方法3：直接搜索博主文章

```
https://blog.csdn.net/qq_45776114/category_12866903.html  # OD新系统真题分类
```

## 已知题目的CSDN链接（Day01已采集）

| 题目 | CSDN链接（banxia_frontend · 首选） |
|:----|:----------------------------------|
| 空间占用计算（新系统4.1） | https://blog.csdn.net/banxia_frontend/article/details/160384087 |
| 8位LED控制器（新系统4.19） | https://blog.csdn.net/banxia_frontend/article/details/160382843 |
| 操作历史管理器（新系统4.29） | https://blog.csdn.net/banxia_frontend/article/details/160995076 |
| 螺旋数字矩阵（双机位C卷） | https://blog.csdn.net/banxia_frontend/article/details/148458505 |
| 配置操作失败统计（新系统4.8） | https://blog.csdn.net/banxia_frontend/article/details/160382054 |
| 美观的灯笼排序（新系统5.10） | https://blog.csdn.net/banxia_frontend/article/details/161264779 |
| IP地址分类识别（新系统5.17） | https://blog.csdn.net/banxia_frontend/article/details/161235313 |
| 简单表达式运算（新系统5.24） | https://blog.csdn.net/banxia_frontend/article/details/161495339 |

## CSDN访问限制

- 服务器直接 curl 可以访问（需要 Windows UA，`--max-time 15`）
- 搜狗/百度搜索不可用（被拦截）
- 浏览器工具同样返回403
- 数据采集工具链优先级：先试 curl → 再试 Jina Reader → 最后浏览器
