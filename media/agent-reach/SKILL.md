---
name: agent-reach
description: Agent Reach 互联网访问渠道 —— 通过上游 CLI 工具直接访问 YouTube、B站、微博、Twitter、GitHub、RSS、网页等平台内容。安装后使用上游工具，Agent Reach 是安装器+健康检查器。
version: 1.4.0
category: media
---

# Agent Reach — 互联网访问渠道

## 概述

Agent Reach 是一个互联网访问工具集，提供 16+ 个内容渠道。已安装到本环境，所有上游工具可直接使用。

### 工具链四件套（用户偏好）

| # | 工具 | 定位 |
|:-:|:----|:----|
| 1️⃣ | web_search + web_extract | 公开网页搜索和正文提取，看网上最新热点 |
| 2️⃣ | AutoCLI | 读取各平台内容，复用 Chrome 登录态 |
| 3️⃣ | Agent Reach | YouTube/GitHub/RSS/微博/B站等能力打包（即本技能） |
| 4️⃣ | bb-browser | "Your browser is the API" — 直接控浏览器读点操作 |

采集任务按以上四件套优先选型。

## 已安装渠道一览

| 状态 | 渠道 | 工具 | 命令示例 |
|:----:|:----|:----|:---------|
| ✅ | **任意网页** | Jina Reader | `curl -s "https://r.jina.ai/URL"` |
| ✅ | **全网语义搜索** | Exa (mcporter) | `mcporter call 'exa.web_search_exa(query: "...")'` |
| ✅ | **YouTube** | yt-dlp | `yt-dlp --dump-json URL` |
| ✅ | **B站** | yt-dlp + bili API | `yt-dlp --dump-json URL` / `bili search "query" --type video` |
| ✅ | **RSS/Atom** | feedparser | `python3 -c "import feedparser; ..."` |
| ✅ | **微信公众号** | Exa | 通过 Exa 搜索阅读 |
| ✅ | **雪球** | 公开 API | 行情、搜索、热帖、热股 |
| ✅ | **GitHub** | gh CLI | `gh search repos "query"` |
| ✅ | **Reddit** | rdt-cli | `rdt search "query"` / `rdt read POST_ID` |
| ⬜ | **微博** | mcporter | `mcporter call 'weibo.get_trendings(limit: 10)'` |
| ⬜ | **Twitter/X** | twitter-cli | `twitter search "query" -n 10` |
| ⬜ | **小红书** | mcporter | `mcporter call 'xiaohongshu.search_feeds(...)'` |
| ⬜ | **小宇宙播客** | transcribe.sh | `bash ~/.agent-reach/tools/xiaoyuzhou/transcribe.sh URL` |
| ⬜ | **抖音** | mcporter | `mcporter call 'douyin.parse_douyin_video_info(...)'` |
| ⬜ | **LinkedIn** | mcporter | `mcporter call 'linkedin.get_person_profile(...)'` |

> ✅ = 已装好即用  ⬜ = 需用户提供 Cookie/Key 后激活

## 常用命令

| 命令 | 作用 |
|:----|:-----|
| `agent-reach doctor` | 查看所有渠道健康状态 |
| `agent-reach install --channels=all` | 安装所有可选渠道 |
| `agent-reach install --channels=twitter,weibo` | 安装指定可选渠道 |
| `agent-reach configure twitter-cookies "..."` | 配置 Twitter Cookie |
| `agent-reach configure proxy URL` | 配置代理（解锁 Reddit/B站等） |
| `agent-reach configure groq-key gsk_xxx` | 配置小宇宙播客转录 Key |
| `agent-reach configure xhs-cookies "..."` | 配置小红书 Cookie |

## 各渠道使用说明

### 网页读取（Jina Reader）

```bash
curl -s "https://r.jina.ai/https://example.com"
```

将 URL 内容转为 markdown 格式返回，适合无 API 的网页。

### 微信公众号文章（原始HTML提取法）

当浏览器被CAPTCHA拦截或Jina Reader超时，直接从服务器HTML提取正文：

1. `curl` 下载原始HTML（带Android UA）
2. Python提取 `<div id="js_content">` 中的文本
3. 去HTML标签+解码实体

详见 `references/weixin-article-raw-extract.md`。

**优势**：绕过CAPTCHA，文章正文始终在原始HTML中（被CSS隐藏，等待JS渲染）。微信阻断的是浏览器渲染，不是HTTP响应。

### YouTube 视频字幕

```bash
# 获取视频信息
yt-dlp --dump-json "https://youtube.com/watch?v=ID"

# 下载字幕（自动字幕）
yt-dlp --write-auto-sub --sub-lang zh-Hans,en --skip-download "https://youtube.com/watch?v=ID"

# 下载音频
yt-dlp -x --audio-format mp3 "https://youtube.com/watch?v=ID"
```

### B站（yt-dlp + bili API）

```bash
# 视频信息
yt-dlp --dump-json "https://www.bilibili.com/video/BVxxx"

# 搜索（通过 bili-cli，如已安装）
bili search "关键词" --type video

# 热门
bili hot
```

### GitHub

```bash
gh search repos "query"
gh repo view owner/repo
gh issue list -R owner/repo
```

### RSS 订阅源

```python
import feedparser
feed = feedparser.parse("https://example.com/feed.xml")
for entry in feed.entries[:5]:
    print(entry.title, entry.link)
```

### 微博（需安装激活后）

```bash
mcporter call 'weibo.get_trendings(limit: 10)'
mcporter call 'weibo.search(keyword: "关键词", limit: 10)'
```

### Twitter/X（需 Cookie 登录后）

```bash
twitter search "query" -n 10
twitter timeline
```

## 安装（如需重装）

```bash
pipx install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto
