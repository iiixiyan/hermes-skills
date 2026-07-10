---
name: codefun-scraper
description: |
  Scrape CodeFun2000 (Hydro OJ) problem sets — extract problem lists,
  descriptions, and code templates. Requires Chrome login session
  cookies for authenticated API access.
version: 1.1.0
platforms: [linux]
metadata:
  hermes:
    tags: [scraping, codefun2000, hydro-oj, problemset, hwod]
    category: data-science
---

# CodeFun2000 Problem Scraper

Scrape complete problem sets from CodeFun2000 (Hydro OJ platform), including
descriptions and blank code templates for all supported languages.

## Prerequisites

- Python packages: `browser-cookie3`, `requests`
- Install: `pip install --break-system-packages browser-cookie3 requests`
- One-time WeChat QR authentication (see Step 1 for methods)

## Workflow

### Step 1: Authenticate - Get Cookies (One-Time)

The site only supports WeChat QR code login. Choose one method:

#### Method A: Desktop Chrome (GUI available)

On a machine with Chrome + display, log in via QR code once. Then the
script's `browser-cookie3` approach extracts cookies automatically:

```python
import browser_cookie3, pickle, os

COOKIE_FILE = os.path.expanduser("~/.cache/cf_cookies.pkl")
cj = browser_cookie3.chrome(domain_name='codefun2000.com')
cookies = [{'name': c.name, 'value': c.value,
            'domain': c.domain, 'path': c.path} for c in cj]
with open(COOKIE_FILE, 'wb') as f:
    pickle.dump(cookies, f)
```

Transfer the resulting `cf_cookies.pkl` to the headless environment.

#### Method B: Hermes Browser + User Scans QR (no GUI)

Use Hermes browser tools to generate the WeChat QR code and send it as a
MEDIA attachment to the user, who scans it with their phone:

```
# 1. Navigate to the target problemset page
browser_navigate("https://codefun2000.com/problemset/hwod")

# 2. Click "登录查看题目列表" → opens login dialog
# 3. Click "WeChatLogin" → shows QR code image

# 4. Extract the QR code URL:
browser_get_images()
# → find the URL matching mp.weixin.qq.com/cgi-bin/showqrcode

# 5. Download and send to user:
curl -sL "QR_URL" -o /tmp/wechat_qr.png
# Send via MEDIA:/tmp/wechat_qr.png

# 6. User scans QR with phone WeChat
#    → Reload page; if "登录查看题目列表" is gone, auth worked
```

**Pitfall**: Browser session may lose auth on navigation. If the login
button reappears, generate a fresh QR code in the same browser context.

#### Method C: Pre-extracted Cookie File

Copy an existing pickle file directly:
```bash
cp /path/to/cf_cookies.pkl ~/.cache/cf_cookies.pkl
```

### Step 1.5: Reusable Cookie-based Session

Once cookies are available, use them for all API calls:

```python
import pickle, os, requests

COOKIE_FILE = os.path.expanduser("~/.cache/cf_cookies.pkl")

def get_session():
    session = requests.Session()
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'rb') as f:
            for c in pickle.load(f):
                session.cookies.set(c['name'], c['value'],
                                    domain=c['domain'], path=c['path'])
        return session
    raise FileNotFoundError(
        f"No cookie file at {COOKIE_FILE}. "
        "Run one-time auth first (Step 1).")
```

