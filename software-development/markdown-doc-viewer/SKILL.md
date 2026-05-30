---
name: markdown-doc-viewer
description: 从Gitee/GitHub的Markdown仓库构建自包含的静态文档浏览站点——单HTML文件，侧栏目录，Markdown渲染，手机端自适应。适用于学习笔记、技术文档、API文档等场景。
version: 1.0.0
metadata:
  hermes:
    tags: [markdown, static-site, docs, mobile-friendly, gitee]
    requires_toolsets: [terminal]
---

# 从Markdown仓库构建静态文档浏览站点

> 生成一个自包含的HTML文件，从Gitee/GitHub raw API加载Markdown文件并渲染为可导航的文档站点，无需任何构建工具或服务器配置。

---

## 何时使用

| 优先级 | 触发场景 |
|:------:|:---------|
| ⭐⭐⭐ | 用户要将Markdown笔记仓库变成可浏览的文档站点 |
| ⭐⭐⭐ | 用户需要手机端友好的学习笔记页面 |
| ⭐⭐ | 用户需要从git仓库生成文档导航页 |
| ⭐⭐ | 用户需要自包含（单HTML文件）的文档浏览器 |

---

## 核心架构

```
┌─────────────────────────────────────┐
│  index.html (单文件自包含)            │
│                                     │
│  ├── CSS (暗色主题 + 手机自适应)      │
│  ├── HTML (侧栏目录 + 内容区)        │
│  └── JavaScript:                    │
│      ├── marked.js (CDN加载)         │
│      ├── 目录树生成                  │
│      ├── Markdown获取+渲染            │
│      └── 移动端侧栏切换              │
└─────────────────────────────────────┘
          │  fetch Markdown
          ▼
   Gitee/GitHub Raw API
   https://gitee.com/{user}/{repo}/raw/master/{path}
```

## 实现步骤

### 第1步：分析仓库结构

用浏览器或`git clone`获取仓库的组织结构：

```bash
git clone https://gitee.com/{user}/{repo}.git /tmp/{repo}
cd /tmp/{repo}
find . -name "*.md" | sort
```

确认：
- 是否按目录分组（如 `week-01-xxx/`, `week-02-xxx/`）
- 文件命名规范（如 `Day01-xxx.md`, `Day02-xxx.md`）
- 根目录是否有 `README.md` 用作首页

### 第2步：生成HTML文件

单HTML文件框架，包含以下关键组件：

**a) 侧栏目录树**
```html
<nav class="sidebar">
  <div class="sidebar-section">
    <div class="sidebar-section-title" onclick="toggleWeek(this)">
      <span class="arrow">▶</span>
      第1周：主题名
      <span class="week-tag">Day 1-7</span>
    </div>
    <div class="sidebar-subsection">
      <a class="sidebar-item" onclick="loadDoc('path/to/file.md')">
        <span class="day-num">Day01</span>标题
      </a>
      <!-- 更多条目... -->
    </div>
  </div>
</nav>
```

**b) Markdown渲染引擎**
```html
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
marked.setOptions({ breaks: true, gfm: true, headerIds: true });

async function loadDoc(path) {
  const url = `https://gitee.com/{user}/{repo}/raw/master/${path}`;
  const resp = await fetch(url);
  const md = await resp.text();
  const html = marked.parse(md);
  document.getElementById('mainContent').innerHTML =
    `<div class="markdown-body">${html}</div>`;
}
</script>
```

**c) 移动端侧栏切换**
```css
@media (max-width: 768px) {
  .sidebar { transform: translateX(-100%); width: 85vw; }
  .sidebar.open { transform: translateX(0); }
  .main { margin-left: 0; }
}
```

### 第3步：Markdown内容样式

使用暗色主题，关键样式规则：

```css
:root {
  --bg-primary: #0f0f1a;
  --bg-secondary: #1a1a2e;
  --bg-card: #16213e;
  --text-primary: #e0e6f0;
  --accent: #4fc3f7;
  --border: #2a2a4a;
  --code-bg: #1a1a2e;
}

.markdown-body h1 { font-size: 28px; border-bottom: 2px solid var(--border); }
.markdown-body h2 { font-size: 22px; color: var(--accent); }
.markdown-body pre {
  background: var(--code-bg); border: 1px solid var(--code-border);
  border-radius: 10px; padding: 16px 20px; position: relative;
}
.markdown-body pre code { font-size: 14px; color: #e6db74; }
.markdown-body table { width: 100%; border-collapse: collapse; }
.markdown-body th { background: var(--bg-hover); color: var(--accent); }
.markdown-body td { background: var(--bg-card); }
.markdown-body blockquote {
  border-left: 4px solid var(--accent-dim);
  background: var(--bg-card); padding: 12px 20px;
}
```

### 第4步：代码块复制按钮

```javascript
document.querySelectorAll('.markdown-body pre').forEach(pre => {
  const btn = document.createElement('button');
  btn.className = 'copy-btn';
  btn.textContent = '📋 复制';
  btn.onclick = () => {
    const code = pre.querySelector('code');
    navigator.clipboard.writeText(code.textContent).then(() => {
      btn.textContent = '✅ 已复制';
      setTimeout(() => { btn.textContent = '📋 复制'; }, 2000);
    });
  };
  pre.appendChild(btn);
});
```

### 第5步：部署与托管

可使用三种方式部署：

| 方式 | 命令/操作 | 说明 |
|:----|:---------|:-----|
| **Gitee直链** | 推送到仓库 → 用raw URL直接访问 | 无需配置，直链可正常加载 |
| **Gitee Pages** | 仓库→服务→Gitee Pages→选择部署分支 | 需账号实名认证 |
| **GitHub Pages** | 推送到gh-pages分支或docs目录 | 免费自动部署 |

**直链URL格式**：
```
https://gitee.com/{user}/{repo}/raw/{branch}/index.html
```

**⚠️ 注意事项**：
- Gitee raw CDN (`raw.giteeusercontent.com`) 对部分HTML文件有内容审查，但实测真实浏览器可正常加载
- 如果使用`gh-pages`分支，可在该分支仅保留`index.html`，减少仓库体积
- marked.js 从CDN加载，需确保网络可达
- 手机端侧栏通过 overlay + translateX 实现，无需JavaScript框架

---

## 输出示例

参考：`https://gitee.com/iiixiyan/huawei-od-learning/raw/master/index.html`

该文件包含：
- 3周19篇文档的完整目录
- 暗色主题 + 手机自适应
- 代码块复制按钮
- 首页README渲染 + 学习进度统计

## 模板文件

`templates/doc-viewer-template.html` — 可复用的HTML骨架模板。

## 更新日志

| 版本 | 日期 | 变更 |
|:----|:----|:-----|
| v1.0.0 | 2026-05-29 | 初始创建：从Gitee仓库构建静态文档站点的完整方法论 |