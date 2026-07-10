# 新浪竞彩API + 竞彩官方API + 雷速体育API 参考

> 2026-06-16 探查记录。三大数据源可作为59itou采集的补充或替代。

---

## 一、新浪竞彩API

**基础URL：** `https://mix.lottery.sina.com.cn/gateway/index/entry`

> ⚠️ **2026-06-17排查：所有新浪API子接口必须同时带以下3个参数，缺一不可：**
> - `__caller__=wap` — 指定WAP端数据格式
> - `__version__=1.0.0` — **最容易漏！缺此参数API静默返回空(`result.data=[]`)，不会报错**
> - `__verno__=10000` — 缺此参数返回非JSON错误页面
>
> **响应结构（所有接口一致）：**
> ```json
> {"result": {"_timestamp": 1700000000, "data": [...]}}
> ```
> **⚠️ 数据在 `result.data` 下！** 不是 `data`，也没有 `code` 字段。
> 正确解析：`d.get('result', {}).get('data', [])`
> ❌ 错误解析：`d.get('data')` 或 `d['data']` 或检查 `d.get('code')`
>
> **错误模式**：缺`__version__`时，接口返回 `{"result": {"_timestamp": ..., "data": []}}`（空数组但status正常），误判为"成功但无数据"。这是最常见的API故障原因。

### 接口总表

| cat1 | 用途 | 关键参数 | 数据量 |
|:-----|:-----|:---------|:-------|
| `jczqMatches` | 竞足比赛列表+SP | `date`, `gameTypes`, `isAll=1` | SPF/RQSPF/BF/BQC/JQ各玩法SP |
| `footballMatchDetail` | 比赛详情 | `matchId` | 联赛ID/轮次/阶段/天气/中立/排名 |
| `footballMatchOddsEuro` | 欧赔（**53家公司**） | `matchId` | 53家初赔+即赔，可算百家平均 |
| `footballMatchOddsEuroChange` | 欧赔变化历史 | `matchId`, `companyId`, `offerId` | 完整时间序列（155+条） |
| `footballMatchOddsAsia` | 亚盘（**17家公司**） | `matchId` | 17家初盘+即盘+水位+盘口 |
| `footballMatchOddsAsiaChange` | 亚盘变化 | `matchId`, `companyId`, `offerId` | 盘口变化历史 |
| `footballMatchIncident` | 比赛事件 | `matchId` | 进球/黄牌/换人/VAR |
| `footballMatchStat` | 数据统计 | `matchId` | 技术统计 |
| `footballMatchTLive` | 直播 | `matchId` | 实时比分/状态 |
| `syncClock` | 同步时间 | 无 | 服务器时间 |

### 比赛列表API

```
GET jczqMatches?gameTypes=spf&date=2026-06-16&isAll=1
```

**返回字段（无dpc参数 — 当前/未来比赛）：**
- `hostName`, `guestName`, `leagueName` — 队名和联赛名（仅未来比赛有值）
- `spf`: "1.32,4.20,7.45" → 胜平负SP
- `rqspf`: "-1,2.07,3.45,2.81" → 让球数,让胜,让平,让负SP
- 无赛果数据

**返回字段（有 `dpc=1` 参数 — 过往比赛赛果）：**\n- **`team1`**, **`team2`** — ⚠️ 字段名为 `team1`/`team2`，不是 `hostName`/`guestName`！\n- **`league`** — ⚠️ 字段名为 `league`，不是 `leagueName`！\n- `score1`, `score2` — 全场比分（整数，**比赛未结算时为空字符串**）\n- `halfScore1`, `halfScore2` — 半场比分\n- `showSellStatus` — 比赛状态（见下方状态码说明）\n- `spf` — SPF赔率（开奖前数据）\n- `rqspf` — 让球SPF\n- `bf`, `bqc`, `jq` — 各玩法SP+开奖\n\n> ⚠️ **`showSellStatus` 状态码（2026-07-02实战验证）：**\n> - **`1`** = 待开售 / 未结算 — 比赛已进行但竞彩未开奖，`score1/score2` 为空\n> - **`2`** = 已开售 — 可能有赛果但尚未完全结算\n> - **`3`** = 完赛 — 有完整比分，`score1/score2` 为整数\n>\n> **延迟问题：** 世界杯R32比赛结束后，新浪API的 `showSellStatus` 在数小时内仍为 `1` 或 `2`，`score1/score2` 为空。**不能用于当日赛后即时回测**。即时赛果请用 ESPN scoreboard（见 backtest-workflow.md）。

