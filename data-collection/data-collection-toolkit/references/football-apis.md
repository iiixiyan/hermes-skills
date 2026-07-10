# 足球数据API速查手册

> 发现于 2026-06-16。三大可编程数据源 + 59itou隐藏API，覆盖世界杯/竞足数据采集。

---

## 一、新浪竞彩API

### 基础地址
```
https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap
```

### 可用接口

| cat1 | 功能 | 参数 | 数据 |
|:-----|:-----|:------|:------|
| **jczqMatches** | 竞足比赛列表 | `gameTypes`, `date` | SPF/RQSPF/BF/JQ/BQC 各玩法SP + 赛果 |
| **footballMatchOddsEuro** | 欧赔 | `matchId` | **53家公司**初赔+即赔，可算百家平均 |
| **footballMatchOddsAsia** | 亚盘 | `matchId` | **17家公司**盘口+水位 |
| **footballMatchOddsEuroChange** | 欧赔变化历史 | `matchId`, `companyId`, `offerId` | 完整时间序列（155条+） |
| **footballMatchOddsAsiaChange** | 亚盘变化 | `matchId`, `companyId`, `offerId` | 盘口变化历史 |
| **footballMatchDetail** | 比赛详情 | `matchId` | 排名(team1Position/team2Position)、天气(weather)、轮次(round)、阶段(stage)、中立(isNeutral) |
| **footballMatchIncident** | 比赛事件 | `matchId` | 进球/黄牌/换人/VAR |
| **footballMatchStat** | 统计 | `matchId` | 技术统计 |
| **footballMatchTLive** | 直播 | `matchId` | 实时比分 |
| **FootballSeasonBracket** | 赛季对阵表 | `leagueId`, `seasonId` | 小组赛/淘汰赛对阵 |
| **syncClock** | 同步时间 | 无 | 服务器时间戳 |

### 欧赔字段说明
```json
{
  "companyId": "9",           // 公司ID
  "companyName": "威*",       // 公司名称（脱敏）
  "o1Ini": "1.400",           // 主胜初赔
  "o2Ini": "4.200",           // 平局初赔
  "o3Ini": "7.000",           // 客胜初赔
  "o1New": "1.440",           // 主胜即赔
  "o2New": "4.200",           // 平局即赔
  "o3New": "6.500"            // 客胜即赔
}
```

### 亚盘字段说明
```json
{
  "companyId": "9",
  "companyName": "威*",
  "o1Ini": "1.980",           // 主队初盘水位
  "o2Ini": "1.780",           // 客队初盘水位
  "o3Ini": "-1.250",          // 初盘盘口（负数=主让，正数=客让）
  "o3IniCn": "一球/球半",    // 初盘中文描述
  "o3IniStr": "-1/1.5",       // 初盘字符串
  "o1New": "1.690",           // 主队即盘水位
  "o2New": "1.960",           // 客队即盘水位
  "o3New": "-1.000",          // 即盘盘口
  "o3NewCn": "一球"
}
```

### 竞彩SP字段说明（jczqMatches）
```json
{
  "spf": "1.32,4.20,7.45",    // 胜平负SP
  "rqspf": "-1,2.07,3.45,2.81", // 让球数, 让胜SP, 让平SP, 让负SP
  "bf": "6.70,6.50,...(31个)", // 31个比分选项SP（见下方映射）
  "bqc": "1.18,40.00,...(9个)", // 9个半全场选项SP
  "jq": "42.00,11.00,...(8个)" // 8个进球数选项SP
}
```

**比分SP(bf) 31个值对应关系：**
```
索引 0-12（主胜比分）: 1:0, 2:0, 2:1, 3:0, 3:1, 3:2, 4:0, 4:1, 4:2, 5:0, 5:1, 5:2, 胜其他
索引 13-18（平局比分）: 0:0, 1:1, 2:2, 3:3, 4:4, 平其他
索引 19-30（客胜比分）: 0:1, 0:2, 1:2, 0:3, 1:3, 2:3, 0:4, 1:4, 2:4, 0:5, 1:5, 2:5, 负其他
```

### 注意
- 新浪API matchId ≠ 雷速 matchId ≠ 竞彩官方API matchId。需要通过比赛日期+对阵双方桥接。
- 欧赔公司名称已脱敏（威*=威廉希尔, 36*=36*等），但不影响数值使用。
- **⚠️ 所有新浪子接口必须带以下3参数，缺一不可：**
  ```
  __caller__=wap&__version__=1.0.0&__verno__=10000
  ```
  - 缺`__version__=1.0.0`：**静默返回空数据(data=[]，code=0)** — 最危险的错误模式！不会报错
  - 缺`__verno__=10000`：报错code=1002（显式失败，易定位）
  - `footballMatchOddsEuro` 和 `footballMatchOddsAsia` 使用与 `jczqMatches` 相同的matchId（3625xxx格式），无需转换。

