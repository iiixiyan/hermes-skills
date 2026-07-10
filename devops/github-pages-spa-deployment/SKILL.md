---
name: github-pages-spa-deployment
description: Deploy React SPAs to GitHub Pages with correct Vite base path, SPA routing, and data loading strategy. Covers blank-page debugging, trailing slash routing, and large data file handling.
---

# GitHub Pages SPA Deployment

Deploying a React (Vite) SPA to GitHub Pages has several critical configuration points that must all be correct. This skill covers the full lifecycle: build config → data strategy → SPA routing → debugging.

## Trigger

Use this skill when:
- Deploying a **Vite/React SPA** to **GitHub Pages** (subdirectory `https://<user>.github.io/<repo>/`)
- Debugging a **blank page** or **404** on GitHub Pages
- Setting up **SPA routing** (React Router) on GitHub Pages
- The user's site is served from `<username>.github.io/<repo>/` (not a custom domain)

## Critical Configuration Points

### 1. Vite Base Path

Set `base` in `vite.config.ts` to the subdirectory path:

```ts
export default defineConfig({
  base: '/<repo-name>/',  // <--- CRITICAL: must match GitHub pages subdirectory
  plugins: [react()],
})
```

**Why**: GitHub Pages serves the site at `https://<user>.github.io/<repo>/`. With `base: '/'`, the generated `<script src="/assets/index-xxx.js">` points to the wrong absolute path (`https://<user>.github.io/assets/...` → 404).

**Verify**: After build, `dist/index.html` must have:
```html
<script type="module" crossorigin src="/<repo-name>/assets/index-xxx.js"></script>
```

### 2. SPA Routing (React Router)

GitHub Pages has no client-side routing support. Two fixes needed:

**a. Copy index.html as 404.html**
```bash
cp dist/index.html dist/404.html
```
GitHub Pages serves `404.html` for all unmatched routes, which lets the React app bootstrap and handle routing client-side.

**b. Handle trailing slashes in routes**
GitHub Pages automatically redirects `/questions` → `/questions/` (adds trailing slash). React Router's `path="/questions"` does NOT match `/questions/`. Fix: use trailing slash in route paths:

```tsx
<Route path="/questions/" element={<QuestionList />} />
<Route path="/favorites/" element={<Favorites />} />
<Route path="/question/:pid" element={<QuestionDetail />} />
<Route path="*" element={<HomePage />} />
```

### 3. Data URL Strategy (AJAX/fetch)

GitHub Pages CDN is slow for large files. 1MB+ files may timeout (especially with 15s AbortController limits).

**DO NOT** hardcode data URLs (e.g., `'/data.json'`). Use `import.meta.env.BASE_URL`:

```ts
const BASE = import.meta.env.BASE_URL;
const DATA_URL = BASE + 'index.json';  // resolves to /repo-name/index.json
```

**Strategy for large datasets** (>200KB):
- Split into: `index.json` (metadata only, small) + `questions/{pid}.json` (per-item)
- Homepage/list pages fetch `index.json` (fast, <50KB)
- Detail pages fetch per-item `{id}.json` on-demand
- This avoids the 15s+ timeout on large single-file downloads via GitHub Pages CDN

### 4. Public Directory Structure

Files in `public/` get copied to `dist/` at build time. Place data files here:

```
public/
  index.json          ← metadata (small, loaded by list/home pages)
  questions/
    P12345.json       ← per-item detail files
```

## Debugging: "Page flashes then goes blank"

This is the most common GitHub Pages SPA failure mode. Root cause chain:

1. **React mounts successfully** → antd/layout renders briefly → (user sees layout for a split second)
2. **JS runtime error** → React error boundary (implicit) catches → **whole component tree unmounts** → blank page
3. The runtime error is almost always a **data structure mismatch**

### Step-by-step debugging:

1. **Browser console** (MOST IMPORTANT):
   ```js
   // Check for uncaught errors
   performance.getEntriesByType('resource')
   // Check if data.json loaded
   document.getElementById('root')?.innerHTML
   ```

2. **Network tab**: Verify ALL resources return 200:
   - `index.html`
   - `assets/index-xxx.js`
   - `assets/index-xxx.css`
   - Data files (`index.json`, etc.)
   - **Check the URL pattern** — if JS/CSS URLs start with `/assets/` instead of `/repo-name/assets/`, the base path is wrong

3. **Check data.json format**:
   ```bash
   curl -sL "https://raw.githubusercontent.com/<user>/<repo>/master/data.json" | head -c 200
   ```
   Verify top-level keys match what the React code expects (e.g., `题目列表` vs `2026年新系统题库`)

4. **CDN cache**: GitHub Pages CDN caches aggressively (5-15 min). Use commit SHA URLs to bypass:
   ```
   https://raw.githubusercontent.com/<user>/<repo>/<commit-sha>/data.json
   ```

5. **File size timeout**: If `data.json` is >500KB and GitHub Pages CDN is slow:
   ```bash
   curl -sL --max-time 10 -o /dev/null -w "time: %{time_total}s" "https://<user>.github.io/<repo>/data.json"
   ```
   If `time_total` > 15s and the React code has a 15s AbortController timeout, the fetch will fail.

## Build & Deploy Commands

```bash
npm run build                    # Build to dist/
cp dist/index.html dist/404.html # SPA routing fallback
# Copy dist/* to git root (or deploy via GitHub Actions)
cd /repo && cp -r dist/* .
git add -A && git commit -m "deploy vN" && git push origin master
```

## Pitfalls

- **Forgotten `404.html`**: Routes other than `/` return GitHub Pages 404 page (not the app)
- **Trailing slash redirect**: GitHub Pages silently redirects `/questions` → `/questions/`, breaking React Router match
- **`base: '/'` in Vite**: All JS/CSS URLs start from root, not subdirectory → 404s for every asset
- **Hardcoded fetch URLs**: `'/data.json'` instead of `import.meta.env.BASE_URL + 'data.json'` → wrong path when deployed to subdirectory
- **Old `index.html` overridden**: Don't commit built `index.html` as Vite source — Vite needs `index.html` referencing `src/main.tsx`, not `assets/*.js`
- **React strict mode double-mount**: In development, `StrictMode` mounts components twice → double data fetches. Not an issue in production build
- **GitHub Actions deploy-pages incompatibility**: Old-style (branch-based) Pages is incompatible with the `deploy-pages` action. Either switch to the newer Actions-based Pages mode or stick to manual upload
