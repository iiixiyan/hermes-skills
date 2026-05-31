# 微信公众号文章：原始HTML提取法

> 当浏览器被CAPTCHA拦截、Jina Reader/Exa超时或不可用时，直接从服务器返回的原始HTML中提取文章内容。

## 背景

微信公众号文章的访问控制策略：
- **浏览器渲染** → 大概率触发环境异常CAPTCHA（尤其在服务器/IP无微信登录态时）
- **Jina Reader** (`r.jina.ai`) → 可能超时或返回受限内容
- **Exa搜索** → 需要API额度，不适合快速单篇读取

**但文章正文始终在原始HTML中**，以 `<div id="js_content">` 嵌入，被CSS隐藏（`visibility: hidden; opacity: 0`），等待JS渲染后显示。直接提取这个div即可绕过CAPTCHA。

## 操作流程

### Step 1: 下载原始HTML

```bash
curl -sL --max-time 10 "https://mp.weixin.qq.com/s/ARTICLE_ID" \
  -H "User-Agent: Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
  -H "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8" \
  -H "Referer: https://mp.weixin.qq.com/" \
  > /tmp/weixin_article.html
```

⚠️ `-L` 跟随重定向（微信会重定向到CAPTCHA页，但原始HTML不受影响）
⚠️ Android UA 比桌面 UA 更不容易被限
⚠️ 文件通常 2~4MB（含大量JS和CSS），但正文只占 ~10KB

### Step 2: Python提取js_content

```python
import re

with open("/tmp/weixin_article.html", "r", encoding="utf-8") as f:
    html = f.read()

# 定位 js_content div 的起始和结束
start_marker = 'id="js_content"'
start_idx = html.find(start_marker)
if start_idx == -1:
    print("无法找到文章内容")
    exit()

# 从 id="js_content" 之后找到 > 符号（属性结束）
start_idx = html.find('>', start_idx) + 1
# 找到闭合的 </div>
end_idx = html.find('</div>', start_idx)

content_html = html[start_idx:end_idx]

# 去HTML标签
text = re.sub(r'<[^>]+>', '', content_html)
# 解码HTML实体
text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
# 清理多余空白
text = re.sub(r'\s+', ' ', text).strip()

print(text)
```

### Step 3: 提取标题和元信息（可选）

在HTML中搜索以下标记：
- `<h1 class="rich_media_title"` → 文章标题
- `var ct = "` → 发布时间（Unix时间戳）
- `msg_title` → 备用标题
- `msg_link` → 文章链接

```python
# 标题
title_match = re.search(r'<h1[^>]*class="rich_media_title"[^>]*>(.*?)</h1>', html, re.DOTALL)
title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "未找到标题"

# 作者
author_match = re.search(r'var nickname\s*=\s*"([^"]+)"', html)
author = author_match.group(1) if author_match else "未找到作者"

# 公众号
account_match = re.search(r'var round_head_nickname\s*=\s*"([^"]+)"', html)
account = account_match.group(1) if account_match else "未找到公众号名"
```

## 注意事项

1. **CAPTCHA页不影响正文提取** — 即使浏览器遇到CAPTCHA重定向，原始HTML中仍包含完整文章内容
2. **文件较大**（2~4MB）— 用Python提取而不是直接cat
3. **js_content被CSS隐藏** — 提取到的文本中行内样式可能包含 `visibility: hidden`，不影响文本内容
4. **图片不可见** — 图片URL在HTML中以 `<img>` 标签存在，但本文方法只提取纯文本；如需图片可以额外提取 `data-src` 属性
5. **动态内容** — 部分微信文章包含小程序卡片、投票等动态组件，这些不会被提取到纯文本中

## 适用场景

| 场景 | 推荐方法 |
|:----|:--------|
| 快速获取正文 | 原始HTML提取（本文方法） |
| 需要图片/排版 | 浏览器渲染（有CAPTCHA风险） |
| 批量搜索 | Exa API |
| 多篇文章对比 | 原始HTML提取+Python批量处理 |

## 已知局限

- ❌ 无法获取"阅读原文"跳转后的内容（那是另一个页面）
- ❌ 无法获取评论区内容（评论区通过JS懒加载）
- ❌ 部分保护级文章（如付费专栏）内容可能不在js_content中
- ⚠️ 微信可能修改前端代码结构，js_content的定位方式可能需要更新
