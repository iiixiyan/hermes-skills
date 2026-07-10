# Single-Page Data Browser (from static JSON)

Reusable pattern: an HTML page that loads a JSON dataset and provides **full-text search**, **tag filtering**, **category grouping**, **detail modal overlay**, **year/source tabs**, and **stats** — all client-side, no build step, zero dependencies.

## Architecture

```
repo/
├── complete-data.json   # The dataset (load at runtime)
└── index.html           # Self-contained browser page, no build
```

**Data flow:** `index.html` fetches `complete-data.json` from a raw GitHub URL → builds search index + tag index → renders via vanilla JS → hosted on GitHub Pages.

## Key Features

| Feature | Implementation |
|---------|---------------|
| Load JSON | `fetch(DATA_URL)` → `await resp.json()` |
| Text search | `p.title.toLowerCase().includes(query)` with highlight |
| Tag filter | Build `allTags{}` with count, click toggles `activeTag` |
| Category group | Group by top-level key, collapsible header |
| **Detail modal** | Full-screen overlay: title, meta, full Markdown body |
| **Year tabs** | Filter by year category (2025/2026) |
| Stats bar | Total / Categories / Tags / Filtered count |
| Markdown desc | Full MD→HTML: tables, code blocks, images, links, lists, headings |

---

## 1. Data Loading & Initialization

```javascript
const DATA_URL = 'https://raw.githubusercontent.com/owner/repo/main/data.json';
let allData = {};

async function init() {
  const resp = await fetch(DATA_URL);
  allData = await resp.json();
  buildTags();
  render();
}
```

---

## 2. Tag Index Building

```javascript
function buildTags() {
  allTags = {};
  for (const [cat, items] of Object.entries(allData)) {
    for (const item of items) {
      const tags = Array.isArray(item.topics) ? item.topics : [];
      for (const t of tags) {
        if (t) allTags[t] = (allTags[t] || 0) + 1;
      }
    }
  }
}
```

---

## 3. Tag Filtering Pattern

```javascript
let activeTag = '';

function toggleTag(tag) {
  activeTag = (activeTag === tag) ? '' : tag;
  render();
}

// Inside render()
const filtered = items.filter(p => {
  const matchTitle = !query || p.title.toLowerCase().includes(query);
  const tags = Array.isArray(p.topics) ? p.topics : [];
  const matchTag = !activeTag || tags.includes(activeTag);
  return matchTitle && matchTag;
});
```

---

## 4. Modal Detail Overlay (replaces inline expand)

Full-screen overlay with a centered card. Render full markdown body inside.

```html
<!-- Modal HTML structure -->
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal-card">
    <div class="modal-header">
      <div class="info">
        <div class="mtitle" id="modalTitle"></div>
        <div class="msub" id="modalSub"></div>
      </div>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>
```

```javascript
function openModal(p, cat) {
  // Set title, meta (difficulty, date, PID, tags, year badge)
  // Render body: mdToHtml(p.description_md) or "暂无详解" fallback
  document.getElementById('modal').classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('modal').classList.remove('show');
  document.body.style.overflow = '';
}

// Escape key close
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
```

### CSS for modal

```css
.modal-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,.5); z-index: 1000;
  justify-content: center; align-items: flex-start;
  padding: 30px 20px; overflow-y: auto;
}
.modal-overlay.show { display: flex; }
.modal-card {
  background: #fff; border-radius: 12px; max-width: 860px;
  width: 100%; margin: auto; max-height: 90vh;
  display: flex; flex-direction: column;
  box-shadow: 0 8px 32px rgba(0,0,0,.2);
}
.modal-header { display: flex; justify-content: space-between;
  padding: 18px 22px 14px; border-bottom: 1px solid #f0f0f0; }
.modal-body { padding: 20px 22px; overflow-y: auto; flex: 1;
  font-size: 14px; line-height: 1.7; }
.modal-close { width: 32px; height: 32px; border-radius: 50%;
  border: none; background: #f5f5f5; font-size: 18px;
  cursor: pointer; display: flex; align-items: center;
  justify-content: center; }
```

