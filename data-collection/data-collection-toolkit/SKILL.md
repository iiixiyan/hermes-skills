---
name: data-collection-toolkit
description: "数据采集工具链选型框架：四件套优先级策略。当需要在网上获取数据时，按此框架选择最优工具，而非随机尝试。"
tags: ["web-scraping", "data-acquisition", "tool-priority"]
related_skills:
  - autocli-skill
  - agent-reach
  - 59itou-data-fetch
  - bb-browser
---

# 数据采集工具链选型框架

## 用户工具链四件套

当接到数据采集任务时，按以下优先级选型（从轻到重）：

| 优先级 | 工具 | 定位 | 用户说 | 适用场景 |
|:-----:|:----|:----|:------|:---------|
| **1️⃣** | **web_search + web_extract** | 公开网页搜索+正文提取 | "我的望远镜——能看到网上最新的热点" | 搜索引擎可找到的公开内容 |
| **2️⃣** | **AutoCLI (autocli)** | 55+平台CLI，复用Chrome登录态 | "我的内线——读取各大平台内容，关键是能复用Chrome登录态" | 需要登录的平台（微博/知乎/B站/推特/小红书等） |
| **3️⃣** | **Agent-Reach** | YouTube字幕/GitHub/RSS/Exa搜索 | "我的采集技能包——把YouTube字幕、GitHub、RSS等能力打包给Agent" | 视频转文字、GitHub仓库、RSS订阅、语义搜索 |
| **4️⃣** | **bb-browser** | 浏览器即API，直接控浏览器 | "理念很狠：Your browser is the API——很多网站没有API，但浏览器已经能看，让Agent直接控制浏览器去读、去点" | 以上三件套都不支持的特殊网站、需交互操作的页面 |

### 工具切换检验标准

```
当尝试当前工具失败时：
  exit_code 非零 → 尝试下一优先级工具
  返回空数据 → 尝试下一优先级工具
  返回 \"not found\" / \"不支持\" → 尝试下一优先级工具
  超时 > 30s → 考虑是否需要降级或换工具
```

**核心原则**：永远不先说"不支持"。先试 autocli，再试 Agent-Reach，最后 bb-browser 兜底。

## 各工具安装状态

| 工具 | 状态 | 安装方式 |
|:----|:----|:---------|
| web_search / web_extract | ✅ Hermes 原生 | — |
| AutoCLI (autocli) | ✅ v0.3.8 (Rust 8MB单文件) | 二进制 `/usr/local/bin/autocli`，见 `social/autocli-skill` |
| Agent-Reach | ✅ v1.4.0 | `pipx install`，7/16渠道活跃（Web/Jina/Exa/YouTube/B站/RSS/公众号/雪球） |
| bb-browser | ✅ 已装 (14 packages) | `npm install -g bb-browser`，`bb-browser site|open|snap|click|fill|type` |

## 数据采集铁律（用户强制要求）

### ⚡ 原始数据铁律

所有网页数据采集，必须保留 **`document.body.innerText` 原始完整内容**：
- ❌ 禁止任何总结、归纳、格式化、省略、简化
- ❌ 禁止 AI 改写或精简原文
- ❌ 禁止只提取关键信息
- ✅ 一字不改，原文呈现
- ✅ 用于足球数据的 59itou 采集特别强调此规则

### 平台覆盖参考

| 平台 | 推荐工具 | 备注 |
|:----|:--------|:-----|
| 59itou（足球数据） | Playwright+Chromium（手动） | 6Tab全采集，lotteryId区分北单(45)/竞足(90) |
| 微博热搜/搜索 | autocli weibo | 无需登录即可用公共模式 |
| B站热门/搜索 | autocli bilibili | 公共模式可用 |
| 知乎热榜/搜索 | autocli zhihu | 公共模式可用 |
| HackerNews | autocli hackernews | 公共模式 |
| arXiv论文 | autocli arxiv | 公共模式 |
| YouTube视频/字幕 | Agent-Reach (yt-dlp) | 或 autocli youtube |
| GitHub仓库/代码 | Agent-Reach (gh CLI) | 或 autocli gh |
| RSS订阅 | Agent-Reach (feedparser) | 或 autocli read |
| 任意网页正文 | autocli read <url> | 基于Mozilla Readability |
| 需要登录的平台（微博/小红书等） | autocli（浏览器模式） | 需Chrome+扩展 |
| 特殊交互网站 | bb-browser | 最后兜底 |

## autocli 使用速查

```bash
# 常用命令
autocli doctor                    # 先检查状态
autocli bilibili hot --limit 10   # B站热门
autocli zhihu hot --limit 10      # 知乎热榜
autocli hackernews top --limit 20 # HackerNews
autocli arxiv search --keyword "xxx" --limit 5  # arXiv论文
autocli v2ex hot --limit 10       # V2EX热门
autocli read <url>                # 任意网页正文提取

# 通用参数
--format json   # JSON输出（推荐）
--limit N       # 结果数量
```

## 环境已知限制

### 境外搜索引擎不可达

服务器网络限制，以下搜索引擎/知识库**完全不可达**（DNS解析失败或连接超时）：
- Google (google.com) ❌
- Bing (bing.com) ❌
- DuckDuckGo (duckduckgo.com) ❌
- arXiv (arxiv.org) ❌
- Wikipedia (wikipedia.org) ❌

**替代方案**：搜索用百度（baidu.com）、新浪（sina.com.cn）、QQ（qq.com）等国内站点，或直接采集已知可达平台（59itou、知乎、微博等）。工具链四件套中的 2️⃣-4️⃣ 均不依赖境外搜索引擎。

### 中国服务器网络环境

当从 GitHub 下载资源时，直接连接可能超时（`exit=28`/`Connection timed out`）。详见 `references/github-proxy-download.md` 中 ghproxy 代理方案。

```bash
# 使用 ghproxy 代理下载
curl -sL "https://ghproxy.net/https://github.com/.../releases/download/..." -o output.tar.gz
```

### 终端工具已知问题

`terminal` 工具存在持续 bug：所有命令报错 `cd: y: No such file or directory`，exit_code=126。
**解决方案**：始终使用 `execute_code` 配合 Python `subprocess.run()` 执行系统命令。
