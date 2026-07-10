# React + Vite + KaTeX to GitHub Pages — Full Walkthrough

## Problem

Deploy a React SPA (74-question Huawei OD question bank) to GitHub Pages at `https://user.github.io/repo/` with:

- Vite build with `base: '/repo/'`
- React Router with `basename`
- SPA 404 fallback for sub-path routing
- KaTeX math formula rendering (inline `$...$` and display `$$...$$`)
- Split-layout detail page with sidebar question list

## Data structure

```
public/
  index.json          ← 13KB metadata (question list summary)
  questions/          ← 74 x {pid}.json (full description + solution + templates)
    P14415.json
    ...
```

Each `{pid}.json` has fields: `title`, `pid`, `difficulty`, `date`, `description_md`, `solution`, `code_templates`, `topics`, `has_signature`, `accept_rate`.

## Vite + React config

### vite.config.ts

```ts
base: '/repo-name/',
build: {
  rollupOptions: {
    output: {
      manualChunks(id) {
        if (id.includes('node_modules/antd')) return 'antd';
        if (id.includes('node_modules/react-markdown') || id.includes('node_modules/remark-') || id.includes('node_modules/rehype-') || id.includes('node_modules/katex')) return 'markdown';
      }
    }
  }
}
```

### App.tsx / main.tsx

```tsx
<BrowserRouter basename="/repo-name/">
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/questions/" element={<QuestionList />} />
    <Route path="/question/:pid" element={<QuestionDetail />} />
    <Route path="/favorites/" element={<Favorites />} />
    <Route path="*" element={<Home />} />
  </Routes>
</BrowserRouter>
```

### All fetch paths

```tsx
const BASE = import.meta.env.BASE_URL; // always '/repo-name/'
fetch(BASE + 'index.json')
fetch(BASE + 'questions/' + pid + '.json')
```

## KaTeX math rendering

### Install

```bash
npm install katex remark-math rehype-katex
```

### MarkdownRenderer.tsx

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

No special configuration needed — `remark-math` v6 parses `$...$` and `$$...$$` automatically.

### Verify

Count rendered KaTeX elements in browser console:

```js
document.querySelectorAll('.katex').length
// → 296 (example from P14387 which had extensive formulas)
```

## React hooks pitfall

**WRONG** — hooks rule violation:

```tsx
const [data, setData] = useState(null);
// fetch data...
if (!data) return <Card loading />;           // ← EARLY RETURN before useMemo
const filtered = useMemo(() => data.filter(...), [data]);  // ← This is the 9th hook, but earlier renders only had 8
```

**RIGHT** — all hooks before conditional return:

```tsx
const [data, setData] = useState(null);
// fetch data...
const allTags = data ? getAllTags(data.题目列表) : [];     // ← memo-like, runs unconditionally
const filtered = useMemo(() => {
  if (!data) return [];
  return data.题目列表.filter(...);
}, [data]);
if (!data) return <Card loading />;            // ← AFTER all hooks
```

## GitHub Actions deployment

See the main `SKILL.md` for the deploy.yml template. Key points:

1. **Environment required**: `environment: name: github-pages` on the build job.
2. **SPA fallback**: `cp dist/index.html dist/404.html` after build.
3. **Pages mode**: Must be "GitHub Actions", not Legacy (branch-based).

## KaTeX CSS and fonts

When using `import 'katex/dist/katex.min.css'` in a component, Vite bundles ~60 KaTeX font files (woff2, woff, ttf). These are normal — don't be alarmed by the large number in build output. The markdown chunk CSS file includes all KaTeX styles.

## Multi-language code templates

Display 7 languages (Python, Java, C++, JavaScript, C) with tab switcher:

```tsx
const LANG_LABELS = { py: 'Python', java: 'Java', cc: 'C++', js: 'JavaScript', c: 'C' };
const LANG_KEYS = ['py', 'java', 'cc', 'js', 'c'];
```

## Code display styling

Tokyo Night theme (`#1a1b26` background, `#a9b1d6` text) with JetBrains Mono font stack:

```css
.code-template-pre, .markdown-body pre {
  background: #1a1b26;
  color: #a9b1d6;
  padding: 16px 18px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.5;
  font-family: 'JetBrains Mono','Fira Code','Cascadia Code','Consolas','Monaco','Menlo',monospace;
  font-variant-ligatures: normal;
  border: 1px solid rgba(255,255,255,.06);
}
```

## Removing custom markdown directives

The data contained `#code-switcher` and `#hot100-card { ... }` directives that should be invisible in the UI. Strip them before rendering:

```tsx
content.replace(/^#code-switcher\s*$/gm, '')
       .replace(/#hot100-card\s*\{[\s\S]*?\}/g, '')
```

The `#hot100-card` block is multi-line (lines 177-181 in source), so the second regex uses `[\s\S]*?` (non-greedy dot-all) to match the entire block from opening `{` to closing `}`.

## API-based git push (fallback)

When `git push` times out over HTTPS, use GitHub API:

```
1. Get latest commit SHA from refs/heads/master
2. Create blob(s) via POST /repos/{owner}/{repo}/git/blobs
3. Get current tree from the latest commit
4. Build new tree with updated blob SHA(s)
5. POST new tree → /git/trees
6. POST new commit → /git/commits (tree + parent)
7. PATCH ref → /git/refs/heads/master (with sha + force: true)
```