Cookies persist at `~/.cache/cf_cookies.pkl`. Delete this file to
force re-authentication. If cookies expire (API returns "Invalid
username or password"), re-authenticate via one of the methods above.

### Step 2: Get Problemset List

```
GET https://codefun2000.com/problemset/{pset_id}?format=json
```

Returns:
```json
{
  "ps": {"name": "...", "introduction": "...", "dagLength": N},
  "nodes": [{
    "id": N,
    "title": "日期",
    "problems": [{"pid": "P12345", "title": "...", "difficulty": N, "docId": N, "isDone": bool}]
  }]
}
```

Common pset IDs:
- `hwod` — 华为od最新题库(2026版)
- `hwod2025` — 华为od题库(2025版)
- `hw` — 华为校招机考题库
- Browse `/pset` page for others.

### Step 3: Get Problem Details

Two endpoints, prefer the API one:

```
GET https://codefun2000.com/api/problem?id={pid}
```

Returns:
- `content` — JSON string with `{"zh": "markdown description"}`
- `config` — `{"langs": [...], "timeMin": ..., "memoryMin": ...}`
- `tag` — algorithm tags array
- `difficulty` — 1–10 scale
- `nSubmit`, `nAccept` — submission stats

Also available:
```
GET https://codefun2000.com/p/{pid}?format=json
```
Returns page-level data including `rdoc` (user's last submission record).

### Step 3.5: Fetch Official Solutions

The page API includes `pdoc.textSol` — the official editorial with:
approach, complexity analysis, and **multi-language reference code**.

```python
r = session.get(f"https://codefun2000.com/p/{pid}?format=json", headers=headers)
pdoc = r.json().get('pdoc', {})
text_sol = pdoc.get('textSol', '')  # Markdown with #code-switcher markers
```

Solution format:
```
## 解题思路        ← approach & algorithm framework
## 复杂度分析      ← time/space complexity
## 代码实现        ← multi-language code blocks
#code-switcher
```python
class Solution:
    def method(self, ...):
        ...  ← complete reference implementation
```
```

Solutions are **not available via `/api/problem`** — only from the page endpoint.

### Step 4: Extract Code Templates

CodeFun2000 uses LeetCode-style "core code mode". Templates are NOT
available via API — extract from user's submission records or generate
generic stubs.

**If user has submitted the problem** (rdoc exists):
```python
rdoc = page_data.get('rdoc', {})
if rdoc and rdoc.get('code'):
    # Extract class + method signature from submitted code
    signature = extract_py_signature(rdoc['code'])
```

**Signature extraction** (Python):
```python
def extract_py_signature(code):
    lines = code.strip().split('\n')
    sig = []
    for line in lines:
        s = line.rstrip()
        if s.startswith('from ') or s.startswith('import '):
            sig.append(s)
        elif s.startswith('class '):
            sig.append(s)
        elif s.startswith('    def ') or s.startswith('\tdef '):
            last_colon = s.rfind(':')
            sig.append(s[:last_colon + 1])
            break
    return '\n'.join(sig) if sig else None
```

**If no rdoc**: generate generic template:
```python
template = "# 空白解题模板\n\nclass Solution:\n    def solve(self):\n        # Write your code here\n        pass\n"
```

### Step 5: Template Generation per Language

```python
def make_template(sig, lang):
    if lang in ('py.py3', 'py'):
        if sig: return sig + '\n        # Write your code here\n        pass\n'
        return "# 空白模板\nclass Solution:\n    def solve(self):\n        pass\n"
    elif lang == 'java':
        return "class Solution {\n    public void solve() {\n        // Write code\n    }\n}\n"
    elif lang.startswith('cc'):
        return "class Solution {\npublic:\n    void solve() {\n        // Write code\n    }\n};\n"
    elif lang == 'c':
        return "#include <stdio.h>\n\nint main() {\n    return 0;\n}\n"
    elif lang == 'js':
        return "// Write your solution here\n"
```

### Step 7: Rate Limiting

Add `time.sleep(0.15)` between API calls. 74 problems takes ~30 seconds
for descriptions, plus another ~40 seconds for solutions (~70s total).

### Step 8: Complete Batch Script

```python
import requests, json, time, pickle, os

COOKIE_FILE = os.path.expanduser("~/.cache/cf_cookies.pkl")

def get_session():
    session = requests.Session()
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'rb') as f:
            for c in pickle.load(f):
                session.cookies.set(c['name'], c['value'], domain=c['domain'], path=c['path'])
        return session
    raise FileNotFoundError(f"No cookie file at {COOKIE_FILE}. Authenticate first (Step 1).")

session = get_session()
headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# 1. Get problemset
pset_id = "hwod"  # change for other sets
r = session.get(f"https://codefun2000.com/problemset/{pset_id}?format=json", headers=headers)
pset_data = r.json()

all_problems = []
for node in pset_data['nodes']:
    for p in node['problems']:
        all_problems.append({
            'pid': p['pid'], 'title': p['title'],
            'date': node['title'], 'difficulty': p['difficulty']
        })

# 2. Fetch each problem
results = []
for p in all_problems:
    # Description + config
    r1 = session.get(f"https://codefun2000.com/api/problem?id={p['pid']}", headers=headers)
    detail = r1.json()
    desc = json.loads(detail['content']).get('zh', '')
    
    # Solution + template
    r2 = session.get(f"https://codefun2000.com/p/{p['pid']}?format=json", headers=headers)
    page = r2.json()
    pdoc = page.get('pdoc', {})
    solution = pdoc.get('textSol', '')
    rdoc = page.get('rdoc', {})
    
    # Extract signature if available
    sig = extract_py_signature(rdoc.get('code', '')) if rdoc else None
    
    results.append({
        **p,
        'description_md': desc,
        'solution': solution,
        'code_templates': {lang: make_template(sig, lang) for lang in detail['config']['langs']},
        'has_signature': sig is not None,
    })
    time.sleep(0.15)

# 3. Save
with open(f'{pset_id}_complete.json', 'w') as f:
    json.dump({'题库名称': pset_data['ps']['name'], '总题数': len(results),
               '有题解': sum(1 for r in results if r['solution']), '题目列表': results},
              f, ensure_ascii=False, indent=2)
```

### Step 9: Push to Git Repo

```bash
cd /tmp/od-skills && git pull origin master
cp output.json 华为OD_2026题库_完整版.json
git add . && git commit -m "Sync latest problems" && git push origin master
```

## Output Format

```json
{
  "题库名称": "...",
  "总题数": N,
  "题目列表": [{
    "pid": "P12345",
    "title": "题目标题",
    "date": "2026年7月5日",
    "difficulty": 4,
    "tags": ["哈希表"],
    "description_md": "# 题目内容\n...",
    "code_templates": {
      "py.py3": "from typing import List\n\nclass Solution:\n    def solve(self):\n        pass\n",
      "java": "...",
      "cc.cc14o2": "..."
    },
    "has_signature": false,
    "solution": "## 解题思路\n...\n## 复杂度分析\n...\n## 代码实现\n...",
    "accept_rate": "13/120"
  }]
}
```

## Pitfalls

1. **WeChat-only login** — No username/password, no API token. Use Method A (desktop Chrome) or Method B (Hermes browser + user scans QR) from Step 1.
2. **Cookies expire** — "Invalid username or password" means re-auth needed. Delete `~/.cache/cf_cookies.pkl` and re-run Step 1.
3. **API requires authentication** — cookies must be from an active session
4. **Chrome cookies are encrypted** — `browser-cookie3` handles this but needs
   the system keyring daemon running (only needed for Method A)
5. **No direct template API** — CodeFun2000/Hydro generates templates client-side.
   Only problems with user submissions (rdoc) can extract exact signatures.
6. **CloudWAF blocks programmatic access** — use browser cookies, not direct API tokens
7. **`?format=json` suffix** — Hydro's magic parameter for JSON output on page endpoints
8. **`/api/problem/list` requires auth** — returns "Invalid username or password" without
   proper session cookies; use `?format=json` on page endpoints instead
9. **Compound CSS selectors fail on Linux** — AT-SPI doesn't support them in cua-driver's
   `page` tool; use `execute_javascript` or direct API calls instead
10. **PEP 668** — use `pip install --break-system-packages` on Debian/Ubuntu
11. **Solutions require page API** — `textSol` is only in `/p/{pid}?format=json`,\
    NOT in `/api/problem?id={pid}`. Need a second API call per problem.
12. **`#code-switcher` markers** — solutions use this custom marker (not standard
    markdown) to separate language tabs in code blocks.

## Verification

```bash
python3 -c "
import json
with open('output.json') as f:
    data = json.load(f)
print(f'Problems: {data[\"总题数\"]}')
print(f'With signatures: {sum(1 for p in data[\"题目列表\"] if p[\"has_signature\"])}')
print(f'Sample: {data[\"题目列表\"][0][\"title\"]}')
"
```
