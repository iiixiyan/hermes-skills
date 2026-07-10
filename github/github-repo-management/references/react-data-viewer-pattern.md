# React/TypeScript Data Viewer (from DESIGN.md + JSON)

For datasets that need **routing, state management, rich UI, and automated CI/CD**, use a React + TypeScript + Vite + antd project instead of a vanilla HTML page. This pattern follows from a `DESIGN.md` spec in the repo.

## When to use

- Dataset has **per-item state** (favorites, progress tracking) → needs localStorage
- Need **multiple pages** (home / list / detail / favorites) → needs routing
- Dataset has **nested/complex content** (Markdown with code blocks, math) → needs proper rendering libraries
- Want **automated builds** via GitHub Actions → needs build step

## Architecture

```
repo/
├── DESIGN.md                   # Design spec — write first, code from it
├── public/data.json            # Dataset (copied into build)
├── src/
│   ├── types/question.ts       # TypeScript interfaces
│   ├── utils/parseAcceptRate.ts
│   ├── hooks/
│   │   ├── useFavorites.ts     # localStorage: toggle/get
│   │   └── useProgress.ts      # localStorage: undone/doing/done
│   ├── components/
│   │   ├── Layout.tsx          # antd Layout + Menu (dark header)
│   │   ├── HomePage.tsx        # Stats cards, difficulty dist, tag cloud
│   │   ├── QuestionList.tsx    # Search + filter + sort + card grid
│   │   ├── QuestionDetail.tsx  # 3-Tab: description, template, solution
│   │   ├── Favorites.tsx       # Filtered grid from localStorage
│   │   └── MarkdownRenderer.tsx # react-markdown + remark-gfm
│   ├── App.tsx                 # BrowserRouter + routes
│   ├── main.tsx                # entry + ConfigProvider
│   └── index.css               # Markdown body styles, scrollbar
├── .github/workflows/deploy.yml # GitHub Actions → Pages
├── vite.config.ts              # manualChunks: antd, markdown
├── tsconfig.json
└── package.json
```

## 1. Project Scaffolding

```bash
npm create vite@latest PROJECT_NAME -- --template react-ts
cd PROJECT_NAME
npm install antd react-router-dom react-markdown remark-gfm rehype-raw \
  rehype-highlight highlight.js katex
```

Key dependencies:

| Package | Purpose |
|---------|---------|
| `antd` | UI components: Card, Tag, Select, Progress, Tabs, Button, Statistic |
| `react-router-dom` | Client routing: `/` → home, `/questions`, `/question/:pid`, `/favorites` |
| `react-markdown` + `remark-gfm` | Markdown → HTML rendering with tables, lists, code |
| `highlight.js` | Code syntax highlighting in Markdown blocks |

## 2. Data Loading Strategy

Place `data.json` in `public/` so it's served at runtime from the same domain:

```typescript
const DATA_URL = '/data.json';

// In each component that needs data:
const [data, setData] = useState<TopLevel | null>(null);
useEffect(() => {
  fetch(DATA_URL).then(r => r.json()).then(setData).catch(() => {});
}, []);
```

**Why not import?** The data is large (1MB+) and changes independently. Fetching at runtime avoids rebuilds when the dataset updates.

## 3. TypeScript Types

```typescript
export interface Question {
  pid: string;
  title: string;
  date: string;
  difficulty: number;       // 1-10
  tags: string[];            // knowledge tags
  description_md: string;    // markdown content
  code_templates: Record<string, string>;  // {py: "...", java: "...", ...}
  has_signature: boolean;
  python_signature: string | null;
  accept_rate: string;       // "14/122"
  solution: string;          // markdown with embedded code blocks
}

export type ProgressStatus = 'undone' | 'doing' | 'done';
```

## 4. localStorage Hooks

```typescript
// useFavorites.ts
const STORAGE_KEY = 'od-favorites';

export function useFavorites() {
  const [favorites, setFavorites] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
    catch { return []; }
  });

  const toggleFavorite = useCallback((pid: string) => {
    setFavorites(prev => {
      const next = prev.includes(pid) ? prev.filter(p => p !== pid) : [...prev, pid];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return { favorites, toggleFavorite, isFavorite: (pid: string) => favorites.includes(pid) };
}
```

```typescript
// useProgress.ts
const STORAGE_KEY = 'od-progress';
type UserProgress = Record<string, ProgressStatus>;

export function useProgress() {
  const [progress, setProgress] = useState<UserProgress>(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch { return {}; }
  });

  const setStatus = useCallback((pid: string, status: ProgressStatus) => {
    setProgress(prev => {
      const next = { ...prev, [pid]: status };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const getStatus = useCallback((pid: string) => progress[pid] || 'undone', [progress]);
  const getStats = useCallback(() => ({
    done: Object.values(progress).filter(v => v === 'done').length,
    doing: Object.values(progress).filter(v => v === 'doing').length,
    undone: Object.values(progress).filter(v => v === 'undone').length,
  }), [progress]);

  return { progress, setStatus, getStatus, getStats };
}
```

## 5. App Structure with Routes

```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import HomePage from './components/HomePage';
import QuestionList from './components/QuestionList';
import QuestionDetail from './components/QuestionDetail';
import Favorites from './components/Favorites';

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={{ token: { borderRadius: 8 } }}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/questions" element={<QuestionList />} />
            <Route path="/question/:pid" element={<QuestionDetail />} />
            <Route path="/favorites" element={<Favorites />} />
            <Route path="*" element={<HomePage />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
}
```

