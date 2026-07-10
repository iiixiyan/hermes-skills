---
name: github-pages-deploy
category: devops
description: Deploy React/Vue/static SPAs to GitHub Pages with Vite, SPA routing, Actions CI/CD, and KaTeX math rendering.
---

# GitHub Pages SPA Deployment

## When to use

When deploying a frontend SPA (React, Vue, vanilla Vite) to GitHub Pages at a **sub-path** (e.g. `username.github.io/repo-name/`). Covers:

- Vite `base` path configuration
- React Router `basename` setup
- SPA 404 fallback (`404.html`)
- GitHub Actions CI/CD (`deploy.yml`)
- KaTeX math rendering integration
- Switching Pages between Legacy and Actions mode

## Environment defaults

| Setting | Value |
|---|---|
| Sub-path | `/repo-name/` |
| Build tool | Vite |
| Router | React Router v6/v7 |
| Auth | GitHub OAuth token (from `~/.git-credentials`) |

## Step-by-step

### 1. Vite base path

In `vite.config.ts`:

```ts
export default defineConfig({
  base: '/repo-name/',
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('node_modules/antd')) return 'antd';
          if (id.includes('node_modules/react-markdown') || id.includes('node_modules/remark-') || id.includes('node_modules/rehype-') || id.includes('node_modules/katex')) return 'markdown';
        }
      }
    },
    chunkSizeWarningLimit: 1000,
  },
});
```

**Critical**: all `fetch` URLs in components must use `import.meta.env.BASE_URL` — never hardcode paths.

### 2. React Router basename

In `src/main.tsx` or `App.tsx`:

```tsx
<BrowserRouter basename="/repo-name/">
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/questions/" element={<QuestionList />} />
    <Route path="/question/:pid" element={<QuestionDetail />} />
    <Route path="*" element={<Home />} />
  </Routes>
</BrowserRouter>
```

### 3. SPA 404 fallback

GitHub Pages doesn't natively support SPA routing. Add in `deploy.yml`:

```yaml
- run: cp dist/index.html dist/404.html
```

### 4. GitHub Actions deploy.yml

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [master]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - run: cp dist/index.html dist/404.html
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist
      - id: deployment
        uses: actions/deploy-pages@v4
```

**Pitfall**: The `build` job MUST have `environment: name: github-pages`. Without it, `deploy-pages` fails with "Missing environment".

### 5. Pages mode: Legacy → GitHub Actions

Use the API to switch (requires repo admin token):

```
PUT /repos/{owner}/{repo}/pages
{"build_type": "workflow", "source": {"branch": "master", "path": "/"}}
```

Or the user can go to Settings → Pages → Source → "GitHub Actions".

### 6. index.html must be clean

GitHub Pages serves from master's root. The `index.html` file in the repo **must** be the Vite dev template, NOT a previous build's artifact with hardcoded hashes:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>App Title</title>
</head>
<body>
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

Vite injects production hashes during `npm run build`. If a stale build artifact's `<script>`/`<link>` tags are present in `index.html`, Vite will fail to build.

### 7. CDN cache

After deploying, GitHub Pages CDN (Fastly) can take 1–10 minutes to refresh. Use a query parameter (`?t=N`) to force-bypass cache in the browser.

## Pitfalls

- **React hooks rule violation**: A loading-state guard (`if (!data) return <Loading />`) BEFORE `useMemo` causes "Rendered fewer hooks than expected". Move loading checks AFTER all hooks.
- **Route path mismatch**: Be consistent with trailing slashes. If list page is `/questions/` (trailing), don't link detail as `/questions/:pid`. Use `/question/:pid`.
- **index.html overwritten**: Never `cp dist/* .` in the repo root — it overwrites the Vite template. Use a separate deploy branch or Actions workflow.
- **gh-pages branch vs Actions mode**: These are mutually exclusive. If Pages is in Legacy mode, Actions deployments to the `github-pages` environment don't affect the live URL. Switch to Actions mode.
- **Git push to GitHub over HTTPS can timeout** in certain network environments. Fall back to GitHub API commits (create blob → tree → commit → update ref).
- **KaTeX block math `$$...$$` loses background color**: `remark-math` + `rehype-katex` renders block math as `<pre><code class="language-math math-display">`. If your markdown CSS has `.markdown-body pre code { background: 0 0; }` (common pattern to let code blocks use their own background), block formulas lose their background while inline `$...$` math still has it. Fix: add CSS rule targeting only math-display elements, placed AFTER the generic code rule. KaTeX's own `katex.min.css` does NOT add background — it inherits from parent `<code>`, which is why pre code override breaks display math differently from inline math.

## Related

- See `references/react-github-pages-setup.md` for a full walkthrough with data file splitting and KaTeX rendering integration.
- See `references/katex-math-formula-background.md` for KaTeX formula background styling (block vs inline math CSS inheritance differences).
