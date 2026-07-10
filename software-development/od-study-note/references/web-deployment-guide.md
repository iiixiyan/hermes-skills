# 题库Web页面部署指南

> v2 — 2026-07-07 更新: 三Tab设计(题目描述/空白模板/题解), 完整数据字段, 5种语言代码切换, 块级Markdown渲染
> v1 — 2026-07-07 首次部署: 1208道题, GitHub Pages

---

## 仓库信息

| 项目 | 值 |
|:----|:----|
| GitHub仓库 | `https://github.com/iiixiyan/huawei-od-questions` |
| GitHub Pages | `https://iiixiyan.github.io/huawei-od-questions/` |
| 数据文件 | `complete-data.json`（1分类, 74道2026题, 19标签） |
| 前端页面 | `index.html`（单页应用, 三Tab, 无外部依赖） |
| 数据源 | GitCode `suijiong/od` → `华为OD_2026题库_完整版.json` |

## 完整数据格式（重要：含全部字段）

```python
{
  "2026年新系统题库（含题目详解）": [
    {
      "title": "省超足球比赛获胜队伍计算（100分）",  # 题目名（含分值）
      "topics": ["哈希表"],                           # 考点标签
      "pid": "P14415",                                # 题目唯一编号
      "difficulty": 4,                                # 难度 1-10
      "date": "2026年7月5日",                         # 考试日期
      "description_md": "# 题目内容\n...",             # ⭐ Markdown题目描述
      "has_signature": true,                          # 是否有函数签名
      "python_signature": "from typing import List...", # 函数签名
      "accept_rate": "14/122",                        # 通过率
      "code_templates": {                             # ⭐ 代码模板
        "py": "from typing import List\nclass Solution:...",
        "java": "class Solution { public void solve()...",
        "cc": "#include <bits/stdc++.h>...",
        "js": "// JavaScript空白模板...",
        "c": "#include <stdio.h>..."
      },
      "solution": "## 解题思路\n..."                  # ⭐ 题解（含多语言代码）
    }
  ]
}
```

### ⚠️ 合并数据时务必检查源数据的 ALL 字段

**教训**：初次只提取了 `title/topics/pid/difficulty/date/description_md`，遗漏了 `code_templates/solution/has_signature/python_signature/accept_rate`。用户指出后才补全。

**正确做法**：
```python
# 先 dump 源数据的所有字段
q = raw['题目列表'][0]
for k, v in q.items():
    print(f"  {k}: {type(v).__name__}")

# 提取全部字段
item = {
    "title": q['title'],
    "topics": q.get('tags', []),
    "pid": q['pid'],
    "difficulty": q['difficulty'],
    "date": q['date'],
    "description_md": q.get('description_md', ''),
    "has_signature": q.get('has_signature', False),
    "python_signature": q.get('python_signature', ''),
    "accept_rate": q.get('accept_rate', ''),
    "code_templates": q.get('code_templates', {}),
    "solution": q.get('solution', '')
}
```

## 数据获取：从 GitCode 克隆

源数据在 GitCode（不是 Gitee），有 WAF 防护，API 返回 418，只能用 git clone：

```bash
git clone https://oauth2:${GC_TOKEN}@gitcode.com/suijiong/od.git
```

Token 存储在 `~/.git-credentials`：
- `gitcode.com` → `4rHcGPiMQj6b6aGYxJNCMxfq`
- `github.com` → `github_pat_...`
- `gitee.com` → `f5b4e45ce364dd9dcac7e9c20c6423f7`

## 页面架构（三Tab设计）

| Tab | 数据源 | 渲染方式 | 场景 |
|:----|:-------|:---------|:-----|
| 📄 题目描述 | `description_md` | Markdown 块级渲染 | 读题 |
| 💻 空白模板 | `code_templates[lang]` | 代码块 + 复制按钮 | 自己先写 |
| 📖 题解 | `solution` | Markdown + 语言切换代码 | 对答案 |

### 语言键映射

```javascript
const LANG_KEYS = ['py', 'java', 'cc', 'js', 'c'];
const LANG_MAP = {
  'py': 'Python', 'java': 'Java', 'cc': 'C++',
  'js': 'JavaScript', 'c': 'C'
};
const SOL_LANG_MAP = {
  'python': 'py', 'java': 'java', 'cpp': 'cc',
  'javascript': 'js', 'c': 'c'
};
```

### 题解解析：分离 Markdown 描述 + 各语言代码

