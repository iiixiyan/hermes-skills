---
name: static-spa-debugging
description: >-
  Diagnose and fix blank/crashing React or Vue SPAs deployed to static hosting
  (GitHub Pages, GitLab Pages, Cloudflare Pages, etc.). Covers the complete
  diagnostic pipeline: network tab → console errors → data structure matching →
  CDN cache invalidation — with platform-specific pitfalls for each host.
trigger:
  - blank page after SPA deploy
  - SPA shows loading state then goes blank
  - React app mounts then crashes silently
  - Vite/Vue/React build deployed but shows nothing
  - GitHub Pages 404 on assets
  - "页面一闪然后空白"
category: software-development
---

# Static SPA Deployment Debugging

## 1. Diagnostic Pipeline (always run these in order)

### 1.1 Resource Loading Check (Network Tab)
Check if JS/CSS/fetch requests return 200 or 404/5xx:

```js
// Run in browser console
performance.getEntriesByType('resource').map(r => ({
  name: r.name.split('/').pop(),
  type: r.initiatorType,
  status: r.responseStatus,
  size: r.transferSize
}))
```

**Common issues:**
- ❌ **404 on JS/CSS** → Vite `base` path mismatch (e.g. `base: '/'` but deployed to subdirectory `/repo-name/`)
- ❌ **JS returns HTML** → URL is being interpreted as a directory index — same root cause as above
- ❌ 的 **CORS error** → hosting platform doesn't serve `Access-Control-Allow-Origin`

### 1.2 Console Error Capture
SPA may crash before your error handler script runs. Use a pre-mounted error capture:

```js
// Run BEFORE page load (inject via browser_console expression)
window.__errors = [];
const origOnError = window.onerror;
window.onerror = (msg, url, line, col, err) => {
  window.__errors.push({ msg, url, line, col, stack: err?.stack });
  origOnError?.apply(window, arguments);
};
window.addEventListener('unhandledrejection', e => {
  window.__errors.push({ type: 'unhandledrejection', reason: e.reason?.stack || e.reason?.message || String(e.reason) });
});
```

**Then navigate**, wait, and check `window.__errors`.

▶️ 对于"先显示一下然后空白"的场景：**JS资源正常加载但后续数据/渲染报错导致React整棵树卸载**。

### 1.3 Data Structure Matching
The #1 subtle cause: **API/data.json format doesn't match frontend expectations**.

**Steps:**
1. Find the data URL in the JS bundle: search `data.json` or `fetch(` in bundled JS
2. Curl that URL to check actual structure
3. Compare against what the code reads (search for `.题目列表` or `.data` or `.items` in the JS)
4. If mismatch occurs, the fetch succeeds (200) but code hits `undefined.length` or `undefined.filter` → crash

**Fix:** Transform the data to match frontend expectations or update the frontend code.

```python
# Fix example: re-key data.json
import json
with open('data.json') as f:
    d = json.load(f)
# Find the actual question list key
for k, v in d.items():
    if isinstance(v, list) and len(v) > 0:
        questions = v
new_data = {"题目列表": questions}
with open('data_new.json', 'w') as f:
    json.dump(new_data, f, ensure_ascii=False)
```

### 1.4 Verify with Raw CDN-Bypass URL
GitHub Pages / GitLab Pages / Cloudflare Pages all have CDN caches (5-15 min).

**GitHub Pages bypass:**
```bash
# Use commit SHA to bypass master ref cache
COMMIT_SHA=$(git rev-parse HEAD)
curl -sL "https://raw.githubusercontent.com/<user>/<repo>/$COMMIT_SHA/data.json" | head -c 100
# Verify correct format before waiting for CDN
```

**Check if CDN has refreshed:**
```bash
# Compare Pages URL vs raw URL
curl -sL "https://<user>.github.io/<repo>/data.json" | head -c 100
```

### 1.5 Full Browser Validation
Once CDN refreshes (5-10 min), load in browser and verify:
1. Navigation renders (top bar, menu items)
2. Main content area shows data (not loading spinner)
3. Click through to question detail / favorites
4. Check console for any JS errors

## 2. Platform-Specific Pitfalls

### GitHub Pages
| Issue | Symptom | Fix |
|-------|---------|-----|
| Vite base path wrong | All JS/CSS return 404 | Set `base: '/<repo>/'` in vite.config.ts |
| Data JSON fetch timeout | Loading spinner forever | 1MB+ files may exceed CDN fetch timeout; reduce file size or increase timeout to 30s |
| CDN stale cache | Git push but old content served | Wait 5-10 min or use commit-SHA URL to verify |
| Branch-based deploy | gh-pages branch not found | Pages serves from master/default branch; push build artifacts to master |
| Git push auth | `Invalid username or token` | Use `oauth2:${GH_TOKEN}@github.com` in remote URL |

### Git Credential Reset (GitHub)
```bash
git remote set-url origin "https://oauth2:${GH_TOKEN}@github.com/<user>/<repo>.git"
```

## 3. Quick Reference: "页面一闪然后空白"诊查流程

```
1. 开浏览器 → 页面URL
2. console → performance.getEntriesByType('resource') → 看status
3. 如果有文件200但页面空 → 看console error
4. console error提到某变量undefined → 检查data.json格式vs代码读取路径
5. curl data.json查看实际格式
6. 脚本转换成前端需要的格式
7. git push到master分支
8. 等待5-10min CDN刷新
9. 刷新浏览器验证
```

## 4. CDN Cache Timeline

| Platform | Approx Cache TTL |
|----------|-----------------|
| GitHub Pages (`*.github.io`) | 5-10 min |
| raw.githubusercontent.com (branch ref) | 2-5 min |
| raw.githubusercontent.com (commit SHA) | No cache (fresh) |
| Cloudflare Pages | ~30 sec |
| GitLab Pages | ~5 min |

Use commit SHA URLs to verify pushes immediately without cache wait.

## 5. Related Tools
- `browser_console(expression)` — get JS output from browser
- `terminal()` with `curl` — verify file content and HTTP status
- `git remote set-url` — fix token auth before push