---

## 5. Year / Source Filter Tabs

Group categories by year (e.g. 2025 vs 2026) and show tabs to toggle.

```javascript
// Determine year from category name
function getYear(cat) {
  return cat.includes('2026') ? '2026' : '2025';
}

// Build year tabs with counts
function buildYearTabs() {
  // Count items per year
  let c2026 = 0, c2025 = 0;
  for (const [cat, items] of Object.entries(allData)) {
    if (getYear(cat) === '2026') c2026 += items.length;
    else c2025 += items.length;
  }
  // Render 3 tabs: 全部 / 2026 / 2025
  // Each tab calls setYear(year) on click
}

// Filter in render()
for (const [cat, items] of Object.entries(allData)) {
  if (yearFilter !== 'all' && yearFilter !== getYear(cat)) continue;
  // ... render category
}

// Year badge on each category header + each question item
const yearTagClass = year === '2026' ? 'y2026' : 'y2025';
html += `<span class="year-badge ${yearTagClass}">${year}</span>`;
```

### Year tag CSS

```css
.year-badge.y2026 { background: #e8f5e9; color: #2e7d32; }
.year-badge.y2025 { background: #e3f2fd; color: #1565c0; }
```

---

## 6. Full Markdown to HTML (zero dependencies)

Complete rendering engine handling all common Markdown constructs. Process in this order to avoid conflicts:

```javascript
function mdToHtml(md) {
  if (!md || !md.trim()) return '';
  let h = md;
  // 1. Escape HTML tags
  h = h.replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // 2. Code blocks (triple backtick) — process before escaping inside
  h = h.replace(/```(\w*)\n?([\s\S]*?)```/g, function(m, lang, code) {
    code = code.replace(/&lt;/g, '<').replace(/&gt;/g, '>');
    const langAttr = lang ? ` class="lang-${lang}"` : '';
    return `<pre><code${langAttr}>${htmlEscape(code.trim())}</code></pre>`;
  });

  // 3. Inline code
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 4. Images ![alt](url)
  h = h.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" loading="lazy">');

  // 5. Links [text](url)
  h = h.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

  // 6. Bold **text** and Italic *text*
  h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  h = h.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // 7. Headings h1-h6
  h = h.replace(/^######\s+(.+)$/gm, '<h6>$1</h6>');
  h = h.replace(/^#####\s+(.+)$/gm, '<h5>$1</h5>');
  h = h.replace(/^####\s+(.+)$/gm, '<h4>$1</h4>');
  h = h.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
  h = h.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
  h = h.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');

  // 8. Horizontal rules
  h = h.replace(/^---+\s*$/gm, '<hr>');
  h = h.replace(/^\*\*\*+\s*$/gm, '<hr>');

  // 9. Blockquotes
  h = h.replace(/^>\s+(.+)$/gm, '<blockquote>$1</blockquote>');

  // 10. Unordered/ordered lists — simplified approach
  // Wrap consecutive <li> in <ul>/<ol>
  h = h.replace(/^[\*\-]\s+(.+)$/gm, '<li>$1</li>');
  h = h.replace(/(<li>.*<\/li>\n?)+/g, m => '<ul>' + m + '</ul>');

  // 11. Pipe tables (basic)
  h = h.replace(/^\|(.+)\|$/gm, (m, row) => {
    const cells = row.split('|').map(c => c.trim()).filter(c => c);
    if (/^[\s:-]+$/.test(cells.join(''))) return ''; // skip separator row
    return '<tr><td>' + cells.join('</td><td>') + '</td></tr>';
  });
  h = h.replace(/((?:<tr>.*<\/tr>\n?)+)/g, '<table>$1</table>');

  // 12. Paragraph wrapping (crude but works for structured content)
  h = h.replace(/\n\n+/g, '</p><p>');
  h = '<p>' + h + '</p>';
  // Clean: move block-level elements out of <p>
  h = h.replace(/<p>((<h[1-6]>|<pre>|<blockquote>|<table>|<ul>))/g, '$1');
  h = h.replace(/(<\/(h[1-6]|pre|blockquote|table|ul)>|\/>)<\/p>/g, '$1');

  return h;
}
```