> ⚠️ **关键发现（2026-06-18）：** 有`dpc=1`时，队名和联赛名字段名与无`dpc`时不同——
> 无dpc: `hostName`/`guestName`/`leagueName`
> 有dpc: `team1`/`team2`/`league`
> 另外，无dpc时所有返回数据的队名均为空（无法获取过往比赛队名）

**比分SP的31个值对应关系：**
```
[1:0, 2:0, 2:1, 3:0, 3:1, 3:2, 4:0, 4:1, 4:2, 5:0, 5:1, 5:2, 胜其他,
 0:0, 1:1, 2:2, 3:3, 4:4, 平其他,
 0:1, 0:2, 1:2, 0:3, 1:3, 2:3, 0:4, 1:4, 2:4, 0:5, 1:5, 2:5, 负其他]
```

### 欧赔API

```
GET footballMatchOddsEuro?matchId=3625100
→ 返回53家公司，含初赔(o*Ini)和即赔(o*New)
→ 直接计算百家平均
```

### 欧赔变化API

```
GET footballMatchOddsEuroChange?matchId=3625100&companyId=2&offerId=1
→ 返回155条时间序列（以36*公司为例）
→ 最早→最晚的完整赔率走势
```

### 亚盘API

```
GET footballMatchOddsAsia?matchId=3625100
→ 返回17家公司
→ 盘口字段：o3IniStr/o3NewStr（如 "-1/1.5"->"-1"）
→ 水位字段：o1Ini/o1New（主队水），o2Ini/o2New（客队水）
```

### cURL示例

```bash
# ⚠️ 所有新浪API调用必须带完整三参数：__caller__=wap + __version__=1.0.0 + __verno__=10000

# 赛程+SP
curl -s 'https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000&cat1=jczqMatches&gameTypes=spf&date=2026-06-16&isAll=1&dpc=1'

# 欧赔53家
curl -s 'https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000&cat1=footballMatchOddsEuro&matchId=3625100'

# 亚盘17家
curl -s 'https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000&cat1=footballMatchOddsAsia&matchId=3625100'
```

**注意：** 新浪的 `matchId`（如3625100）与竞彩官方 `matchId`（如2040178）不同。通过 `jczqMatches` 的 `tiCaiId` 字段关联竞彩官方ID。

---

## 二、竞彩官方API

**基础URL：** `https://webapi.sporttery.cn/gateway/uniform/fb/`

### 接口

| 接口 | method | 用途 |
|:-----|:-------|:-----|
| `getConditionsV1.qry` | `result` / `concern` | 联赛筛选列表 |
| `getMatchDataPageListV1.qry` | `concern` | 赛程+SPF赔率 |
| `getMatchDataPageListV1.qry` | `result` | 赛果+比分 |

### 赛程API（带官方SPF）

```
GET getMatchDataPageListV1.qry?method=concern&pageSize=20
```

关键字段：
- `h` = 主胜SP，`d` = 平局SP，`a` = 客胜SP
- `matchStatus`: 1=待开售, 3=已开售, 11=已完成
- `sectionsNo1` = 半场比分，`sectionsNo999` = 全场比分
- `leagueId`: 72=世界杯

### 赛果API

```
GET getMatchDataPageListV1.qry?method=result&pageSize=20&matchBeginDate=2026-06-15&matchEndDate=2026-06-15
```

返回已完成比赛的分组数据（按日期分组），含半场和全场比分。

### cURL示例

```bash
# 赛程
curl -s 'https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry?method=concern&pageSize=20' \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 14)'

# 赛果
curl -s 'https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry?method=result&pageSize=20&matchBeginDate=2026-06-15&matchEndDate=2026-06-15' \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 14)'
```

---

## 三、雷速体育API

**基础URL：** `https://api-gateway.leisu.com/v1/web/match/database/football/`

### 接口

| 端点 | 参数 | 数据 |
|:-----|:-----|:------|
| `comp_info` | `comp_id=1` | 联赛信息（卫冕冠军、历届冠军） |
| `comp_matches` | `comp_id=1&season_id=13776` | 全部比赛+赔率 |
| `comp_tables` | `comp_id=1&season_id=13776` | 小组积分榜 |
| `comp_best_lineup` | `season_id=13776` | 最佳阵容 |

