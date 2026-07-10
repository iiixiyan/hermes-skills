---
name: football-data-sources
description: 足球赔率/基本面数据源速查 — 19个站点的接口/覆盖/反爬对比，含最佳采集管道推荐
category: data-collection
version: 2.0.0
---

# 足球数据源速查手册

> 实测40+站点，精选19个可用。2026-06-20验证。

---

## 一、API类（可编程，无浏览器，优先使用）

### 1️⃣ 新浪竞彩API ⭐⭐⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **基础URL** | `https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000` |
| **接口** | `cat1=jczqMatches`(竞彩SP/赛果/比分) `cat1=footballMatchOddsEuro`(53家欧赔) `cat1=footballMatchOddsAsia`(17家亚盘) `cat1=footballMatchDetail`(排名/天气/轮次) `cat1=footballMatchOddsEuroChange`(欧赔变化历史) |
| **响应结构** | `d['result']['data']` — 注意不是 `d.data` 也不是 `d.code` |
| **欧赔** | 53家公司，字段：o1Ini/o1New(主胜) o2Ini/o2New(平) o3Ini/o3New(客胜) |
| **亚盘** | 17家公司，字段：o3IniStr/o3NewStr(盘口) o1Ini/o1New(主水) o2Ini/o2New(客水) |
| **必带参数** | `__caller__=wap&__version__=1.0.0&__verno__=10000` — 缺`__version__`静默返空! |
| **反爬** | ❌ 无 |
| **速度** | ⚡ 1-3秒 |
| **Python示例** | `json.loads(urllib.request.urlopen(url).read())['result']['data']` |

### 2️⃣ 59itou API ⭐⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **URL** | `https://apic.jindianle.com/api/match/selectlist?platform=koudai_mobile&_prt=https&ver=20180101000000&hide_more=1&single_support=2` |
| **竞足** | `lotteryId=90` → 比赛列表含SP+FIFA排名+让球数 |
| **北单** | `lotteryId=45` → **唯一北单API数据源** |
| **响应结构** | `d['data']` — 按日期key分组的字典 |
| **排名字段** | `m['rank'][0]['rank']`(主队) `m['rank'][1]['rank']`(客队) |
| **注意** | 无欧赔详表，无亚盘数据 |
| **反爬** | ❌ 无 |
| **速度** | ⚡ 1-2秒 |

### 3️⃣ 竞彩官方API ⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **URL** | `https://webapi.sporttery.cn/gateway/uniform/fb/1.0/getMatchResult?method=result` |
| **method参数** | `result`(赛果比分) `concern`(赛程SPF) |
| **官方赛果** | 含半全场比分、matchStatus，**最权威** |
| **反爬** | 🚫 EdgeOne WAF — 需完整5头(UA+Referer+Accept+Accept-Language+Origin) |
| **速度** | ⚡ 2-5秒(含WAF) |
| **验证** | 2026-06-19 curl 403，Playwright可行 |

### 4️⃣ SofaScore API ⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **URL** | `https://api.sofascore.com/api/v1/` |
| **接口** | `/sport/football/events/live`(直播) `/match/{id}/odds`(赔率) |
| **格式** | 纯净JSON |
| **特点** | 球员评分+热力图+统计 |
| **速度** | ⚡ 1-3秒 |

---

## 二、浏览器类（中文站）

### 5️⃣ 500彩票网 odds.500.com ⭐⭐⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **URL模式** | `https://odds.500.com/fenxi/shuju-{matchId}.shtml`(基本面) |
| **当前比赛ID范围** | **13592xx** (如1359204=荷兰vs瑞典) — 从首页赛程自动获取 |
| **Playwright自动采集** | ✅ `automated_l3.py` → `find_500_id()` + `parse_500()` |
| **百家欧赔** | ✅ **100+家赔率公司** — 国内最全 |
| **FIFA排名** | ✅ **唯一有3期排名变化+积分的** |
| **预计阵容** | ✅ 阵型+首发+替补+伤病+停赛 |
| **澳门心水** | ✅ 文字分析+推介方向 |
| **未来赛程** | ✅ 含相隔天数 |
| **近期战绩** | ✅ 10场盘路+赛事明细 |
| **主客场战绩** | ✅ 总/主/客三分栏 |
| **⚠️ 已完赛比赛** | ❌ 返回"暂无数据" — **仅当前/未来比赛有效** |
| **反爬** | 浏览器正常 ✅ Playwright可用 |