**Ordering matters:** code blocks before inline code, HR before lists, tables before paragraph wrapping.

---

## 7. Stats Bar Pattern

```html
<div class="stats">
  <div class="stat-card"><div class="num">${total}</div><div class="label">总题数</div></div>
  <div class="stat-card green"><div class="num">${c2026}</div><div class="label">2026</div></div>
  <div class="stat-card blue"><div class="num">${c2025}</div><div class="label">2025</div></div>
  <div class="stat-card"><div class="num">${tags}</div><div class="label">考点标签</div></div>
</div>
```

---

## 8. Multi-Source JSON Merging

When datasets come from different sources with different schemas, merge them before building the page.

```python
import json

# Source A: {title, topics} format
with open('source_a.json') as f:
    data_a = json.load(f)  # dict with category keys

# Source B: {pid, title, date, difficulty, tags, description_md} format
with open('source_b.json') as f:
    raw_b = json.load(f)
    questions_b = raw_b['题目列表']

# Normalize to common format
new_category = "题库名称（2026新版）"
data_a[new_category] = [{
    "title": q['title'],
    "topics": q.get('tags', []),
    "pid": q.get('pid'),
    "difficulty": q.get('difficulty'),
    "date": q.get('date'),
    "description_md": q.get('description_md', '')
} for q in questions_b]

json.dump(data_a, open('merged.json','w'), ensure_ascii=False, indent=2)
```

### Deduplication between sources

When sources overlap, normalize titles for comparison:

```python
import re
def clean_title(t):
    t = re.sub(r'^华为OD(机试|机考).*?[-—]\s*', '', t)  # Remove prefixes
    t = re.sub(r'\s*[（(]\d+分[)）]\s*', '', t)           # Remove score suffix
    t = re.sub(r'\s+', '', t)
    return t.lower()

old_titles = {clean_title(q['title']): q for q in source_a}
new_titles = {clean_title(q['title']): q for q in source_b}
overlap = set(old_titles) & set(new_titles)
unique_old = set(old_titles) - set(new_titles)
unique_new = set(new_titles) - set(old_titles)
```

Then merge: keep new descriptions for overlapping items, add unique old items as well.

---

## 9. GitHub Push Fallback via Contents API

When `git push` over HTTPS times out (stalls at `Trying 20.205.243.166:443...`) but `curl api.github.com` works, push individual files via the GitHub Contents API:

```python
import json, base64, urllib.request

TOKEN="ghp_..."  # GitHub PAT
OWNER, REPO = "owner", "repo"

def get_sha(path):
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}")
        req.add_header("Authorization", f"Bearer {TOKEN}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()).get("sha")
    except: return None

def push_file(path, content, msg):
    sha = get_sha(path)
    data = {"message": msg, "content": base64.b64encode(content.encode()).decode()}
    if sha: data["sha"] = sha
    req = urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}",
                                 data=json.dumps(data).encode(), method="PUT")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30):
        pass
    print(f"  {path}: pushed OK")

push_file("index.html", html_content, "Update page")
push_file("data.json", json_content, "Update data")
```

Limitations: individual files only (≤ 1 MB each). See `github-repo-management` SKILL.md §Pitfalls for details.

---

## When to use this pattern

- You have a JSON dataset you want users to browse/search/filter
- You don't want a backend or build step
- You're hosting on GitHub Pages, Netlify, or any static host
- Dataset < 10MB (GitHub raw has no hard limit but large files slow initial load)

## When NOT to use

- Real-time / dynamic data (needs a backend)
- Dataset > 10MB or highly nested (will freeze browser on load)
- Need authentication or user-specific views
- Already have a SPA framework (React/Vue) — use existing infra instead

## Variants

- **Multiple datasets**: fetch multiple JSON URLs, merge client-side
- **Deep links**: encode search/filter state in URL hash `#q=search&tag=filter`
- **Pagination**: add scroll-based virtual list for >5000 items
- **Sorting**: add sort buttons (by name, date, difficulty)
- **Caching**: `localStorage` cache of fetched JSON to avoid re-download
- **React SPA**: for routing, state management, and CI/CD builds, see `references/react-data-viewer-pattern.md`