**注意：** API使用 `auth_key` 防盗链机制。数据可通过浏览器Vue store提取：`window.$nuxt.$store.state.data.ftbComp`

### 比赛数据字段（每场）

```
{
  id: 4459820,
  home_team: {id, name, logo},
  away_team: {id, name, logo},
  title: "世界杯 小组赛第1轮",
  venue: {id, name_zh, name_en},
  match_time: 1781204400 (时间戳),
  status_id: 5 (5=已完成),
  home_score: 2, away_score: 0,
  round_num: 1, group_num: 1,
  home_scores: [2,1,1,1,3,0,0],  // 近7场结果
  away_scores: [0,0,2,2,1,0,0],
  // 赔率 (odd_list: 4个数组)
  odd_list: [
    "0.9,1.0,0.95,0",     // 亚盘: 主水,盘口,客水
    "1.5,4.0,5.5,0",      // 欧赔: 主胜,平局,客胜
    "0.95,2.5,0.9,0",     // 大小: 大水,大小线,小水
    ""                     // 保留
  ],
  half_odd_list: [...]    // 同上，半场赔率
  extra_data: {
    support_data: {team_id: count},  // 球迷支持度
    weather: 5, temperature: "23°C",
    wind: "2.6m/s", humidity: "53%",
    referees: {var, fourth, assistant1, assistant2, assistant_var},
    jc: "260611_周四001",  // 竞彩编号
    analysis: 35,          // 分析文章数
    intelligence: 1,       // 情报数
  },
  fb_extra: {
    player: {id, name, logo},  // MVP
    rating: "8.5",
    incidents: [{type, time, player_id, ...}]  // 比赛事件
  }
}
```

### 积分榜数据

```json
{
  "stages": [{
    "tables": [{
      "name": "A组",
      "rows": [{
        "team": {"name": "墨西哥", "logo": "...", "name_en": "Mexico"},
        "fb_detail": {
          "points": 3, "position": 1,
          "total": 1, "won": 1, "draw": 0, "loss": 0,
          "goals": 2, "goals_against": 0,
          "home_points": 0, "away_points": 0, ...
        }
      }]
    }]
  }]
}
```

### 通过浏览器提取数据

```javascript
// 比赛+赔率
window.$nuxt.$store.state.data.ftbComp.comp_match_data['1'].stages
// 积分榜
window.$nuxt.$store.state.data.ftbComp.comp_point_data['1'].stages[0].tables
```

---

## 四、三源对比与选用策略

| 维度 | 新浪API | 官方API | 雷速API |
|:-----|:--------|:--------|:--------|
| 欧赔(53家初+即) | ✅ | ❌ | ❌(仅1家) |
| 亚盘(17家) | ✅ | ❌ | ✅(1家) |
| 大小球 | ❌ | ❌ | ✅ |
| 竞彩SP(SPF) | ✅ | ✅ h/d/a | ❌ |
| 竞彩SP(比分/半全场) | ✅ BF/BQC/JQ | ❌ | ❌ |
| 赛果+半全场 | ✅ 含SP开奖 | ✅ | ✅ |
| 近期战绩 | ❌ | ❌ | ✅ (home_scores数组) |
| 小组积分榜 | ❌ | ❌ | ✅ |
| 天气/裁判 | ❌ | ❌ | ✅ |
| 比赛事件 | ✅ | ❌ | ✅ |
| 场地信息 | ❌ | ❌ | ✅ |
| 所需matchId | 新浪ID(数字) | tiCaiId | leisu ID |
| 采集方式 | curl直取JSON | curl直取JSON | 浏览器Vue store |

### 推荐组合

- **赛前完整SP** → 新浪API（一场调用拿全SPF/RQSPF/BF/BQC/JQ）
- **欧赔53家** → 新浪API（直接算百家平均+指数变化家数）
- **亚盘17家** → 新浪API（盘口+水位变化）
- **官方SPF确认** → 竞彩官方API（h/d/a字段，最权威）
- **积分榜+天气+裁判** → 雷速API（通过Vue store）
- **阵容/伤停/排名Tab** → 仍需59itou（三源均无）

### 采集简化建议

对于日常预测，**仅用新浪API** 即可完成：
1. `jczqMatches` 获取SPF/RQSPF/比赛基本信息
2. `footballMatchOddsEuro` 获取53家欧赔（代替59itou欧指Tab）
3. `footballMatchOddsAsia` 获取17家亚盘（代替59itou亚指Tab）