### 6️⃣ 球探体育 zq.titan007.com ⭐⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **URL** | `https://zq.titan007.com/analysis/{analysisId}cn.htm` (注意是zq不是info) |
| **分析ID范围** | 世界杯比赛在 **2906943-2907370** 区间（从赛程页「析」链接获取） |
| **Playwright自动采集** | ✅ `automated_l2.py` → `fetch_titan007()` → `titan007_to_form_signal()` |
| **提取数据** | 天气(精确到℃) / 球员评分(平均评分5.0-10.0) / 阵容伤停 / 杯赛积分排名 / 场均进球 / H2H / 近期战绩 |
| **搜索接口** | ❌ `/Search/` 返回404，只能从联赛页JS提取analysisId |
| **反爬** | 浏览器正常 ✅ Playwright可用，但批量采集需3秒间隔 |
| **历史比赛** | ✅ 已完赛分析页仍有完整数据(body 6000+ chars) |

### 7️⃣ 中国足彩网 zgzcw.com ⭐⭐
| 维度 | 内容 |
|:----|:------|
| **URL** | `https://news.zgzcw.com/jczq/zx_{id}.shtml`(比赛分析新闻) |
| **数据类型** | ⚠️ **仅新闻文章** — 无结构化比赛数据表(FIFA排名/走势/方差在新闻正文中偶有提及但不可靠) |
| **⚠️ 2026-06-20验证** | ❌ 比赛分析页(analysis/schedule/detail)均返回404 |
| **原期望数据**(parse_zgzcw中) | 赛季排名对比/40场走势/赔率方差 — **实际不可用** |
| **反爬** | 浏览器正常 ✅ |

### 8️⃣ 雷速体育 www.leisu.com ⭐⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **功能** | 直播+数据+资料库 |
| **赛事直播** | ✅ 全球足球/篮球直播(含动画) |
| **赛事情报** | ✅ 每场情报链接 |
| **资料库** | ✅ 世界杯/五大联赛/中超 |
| **反爬** | ⚠️ 详情页阿里云WAF 405阻断 |
| **特点** | Vue store数据需console提取 |

### 9️⃣ 澳客网 www.okooo.com ⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **URL** | `https://www.okooo.com/soccer/` |
| **世界杯联赛页** | `https://www.okooo.com/soccer/league/16/schedule/` |
| **比赛详情URL** | `https://www.okooo.com/soccer/match/{matchId}/odds/` (欧赔/身价) |
| **比赛ID** | 当前比赛 **1315877**+ 范围 — 从赛程页自动匹配队名获取 |
| **Playwright自动采集** | ✅ `automated_l3.py` → `find_okooo_id()` → `parse_okooo()` |
| **身价** | ✅ 两队总身价(€) — 如8.37亿€ vs 4.27亿€ |
| **球员数据** | ✅ 球员一览页面含身价/进球/助攻/红黄牌 |
| **积分榜** | ✅ 小组/联赛积分榜 |
| **⚠️ 注意** | 比赛详情页正文较短(~762c)，身价和积分榜是主要可用数据 |
| **反爬** | 浏览器正常 ✅ Playwright可用 |

### 🔟 澳客网开奖页（⭕ 赛果唯一权威数据源）
| 维度 | 内容 |
|:----|:------|
| **URL** | `https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=SportteryScore&LotteryNo={SALE_DATE}` |
| **作用** | **竞足赛果/比分/半场/SP的唯一天然数据源** |
| **请求方式** | curl + 标准UA + Referer |
| **编码** | GBK → 必须 `iconv -f GBK -t UTF-8//IGNORE` 解码 |
| **响应结构** | HTML `<td>` 表格，列序：编号 \| 主队 \| VS \| 客队 \| 比分半场 \| SP |
| **比分格式** | `"5:0半场3:0"` — 连在一起的字符串，需正则拆分 |
| **SP格式** | `"5:015.00"` — 比分+SP连写，需正则 `(\\d+):(\\d+)([\\d.]+)` 拆分 |
| **更新速度** | 赛后1-2小时 |
| **日期参数** | `LotteryNo` 用**销售日期**（非比赛日期）；凌晨比赛<10:00归前销售日 |
| **编号前缀** | 1=周一 2=周二 3=周三 4=周四 5=周五 6=周六 7=周日 |