---

## 10. Coding Question Bank Variant (Three-Tab Pattern)

For programming question banks (like Huawei OD, LeetCode variants), extend the modal pattern with **three tabs** inside the detail view. Each question has three data sections: description, code template, and solution.

### Data model

Each question in the JSON should include:

```json
{
  "title": "最小极差分组(100分)",
  "pid": "P14409",
  "difficulty": 5,
  "date": "2026年6月28日",
  "topics": ["贪心算法"],
  "description_md": "# 题目内容...",
  "code_templates": {
    "py": "from typing import List\nclass Solution:\n    def method(self, arg):\n        pass",
    "java": "class Solution { public void solve() { } }",
    "cc": "class Solution { public: void solve() {} };",
    "js": "var method = function() { };",
    "c": "#include <stdio.h>\nint main() { return 0; }"
  },
  "solution": "## 解题思路\n...\n```python\ncode here\n```\n```java\ncode here\n```",
  "has_signature": true,
  "accept_rate": "14/122"
}
```

**⚠️ KEY PITFALL — Check ALL source fields during merge**

When merging data from a foreign format (e.g. GitCode JSON → your schema), dump the **first item's full structure** before writing extraction code. It's easy to miss fields like `code_templates`, `solution`, `has_signature` that live alongside the obvious `title`/`description_md`.

```python
# WRONG — only extracts obvious fields, misses templates & solutions
new = [{"title": q["title"], "description_md": q.get("description_md", "")}]

# RIGHT — dump first item to see ALL fields before mapping
json.dumps(source["题目列表"][0], ensure_ascii=False, indent=2)
# Then check what you missed
all_keys = set()
for q in source["题目列表"]:
    all_keys.update(q.keys())
print(f"All available fields: {all_keys}")
```

### Three-tab HTML structure

```html
<!-- In the detail view, below the question header -->
<div class="tab-bar">
  <div class="tab act" data-tab="desc" onclick="switchTab('desc')">📄 题目描述</div>
  <div class="tab" data-tab="template" onclick="switchTab('template')">💻 空白模板</div>
  <div class="tab" data-tab="solution" onclick="switchTab('solution')">📖 题解</div>
</div>
<div class="tab-content show" id="tabDesc"><!-- Markdown-rendered description --></div>
<div class="tab-content" id="tabTemplate"><!-- Code template with language tabs --></div>
<div class="tab-content" id="tabSolution"><!-- Solution with lang switching --></div>
```

### Tab 2: Code template with language switching

