---
name: github-pages-spa
title: GitHub Pages React SPA Deployment
description: Deploy React (Vite) single-page apps to GitHub Pages subdirectory with correct SPA routing, data loading, and CDN considerations.
---

# GitHub Pages React SPA Deployment

Deploy a Vite + React SPA to `https://<user>.github.io/<repo>/` (subdirectory). Covers routing, basename, data splitting, CDN cache, and the root-index-html trap.

## Triggers

- User says "deploy to GitHub Pages" or "页面部署到 GitHub Pages"
- User reports "page loads blank", "404 on sub-routes", "resources not found"
- Building a React app served from a subdirectory (not a custom domain)

## Workflow

### 1. Vite Configuration

```ts
// vite.config.ts
export default defineConfig({
  base: '/<repo-name>/',           // MUST match GitHub Pages subdirectory
  plugins: [react()],
})
```

### 2. React Router Basename

All `<BrowserRouter>` components MUST have `basename` matching the Vite `base`:

```tsx
<BrowserRouter basename="/<repo-name>">
```

Without this, React Router sees the full path `/repo-name/questions/` and none of the routes (`/`, `/questions/`) match → falls through to `path="*"`.

### 3. Trailing Slash Routes

GitHub Pages auto-redirects `/questions` → `/questions/` (adds trailing slash). React Router `path="/questions"` does **NOT** match `/questions/`. **Both** Route paths **and** nav-menu `onClick` targets must use trailing slashes:

```tsx
<Route path="/questions/" element={<QuestionList />} />
<Route path="/favorites/" element={<Favorites />} />
// nav onClick:
{ key: '/questions/', onClick: () => nav('/questions/') }
```

### 4. 404.html for SPA Fallback

GitHub Pages serves `404.html` for unrecognised paths. Copy the built `index.html` as `404.html` at the repository root so all routes boot the React app:

```bash
cp dist/index.html 404.html
```

### 5. Data File Splitting

GitHub Pages CDN is slow on large files (>500KB). A 1MB `data.json` can take >15s to download, triggering browser `AbortController` timeouts:

- **List/index data** (metadata only): ~15KB → fast
- **Individual item data**: loaded on-demand per route

Fetch URLs must use `import.meta.env.BASE_URL`:

```ts
const BASE = import.meta.env.BASE_URL;  // '/repo-name/'
fetch(BASE + 'index.json');
fetch(BASE + 'questions/' + pid + '.json');
```

### 6. React Hooks Rule: No Early Return Before Hooks

**Most common crash.** A component with:

```tsx
if (!data) return <Card loading />;   // EARLY RETURN — BAD
const filtered = useMemo(() => ...);  // hook runs only on 2nd render
```

Violates the Rules of Hooks: first render has N hooks, second has N+1 → React error #310.

**Fix**: Move all hook calls above the early return:

```tsx
function QuestionList() {
  const [data, setData] = useState(null);
  const filtered = useMemo(() => {
    if (!data) return [];             // safe: useMemo already called
    ...
  }, [data, ...]);
  if (!data) return <Card loading />; // OK — all hooks above
  return <div>...{filtered.map(...)}</div>;
}
```

### 7. The Root index.html Trap

The repo stores both **source** and **built artifacts** on master. The root `index.html` must serve two contradictory roles:

1. **During build**: Vite source template (`<script src="/src/main.tsx">`)
2. **At runtime on GitHub Pages**: built artifact (`<script src="/repo-name/assets/hash.js">`)

**Correct sequence**:

```bash
# 1. Restore Vite template temporarily
# 2. Build
npm run build
# 3. Overwrite with built version for deployment
cp dist/index.html index.html
cp dist/index.html 404.html
cp -r dist/questions .   # if using split data
cp dist/index.json .
```

## GitHub Actions deploy.yml

When using the modern "GitHub Actions" Pages mode, the workflow file needs two things that are easy to miss:

### 1. Environment Declaration

`actions/deploy-pages@v4` **requires** the job to declare `environment: name: github-pages` and the page URL. Without it you get `HttpError: Missing environment`:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run build
      - run: cp dist/index.html dist/404.html    # <--- SPA fallback
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 2. 404.html in the Workflow (not just manually)

Copying `index.html` → `404.html` must happen **before** `upload-pages-artifact` so the fallback is included in the deployment artifact:

```yaml
      - run: npm run build
      - run: cp dist/index.html dist/404.html     # <--- MUST be here, not as a separate manual step
      - uses: actions/upload-pages-artifact@v3
```

## Switching Pages Mode (Legacy → GitHub Actions)

