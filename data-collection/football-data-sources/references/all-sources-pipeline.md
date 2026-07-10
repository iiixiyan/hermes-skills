# 全站自动采集管线 (L1+L2+L3)

> 2026-06-20更新：`all_sources_collector.py` (手动浏览器) → `automated_l2.py` + `automated_l3.py` (Playwright全自动)
> 一站式: `automated_all.py` → `collect_all()` + `predict_with_all()`

## 三级数据源分类

| 级别 | 采集方式 | 数据源 | 覆盖范围 | 代码 |
|:----|:--------|:-------|:---------|:-----|
| **L1-自动** | 纯API (curl/requests) | 新浪API(欧赔8参数+SP+排名) + 59itou API(综合实力分) | 所有比赛 (已完赛+未来) | `fundamental_scout.py` |
| **L2-自动** | Playwright → titan007分析页 | 天气/球员评分/阵容伤停/杯赛排名/场均进球/H2H | 所有比赛 (titan007历史数据) | `automated_l2.py` |
| **L3-自动** | Playwright → 500彩票网shuju页 + 澳客网 | FIFA排名3期/预计阵容/伤病停赛/澳门心水/未来赛程/身价 | **仅当前/未来比赛** (完赛显示"暂无数据") | `automated_l3.py` |

## 采集流程

```
worldcup-predict-all.py ARGS
  │
  ├── L1 (always) ──── 新浪API → 欧赔8参数 + FIFA排名
  │                   59itou API → 综合实力分(0-100)
  │                   → form_signal → v10引擎 → 预测
  │
  ├── --browser 模式 (可选) ──── Playwright + 系统Chromium启动
  │                   
  │   L2: Playwright → info.titan007.com/analysis/{id}cn.htm
  │   │              → 天气/评分/伤停/排名/H2H → form_signal
  │   │              → (所有比赛有效，含历史数据)
  │   │
  │   L3: Playwright → odds.500.com/ → 赛程匹配队名 → shuju-{id}.shtml
  │   │              → FIFA3期/阵容/伤病/澳门心水/未来赛程/主客场战绩 → form_signal
  │   │              → (仅当前/未来比赛有效)
  │   │   Playwright → okooo.com/soccer/league/16/schedule/
  │   │              → 赛程匹配队名 → match/{id}/odds/
  │   │              → 身价(两队总€) → form_signal
  │   │
  │   └── 汇聚: merge(L1_signal, L2_signal, L3_signal) → form_signal
  │                    → v10引擎 → 预测
  │
  └── 输出: 🎯 比分预测 + 数据源标记
```

## key 发现 (2026-06-20 28场全量回测)

| 发现 | 值 |
|:----|:---|
| L2(titan007)对预测的影响 | **0场差异** — 规则链已通过L1隐含覆盖 |
| L3(500彩票网) | 仅当前/未来比赛有数据 |
| 中国足彩网 | 只有新闻文章，**无结构化比赛数据表** |
| 系统Chromium版本 | `/usr/bin/chromium-browser` v148 ✅ |
| Playwright配置 | `executable_path='/usr/bin/chromium-browser', headless=True, args=['--no-sandbox']` |

## 快速用法

```python
from playwright.sync_api import sync_playwright
from automated_all import collect_all, predict_with_all

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path='/usr/bin/chromium-browser',
        headless=True,
        args=['--no-sandbox']
    )
    # 全自动采集L2+L3
    data = collect_all(browser, h_name, a_name, schedule_id)
    # 预测 (L1+L2+L3)
    h, a, rule, conf, sig = predict_with_all(h, g, ..., browser_data=data)
```

## 命令行

```bash
python3 worldcup-predict-all.py --date YYYY-MM-DD           # L1 only
python3 worldcup-predict-all.py --date YYYY-MM-DD --browser  # L1+L2+L3
```