```javascript
// Language key mapping
const LANG_MAP = {
  'py': 'Python', 'java': 'Java', 'cc': 'C++', 'js': 'JavaScript', 'c': 'C'
};
const LANG_KEYS = ['py', 'java', 'cc', 'js', 'c'];
let curLang = 'py';

function renderTemplate(p) {
  const ct = p.code_templates || {};
  // Render language buttons
  let h = '<div class="lang-bar">';
  for (const k of LANG_KEYS) {
    const hasCode = ct[k];
    h += `<button class="lang-btn${curLang===k?' act':''}${hasCode?'':' disabled" style="opacity:.4"'}">${LANG_MAP[k]}</button>`;
  }
  h += '</div>';
  // Render code block with copy button
  const code = ct[curLang] || '// No template for this language';
  h += `<div class="code-block">${esc(code)}`;
  h += `<button class="copy-btn" onclick="copyText('${esc(code)}')">📋 复制</button></div>`;
}
```

### Tab 3: Solution with extracted code blocks

The solution markdown field contains both prose and multi-language code blocks. Parse them separately:

```javascript
function parseSolution(sol) {
  if (!sol) return { desc: '', codes: {} };
  let codes = {};
  // Extract code blocks by language tag
  const re = /```(\w+)\n?([\s\S]*?)```/g;
  let match;
  while ((match = re.exec(sol)) !== null) {
    const lang = match[1], code = match[2].trim();
    if (lang === 'python' || lang === 'py') codes['py'] = code;
    else if (lang === 'java') codes['java'] = code;
    else if (lang === 'cpp' || lang === 'cc') codes['cc'] = code;
    else if (lang === 'javascript' || lang === 'js') codes['js'] = code;
    else if (lang === 'c') codes['c'] = code;
  }
  // Remove all code blocks from description
  const desc = sol.replace(/```[\s\S]*?```/g, '')
                  .replace(/#code-switcher.*/g, '')
                  .replace(/#hot100-card[\s\S]*/g, '').trim();
  return { desc, codes };
}
```

Then render: markdown-converted description first, then language selector + code block for reference code.

### Question header metadata

Show all available fields in a compact meta bar:

```html
<div class="qmeta">
  ★★★★☆ 5/10           <!-- difficulty stars -->
  📅 2026年6月28日       <!-- date -->
  ✅ 含函数签名           <!-- has_signature flag -->
  ✅ 通过率 14/122       <!-- accept_rate -->
  🏷 贪心算法 哈希表     <!-- topics/tags -->
</div>
```

### CSS for code blocks (dark theme)

```css
.code-block {
  background: #1e1e1e; color: #d4d4d4;
  padding: 14px 16px; border-radius: 8px;
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 13px; line-height: 1.6;
  overflow-x: auto; position: relative;
  white-space: pre;
}
.code-block .copy-btn {
  position: absolute; top: 8px; right: 8px;
  padding: 3px 10px; border-radius: 4px;
  background: rgba(255,255,255,.1); color: #aaa;
  border: 1px solid rgba(255,255,255,.15);
  cursor: pointer; font-size: 11px;
}
.code-block .copy-btn:hover {
  background: rgba(255,255,255,.2); color: #fff;
}
```

### Keyboard navigation in detail view

```javascript
document.addEventListener('keydown', function(e) {
  if (detailViewVisible) {
    if (e.key === 'ArrowLeft') navQ(-1);
    if (e.key === 'ArrowRight') navQ(1);
    if (e.key === 'Escape') showList();
  }
});
```

---

## 11. Token Extraction from git-credentials

When automating GitHub API operations (creating repos, pushing files, enabling Pages), extract tokens from the credential store rather than requiring the user to re-enter them:

```python
import re, os

with open(os.path.expanduser('~/.git-credentials')) as f:
    creds = f.read()

# GitHub token
gh_token = re.search(r'https://oauth2:([^@]+)@github\.com', creds).group(1)
# GitCode token
gc_token = re.search(r'https://oauth2:([^@]+)@gitcode\.com', creds).group(1)
# Gitee token
gitee_token = re.search(r'https://oauth2:([^@]+)@gitee\.com', creds).group(1)
```

**Format of ~/.git-credentials:**
```
https://oauth2:TOKEN@github.com
https://oauth2:TOKEN@gitcode.com
https://oauth2:TOKEN@gitee.com
```

**⚠️ Pitfall:** The token extraction via `re.search(...).group(1)` requires the credential URL to have the exact format `https://oauth2:TOKEN@domain.com`. If the format differs (e.g. `https://user:TOKEN@domain.com`), adjust the regex.

Also note: `$()` in Bash heredoc context (`cat << 'PYEOF' ... PYEOF`) will be interpreted as command substitution. Use `sys.argv` to pass tokens into Python scripts instead, or write the Python script to a file first (via `write_file`), then call it with `python3 script.py "$TOKEN"`.

### Passing tokens to scripts

**Bad** (Bash interprets $() inside heredoc):
```bash
cat > /tmp/script.py << 'PYEOF'
TOKEN=$(...)  # This fails — bash tries to run $(...)
PYEOF
```

**Good** (pass via sys.argv):
```python
# /tmp/script.py
import sys
TOKEN = sys.argv[1]
```

```bash
TOKEN=$(git ...)  # Extract in bash
python3 /tmp/script.py "$TOKEN"  # Pass to script
```
