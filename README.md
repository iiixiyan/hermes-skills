# Hermes Skills

> Hermes Agent 技能仓库 — 65个 Skill，覆盖体育竞猜、AI资讯、开发运维、部署CI、GitHub工具链、社交通讯、软件开发等领域。

自动同步自 Hermes Agent 实例（[iiixiyan/hermes-skills](https://github.com/iiixiyan/hermes-skills) · [Gitee 镜像](https://gitee.com/iiixiyan/hermes-skills)）

---

## 📂 分类索引

- [⚽ 体育竞猜](#-体育竞猜)
- [🤖 AI / 资讯](#-ai--资讯)
- [🛠 开发运维](#-开发运维)
- [🚀 部署 / CI](#-部署--ci)
- [🔧 GitHub 工具链](#-github-工具链)
- [🤝 社交 / 通讯](#-社交--通讯)
- [📚 软件开发](#-软件开发)
- [🧠 自主 AI Agent](#-自主-ai-agent)
- [📊 数据采集](#-数据采集)
- [🎯 彩票分析](#-彩票分析)
- [🧩 其他](#-其他)

---

## ⚽ 体育竞猜

### football-prediction `v10.35`
**竞彩足球比分预测核心引擎。** 世界杯/联赛/杯赛通用。基于泊松分布λ加权模型 + 46条规则链（F1~F46），从百家欧赔变化、亚盘升降、综合实力、核心伤停等维度分析，输出双选比分+单选比分。

- **已验证：** 100%方向 + 100%双选覆盖 + 逐场规则链追踪
- **最新规则：** F44 欧罗巴弱队客场进球 · F45 核心伤停λ修正 · F46 欧战客胜分歧
- **联赛支持：** 韩K/挪超/瑞超/芬超/英超/西甲/意甲/德甲/法甲/日职/澳超/美职/欧冠/世界杯

### bjdc-prediction `v5.9.0`
**北单（北京单场）让球胜平负综合预测体系。** 42条规则全量回测收敛，覆盖让球胜平负方向预测。

### zucai-14cai-prediction
**传统足彩14场胜负彩预测。** 胆/双选/全包策略分配 + 奖金优化模型。

### worldcup-7analyst
**世界杯7分析师独立评分预测体系。** 7维独立分析师各自打分，数学模型将分差转为胜平负/比分概率。

### football-data
**13大联赛数据查询。** 排名/赛程/比赛统计/xG/球员转会/身价。覆盖英超/西甲/德甲/意甲/法甲/美职/欧冠/世界杯等。

### 59itou-data-fetch
**59itou.com 数据采集。** 逐场获取北单/竞足比赛详情，9个Tab完整原始数据（阵容/战绩/欧指/亚指/情报/推荐/排名/盈亏）。

### beidan-okooo-prize-page
**北单开奖结果采集。** 通过okooo.com开奖页获取已开奖场次，比59itou更快的赛果数据源。

### data-collection-toolkit
**数据采集工具链选型框架。** 四件套优先级策略 + 足球API速查。

### football-data-sources
**足球赔率/基本面数据源速查。** 19个站点接口/覆盖/反爬对比 + 最佳采集管道推荐。

### codefun-scraper
**CodeFun2000 OJ题库采集。** 获取华为OD笔试真题，需Chrome登录Cookie认证。

---

## 🤖 AI / 资讯

### aihot
**中文 AI 资讯日报。** 实时查询 AI HOT (aihot.virxact.com)，获取当天AI圈资讯动态、大模型发布、AI 产品更新等。零配置，直接 curl 公开API。

### self-improvement
**持续改进记录器。** 自动捕捉命令失败、用户纠正、API错误、过时知识等learnings，并在关键任务前回顾。

---

## 🛠 开发运维

### hermes-agent
**Hermes Agent 配置/扩展。** 配置CLI/config/model/provider/tool/skill/voice/gateway/plugin等。

### hermes-administration
**Hermes 子系统管理。** cron故障排查、401认证修复、provider固定、升级迁移、内存provider集成。

### hermes-agent-skill-authoring
**Skill编写规范。** 前导metadata格式、验证器、目录结构标准。

### hermes-s6-container-supervision
**Docker s6监督树修改/调试。** 在Hermes Agent Docker镜像中新增服务、调试profile gateway。

### debugging-hermes-tui-commands
**Hermes TUI调试。** Python/gateway/Ink UI斜杠命令调试。

### systematic-debugging
**4阶段根因调试法。** 理解bug → 定位 → 修复 → 验证，全流程方法论。

### test-driven-development
**TDD红绿重构。** 测试先行，强制执行 RED-GREEN-REFACTOR 循环。

### requesting-code-review
**提交前代码审查。** 安全扫描 + 质量门禁 + 自动修复。

### python-debugpy
**Python远程调试。** pdb REPL + debugpy (DAP协议)。

### node-inspect-debugger
**Node.js远程调试。** --inspect + Chrome DevTools Protocol CLI。

### plan
**计划模式。** 写markdown计划到.hermes/plans/，禁止直接执行。

### spike
**一次性验证实验。** 快速验证想法是否可行，不进入生产。

### subagent-driven-development
**子代理驱动开发。** 通过 delegate_task 子代理执行计划（2阶段审查）。

### static-spa-debugging
**静态SPA白屏诊断。** GitHub Pages/GitLab Pages/Cloudflare Pages 部署的React/Vue SPA白屏崩溃诊断管线。

---

## 🚀 部署 / CI

### github-pages-deploy
**GitHub Pages 部署。** React/Vue/静态SPA，Vite构建，SPA路由，Actions CI/CD，KaTeX数学公式。

### github-pages-spa
**SPA子目录部署。** React (Vite) 单页应用部署到GitHub Pages子目录。

### github-pages-spa-deployment
**SPA路由+Base路径部署。** 含白屏调试、尾斜杠路由、大数据文件处理。

### edgeone-pages-deploy
**腾讯EdgeOne部署。** 前端/全栈项目发布到EdgeOne Pages。

### edgeone-pages-dev
**EdgeOne全栈开发。** Edge Functions/Cloud Functions/Middleware/KV Storage/WebSocket。

### external-skill-installation
**外部Skill安装。** 从ClawHub/GitHub仓库/原始SKILL.md URL安装skill。

### webhook-subscriptions
**Webhook事件驱动。** 订阅外部事件触发agent自动运行。

---

## 🔧 GitHub 工具链

### github-auth
**GitHub认证设置。** HTTPS tokens、SSH keys、gh CLI登录。

### github-pr-workflow
**PR全生命周期。** 分支→提交→开PR→CI→合并。

### github-code-review
**PR代码审查。** 查看diff，通过gh或REST API提交inline评论。

### github-issues
**Issue管理。** 创建/分派/打标签/分配，通过gh或REST API。

### github-repo-management
**仓库管理。** 克隆/创建/Fork仓库、管理remote、发布release。含GitHub↔Gitee跨平台镜像同步。

### codebase-inspection
**代码库统计。** 通过pygount统计代码行数/语言占比。

---

## 🤝 社交 / 通讯

### xurl
**X/Twitter CLI操作。** 发推/搜索/私信/媒体上传/v2 API。通过xurl CLI实现。

### QQ空间
**QQ空间运营助手。** 内容创作、相册管理、社交互动、数据分析。

### yuanbao
**元宝群管理。** @提及用户、查询群信息/成员。

### tencent-docs
**腾讯文档在线管理。** 创建/编辑/读取/搜索文档、知识库空间管理、文件导入导出。

### himalaya
**终端邮件客户端。** IMAP/SMTP协议，支持搜索/发送/管理邮件。

---

## 📚 软件开发

### od-study-note
**华为OD备考学习笔记生成器。** 从算法题库源文档生成小白友好型详细学习文档（含完整代码+思路讲解+多解法对比），推送到Gitee学习仓库。

### hermes-agent-skill-authoring
见 [🛠 开发运维](#-开发运维)

### debugging-hermes-tui-commands
见 [🛠 开发运维](#-开发运维)

### hermes-s6-container-supervision
见 [🛠 开发运维](#-开发运维)

---

## 🧠 自主 AI Agent

### claude-code
**委托 Claude Code CLI 编程。** 生成feature/PR，Claude Code独立执行编码任务。

### codex
**委托 OpenAI Codex CLI 编程。** 生成feature/PR，Codex独立执行编码任务。

### opencode
**委托 OpenCode CLI 编程。** 生成feature/PR审查。

### darwin-skill
**达尔文自动优化Skill。** 集成Microsoft Research SkillLens 9维评分体系 + SkillOpt验证门控设计 + 人工-in-the-loop检查点。自动评估SKILL.md并hill-climbing优化。

### kanban-orchestrator
**Kanban编排器。** 任务分解playbook + 反诱惑规则。

### kanban-worker
**Kanban工作器。** 生命周期自动注入，本skill提供场景深度细节。

### kanban-codex-lane
**Codex CLI Kanban集成。** Kanban worker用Codex CLI作为独立实现通道，Hermes保持任务生命周期/测试/交接所有权。

---

## 📊 数据采集

### data-collection-toolkit
见 [⚽ 体育竞猜](#-体育竞猜)

### football-data-sources
见 [⚽ 体育竞猜](#-体育竞猜)

### 59itou-data-fetch
见 [⚽ 体育竞猜](#-体育竞猜)

---

## 🎯 彩票分析

### dlt-lottery-analysis `v8.7.0`
**大乐透(DLT)分析。** 偏态回归核心号选取铁律 + 5注独立策略 + 8+3大底。

### ssq-lottery-analysis
**双色球(SSQ)分析。** 7种分析方法（含恒值号过滤+梅花易数区间直读）+ 5注Pro多策略覆盖 + 12种经典技巧集成。

### kl8-prediction
**快乐8(KL8)单期预测。** 176期×3500号码全量回测，四区均衡防盲区。

---

## 🧩 其他

### native-mcp
**MCP客户端连接。** 配置MCP servers (stdio/HTTP)，自动发现工具。

### jupyter-live-kernel
**Jupyter交互式Python。** 通过hamelnb内核运行即时Python代码。

### obsidian
**Obsidian笔记读写。** 在Obsidian vault中搜索/创建/编辑笔记。

### dogfood
**Web应用Bug探测QA。** 探索性QA：发现bug、收集证据、生成报告。

### godmode
**LLM越狱测试。** Parseltongue/GODMODE/ULTRAPLINIAN等技术用于红队测试。

---

## 📊 统计

| 指标 | 数值 |
|:----|:----:|
| **Skill 总数** | 65 |
| **分类数** | 15 |
| **开发语言** | Python / Shell / Markdown |
| **代码行数** | ~48,938 行 |
| **GitHub** | [iiixiyan/hermes-skills](https://github.com/iiixiyan/hermes-skills) |
| **Gitee** | [iiixiyan/hermes-skills](https://gitee.com/iiixiyan/hermes-skills) |

---

*自动同步自 Hermes Agent 实例 · 最后更新: 2026-07-10*