### 🔟 即嗨体育 www.jihai8.com ⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **功能** | 即时比分+资料库 |
| **覆盖** | ✅ 全球足球比分+赛程 |
| **新闻** | ✅ 转会/赛事新闻 |
| **反爬** | 浏览器正常 ✅ |

### 1️⃣1️⃣ 天天盈球 ttyingqiu.com ⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **URL** | `https://www.ttyingqiu.com/live/zq/matchDetail/info/{matchId}` |
| **阵容** | ✅ 首发+阵型+球员评分+身价 |
| **伤停** | ✅ 伤停信息+解读 |
| **有利不利因素** | ✅ 球队有利不利分析 |
| **精选情报** | ✅ 战术/天气/赛程 |
| **状态** | ⚠️ 2026-06-19 服务器500错误 |

---

## 三、浏览器类（国际站）

### 1️⃣2️⃣ OddsPortal oddsportal.com ⭐⭐⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **定位** | 全球最大赔率对比站 |
| **欧赔1X2** | ✅ 全市场对比 |
| **亚洲盘口** | ✅ **Asian Handicap** |
| **大小球O/U** | ✅ Over/Under |
| **URL** | `https://www.oddsportal.com/football/{league}/` |
| **特点** | 国际市场信号参考 |

### 1️⃣3️⃣ FlashScore flashscore.com ⭐⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **定位** | 全球实时比分+赔率对比 |
| **赔率对比** | ✅ Odds comparison |
| **WebSocket** | ✅ 实时更新 |
| **世界杯** | `//flashscore.com/football/world/world-championship-2026/` |

### 1️⃣4️⃣ 7M Sport 7msport.com ⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **中英双语** | ✅ 亚洲视角 |
| **预测系统** | ✅ 星级评分预测 |
| **赔率** | ✅ 有赔率页面 |

### 1️⃣5️⃣ Soccerway soccerway.com ⭐⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **赛果+赛程** | ✅ 全球联赛 |
| **赔率** | ✅ 含odds数据 |
| **特点** | 数据量大，界面清晰 |

### 1️⃣6️⃣ ESPN Soccer espn.com/soccer ⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **数据** | ✅ 赛果+统计 |
| **赔率** | ✅ 含line/spread |
| **特点** | 英文，全球覆盖 |

### 1️⃣7️⃣ SofaScore sofascore.com ⭐⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **球员评分** | ✅ 可视化 |
| **统计** | ✅ 热力图+数据 |
| **赔率API** | ✅ REST JSON |

### 1️⃣8️⃣ FotMob fotmob.com ⭐⭐⭐
| 维度 | 内容 |
|:----|:------|
| **移动友好** | ✅ 手机端设计 |
| **比分** | ✅ 全球联赛 |

---

## 四、数据覆盖矩阵

### 赔率数据

| 网站 | 欧赔覆盖面 | 亚盘 | 大小球 | 波胆 | 竞彩SP | 北单SP |
|:----|:---------:|:----:|:-----:|:----:|:------:|:------:|
| 新浪竞彩API | **53家** | **17家** | ❌ | ❌ | ✅全玩法 | ❌ |
| 500彩票网 | **100+家** | ✅ | ✅ | ✅ | ❌ | ❌ |
| 球探体育 | ✅百家 | ✅ | ✅ | ❌ | ❌ | ❌ |
| OddsPortal | ✅全球 | ✅Asian | ✅O/U | ⚠️ | ❌ | ❌ |
| 59itou API | ❌ | ❌ | ❌ | ❌ | ✅SP | ✅🚀 |
| 竞彩官方API | ❌ | ❌ | ❌ | ❌ | ✅官方 | ❌ |

### 基本面数据

