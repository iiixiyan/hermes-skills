# 竞彩官方 API (sporttery.cn)

> 中国体育彩票竞彩官方数据接口，返回纯净JSON。
> 与新浪API互补 — 新浪提供欧赔+亚盘+SP全量，竞彩官方提供**官方SPF赔率+赛果比分**（无需采集处理）。
> 发现日期：2026-06-17

---

## 一、基础信息

```
Base URL: https://webapi.sporttery.cn
端点:    /gateway/uniform/fb/
```

> ⚠️ **2026-06-17验证：此API受Tencent Cloud EdgeOne WAF保护。**
> 简单curl返回 **HTTP 567**（"请求已被安全策略拦截"）。
>
> **修复方法**：必须带完整浏览器5头参，缺一不可：
> - `User-Agent: Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36`
> - `Referer: https://webapi.sporttery.cn/`
> - `Accept: application/json, text/plain, */*`
> - `Accept-Language: zh-CN,zh;q=0.9`
> - `Origin: https://webapi.sporttery.cn`
>
> 无需Cookie、无需登录、无频率限制。

---

## 二、接口总览

| # | 接口 | method | 用途 | 关键参数 |
|:-:|:-----|:-------|:-----|:---------|
| ① | `getConditionsV1.qry` | `result` / `concern` | 获取联赛筛选列表 | 无 |
| ② | `getMatchDataPageListV1.qry` | **`concern`** | **赛程+SPF赔率** | `pageSize`, `pageNo` |
| ③ | `getMatchDataPageListV1.qry` | **`result`** | **赛果+比分** | `pageSize`, `matchBeginDate`, `matchEndDate` |

---

## 三、① getConditionsV1 — 联赛列表

```
GET https://webapi.sporttery.cn/gateway/uniform/fb/getConditionsV1.qry?method=result
```

**返回：** 所有竞彩涵盖的联赛ID+名称

**响应结构：**
```json
{
  "success": true,
  "value": {
    "endDate": "2026-06-16",
    "leagueList": [
      {"leagueId": 72, "leagueName": "世界杯", "leagueNameAbbr": "世界杯"},
      {"leagueId": 42, "leagueName": "日本职业联赛", "leagueNameAbbr": "日职"},
      ...
    ]
  }
}
```

**关键联赛ID（世界杯相关）：**
| leagueId | 联赛 | 说明 |
|:--------|:-----|:-----|
| `72` | 世界杯 | 正赛 |
| `73` | 世界杯预选赛 | 世预赛 |
| `39` | 国际赛 | 国际友谊赛 |

---

## 四、② getMatchDataPageListV1 (method=concern) — 赛程+SPF赔率

```
GET https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry?method=concern&pageSize=20&pageNo=1
```

**返回结构（按日期分组）：**
```json
{
  "success": true,
  "value": {
    "matchInfoList": [
      {
        "matchDate": "2026-06-17",
        "matchCount": 9,
        "weekday": "周三",
        "subMatchList": [ ...每场比赛... ]
      },
      ...
    ]
  }
}
```

### 每场比赛字段

| 字段 | 说明 | 示例 | 备注 |
|:-----|:-----|:-----|:-----|
| `matchNumStr` | 编号 | `周二017` | |
| `homeTeamAbbName` | 主队（简） | `法国` | |
| `awayTeamAbbName` | 客队（简） | `塞内加尔` | |
| `leagueAbbName` | 联赛 | `世界杯` | |
| **`h`** | **主胜SP** | `1.32` | **核心字段** |
| **`d`** | **平局SP** | `4.20` | **核心字段** |
| **`a`** | **客胜SP** | `7.45` | **核心字段** |
| `matchId` | 比赛ID | `2040178` | **注意：与新浪API的matchId不同** |
| `matchDate` | 比赛日期 | `2026-06-17` | |
| `matchTime` | 开赛时间 | `03:00` | |
| `matchStatus` | 状态码 | `1`=待开售, `3`=已开售/暂停销售, `11`=已完成 |
| `matchStatusName` | 状态名 | `暂停销售` / `待开售` / `已完成` |
| `businessDate` | 销售日期 | `2026-06-16` | |
| `backColor` | 联赛色标 | `296CA0` | 世界杯蓝色 |
| `sectionsNo1` | 半场比分 | `0:1` | 赛后才有 |
| `sectionsNo999` | 全场比分 | `1:1` | 赛后才有 |

### 状态码含义

| matchStatus | 含义 | SP是否可用 |
|:-----------|:-----|:----------|
| `1` | 待开售 | ❌ 无SP |
| `3` | 暂停销售（=已开售） | ✅ 有SP（h/d/a有值） |
| `11` | 已完成 | ✅ 有赛果 |
| `4` | 销售中 | ✅ 有SP |

**使用方式：** `h/d/a` 字段在 `matchStatus=3` 或 `4` 时有值，直接作为竞彩官方SPF使用。

### 批量查询说明

`pageSize` 控制每页日期数。`pageSize=20` 会返回最近约 **8天** 的赛程数据（按日期分组）。

---

## 五、③ getMatchDataPageListV1 (method=result) — 赛果+比分

```
GET https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry?method=result&pageSize=20&pageNo=1&matchBeginDate=2026-06-15&matchEndDate=2026-06-15
```

