# Sina API 实时数据管道验证（2026-07-01）

## 已验证的工作端点

### 比赛列表（当日竞足）

```
URL: https://mix.lottery.sina.com.cn/gateway/index/entry
参数: format=json&__caller__=wap&__version__=1.0.0&__verno__=10000
命令: cat1=jczqMatches
```

**响应**: `result.data` 数组，每场含：
- `matchId` — 用于拉欧赔/详情
- `team1`/`team2` — 队名（中文）
- `matchNo` — 如"周三080"
- `matchTimeFormat` — 如"2026-07-02 00:00:00"
- `league` — 如"世界杯"
- `score1`/`score2` — 比分（赛后才填充）

### 欧赔（47-53家）

```
命令: cat1=footballMatchOddsEuro&matchId={matchId}
```

**响应**: `result.data` 数组（每家一记录），含：
- `o1Ini`/`o1New` — 主胜初始/即赔
- `o2Ini`/`o2New` — 平局初始/即赔
- `o3Ini`/`o3New` — 客胜初始/即赔
- `companyName` — 公司名（如"1xB*"）
- `oddsTimeIni`/`oddsTimeNew` — 时间戳

**计算8参数**:
```python
r1 = sum(oNew > oIni)  # 升主胜家数
c1 = sum(oNew < oIni)  # 降主胜家数
r2 = sum(o2New > o2Ini)  # 升平家数
c2 = sum(o2New < o2Ini)  # 降平家数
r3 = sum(o3New > o3Ini)  # 升客胜家数
c3 = sum(o3New < o3Ini)  # 降客胜家数
o1 = avg(o1New)  # 平均主胜即赔
o3 = avg(o3New)  # 平均客胜即赔
```

### 比赛详情（FIFA排名/天气/轮次）

```
命令: cat1=footballMatchDetail&matchId={matchId}
```

**响应**: `result.data` 字典，含：
- `team1Position`/`team2Position` — FIFA排名数字
- `environment` — 天气描述（如"局部有云 31°C"）
- `weather` — 天气码
- `isNeutral` — 中立场地标记
- `stage` — 轮次（如"1/16决赛"）
- `statusCn` — 如"未赛"
- `league` — 联赛名

## 已验证失效的端点

| 命令 | 结果 |
|:----|:-----|
| `cat1=fbMatchListByDate&date=...` | 返回空数组（0 matches） |
| `cat1=footballMatchInfo&matchId=...` | 无数据 |

## 判断轮次(rd)规则

从 `stage` 字段推断：
- 小组赛第1轮 → rd=1
- 小组赛第2轮 → rd=2
- 小组赛第3轮 → rd=3
- 1/16决赛 → rd=4
- 1/8决赛 → rd=5
- 1/4决赛 → rd=6
- 半决赛 → rd=7
- 决赛 → rd=8

如果 `stage` 不可用，根据比赛日期推算（世界杯2026年6月15日开幕）：
- 6月15-17日 → R1
- 6月18-21日 → R2
- 6月22-25日 → R3
- 6月28日后 → 淘汰赛
