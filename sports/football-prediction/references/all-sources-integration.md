# ⚡ 全站基本盘数据采集与汇聚

## 采集管线 (v5.7.0 — L2+L3全自动化版)

```
L1-自动 (每次预测无条件执行):
  新浪API(欧赔8参数+SP+排名) ──→ 59itou API(综合实力分) ──→ form_signal ──→ v10引擎

L2-自动 (--browser模式, Playwright→titan007):
  Playwright → info.titan007.com/analysis/{id}cn.htm
    ├ 天气温度      → temperature, weather
    ├ 球员评分      → avg_rating_diff
    ├ 阵容伤停      → injury_impact_h/a
    ├ 首发阵容      → lineup_known
    ├ 杯赛积分排名  → group context
    ├ 场均进球      → goal_diff
    └ H2H历史       → h2h context
  → 代码: automated_l2.py (ID范围: 2906740+)

L3-自动 (--browser模式, Playwright→500彩票网+澳客网):
  500彩票网: odds.500.com/首页赛程→匹配队名→shuju-{id}.shtml
    ├ FIFA排名3期+积分变化
    ├ 预计阵容(首发+替补)
    ├ 伤病+停赛名单
    ├ 澳门心水推荐
    ├ 近期战绩(10场+盘路)
    ├ 未来赛程+相隔天数
    └ 主客场战绩三分栏
  → 代码: automated_l3.py → find_500_id() + parse_500() (ID: 13592xx)
  → ⚠️ 仅当前/未来比赛有效(完赛返回"暂无数据")
  
  澳客网: okooo.com/soccer/league/16/schedule/→匹配队名→match/{id}/odds/
    └ 球队身价(两队总€)
  → 代码: automated_l3.py → find_okooo_id() + parse_okooo() (ID: 131xxxx)

一站式全数据:
  automated_all.py → collect_all() + predict_with_all()
  → worldcup-predict-all.py --date YYYY-MM-DD --browser

已废弃（无结构化数据）:
  中国足彩网 zgzcw.com → 仅有新闻文章解析, 无结构化数据表
  all_sources_collector.py → 已被automated_l2/l3替代
```

## 快速使用

```bash
# API only
python3 worldcup-predict-all.py --date 2026-06-20

# API + Playwright浏览器L2
python3 worldcup-predict-all.py --date 2026-06-20 --browser
```

```python
# 代码中集成L2
from playwright.sync_api import sync_playwright
from automated_l2 import collect_l2_data, predict_with_l2

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path='/usr/bin/chromium-browser',
        headless=True
    )
    t7_data, found = collect_l2_data(browser, schedule_id, h_name, a_name)
    result = predict_with_l2(h, g, fh, fa, rd, 
                            o1, o3, r1, c1, r2, c2, r3, c3,
                            t7_data=t7_data)
```

## 各数据源独有数据

| 数据 | 独占来源 | 不可替代性 | 集成状态 |
|:----|:--------|:----------|:---------|
| 球员评分 | titan007 | 唯一有结构化评分的站 | ✅ L2-自动 |
| 天气温度℃ | titan007 | 精确到温度 | ✅ L2-自动 |
| 综合实力(0-100) | 59itou API | API直取最快 | ✅ L1-自动 |
| 欧赔53家+指数变化 | 新浪API | 唯一API 1秒返回 | ✅ L1-自动 |
| FIFA排名3期变化 | 500彩票网 | 唯一提供趋势的站 | 🔧 L3-就绪 |
| 预计阵容+伤病+停赛 | 500彩票网 | 唯一三合一的站 | 🔧 L3-就绪(已完赛无数据) |
| 澳门心水分析 | 500彩票网 | 唯一专家文字分析 | 🔧 L3-就绪 |
| 球员身价 | 澳客网 | 唯一 | 🔧 L3-就绪 |
| 进球/助攻统计 | 澳客网 | 唯一 | 🔧 L3-就绪 |
| 40场走势图 | 中国足彩网 | 唯一 | 🔧 L3-就绪 |
| 赔率方差分析 | 中国足彩网 | 唯一 | 🔧 L3-就绪 |
| 主客场战绩分开 | 500彩票网 | 唯一 | 🔧 L3-就绪 |

## 当前集成状态

- ✅ **`automated_l2.py`** — Playwright全自动L2采集titan007 (已验证28场)
- ✅ **`fundamental_scout.py`** — 59itou综合实力自动采集 (L1)
- ✅ **`all_sources_collector.py`** — 全站解析器汇聚引擎 (L3就绪)
- 🔧 500彩票网 → Playwright管线待集成 (已完赛比赛返回"暂无该场比赛的数据", 仅对未来比赛有效)
- 🔧 中国足彩网 → Playwright管线待构建
- 🔧 澳客网 → Playwright管线待构建
