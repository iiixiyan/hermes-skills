---
name: data-collection-toolkit
description: "数据采集工具链选型框架：四件套优先级策略 + 足球API速查。当需要在网上获取数据时，按此框架选择最优工具，而非随机尝试。"
tags: ["web-scraping", "data-acquisition", "tool-priority"]
related_skills:
  - autocli-skill
  - agent-reach
  - 59itou-data-fetch
  - bb-browser
---

# 数据采集工具链选型框架

## 快速集成指南（L1/L2/L3方法论 — 2026-06-20更新：L2/L3已全自动）

当采集的数据将用于 **预测/分析管线** 时，需跟踪数据源的**集成状态**以防「文档写了但代码没用」：

| 级别 | 标记 | 含义 | 数据源示例 |
|:----|:----|:------|:----------|
| **L1-自动** | ✅ | 采集代码在主管线中硬编码调用，每次运行自动采集注入引擎 | 新浪API欧赔8参数 + 59itou API综合实力分 |
| **L2-自动** | ✅ | Playwright浏览器全自动采集，`--browser`标志启用，无需人工干预 | titan007分析页 → 天气/评分/伤停/杯赛排名/H2H |
| **L3-自动** | ✅ | Playwright浏览器全自动采集，`--browser`标志启用，仅对当前/未来比赛有效 | 500彩票网shuju页 → FIFA3期/阵容/澳门心水/战绩 |
| **L3-待检** | ⏳ | 采集逻辑就绪但未在大批量数据上验证鲁棒性，或数据源不稳定 | 天天盈球(服务器500错误) |

> **Playwright自动化要点**：使用 Playwright Sync API + 系统Chromium(`/usr/bin/chromium-browser`)。初始化：`p.start()`（**不要用** `p.__enter__()`）。清理：`p.stop()`。
>
> 详见 `football-prediction` skill 的 `Phase D` 章节和 `scripts/automated_l*.py`。

## 用户工具链四件套

当接到数据采集任务时，按以下优先级选型（从轻到重）：

| 优先级 | 工具 | 定位 | 用户说 | 适用场景 |
|:-----:|:----|:----|:------|:---------|
| **1️⃣** | **web_search + web_extract** | 公开网页搜索+正文提取 | "我的望远镜——能看到网上最新的热点" | 搜索引擎可找到的公开内容 |
| **2️⃣** | **AutoCLI (autocli)** | 55+平台CLI，复用Chrome登录态 | "我的内线——读取各大平台内容，关键是能复用Chrome登录态" | 需要登录的平台（微博/知乎/B站/推特/小红书等） |
| **3️⃣** | **Agent-Reach** | YouTube字幕/GitHub/RSS/Exa搜索 | "我的采集技能包——把YouTube字幕、GitHub、RSS等能力打包给Agent" | 视频转文字、GitHub仓库、RSS订阅、语义搜索 |
| **4️⃣** | **bb-browser** | 浏览器即API，直接控浏览器 | "理念很狠：Your browser is the API——很多网站没有API，但浏览器已经能看，让Agent直接控制浏览器去读、去点" | 以上三件套都不支持的特殊网站、需交互操作的页面 |

## 数据源发现铁律

### 当用户要求"找数据源/网站/接口"时

必须**主动搜索+测试大量候选站点**（20个以上），不要仅依赖已知列表。理由：

```text
❌ 错误做法：
   "我知道10个足球网站：1、2、3..." ← 只列已知的，很多已关站/反爬

✅ 正确做法：
   1. 先列出所有已知候选（20+个）
   2. 用curl批量测试连通性（HTTP状态码）
   3. 用浏览器深入检查有数据的站点（看是否有欧赔/亚盘/大小球）
   4. 排除已关站/反爬的
   5. 按可用性分梯队展示
   6. 给出最优组合推荐
```

**用户两次纠正过这个问题："我的意思是你多找找能用的网站进行对比！！"** 意味着"多找找"和"进行对比"都是必须的，不是可选项。

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

### Trafilatura 中文编码注意

Trafilatura 提取中文内容时，**必须传 `resp.content`（原始字节）而非 `resp.text`（已解码字符串）**，否则中文会双编码乱码。

详见 `references/trafilatura-encoding-fix.md`。

### 平台覆盖参考

