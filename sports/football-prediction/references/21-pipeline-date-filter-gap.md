# Pipeline日期过滤器断层 (2026-06-20发现)

## 问题: Step 2 未按日期过滤

`worldcup-predict-all.py --date YYYY-MM-DD` 的Step 1正确按日期从新浪API获取比赛(该日仅3场:荷兰vs瑞典,德国vs科特迪瓦,厄瓜多尔vs库拉索), 但Step 2的v10引擎对所有存储的比赛执行预测(44场), 而非仅Step 1筛选出的比赛。

**症状**: 输出包含大量非当日比赛(过去+未来的所有场次)。

## 临时处理方案

手动从全量输出中提取当日场次:

```python
# 从全量输出中过滤当日比赛
# 已知当日4场(含59itou的跨日期比赛):
targets = {
    "荷兰vs瑞典", "德国vs科特迪瓦", 
    "厄瓜多尔vs库拉索", "突尼斯vs日本"
}
# 仅取这些场次的预测结果
```

## 跨API数据源缺口

**突尼斯vs日本(2026-06-21 12:00)** 的发现:

| API | 2026-06-20查询结果 | 原因 |
|:----|:-----------------|:-----|
| ❌ 新浪API jczqMatches | 不在结果中 | 按 比赛日(2026-06-21) 过滤 |
| ✅ 59itou API selectlist | 在销售日2026-06-20下 | 按 销售日(bet_date=2026-06-20) 分组 |

比赛时间晚于00:00的比赛会跨越到次日, 导致新浪API按比赛日查询时"漏掉"。

**处理方法**: 当日最后一轮(12:00档)比赛需同时检查59itou销售日分组。

## 手动预测流程(API缺失时)

当新浪API没有某场比赛的欧赔数据时:

```python
# 1. 从59itou获取SPF赔率近似欧赔
# SPF对59itou: {'0': 客胜, '1': 平, '3': 主胜}
o1_approx = float(spf['3'])  # 主胜SP -> o1
o3_approx = float(spf['0'])  # 客胜SP -> o3

# 2. 用scout_and_build获取基本面信号
signal, _ = scout_and_build(hn, gn, hf, af)

# 3. engine.predict_with_basics直接注入
h, a, rule, conf = predict_with_basics(
    signal, hn, gn, hf, af, rd,
    o1_approx, o3_approx,
    r1, c1, r2, c2, r3, c3  # 升/降家数从SPF变化趋势估算
)
```