- **⚠️ 2026-06-19 验证：响应结构变更**
  ```python
  # jczqMatches 返回结构:
  # {"result": {"_timestamp": ..., "data": [...]}}
  # data 现在是 LIST（每个元素是一个比赛dict），不再是按matchId为key的dict
  d = json.load(sys.stdin)
  matches = d['result']['data']  # ✅ 现在是list
  for m in matches:
      match_id = m['matchId']
      home_team = m.get('homeTeamName')  # 注意字段名未变
      spf = m.get('spf')
  ```
- **比赛总数**：通过 `result.matchesCount` 获取，不再是 `len(result.data)`

---

## 二、竞彩官方API

### 基础地址
```
https://webapi.sporttery.cn/gateway/uniform/fb/
```

### 可用接口

| 接口 | method | 用途 | 数据 |
|:-----|:-------|:-----|:------|
| `getConditionsV1.qry` | `result` / `concern` | 联赛筛选列表 | 所有联赛ID+名称 |
| `getMatchDataPageListV1.qry` | **`concern`** | **赛程+SPF赔率** | 未来比赛SPF(h/d/a)+联赛+时间+状态 |
| `getMatchDataPageListV1.qry` | **`result`** | **赛果+比分** | 已完成比赛比分+半全场 |

### 赛程接口（method=concern）

```
GET /getMatchDataPageListV1.qry?method=concern&pageSize=20
```

**⚠️ WAF保护（Tencent Cloud EdgeOne）：** 简单curl返回HTTP 567验证码页面。必须携带以下**5个完整请求头**，缺一不可：
```bash
-H 'User-Agent: Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36'
-H 'Referer: https://webapi.sporttery.cn/'
-H 'Accept: application/json, text/plain, */*'
-H 'Accept-Language: zh-CN,zh;q=0.9'
-H 'Origin: https://webapi.sporttery.cn'
```

**关键字段：**
```json
{
  "h": "1.32",        // 主胜SPF
  "d": "4.20",        // 平局SPF
  "a": "7.45",        // 客胜SPF
  "matchStatus": "3", // 1=待开售 3=已开售 11=已完成
  "matchId": 2040178  // 官方matchId
}
```

### 赛果接口（method=result）

```
GET /getMatchDataPageListV1.qry?method=result&pageSize=20&matchBeginDate=YYYY-MM-DD&matchEndDate=YYYY-MM-DD
```

**⚠️ WAF保护：** 同赛程接口，必须带5个完整请求头（UA+Referer+Accept+Accept-Language+Origin），详见§二·赛程接口。
**日期范围建议：** 单次查询不超过5天，以免超时。

**返回结构：**
```json
{
  "matchInfoList": [{
    "matchDate": "2026-06-15",
    "matchCount": 4,
    "subMatchList": [{
      "homeTeamAbbName": "西班牙",
      "awayTeamAbbName": "佛得角",
      "sectionsNo1": "0:0",     // 半场比分
      "sectionsNo999": "0:0",   // 全场比分
      "matchStatus": "11",      // 已完成
      "matchStatusName": "已完成"
    }]
  }]
}
```

---

## 三、雷速体育API

### 基础地址
```
https://api-gateway.leisu.com/v1/web/match/database/football/
```

### 数据获取方式

雷速有 anti-bot 保护（需要 auth_key），**无法通过 curl 直连**。数据通过Vue store获取：

```javascript
// 在浏览器控制台执行
const store = window.$nuxt.$store.state.data.ftbComp;
const matchData = store.comp_match_data['1'];   // comp_id=1=世界杯
const pointData = store.comp_point_data['1'];   // 积分榜
const infoData = store.compInfoData['1'];       // 联赛信息
```

### 比赛数据结构

```javascript
comp_match_data['1'] = {
  comp_type: 2,
  cur_round: 1,
  cur_stage_id: 232934,
  cur_season_id: 13776,
  stages: [{
    id: 232934,
    name: "小组赛",      // 阶段名称
    matches: [{
      id: 4459820,
      home_team: {id: 11764, name: "墨西哥", logo: "..."},
      away_team: {id: 10310, name: "南非", logo: "..."},
      title: "世界杯 小组赛第1轮",
      venue: {id: 1329, name_zh: "墨西哥城体育场"},
      match_time: 1781204400,          // Unix时间戳
      status_id: 5,                    // >=5=已结束
      home_score: 2,                   // 终场比分
      away_score: 0,
      home_scores: [2,1,1,1,3,0,0],    // 近7场进球数组
      away_scores: [0,0,2,2,1,0,0],
      odd_list: [                      // 赔率
        "0.9,1.0,0.95,0",             // [0]亚盘: 主水,盘口,客水,?
        "1.5,4.0,5.5,0",              // [1]欧赔: 主胜,平,客胜,?
        "0.95,2.5,0.9,0",             // [2]大小球: 大球,大小线,小球,?
        ""                             // [3]空
      ],
      half_odd_list: [/* 同上，半场赔率 */],
      extra_data: {
        weather: 5,                    // 天气代码
        temperature: "23°C",           // 温度
        wind: "2.6m/s",                // 风速
        humidity: "53%",               // 湿度
        pressure: "755mmHg",           // 气压
        referees: {                    // 裁判组
          var: 2197, fourth: 2827,
          assistant1: 6290, assistant2: 6289
        },
        support_data: {"10310": 2668, "11764": 7058},  // 球迷支持度
        jc: "260611_周四001",          // 竞彩编号
        analysis: 35,                  // 分析文章数
        intelligence: 1                // 情报数
      },
      fb_extra: {                      // 最佳球员+比赛事件
        player: {id: 80963, name: "基尼奥内斯"},
        rating: "8.5",
        incidents: [{type: 1, time: "9", player_id: 80963}]  // type=1进球
      }
    }]
  }]
}
```

