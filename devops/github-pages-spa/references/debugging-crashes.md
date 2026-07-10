# Debugging React Crashes on GitHub Pages

## The Cross-Origin Error Problem

When a React app crashes on GitHub Pages, the browser console often shows:

```
js_errors: [{message: "", source: "exception"}]
```

**Empty error message.** This happens because:

1. The HTML has `<script type="module" crossorigin src="...">` 
2. GitHub Pages does NOT send `Access-Control-Allow-Origin` CORS headers
3. The browser suppresses error details for cross-origin scripts

## Capturing Actual Error Details

### Method 1: window.onerror (works despite crossorigin)

Set up BEFORE the crash triggers. Navigate to a working page first:

```js
// Execute in browser console on the homepage
window.herr = [];
window.onerror = function(msg, url, line, col, err) {
  window.herr.push({msg, url, line, col, stack: err?.stack});
};
window.addEventListener('unhandledrejection', function(e) {
  window.herr.push({reason: e.reason?.stack || e.reason?.message});
});
```

Then navigate to the broken route. Check captured errors:

```js
window.herr
```

### Method 2: Browser DevTools Network Tab

Even without error message text, the stack trace includes function names and positions:

```
at yr (https://.../index-xxx.js:3:36906)
at fo (https://.../antd-xxx.js:8:47540)
```

- `yr` is the minified function name (QuestionList in this case)
- Position `3:36906` → line 3, character 36906 in the JS file
- Cross-reference with the route map or source map to identify the component

## React Error Number Reference

When you see `Minified React error #310` (or any number):

| # | Meaning | Likely Cause |
|---|---------|-------------|
| 310 | "Rendered more hooks than during the previous render" | Early return before a hook (useState/useMemo/useEffect) |
| 301 | "Rendered fewer hooks than expected" | Conditional hook call on later render |
| 185 | "Cannot update during an existing state transition" | setState inside render or in wrong lifecycle |
| 418 | "Objects are not valid as a React child" | Trying to render an object directly |

Check https://react.dev/errors/{number} for the full message.

## Root HTML Source Check

Always verify which `index.html` is being served:

```js
document.querySelector('script[type=module]')?.outerHTML
```

- Template version: `src="/src/main.tsx"` → WRONG, should be built
- Built version: `src="/repo-name/assets/index-xxx.js"` → CORRECT

## Resource Loading Verification

```js
performance.getEntriesByType('resource').map(r => ({
  name: r.name.split('/').pop(),
  status: r.responseStatus,
  duration: Math.round(r.duration)
}))
```
