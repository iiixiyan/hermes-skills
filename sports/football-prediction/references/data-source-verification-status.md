# 数据源验证状态

> 2026-06-20 Playwright全自动集成时对各站的验证记录。

## ✅ 可用数据源

| 数据源 | URL模式 | 自动采集 | 数据类型 | 验证结果 |
|:-------|:--------|:--------|:---------|:---------|
| **titan007分析页** | `info.titan007.com/analysis/{id}cn.htm` | `automated_l2.py` | 天气/评分/伤停/杯赛排名/H2H/场均进球 | ✅ 5600-7300c, Playwright正常 |
| **500彩票网shuju页** | `odds.500.com/fenxi/shuju-{id}.shtml` | `automated_l3.py` | FIFA3期/阵容/伤病/澳门心水/战绩/未来赛程/主场客场 | ✅ 6200c, Playwright正常⚠️仅当前/未来 |
| **澳客网match页** | `okooo.com/soccer/match/{id}/odds/` | `automated_l3.py` | 身价/积分榜/比赛信息 | ✅ 762c, Playwright正常 |

## ⛔ 已验证不可用

| 数据源 | 期望数据 | 实际结果 | 结论 |
|:-------|:--------|:---------|:-----|
| **中国足彩网比赛分析页** `news.zgzcw.com/jczq/zx_{id}.shtml` | 赛季排名对比/40场走势/赔率方差 | 仅新闻文章(1796-1873c)，无结构化数据表 | ❌ 唯一能找到的是新闻文章，非结构化比赛数据 |
| **中国足彩网analysis/schedule/detail** `zgzcw.com/lottery/jczq/match/analysis` | 比赛数据 | 300c "页面不存在" | ❌ 404 |
| **500彩票网已完赛比赛** `shuju-{sid}.shtml` (sid为历史比赛) | 历史数据 | 9c "暂无该场比赛的数据" | ❌ 仅当前/未来有效 |

## 📌 已废弃/替代

| 文件 | 替代方案 | 原因 |
|:----|:--------|:-----|
| `all_sources_collector.py` | `automated_l2.py` + `automated_l3.py` | 旧版需手动browser→innerText模式，已升级为Playwright全自动 |
| `parse_zgzcw()` 函数 | 无（数据不可用） | 中国足彩网仅有新闻文章，无结构化比赛数据表 |