### Layout with dark navigation

```typescript
// Layout.tsx
import { Layout as AntLayout, Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';

export default function Layout({ children }: { children: ReactNode }) {
  const nav = useNavigate();
  const loc = useLocation();
  const key = loc.pathname === '/' ? '/' : '/questions';

  return (
    <AntLayout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <AntLayout.Header style={{ background: '#001529', padding: '0 20px' }}>
        <div style={{ color: '#fff', fontSize: 18, fontWeight: 700, marginRight: 30 }}>
          📚 OD题库
        </div>
        <Menu theme="dark" mode="horizontal" selectedKeys={[key]}
          items={[
            { key: '/', label: '首页', onClick: () => nav('/') },
            { key: '/questions', label: '题目列表', onClick: () => nav('/questions') },
            { key: '/favorites', label: '我的收藏', onClick: () => nav('/favorites') },
          ]}
        />
      </AntLayout.Header>
      <AntLayout.Content style={{ maxWidth: 1200, margin: '16px auto', padding: '0 16px' }}>
        {children}
      </AntLayout.Content>
    </AntLayout>
  );
}
```

## 6. MarkdownRenderer Component

```typescript
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function CodeBlock({ children }: { children?: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const code = String(children || '').replace(/\n$/, '');
  return (
    <div className="code-block-wrapper">
      <button className="copy-btn" onClick={() => {
        navigator.clipboard.writeText(code);
        setCopied(true); setTimeout(() => setCopied(false), 1500);
      }}>{copied ? '✅ 已复制' : '📋 复制'}</button>
      <pre><code>{code}</code></pre>
    </div>
  );
}

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            if (match) return <CodeBlock>{children}</CodeBlock>;
            return <code {...props}>{children}</code>;
          },
          pre({ children }) { return <>{children}</>; }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
```

## 7. QuestionDetail — Three-Tab Pattern

```typescript
const LANG_KEYS = ['py', 'java', 'cc', 'js', 'c'];
const LANG_LABELS: Record<string, string> = {
  py: 'Python', java: 'Java', cc: 'C++', js: 'JavaScript', c: 'C'
};

// Inside component:
<Card>
  <Tabs items={[
    {
      key: 'desc',
      label: '📄 题目描述',
      children: <MarkdownRenderer content={q.description_md} />
    },
    {
      key: 'solution',
      label: '📖 题解',
      children: <MarkdownRenderer content={q.solution} />
    },
    {
      key: 'template',
      label: '💻 代码模板',
      children: (
        <div>
          <Space style={{ marginBottom: 12 }}>
            {LANG_KEYS.map(k => (
              <Button key={k} type={codeLang === k ? 'primary' : 'default'}
                size="small" onClick={() => setCodeLang(k)}
                disabled={!q.code_templates[k]}>
                {LANG_LABELS[k]}
              </Button>
            ))}
          </Space>
          <pre style={darkCodeStyle}>
            <code>{q.code_templates[codeLang] || '// No template'}</code>
          </pre>
        </div>
      )
    }
  ]} />
</Card>
```

## 8. Vite Config (chunk splitting for antd)

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/',  // Must match GitHub Pages deployment path
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          antd: ['antd'],
          markdown: ['react-markdown', 'remark-gfm'],
        }
      }
    },
    chunkSizeWarningLimit: 1000,
  },
});
```

## 9. GitHub Actions Deployment

```yaml
# .github/workflows/deploy.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [master]  # or main — match your default branch name

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist
      - id: deployment
        uses: actions/deploy-pages@v4
```

**⚠️ Pitfall:** The `on.push.branches` must match your repo's default branch name. Our repo uses `master` (from `git init` default), not `main`. Update the workflow if your default differs.

## 10. DESIGN.md Workflow

When a `DESIGN.md` exists in the repo root, treat it as a **specification** — build from it rather than inventing a structure:

1. Read DESIGN.md fully first — identify tech stack, component tree, data model
2. Scaffold project with the specified tech stack (React/TypeScript/Vite/antd in our case)
3. Copy data.json to `public/` 
4. Write types first (based on the JSON structure and DESIGN.md's data model section)
5. Write hooks (state management primitives)
6. Write utility functions
7. Write components bottom-up (atomic → composite)
8. Wire up routing and App shell
9. Write CSS (focus on Markdown body/scrollbar styling)
10. Commit and push

**Pitfall:** Design docs may specify libraries like `react-markdown` + `remark-gfm` for rendering. Use them — don't reimplement with vanilla regex when the spec calls for proper dependencies.

## 11. Git Push Troubleshooting

If `git push` via HTTPS times out (stalls at `Trying 20.205.243.166:443...`) but the GitHub API responds, the token in `~/.git-credentials` may use `github_pat_` format which git HTTPS transport handles differently than the API `Bearer` header:

```bash
# Check credential format
cat ~/.git-credentials | grep github
# → https://username:github_pat_XXXX@github.com

# For git push, use: username = the account name, password = the PAT
git remote set-url origin https://USERNAME:github_pat_XXXX@github.com/owner/repo.git

# For API calls, use:
curl -H "Authorization: Bearer github_pat_XXXX" https://api.github.com/
```

The `github_pat_` tokens work with both formats — just make sure the URL has the right structure for git operations.