**关键参数：**
| 参数 | 说明 | 示例 |
|:-----|:-----|:-----|
| `matchBeginDate` | 开始日期 | `2026-06-15` |
| `matchEndDate` | 结束日期 | `2026-06-15` |
| `method` | **必须=result** | `result` |

**返回：** 与赛程接口结构相同，但 `subMatchList` 中的 `sectionsNo1`(半场) 和 `sectionsNo999`(全场) 有值。

**⚠️ 2026-06-24 实测：此API赛后延迟1-4小时**

比赛结束后1-4小时内，该API仍返回 `matchStatusName="待开奖"`、`sectionsNo999=""`（空比分）。这**不是API不可用**而是官方结算延迟。

**正确做法的优先级：**
1. 🥇 **新浪API footballMatchDetail** → `score1`/`score2`字段赛后立即更新（首选）
2. 🥈 此API method=result → 延迟1-4h（备选）
3. 🥉 okooo开奖页 → 赛后1-2h更新

**状态码对比实测（2026-06-24）：**
| matchStatus | sectionsNo999 | 新浪 score1/score2 | 含义 |
|:-----------|:-------------|:------------------|:-----|
| `11` | 有值 ✅ | 有值 ✅ | 已完成 |
| 待开奖(新) | 空 ❌ | **有值 ✅** | 新浪已更新但官方未结算 |
| `1` | 空 | 空 | 未开始 |

**示例输出：**
```python
# Python解析赛果
import requests, json

r = requests.get('https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry',
    params={'method':'result','pageSize':20,'pageNo':1,'matchBeginDate':'2026-06-15','matchEndDate':'2026-06-15'},
    headers={'User-Agent':'Mozilla/5.0 (Linux; Android 14)'})

data = r.json()
for dg in data['value']['matchInfoList']:
    date = dg['matchDate']
    for m in dg['subMatchList']:
        half = m.get('sectionsNo1','')
        full = m.get('sectionsNo999','')
        print(f"{date} {m['matchNumStr']} {m['homeTeamAbbName']} {full} {m['awayTeamAbbName']} (半场{half})")
```

**输出：**
```
2026-06-15 周一013 西班牙 0:0 佛得角 (半场0:0)
2026-06-15 周一014 比利时 1:1 埃及 (半场0:1)
2026-06-15 周一015 沙特 1:1 乌拉圭 (半场1:0)
2026-06-15 周一016 伊朗 2:2 新西兰 (半场1:1)
```

---

## 六、与现有数据源对比

| 维度 | 竞彩官方API | 新浪API | 59itou | 首选 |
|:----|:----------|:--------|:-------|:----|
| **赛前SPF赔率** | ✅ `h/d/a` | ✅ `spf` 字段 | ✅ 列表页 | **平手** — 两者皆可 |
| **赛后比分** | ✅ `sectionsNo999` | ✅ `score1/score2` | ✅ Prize page | **平手** |
| **赛果批量查询** | ✅ 日期范围参数 | ✅ 日期参数 | ❌ 需翻页 | **竞彩官方API胜** — range查询 |
| **SP开奖(让球/比分)** | ❌ 无 | ✅ `bfPrize` | ✅ | **新浪/59itou胜** |
| **欧赔+亚盘** | ❌ 无 | ✅ 53家+17家 | ✅ | **新浪胜** |
| **编码/解析** | UTF-8 JSON | UTF-8 JSON | GBK HTML | **API胜** |
| **覆盖日期范围** | 约8天 | 约15天 | 约30天 | **59itou胜** |

**结论：**
- **快速查赛果+比分** → 竞彩官方API（range参数最方便）
- **全量SP+欧赔+亚盘** → 新浪API（一网打尽）
- **历史数据/深度分析** → 59itou（覆盖范围最广）

---

## 七、快速使用示例

### 查今天比赛SPF赔率

```bash
curl -s 'https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry?method=concern&pageSize=20&pageNo=1' \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36' \
  -H 'Referer: https://webapi.sporttery.cn/' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9' \
  -H 'Origin: https://webapi.sporttery.cn' | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for dg in data['value']['matchInfoList']:
    print(f\"--- {dg['matchDate']}({dg.get('weekday','')}) {dg['matchCount']}场 ---\")
    for m in dg['subMatchList']:
        h,d,a = m.get('h','-'), m.get('d','-'), m.get('a','-')
        if h or d or a:
            spf = f\"{h}/{d}/{a}\"
        else:
            spf = '待开售'
        print(f\"{m['matchNumStr']} {m['homeTeamAbbName']} vs {m['awayTeamAbbName']} [{m['leagueAbbName']}] SPF: {spf}\")
"
```

### 查昨天赛果

```bash
YESTERDAY=$(date -d '-1 day' '+%Y-%m-%d')
curl -s \"https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry?method=result&pageSize=20&pageNo=1&matchBeginDate=$YESTERDAY&matchEndDate=$YESTERDAY\" \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36' \
  -H 'Referer: https://webapi.sporttery.cn/' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9' \
  -H 'Origin: https://webapi.sporttery.cn' | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for dg in data['value']['matchInfoList']:
    for m in dg['subMatchList']:
        score = m.get('sectionsNo999','?') or '?'
        half = m.get('sectionsNo1','?') or '?'
        print(f\"{m['matchNumStr']} {m['homeTeamAbbName']} {score} {m['awayTeamAbbName']} (半{half})\")
"
```
