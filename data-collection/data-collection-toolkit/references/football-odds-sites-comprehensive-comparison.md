# 足球基本盘（赔率/亚盘/大小球）网站全面对比

> 实测于 2026-06-19~20 | 测试40+站点，19个可用

---

## 第1梯队：API（无浏览器，优先使用）

### ① 新浪竞彩API ⭐⭐⭐⭐⭐
- **地址:** `//mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000`
- **欧赔53家初即赔:** `cat1=footballMatchOddsEuro&matchId={id}`
- **亚盘17家:** `cat1=footballMatchOddsAsia&matchId={id}`
- **竞彩SP全玩法:** `cat1=jczqMatches&date=YYYY-MM-DD`
- **变化时间序列155条+:** `cat1=footballMatchOddsEuroChange`
- **比赛详情(排名/天气):** `cat1=footballMatchDetail&matchId={id}`
- **2026-06-19验证:** data结构从dict变list，matchesCount单独字段，核心数据不变
- ✅ 无反爬，纯净JSON

### ② 59itou API ⭐⭐⭐⭐
- **地址:** `//apic.jindianle.com/api/match/selectlist?_=1&lotteryId={90竞足|45北单}&date=YYYYMMDD`
- **数据:** 比赛列表、SP赔率、FIFA排名、让球数
- **唯一北单API来源**（lotteryId=45）
- ✅ 无反爬，纯净JSON

### ③ 竞彩官方API ⭐⭐⭐
- **地址:** `//webapi.sporttery.cn/gateway/uniform/fb/1.0/getMatchDataPageListV1.qry`
- **赛程SP:** `method=concern` → SPF赔率(h/d/a)
- **赛果:** `method=result` → 比分+半全场
- 🚫 EdgeOne WAF拦截curl，需完整UA+Referer+Accept+Accept-Language+Origin五件头
- Playwright浏览器可行

### ④ SofaScore API ⭐⭐⭐
- **地址:** `//api.sofascore.com/api/v1/`
- **端点:** `/sport/football/events/live`(直播) `/match/{id}/odds`(赔率)
- ✅ REST JSON可访问

---

## 第2梯队：中文浏览器站

### ⑤ 500彩票网 odds.500.com ⭐⭐⭐⭐⭐
- **URL:** `//odds.500.com/fenxi/ouzhi-{scheduleId}.shtml`
- **百家欧赔100+家**（国内最全），初即赔双列对比
- 让球指数、亚盘对比、大小指数、**波胆赔率**、走势分析、凯利指数
- 赛前积分榜
- ✅ 浏览器正常

### ⑥ 球探体育 info.titan007.com ⭐⭐⭐⭐
- **URL:** `//info.titan007.com/analysis/{scheduleId}cn.htm`
- 百家欧赔、亚盘变化、大小球指数、H2H、技术统计
- 资料库：联赛/球队/球员/转会
- 即时比分: `//live.titan007.com`
- ✅ 浏览器正常

### ⑦ 中国足彩网 zgzcw.com ⭐⭐⭐⭐
- **URL:** `//www.zgzcw.com`
- 赔率中心、竞足带SP、**北单**、世界杯全程赛程
- 特色：310星象图、AI大数据、连红榜
- ✅ 浏览器正常

### ⑧ 澳客网 okooo.com ⭐⭐⭐⭐
- **URL:** `//www.okooo.com/soccer/`
- 100+联赛覆盖(五大/中超/J/K/巴甲等)
- 赛事一览、球队一览、球员一览
- 赔率分析页面
- ✅ 浏览器正常

### ⑨ 天天盈球 ttyingqiu.com ⭐⭐⭐
- **URL:** `//www.ttyingqiu.com/live/zq/matchDetail/info/{matchId}`
- **基本面最强：** 首发+阵型+球员评分+身价、伤停解读、有利/不利因素
- 赔率页: `/odds/{matchId}`
- ⚠️ 2026-06-19 服务器500，可能不稳定

### ⑩ 雷速体育 leisu.com ⭐⭐⭐
- **URL:** `//www.leisu.com/`
- 赛事直播、资料库、赛事情报
- Vue store数据需console提取
- ✅ 浏览器正常

---

## 第3梯队：国际站（可访问）

### ⑪ OddsPortal oddsportal.com ⭐⭐⭐⭐⭐
- **全球最大赔率对比站**
- 欧赔1X2全市场对比、**亚洲盘口(Asian)**、**大小球(O/U)**
- `//www.oddsportal.com/football/{league}/`
- ✅ 浏览器可访问

### ⑫ FlashScore flashscore.com ⭐⭐⭐⭐
- 全球实时比分+赔率对比(Odds comparison)
- 世界杯: `/football/world/world-championship-2026/`
- 1000+比赛, 90+国家, WebSocket实时
- ✅ 浏览器可访问

### ⑬ Soccerway soccerway.com ⭐⭐⭐⭐
- 足球比分+赛果+数据
- ✅ 浏览器可访问

### ⑭ 7M Sport 7msport.com ⭐⭐⭐
- 比分+星级预测+赔率，中英双语
- ✅ 浏览器可访问

### ⑮ ESPN Soccer espn.com/soccer ⭐⭐⭐
- 赛果/赛程/统计/赔率(line/spread)
- ✅ 浏览器可访问

---

## 已关站/不可达

| 网站 | 原因 |
|:----|:------|
| 360彩票 cp.360.cn | **2022年已停服** |
| 网易彩票 caipiao.163.com | 域名不通 |
| 大赢家 win007.com | 域名不通 |
| 搜达足球 sodasoccer.com | 域名不通 |
| 竞彩258 jc258.com | 域名不通 |
| 彩客网 310v.com | 域名不通 |
| 猎球者 lieqiuzhe.com | 已变电影站 |
| 捷报比分 jbscore.com | DNS失败 |
| OddsChecker oddschecker.com | Cloudflare拦截 |
| WhoScored whoscored.com | Cloudflare拦截 |
| Transfermarkt transfermarkt.com | 人机验证 |
| Bet365/Pinnacle | 国内不可达 |

---

## 🎯 最优数据管道

```
赔率数据 → 新浪竞彩API(53家欧赔+17家亚盘) + 500彩票网(100+家补充)
北单独用 → 59itou API（唯一北单数据源）
基本面   → 天天盈球（阵容/伤停）
国际对比 → OddsPortal（含亚洲盘口）+ FlashScore（实时对比）
官方赛果 → 竞彩官方API（Playwright绕过WAF）
```