| 网站 | 阵容/阵型 | 球员评分 | 伤停 | FIFA排名 | 排名详情 | 近期战绩 | H2H盘路 | 天气场地 | 未来赛程 | 走势图 |
|:----|:--------:|:--------:|:----:|:--------:|:--------:|:--------:|:-------:|:--------:|:--------:|:------:|
| **500彩票网** | ✅+伤病停赛 | ❌ | ✅ | ✅3期 | ✅总/主/客 | ✅10场+盘路 | ✅全记录 | ❌ | ✅+天数 | ✅ |
| **球探体育** | ✅+评分 | **✅🚀** | ✅+原因 | ❌ | ✅杯+联 | ✅10场+率 | ✅3场 | **✅℃** | ❌ | ❌ |
| **澳客网** | ✅+身价 | ✅进球助攻 | ❌ | ❌ | ✅小组 | ✅10场+赔率 | ✅2场 | ❌ | ❌ | ✅Canvas |
| **中国足彩网** | ❌ | ❌ | ❌ | ✅单期 | ✅赛季对比 | ✅50场+盘路 | ✅5场 | ✅场+天气 | ✅5场 | ✅40场 |
| **新浪API** | ❌ | ❌ | ❌ | ❌ | ✅排名数字 | ❌ | ❌ | ✅weather | ❌ | ❌ |
| **天天盈球** | ⚠️ | ✅身价评分 | ⚠️ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |

---

## 五、最佳采集管道（2026-06-20更新 — Playwright全自动）

```
═══════ L1-自动 (纯API, 始终启用) ═══════
  新浪竞彩API(欧赔8参数+SP+排名) + 59itou API(综合实力分)
  → 代码: fundamental_scout.py / worldcup-predict-v10.py

═══════ L2-自动 (Playwright, --browser启用) ═══════
  球探体育 titan007 → 天气/评分/伤停/杯赛排名/H2H/场均进球
  → 代码: automated_l2.py
  → URL: zq.titan007.com/analysis/{id}cn.htm (ID: 2906943+)
  → ⚠️ `/Search/` 404, 需从联赛页JS提取ID, 批量3秒间隔

═══════ L3-自动 (Playwright, --browser启用) ═══════
  500彩票网 shuju页 → FIFA排名3期/预计阵容/伤病/澳门心水/未来赛程/主客场战绩
  → 代码: automated_l3.py (find_500_id → parse_500)
  → URL: odds.500.com/fenxi/shuju-{id}.shtml (ID: 13592xx)
  → ⚠️ 仅当前/未来比赛有效
  
  澳客网 match页 → 球队身价(两队总€)/积分榜
  → 代码: automated_l3.py (find_okooo_id → parse_okooo)
  → URL: okooo.com/soccer/match/{id}/odds/ (ID: 131xxxx)

═══════ 一站式管线 ═══════
  automated_all.py → collect_all() + predict_with_all()
  → worldcup-predict-all.py --date YYYY-MM-DD --browser

═══════ 已废弃（结构数据不可用） ═══════
  中国足彩网 zgzcw.com → 仅有新闻文章, 无结构化数据表
  all_sources_collector.py → 已被automated_l2/l3替代(旧的手动浏览器模式)
```

## 六、全站汇聚引擎

通过 `automated_all.py` (football-prediction skill) 一站式采集L1+L2+L3。

- L2: `automated_l2.py` — Playwright → titan007 分析页 → form_signal
- L3: `automated_l3.py` — Playwright → 500彩票网 shuju页 + 澳客网 match页 → form_signal
- 管线: `automated_all.py` → `collect_all()` + `predict_with_all()`

> `all_sources_collector.py` (旧手动浏览器模式) 已废弃，由 `automated_l2.py` + `automated_l3.py` 替代。

详细管线见 `references/all-sources-pipeline.md`。

## 七、已关站/不可达清单

| 网站 | 原因 |
|:----|:------|
| 360彩票 cp.360.cn | 2022年停止服务 |
| 大赢家 win007.com | 域名不通 |
| 搜达足球 sodasoccer.com | 域名不通 |
| 竞彩258 jc258.com | 域名不通 |
| 彩客网 310v.com | 域名不通 |
| 捷报比分 jbscore.com | DNS失败 |
| 网易彩票 163.com | 域名不通 |
| OddsChecker | Cloudflare拦截 |
| WhoScored | Cloudflare拦截 |
| Transfermarkt | 人机验证 |
| Bet365 | 国内不可达 |
