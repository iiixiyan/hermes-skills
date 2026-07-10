# 世界杯单独回测工作流

> 适用场景: skill优化前需要对所有已完赛世界杯比赛进行独立回测
> 核心原则: 不参考历史赛果——从API拉取赛前欧赔数据后独立运行引擎预测，再对比实际赛果

## 工作流（5步）

### 第1步：获取所有已完赛比赛列表

```python
# 用新浪API jczqMatches + dpc=1 扫所有可能的日期
for date in range_dates:
    url = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000&cat1=jczqMatches&gameTypes=spf&date={date}&isAll=1&dpc=1"
    # 筛选 league='世界杯' 且有比分 (score1/score2) 的比赛
```

注意：
- `dpc=1` 参数返回已完赛比赛，队名字段为 `team1`/`team2`，联赛名字段为 `league`
- 无 `dpc` 时返回未来比赛的 `hostName`/`guestName`
- `showSellStatus='3'` = 完赛

### 第2步：拉取欧赔数据

```python
# 对每个 matchId 拉取欧赔
url = f"https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000&cat1=footballMatchOddsEuro&matchId={mid}"
```

计算8参数 (r1/c1/r2/c2/r3/c3) + 百家平均初赔/即赔：
```python
ups = [0,0,0]; downs = [0,0,0]
for o in odds_list:
    if float(o['o1New']) > float(o['o1Ini']): ups[0] += 1
    elif float(o['o1New']) < float(o['o1Ini']): downs[0] += 1
    # 同上 for o2(平) 和 o3(客)
```

### 第3步：运行引擎预测

```python
import importlib.util
spec = importlib.util.spec_from_file_location("v10", "scripts/worldcup-predict-v10.py")
v10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v10)

h_pred, a_pred, rule, conf = v10.predict(
    h=home, g=away, fh=fh, fa=fa, o1=o1, o3=o3,
    r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3, rd=rd,
)
```

⚠️ **每次改引擎后必须清缓存**：
```bash
rm -rf /root/.hermes/skills/sports/football-prediction/scripts/__pycache__/
```

### 第4步：对比实际赛果

```python
actual_h, actual_a = [int(x) for x in score.split('-')]
pred_h, pred_a = [int(x) for x in s1.split('-')]
dev = abs(pred_h - actual_h) + abs(pred_a - actual_a)
```

方向判定：`'胜' if actual_h > actual_a else ('平' if actual_h == actual_a else '负')`

### 第5步：分析偏差模式并优化skill

按**规则链(rule)**分组统计偏差≥2的比赛，找出高频失败模式。

v10.17发现的常见模式:
- P11-Big-Draw平衡局分胜负颠覆
- R10B/R10E-Boom-Big过度乐观(fd≤15不应触发)
- R16-SplitS-D碾压局保守(fd≥50应加开大胜)
- R3出线/淘汰战意分歧(pts缺失)

每次优化后更新SKILL.md:
1. 更新 header 回测统计（精确命中率/双选率/方向准确率/偏差≤1球率）
2. 更新 changelog
3. 将逐场明细存入 reference 文件 `v10.XX-full-backtest-Nmatch.md`

## ⚠️ 陷阱

- **FIFA排名差异**: Sina API返回的FIFA排名可能与该届比赛官方排名不同。R32需手动传入正确值
- **R3 pts缺失**: 引擎 `_calc_motivation(0, fh)` 会返回"已淘汰·无心恋战"降权。未知pts应传 `-1`
- **`.pyc`缓存**: 每次引擎修改后必须 `rm -rf __pycache__/`
- **回测是快照**: 新浪API返回的是比赛结束时最后的欧赔快照，非赛前。但8参数反映了变化趋势

## 🚨 数据源赛果获取：ESPN > 新浪API（2026-07-02实践验证）

### 问题
新浪API `dpc=1` 模式在比赛结束后的数小时内 `score1/score2` 为空字符串（status=1或2）。世界杯R32淘汰赛已验证：赛后3+小时新浪仍未更新比分。

### 解决方案：ESPN scoreboard 作即时赛果源

**操作步骤：**
1. 浏览器导航到 `https://www.espn.com/soccer/scoreboard/_/league/fifa.world/date/YYYYMMDD`
2. 用 `browser_console` 或JavaScript提取比分：

```javascript
// 从ESPN页面提取所有比赛比分（DOM方式）
document.querySelectorAll('[class*="ScoreCell"]').forEach(el => {
  console.log(el.textContent.trim().replace(/\\s+/g, ' '));
});
// 输出示例: "USA 0 BIH 0 15' | ENG 2 COD 1 FT | BEL 3 SEN 2 AET"
```

3. 若ESNP日期页不覆盖某场比赛（如22:00北京场次日才出现），切换 date URL 参数尝试前后一天

### 三源对比

| 数据源 | 赛果延迟 | 可靠性 | 获取方式 | 格式 |
|:------|:---------|:-------|:---------|:-----|
| **ESPN scoreboard** | **即时**（FT/AET实时显示） | ✅ 最高 | 浏览器DOM提取 | 队名缩写+比分串 |
| **新浪API dpc=1** | **延迟大**（数小时~隔日） | ❌ 不能用于当日回测 | curl JSON | 结构化JSON |
| **竞彩官方API** | 需特定header，返回HTML | ❌ 不可用 | 放弃 | - |

**实战建议：**
- 新浪API `showSellStatus`: `1=待开售(未结算)` `2=已开售(可能有赛果)` `3=完赛(有比分)`
- **即时回测（同一日）→ ESPN scoreboard**
- **隔日回测（24h+后）→ 新浪API dpc=1**
- **注意加时赛(AET)**：ESPN标记"AET"的比分包含加时，预测基于90分钟，偏差统计时需区分
