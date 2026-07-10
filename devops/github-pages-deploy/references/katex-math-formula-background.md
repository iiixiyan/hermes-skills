# KaTeX Formula Background Styling for Markdown SPAs

## Problem

When using `react-markdown` + `remark-math` + `rehype-katex` in a React SPA, inline math `$...$` and block math `$$...$$` render differently:

| Math type | Rendered HTML | CSS inheritance |
|-----------|--------------|-----------------|
| Inline `$...$` | `<code class="language-math math-inline"><span class="katex">…</span></code>` | Gets `code { background }` |
| Block `$$...$$` | `<pre><code class="language-math math-display"><span class="katex">…</span></code></pre>` | Gets `pre code { background: 0 0 }` pattern, stripping background |

## Root cause

A common markdown CSS pattern:

```css
.markdown-body code {
  background: #e8e8ee;     /* inline code background */
  padding: 2px 6px;
  border-radius: 4px;
}
.markdown-body pre code {
  background: 0 0;          /* ← this strips block math background */
  padding: 0;
}
```

The second rule is intended to let syntax-highlighted code blocks use their own `pre` background, but it also matches `<code class="language-math math-display">` inside `<pre>`.

## Fix: add specific math rules AFTER generic code rules

```css
/* Block math formula background */
.markdown-body code.language-math.math-display {
  background: #e8e8ee !important;
  border-radius: 6px;
  padding: 12px 16px;
  display: block;
  margin: 12px 0;
}
/* Prevent pre wrapper from interfering */
.markdown-body pre:has(code.language-math) {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}
```

## Verification

```js
// Check rendered formula count
document.querySelectorAll('.katex').length
document.querySelectorAll('code.language-math.math-display').length
document.querySelectorAll('code.language-math.math-inline').length
```

## Alternative: customize per shade

```css
/* Light theme */
.math-display { background: #f0f4ff !important; }

/* Dark theme */
.math-display { background: #1e2030 !important; color: #c0caf5; }
```