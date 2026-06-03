# API-Driven Content Site Pattern

Deploy a static single-page app on EdgeOne Pages that dynamically fetches markdown content from a Gitee (or any Git hosting) API. Content lives in the Gitee repo; the deployed HTML is a shell that renders it on demand.

## Use Case

- Learning notes / documentation site where content is authored as Markdown in a Gitee repo
- Blog or knowledge base with no build step — push a `.md` file and the site updates instantly
- Any scenario where you want to avoid rebuilding/redeploying for every content change

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│  EdgeOne Pages      │  fetch  │  Gitee API            │
│  (static index.html)│ ──────→ │  /repos/.../contents/ │
│                     │ ←────── │  (base64 .md content) │
│  marked.js renders  │  JSON   │                      │
│  .md → HTML         │         └──────────────────────┘
└─────────────────────┘
```

## ⚠️ Critical: Base64 Encoding Fix

Gitee API returns file content as **base64-encoded UTF-8 bytes**. Using `atob()` directly **corrupts multi-byte Chinese characters** (and other non-Latin-1 chars).

```javascript
// ❌ WRONG — garbles Chinese/emoji
const md = atob(data.content);

// ✅ CORRECT — proper UTF-8 decode
function decodeBase64Utf8(b64) {
  const binaryStr = atob(b64);
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }
  return new TextDecoder('utf-8').decode(bytes);
}
```

## Dynamic Sidebar from Directory Listing

Instead of hardcoding navigation, fetch the repo's directory tree and build the sidebar dynamically:

```javascript
const API_BASE = `https://gitee.com/api/v5/repos/${owner}/${repo}/contents`;

async function buildSidebar() {
  const resp = await fetch(`${API_BASE}?ref=${branch}`);
  const items = await resp.json();

  // Filter directories (each = one week)
  const weekDirs = items.filter(i => i.type === 'dir').sort();

  for (const dir of weekDirs) {
    const weekResp = await fetch(`${API_BASE}/${dir.name}?ref=${branch}`);
    const weekItems = await weekResp.json();

    // Filter .md files (each = one day's lesson)
    const mdFiles = weekItems
      .filter(i => i.type === 'file' && i.name.endsWith('.md'))
      .sort((a, b) => a.name.localeCompare(b.name));

    // Render sidebar section...
  }
}
```

## Key Design Decisions

| Decision | Why |
|----------|-----|
| **Static HTML + JS** (no build) | Zero deploy friction for content updates |
| **Gitee API** (not raw file URL) | API returns structured JSON with base64 content, size, SHA |
| **marked.js** for rendering | Lightweight, no build step, CDN-hosted |
| **Client-side fetch** | Simple, no Edge Functions needed |
| **TextDecoder('utf-8')** | Correct handling of Chinese/multi-byte characters |

## Pitfalls

1. **Base64 + atob() = garbled UTF-8**: Always use `TextDecoder('utf-8')` after converting bytes — never rely on `atob()` alone for CJK text.
2. **Gitee API rate limits**: The free API has limits (~5000 req/hr). Fine for personal use; for high-traffic sites, add caching or switch to raw file URLs with proper encoding.
3. **CORS**: Gitee API supports CORS from browsers — no proxy needed.
4. **Sidebar shows stale progress**: The dynamic listing shows what files EXIST, not what's been "completed." Track completion state separately (e.g., a `progress.json` in the repo, or localStorage).
5. **File sorting**: Gitee API returns files in creation order. Always `.sort()` by name for consistent `Day01 < Day02 < ...` ordering.
6. **`ref` query param**: Always include `?ref=${branch}` in API requests to get the latest content, not cached versions.

## Full Working Template

For a complete working example (OD learning notes site deployed on EdgeOne Pages with dynamic Gitee content), see:
- Local copy: `/tmp/huawei-od-learning/index.html`
- Live URL: https://huawei-od-learning-z4y4x63h.edgeone.cool

## Related References

- [recipes.md](recipes.md) — General project structure templates
- [troubleshooting.md](troubleshooting.md) — Debugging EdgeOne Pages issues
