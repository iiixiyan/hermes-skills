# 新浪竞彩API字段名速查

> 2026-06-22更新。不同API端点的字段名不同，混用会静默返回空数据。

## ⚠️ 关键发现：API间matchId不匹配

**不同新浪API端点（jczqMatches vs footballMatchOddsEuro）可能使用完全不同的matchId！**

2026-06-20验证：硬编码的3625106-3625133与jczqMatches返回的正确matchId（3623416、3623420、3625088等）**完全不匹配**。

### 验证结果

| 旧(错误)matchId | 实际matchId | 比赛 |
|:----:|:----:|:-----|
| 3625106 | 3623416 | 墨西哥vs南非 |
| 3625107 | 3625112 | 韩国vs捷克 |
| 3625108 | 3623420 | 加拿大vs波黑 |
| 3625109 | 3623423 | 美国vs巴拉圭 |
| 3625114 | 3625088 | 德国vs库拉索 |
| 3625115 | 3625091 | 荷兰vs日本 |
| 3625118 | 3625097 | 西班牙vs佛得角 |

**正确做法**：从 `jczqMatches` 获取 `matchId` 值，再传给 `footballMatchOddsEuro`。**不要在代码中硬编码matchId！**

### 获取正确matchId的方法

```python
SINA_BASE = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000"
url = f"{SINA_BASE}&cat1=jczqMatches&date=YYYY-MM-DD&isAll=1&dpc=1"
resp = json.loads(urllib.request.urlopen(url).read())
for m in resp['result']['data']:
    match_id = m['matchId']  # ← 此matchId可传给footballMatchOddsEuro
    team1 = m['team1']
    team2 = m['team2']
```

## jczqMatches（比赛列表 + 赛果）

**字段名（dpc=1模式）：**
| 字段 | 说明 |
|:----|:-----|
| `team1` / `team2` | 主/客队名（❗不是`hostName`/`guestName`） |
| `league` | 联赛名（❗不是`leagueName`） |
| `spf` | 胜平负SP，"胜,平,负"格式 |
| `rqspf` | 让球SP，"让球数,让胜,让平,让负"格式 |
| `score1` / `score2` | 主/客队比分（字符串） |
| `halfScore1` / `halfScore2` | 半场主/客队比分 |
| `matchId` | 新浪API matchID |

**不带dpc=1时**，未来比赛有队名，过往比赛无队名。

## footballMatchOddsEuro（欧赔所有公司）

**⚠️ 关键验证（2026-07-02）：此API与 jczqMatches 使用相同 matchId。** 2026-07-02验证确认：`jczqMatches`返回的`matchId`可直接传给`footballMatchOddsEuro`并返回正确数据。

字段：`o1Ini`/`o1New`(主胜初赔/即赔), `o2Ini`/`o2New`(平), `o3Ini`/`o3New`(客胜)

响应结构：`result.data`（列表，每元素是一家公司）——返回的不是聚合数据，各家赔率独立，需手动计算8参数。

### 从 footballMatchOddsEuro 计算8参数（r1/c1/r2/c2/r3/c3）

```python
def calc_8_params(odds_data):
    """odds_data = footballMatchOddsEuro的result.data列表"""
    r1 = c1 = r2 = c2 = r3 = c3 = total = 0
    for co in odds_data:
        try:
            o1i = float(co.get('o1Ini', 0))
            o1n = float(co.get('o1New', 0))
            o2i = float(co.get('o2Ini', 0))
            o2n = float(co.get('o2New', 0))
            o3i = float(co.get('o3Ini', 0))
            o3n = float(co.get('o3New', 0))
            if o1n > 0:
                if o1n > o1i: r1 += 1
                elif o1n < o1i: c1 += 1
            if o2n > 0:
                if o2n > o2i: r2 += 1
                elif o2n < o2i: c2 += 1
            if o3n > 0:
                if o3n > o3i: r3 += 1
                elif o3n < o3i: c3 += 1
            total += 1
        except: pass
    return r1, c1, r2, c2, r3, c3, total
```

### 从 footballMatchOddsEuro 计算百家平均即赔/初赔

```python
def avg_odds(odds_data):
    """百家平均即赔"""
    s1 = s2 = s3 = n = 0
    for co in odds_data:
        try:
            o1 = float(co.get('o1New', 0))
            o2 = float(co.get('o2New', 0))
            o3 = float(co.get('o3New', 0))
            if o1 > 0: s1 += o1; s2 += o2; s3 += o3; n += 1
        except: pass
    return (round(s1/n,3), round(s2/n,3), round(s3/n,3)) if n > 0 else (0,0,0)

def avg_odds_ini(odds_data):
    """百家平均初赔"""
    s1 = s2 = s3 = n = 0
    for co in odds_data:
        try:
            o1 = float(co.get('o1Ini', 0))
            o2 = float(co.get('o2Ini', 0))
            o3 = float(co.get('o3Ini', 0))
            if o1 > 0: s1 += o1; s2 += o2; s3 += o3; n += 1
        except: pass
    return (round(s1/n,3), round(s2/n,3), round(s3/n,3)) if n > 0 else (0,0,0)
```

## footballMatchOddsAsia（亚盘17家）

字段：`o1Ini`/`o1New`(主队水位), `o3IniStr`/`o3NewStr`(盘口,字符串)

⚠️ 盘口字段是字符串（如"-0/0.5"），需解析后才能比较升/降盘。

## footballMatchDetail（比赛详情）

**字段名：**
| 字段 | 说明 | 示例 |
|:----|:-----|:-----|
| `team1` / `team2` | 主/客队名（❗不是`team1Name`/`team2Name`） | "阿根廷", "奥地利" |
| `team1Position` / `team2Position` | FIFA排名（数值字符串） | "1", "21" |
| `environment` | 天气+温度合并字符串 | "阴 31°C", "局部有云 32°C" |
| `weather` | 天气码（数字，非可读文本） | "7"=阴, "1"=晴, "5"=晴/云 |
| `isNeutral` | 中立场地标识 | "1"=中立, "0"=非中立 |
| `league` | 联赛名（❗不是`leagueName`） | "世界杯", "芬超" |
| `round` | 轮次（数值字符串） | "2" |
| `stage` | 阶段描述 | "小组赛" |
| `matchTime` | 开赛时间（Unix秒） | 1782234000 |

**⚠️ 温度提取方法：**
没有单独的`temperature`字段。需从`environment`字符串解析：
```python
import re
env = data.get('environment', '')  # e.g. "阴 31°C"
temp_match = re.search(r'(\d+)°', env)
temp = int(temp_match.group(1)) if temp_match else 20
weather_desc = env.split(' ')[0] if ' ' in env else env  # "阴"
```

**⚠️ 日期参数偏移（2026-06-22验证）：**
- 凌晨比赛（01:00-11:00 CST）属于前一个销售日
- `date=2026-06-22` → 返回4场6月23日凌晨比赛（阿根廷vs奥地利等）
- `date=2026-06-23` → 返回10场（含6场芬超+4场6月24日凌晨世界杯）
- 验证方法：从 `jczqMatches` 获取 `matchTime`（Unix秒），用 `datetime.fromtimestamp()` 转CST后确认实际比赛日期

## 59itou API SPF key映射

59itou用数字key：`'3'=主胜`, `'1'=平局`, `'0'=客胜`（与新浪的主/平/客顺序不同）
