# 59itou (apic.jindianle.com) API 数据源

> 2026-06-17 探查发现59itou底层API域名 `apic.jindianle.com`，部分数据可直接JSON获取。

## API端点

### match/selectlist — 比赛列表+SP赔率+FIFA排名

```
GET https://apic.jindianle.com/api/match/selectlist
     ?platform=koudai_mobile
     &_prt=https
     &ver=20180101000000
     &hide_more=1
     &single_support=2
```

**Headers:** `User-Agent: Mozilla/5.0` + `Referer: https://kt.59itou.com/`

**返回格式：**
```json
{
  "msg": "ok",
  "data": {
    "2026-06-16": {
      "2020": {
        "serial_no": "2020",
        "match_id": "1260616020",
        "match_id2": "2589461",
        "league_name": "世界杯",
        "host_name_s": "奥地利",
        "guest_name_s": "约旦",
        "sale_status": "1",
        "list": {
          "SportteryNWDL": {
            "bet_id": "1621171",
            "is_single": "1",
            "boundary": "0",
            "odds": {"0": "8.25", "1": "4.65", "3": "1.26"}
          },
          "SportteryWDL": {
            "bet_id": "1621170",
            "is_single": "0",
            "boundary": "-1",
            "odds": {"0": "3.16", "1": "3.88", "3": "1.80"}
          }
        },
        "rank": {
          "1": {"team_id": "0", "team_name": "奥地利", "rank": "24", "rank_league": "FIFA"},
          "2": {"team_id": "0", "team_name": "约旦", "rank": "63", "rank_league": "FIFA"}
        },
        "sort": 751
      }
    }
  }
}
```

**关键字段：**

| 字段 | 含义 | 示例 |
|:-----|:------|:------|
| `match_id` | 比赛ID | `1260616020` |
| `match_id2` | 二级比赛ID | `2589461` |
| `rank[1/2].rank` | **FIFA排名** | `24`, `63` |
| `rank[1/2].rank_league` | 排名类型 | `FIFA` |
| `list.SportteryNWDL` | 胜平负SP | odds: 0=客胜, 1=平, 3=主胜 |
| `list.SportteryWDL` | 让球胜平负SP | boundary=让球数 |
| `host_name_s/guest_name_s` | 球队名（简写） | |
| `league_name` | 联赛名 | |

**注：** 0=客胜, 1=平局, 3=主胜 是59itou的SP映射规则（与竞彩官方一致）。

## 用途

- 获取**FIFA排名**（无需浏览器）
- 获取**竞彩SP初赔**（快速参考）
- 获取**match_id/match_id2**（用于详情页跳转）

## 局限性

- ❌ 无阵容/伤停/H2H/战绩数据
- ❌ 详情页仍需浏览器采集
- ❌ 无欧赔/亚盘/百家平均