| 平台 | 推荐工具 | 备注 |
|:----|:--------|:-----|
| 59itou（足球数据·详情页） | 浏览器(Playwright) + URL参数 | **8Tab全采集**。URL格式：`/{station}/match3/?current_tab={tab}&matchid={match_id2}&lotteryId=90`<br>Tab参数：`lineup`(阵容) `info`(情报) `history`(战绩+H2H) `rank`(排名) `odds`(欧指) `handicap`(亚指)<br>lotteryId区分北单(45)/竞足(90)。仅用于阵容/伤停/H2H等API无法覆盖的数据<br>📎 批量采集策略（Prize page matchID提取+delegate_task并行）详见 `references/beidan-batch-review-workflow.md` |
| 59itou隐藏API（足球列表+排名） | **curl REST JSON** | **`apic.jindianle.com/api/match/selectlist`**。直接返回比赛列表+SP赔率+**FIFA排名**+让球数。无需浏览器。详见 `references/59itou-hidden-api.md` |
| **新浪竞彩API（足球欧赔/亚盘/赛果）** | **curl REST JSON** | **`mix.lottery.sina.com.cn`**。`cat1=jczqMatches` 得竞彩SP全玩法（⚠️ 2026-06-19 响应格式变化：`result.data` 现在是list而非dict）；`cat1=footballMatchOddsEuro` 得**53家欧赔**初即赔；`cat1=footballMatchOddsAsia` 得**17家亚盘**盘口+水位；`cat1=footballMatchOddsEuroChange` 得欧赔变化时间序列（155条+）；`cat1=footballMatchDetail` 得比赛详情(排名/天气/轮次)。纯净JSON，无防盗链。详见 `references/football-apis.md` |
| **竞彩官方API（官方SPF/赛果）** | **curl REST JSON** | **`webapi.sporttery.cn/gateway/uniform/fb/`**。`method=concern` 得赛程SPF赔率(h=主胜/d=平/a=客胜)；`method=result` 得赛果（含半全场比分）。**需要UA+Referer头绕过WAF**（详见 `references/football-apis.md §二`）。⚠️ **2026-06-19验证：curl仍被EdgeOne WAF拦截(403)**，需要通过Playwright浏览器访问。 |
| **天天盈球（足球基本面/伤停/阵容）** | **浏览器导航+console提取** | **`www.ttyingqiu.com/live/zq/matchDetail/info/{matchId}`**。往期日期通过左箭头(<-)回退。可用 `browser_console(expression='document.body.innerText')` 全文提取。含：首发阵容+阵型+球员评分+身价、伤停信息+伤停解读、球队有利/不利因素分析、精选情报(战术/天气/赛程)。无Cloudflare反爬。详见 `references/ttyingqiu-data-source.md`（在football-prediction skill下）。⚠️ 2026-06-19 返回500错误，可能不稳定。 |
| **500彩票网（赔率对比·百家欧赔/亚盘/大小）** | **Playwright自动采集(automated_l3.py)** | **`odds.500.com/fenxi/shuju-{id}.shtml`**。**100+家**赔率公司百家欧赔+亚盘对比+大小指数+波胆+走势图。Playwright全自动：从首页赛程→匹配队名→ID(13592xx)→shuju页→FIFA3期/阵容/伤病/澳门心水/近期战绩/未来赛程/主客场战绩→form_signal。**⚠️仅当前/未来比赛有效**(已完赛返回"暂无数据")。详见 `football-prediction/scripts/automated_l3.py`。 |
| **球探体育（足球资料库·分析页面）** | **Playwright自动采集(automated_l2.py)** | **`info.titan007.com/analysis/{analysisId}cn.htm`**。Playwright全自动：导航→提取innerText→解析天气/评分/伤停/杯赛排名/H2H/场均进球→form_signal。分析ID范围：首轮世界杯在2906740-2906809。详见 `football-prediction/scripts/automated_l2.py`。 |
| **雷速体育（赛事直播·资料库）** | **浏览器导航+console提取** | **`www.leisu.com`**。体育直播+资料库+赛事情报。Vue store数据需从console提取。`data.leisu.com` 子域返回405。详见 `references/football-odds-sites-comparison.md`。 |
| **澳客网（足球赛事数据·赔率分析）** | **Playwright自动采集(automated_l3.py)** | **`www.okooo.com/soccer/match/{id}/odds/`**。Playwright全自动：从世界杯赛程页(`/soccer/league/16/schedule/`)→匹配队名→matchId(131xxxx)→提取身价(两队总€)/积分榜→form_signal。详见 `football-prediction/scripts/automated_l3.py`。 |
| **中国竞彩网（官方SP赔率·赛果）** | **浏览器导航** | **`www.sporttery.cn`**。官方竞彩SP/赛果。EdgeOne WAF保护，curl直接访问403。详见 `references/football-odds-sites-comparison.md`。 |
| 微博热搜/搜索 | autocli weibo | 无需登录即可用公共模式 |
| B站热门/搜索 | autocli bilibili | 公共模式可用 |
| 知乎热榜/搜索 | autocli zhihu | 公共模式可用 |
| HackerNews | autocli hackernews | 公共模式 |
| arXiv论文 | autocli arxiv | 公共模式 |
| YouTube视频/字幕 | Agent-Reach (yt-dlp) | 或 autocli youtube |
| GitHub仓库/代码 | Agent-Reach (gh CLI) | 或 autocli gh |
| RSS订阅 | Agent-Reach (feedparser) | 或 autocli read |
| 搜狗搜索 | curl | 中文搜索首选，bot检测弱于百度 |
| 搜狗微信搜索 | curl | 查微信公众号文章和账号 |
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