### 积分榜数据结构

```javascript
comp_point_data['1'] = {
  stages: [{
    tables: [{
      id: 33401,
      name: "A组",
      rows: [{
        team: {id: 11764, name: "墨西哥"},
        fb_detail: {
          points: 3,              // 积分
          position: 1,            // 排名
          total: 1,               // 已赛场次
          won: 1, draw: 0, loss: 0,
          goals: 2,               // 进球
          goals_against: 0,       // 失球
          goal_difference: 2      // 净胜球
        }
      }]
    }]
  }]
}
```

---

## 四、数据源选择策略（足球数据）

```
优先级排序：
  1️⃣ 新浪API（REST JSON，无防盗链）→ 欧赔/亚盘/竞彩SP/比赛详情
  2️⃣ 59itou API（REST JSON）→ FIFA排名/北单SP
  3️⃣ 竞彩官方API（REST JSON，需WAF绕过）→ SPF赔率/赛果比分
  4️⃣ 雷速store（Vue store直取）→ 赔率交叉验证/战绩数组/天气裁判/积分榜
  5️⃣ 500彩票网/球探体育（浏览器）→ 百家欧赔100+家/走势图/波胆
  6️⃣ 59itou浏览器（最后兜底）→ 阵容/伤停/H2H（仅前三者无API替代时用）
```

**能用API直连的绝不用浏览器。** 浏览器仅用于阵容/伤停/H2H和无API替代的模块。

## 六、2026-06-20 全面验证补充

详见同级文件 `references/football-odds-sites-comprehensive-comparison.md`，含：
- 40+站点实测结果
- 19个可用站点分3梯队对比矩阵
- 已关站/不可达站点清单
- 最佳数据管道推荐

关键发现汇总：
| 发现 | 内容 |
|:----|:------|
| 新浪API | 继续可用，data从dict变list |
| 竞彩官方 | EdgeOne WAF需UA+Referer+Accept五件头 |
| 59itou | **唯一北单API**，lotteryId=45 |
| 新发现 | 500彩票网(100+家赔率)、中国足彩网(北单)、OddsPortal(全球) |
| 已关站 | 360彩票(22年停)、大赢家、搜达、竞彩258、彩客网 |

---

## 五、59itou隐藏API

### 基础地址
```
https://apic.jindianle.com/api/
```

### 可用接口

| 接口 | 方法 | 功能 | 备注 |
|:-----|:-----|:------|:------|
| `match/selectlist` | GET/POST | 比赛列表+FIFA排名+SP赔率 | **最有用！** 无需浏览器直接取FIFA排名 |
| `match/leaguequerylist` | GET | 联赛列表 | 辅助数据 |

### selectlist 请求参数

```
GET /api/match/selectlist?platform=koudai_mobile&_prt=https&ver=20180101000000
```

**必带Header：**
```bash
-H 'User-Agent: Mozilla/5.0' -H 'Referer: https://kt.59itou.com/'
```

**返回示例（FIFA排名）：**
```json
{
  "data": {
    "2026-06-16": {
      "2020": {
        "host_name_s": "奥地利",
        "guest_name_s": "约旦",
        "rank": {
          "1": {"team_name": "奥地利", "rank": "24", "rank_league": "FIFA"},
          "2": {"team_name": "约旦", "rank": "63", "rank_league": "FIFA"}
        }
      }
    }
  }
}
```

### 可选参数
- `hide_more=1` — 仅返回当前销售日（不传则返回当前日+未来2天）
- `single_support=2` — 单关支持

### 局限
- ❌ 无欧赔/亚盘/百家平均
- ❌ 无阵容/伤停/H2H
- ❌ 无赛果/比分（仅赛前数据）

### 详情页URL格式（浏览器采集）
```
https://kt.59itou.com/{station}/match3/?current_tab={tab}&matchid={match_id2}&lotteryId=90
```
- `{station}`：动态数字（如223），从列表页点击"分析"进入后自动获取
- `{match_id2}`：从 `match/selectlist` API返回的match_id2字段
- `lotteryId=90`：竞足，`lotteryId=45`：北单
- `{tab}`取值：`lineup`(阵容) / `info`(情报) / `history`(战绩+H2H) / `rank`(排名) / `odds`(欧指) / `handicap`(亚指)
- **注意：** 欧赔/亚盘/排名数据已被新浪API覆盖，详情页无需再采这3个Tab