If Pages is configured as `build_type: legacy` (serving from a branch), the `deploy-pages` action succeeds but the site URL never updates because it deploys to a different pipeline. Switch via API:

```bash
# Requires repo admin token
curl -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/<owner>/<repo>/pages \
  -d '{"build_type":"workflow","source":{"branch":"master","path":"/"}}'
```

Verify the switch:
```bash
curl -s -H "Authorization: token $TOKEN" \
  https://api.github.com/repos/<owner>/<repo>/pages \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['build_type'])"
# Should print: workflow
```

## Markdown Rendering with KaTeX Math

If the app uses `react-markdown` and the content has LaTeX math (`$...$`, `$$...$$`), you need two additional remark/rehype plugins:

```bash
npm install remark-math rehype-katex
# katex is already a transitive dep or installed alongside
```

Update the markdown component:

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

<ReactMarkdown
  remarkPlugins={[remarkGfm, remarkMath]}
  rehypePlugins={[rehypeKatex]}
>
  {content}
</ReactMarkdown>
```

### Vite manualChunks for KaTeX

To keep KaTeX fonts/styles in a separate chunk (avoid bloating the main bundle):

```ts
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks(id: string) {
        if (id.includes('node_modules/antd')) return 'antd';
        if (id.includes('node_modules/react-markdown')
          || id.includes('node_modules/remark-')
          || id.includes('node_modules/rehype-')
          || id.includes('node_modules/katex')) return 'markdown';
      }
    }
  }
}
```

### KaTeX CSS Import

Import the CSS in the component that uses KaTeX (Vite bundles it):
```tsx
import 'katex/dist/katex.min.css';
```

This produces ~50 KaTeX font files in `dist/assets/` — expected, they are lazy-loaded by KaTeX.

### KaTeX Background Color on Inline Math

After adding KaTeX, inline math (`$...$`) may render with a **gray/colored background** even though KaTeX itself outputs transparent elements. Root cause: the markdown renderer wraps inline math in `<code>` tags, and the site's CSS has a `code { background: #eee; }` or `.markdown-body code { background: #e8e8ee; }` rule.

**Fix**: Add CSS rules that target KaTeX elements specifically:

```css
/* Clear KaTeX formula background inherited from code styles */
.markdown-body .katex,
.markdown-body .katex-display,
.markdown-body .katex * {
  background: transparent !important;
}

/* If code wraps math, strip the code background */
.markdown-body code:has(.katex),
.markdown-body code:has(.katex-inline) {
  background: transparent !important;
  padding: 0 2px !important;
}
```

**Note**: `:has()` is supported in all modern browsers (Chrome 105+, Firefox 121+, Safari 15.4+). For broader compatibility, add a class to the `<code>` tag via the markdown renderer's `components` prop when wrapping math.

## Pitfalls

- **Basename mismatch**: Vite `base` and BrowserRouter `basename` must be identical.
- **CDN cache**: GitHub Pages caches aggressively (5-10 min). Append `?v=N` cache-buster to verify before CDN refresh.
- **404.html location**: Must be in the deployment artifact (within `dist/`), not just at the repo root.
- **Cross-origin error suppression**: `<script crossorigin>` without CORS headers hides JS errors. Use `window.onerror` or `window.addEventListener('error')` to capture minified React error numbers.
- **Minified React error #310**: "Rendered more hooks than during the previous render" — always a conditional hook call or early return before a hook.
- **index.html overwritten by build**: The repo root `index.html` must be the Vite template (`<script src="/src/main.tsx">`) before `npm run build`, or the build will fail with `Failed to resolve /assets/index-xxx.js`. After build, `dist/index.html` has the production version — do NOT overwrite the template with it unless you intend to rebuild.
- **deploy.yml failing silently**: Even when `deploy-pages@v4` succeeds, the site may still show old content if Pages is in Legacy mode (see "Switching Pages Mode" above). Check `conclusion=success` AND `build_type=workflow` in the Pages settings.

## Verification

1. `curl -sL https://<user>.github.io/<repo>/index.json` → 200
2. `curl -sL https://<user>.github.io/<repo>/404.html` → 200, same as index.html
3. Browser at `/<repo>/` → homepage renders
4. Browser at `/<repo>/questions/` → question list (not homepage)
5. Browser at `/<repo>/question/P14415` → question detail renders
6. Browser console → 0 JS errors

## Reference Files

- `references/debugging-crashes.md` — Debugging React crashes with suppressed error messages (cross-origin + crossorigin), React error number reference, and diagnostic checks