**替代方案**：
1. **首选 → 搜狗搜索(sogou.com)**：国内搜索引擎，bot检测弱于百度，可靠度高。搜狗微信搜索(weixin.sogou.com)可查微信公众号文章。
2. **备用 → 百度(baidu.com)**：可能触发"百度安全验证"反爬，超时即fallback到搜狗。
3. **其他 → 新浪(sina.com.cn)、QQ(qq.com)**等国内站点。
4. **足球数据** → 直接采集已知可达平台（59itou、知乎、微博等）。

工具链四件套中的 2️⃣-4️⃣ 均不依赖境外搜索引擎。

### 中国服务器网络环境

当从 GitHub 下载资源时，直接连接可能超时（`exit=28`/`Connection timed out`）。详见 `references/github-proxy-download.md` 中 ghproxy 代理方案。

```bash
# 使用 ghproxy 代理下载
curl -sL "https://ghproxy.net/https://github.com/.../releases/download/..." -o output.tar.gz
```

---

## Agent Reach 工具参考

Agent Reach 提供 16+ 个互联网内容渠道的访问能力。本环境已安装部分渠道。

### 渠道一览

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

### 常用命令

| 命令 | 作用 |
|:----|:-----|
| `agent-reach doctor` | 查看所有渠道健康状态 |
| `agent-reach install --channels=all` | 安装所有可选渠道 |
| `agent-reach install --channels=twitter,weibo` | 安装指定可选渠道 |
| `agent-reach configure twitter-cookies "..."` | 配置 Twitter Cookie |
| `agent-reach configure proxy URL` | 配置代理（解锁 Reddit/B站等） |
| `agent-reach configure groq-key gsk_xxx` | 配置小宇宙播客转录 Key |
| `agent-reach configure xhs-cookies "..."` | 配置小红书 Cookie |

### CSDN 博客表格解析

CSDN 博客经常包含结构化表格数据（如题库、排行榜等）。使用 curl + 移动端 UA + 正则提取 `<table>`→`<tr>`→`<td>` 结构，可批量解析。

**核心步骤**：获取HTML → 提取 `id="article_content"` → 正则提取所有 `<table>` → 解析每行 `<td>` → 清理HTML实体和标签。

详见 `references/csdn-blog-table-parsing.md`。

### CSDN 文章内容提取（含付费墙绕过）

当需要获取CSDN文章的**问题描述/题目原文**（而非表格数据）时，使用 `references/csdn-article-extraction.md` 中提供的函数。

**适用场景**：文章有付费墙但问题描述在付费墙前，只需提取题目描述+输入输出格式+示例（不计费部分）。解题代码和完整题解在付费墙后不可得。

**与表格解析的区别**：`csdn-blog-table-parsing.md` 提取表格结构化数据；`csdn-article-extraction.md` 提取文章文本内容（带代码块保护）。

### 各渠道详细用法

#### 网页读取（Jina Reader）

```bash
curl -s "https://r.jina.ai/https://example.com"
```

将 URL 内容转为 markdown 格式返回，适合无 API 的网页。

#### 微信公众号文章 — 原始HTML提取法

当浏览器被CAPTCHA拦截或Jina Reader超时，直接从服务器HTML提取正文。详见 `references/weixin-article-raw-extract.md`。

**优势**：绕过CAPTCHA — 文章正文始终在原始HTML的 `<div id="js_content">` 中（被CSS隐藏，等待JS渲染）。微信阻断的是浏览器渲染，不是HTTP响应。

#### YouTube 视频字幕

```bash
# 获取视频信息
yt-dlp --dump-json "https://youtube.com/watch?v=ID"
# 下载字幕（自动字幕）
yt-dlp --write-auto-sub --sub-lang zh-Hans,en --skip-download "https://youtube.com/watch?v=ID"
# 下载音频
yt-dlp -x --audio-format mp3 "https://youtube.com/watch?v=ID"
```

#### B站（yt-dlp + bili API）

```bash
yt-dlp --dump-json "https://www.bilibili.com/video/BVxxx"
bili search "关键词" --type video
bili hot
```

#### GitHub

```bash
gh search repos "query"
gh repo view owner/repo
gh issue list -R owner/repo
```

#### RSS 订阅源

```python
import feedparser
feed = feedparser.parse("https://example.com/feed.xml")
for entry in feed.entries[:5]:
    print(entry.title, entry.link)
```

### 安装（如需重装）

```bash
pipx install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto
```