`solution` 是完整 Markdown，内含多个语言代码块：
```
## 解题思路
...
## 代码实现
```python
class Solution: ...
```
```java
class Solution { ...
```
```

解析方案：
```javascript
function parseSolution(sol) {
  var desc = sol, codes = {};
  var re = /```(\w+)\n?([\s\S]*?)```/g;
  var match;
  while ((match = re.exec(sol)) !== null) {
    var lang = match[1], code = match[2].trim();
    if (lang === 'python' || lang === 'py') codes['py'] = code;
    else if (lang === 'java') codes['java'] = code;
    else if (lang === 'cpp' || lang === 'cc') codes['cc'] = code;
    else if (lang === 'javascript' || lang === 'js') codes['js'] = code;
    else if (lang === 'c') codes['c'] = code;
  }
  desc = sol.replace(/```[\s\S]*?```/g, '').trim();
  return { desc, codes };
}
```

## Markdown 块级渲染（核心技巧）

**不要**用逐行 `<br>` 替换。必须按行类型分块输出 HTML 元素：

```javascript
function md2html(md) {
  var lines = md.split('\n'), out = '', i = 0;
  while (i < lines.length) {
    var l = lines[i];
    // 1. 代码块（最优先匹配）
    if (/^```/.test(l)) { /* collect to next ``` */ continue; }
    // 2. 标题
    var hm = l.match(/^(#{1,6})\s+(.+)/);
    if (hm) { out += '<h'+hm[1].length+'>'+hm[2]+'</h'+hm[1].length+'>'; i++; continue; }
    // 3. 分隔线
    if (/^---+$/.test(l)) { out += '<hr>'; i++; continue; }
    // 4. 引用
    if (/^>\s/.test(l)) { /* collect lines */ continue; }
    // 5. 空行 = 段落间隔
    if (/^\s*$/.test(l)) { out += '</p><p>'; i++; continue; }
    // 6. 无序列表
    var lm = l.match(/^[\s]*[-*]\s+(.+)/);
    if (lm) { /* collect until next item or blank */ continue; }
    // 7. 有序列表
    var om = l.match(/^\s*\d+\.\s+(.+)/);
    if (om) { out += '<ol><li>'+om[1]+'</li></ol>'; i++; continue; }
    // 8. 表格行
    if (/^\|/.test(l) && /\|$/.test(l)) { /* parse cells */ continue; }
    // 9. 普通文本
    out += l + '\n'; i++;
  }
  // 包裹段落 + 行内格式化
  out = '<p>' + out + '</p>';
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
  out = out.replace(/\n/g, '<br>');
  return out;
}
```

**错误的旧做法**（段落结构被破坏）：
```javascript
// ❌ 不要这样做
h = h.replace(/\n\n+/g, '<br><br>');
h = h.replace(/\n/g, '<br>');  // 所有换行变<br>, 页面全是割裂的文本
```

## GitHub API 推送（git push 超时替代方案）

当 `git push` 超时时，用 Contents API 直接 PUT 文件：

```python
import json, base64, urllib.request

def update_file(token, owner, repo, path, content, message):
    """创建或更新 GitHub 文件"""
    # 1. 获取当前 SHA
    sha = None
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}")
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            sha = json.loads(resp.read().decode()).get("sha")
    except: pass

    # 2. PUT 新内容
    data = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode()
    }
    if sha: data["sha"] = sha

    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
        data=json.dumps(data).encode(), method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())
```

**优缺点**：不受 git push 网络限制，但每次只更新一个文件，不保留批量 git 历史。

## 部署步骤

### 1. 创建仓库

```python
import urllib.request, json, os, re

with open(os.path.expanduser('~/.git-credentials')) as f:
    creds = f.read()
token = re.search(r'https://oauth2:([^@]+)@github\.com', creds).group(1)

req = urllib.request.Request(
    "https://api.github.com/user/repos",
    data=json.dumps({"name": REPO, "description": "...", "private": False}).encode(),
    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
    method="POST")
result = json.loads(urllib.request.urlopen(req, timeout=15).read())
```

### 2. 推送文件

```bash
git init && git add -A && git commit -m "init"
git remote add origin https://oauth2:$TOKEN@github.com/$OWNER/$REPO.git
git push -u origin master
```

### 3. 启用 GitHub Pages

```python
req = urllib.request.Request(
    f"https://api.github.com/repos/{owner}/{repo}",
    method="DELETE",
    headers={"Authorization": f"Bearer {token}"})
urllib.request.urlopen(req, timeout=15)  # HTTP 204
```

## Related

- `github-repo-management/references/react-data-viewer-pattern.md` — React/TypeScript/Vite/antd approach with routing, localStorage state, and GitHub Actions CI/CD (for richer interactivity than vanilla HTML)
- `github-repo-management/references/data-browser-page-pattern.md` — General single-page data browser pattern (tag filtering, modal overlay, year tabs)

### 4. 验证

```bash
curl -s -o /dev/null -w "HTTP %{http_code}" "https://$OWNER.github.io/$REPO/"
```

## 删除仓库

```python
req = urllib.request.Request(
    f"https://api.github.com/repos/{owner}/{repo}", method="DELETE",
    headers={"Authorization": f"Bearer {token}"})
urllib.request.urlopen(req, timeout=15)  # HTTP 204
```
