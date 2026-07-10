# 59itou 隐藏API (apic.jindianle.com)

> 发现于 2026-06-16。59itou 的竞彩列表页通过 `apic.jindianle.com` 的 REST API 加载数据，无需浏览器。

## 基础地址

```
https://apic.jindianle.com/api/
```

## 已验证可用的端点

### match/selectlist — 比赛列表（核心）

```
GET /api/match/selectlist?platform=koudai_mobile&_prt=https&ver=20180101000000&hide_more=1&single_support=2
```

**返回数据结构：**
```json
{
  "msg": "ok",
  "data": {
    "2026-06-16": {
      "2020": {
        "serial_no": "2020",
        "match_id": "1260616020",
        "match_id2": "2589461",
        "match_time": "2026-06-17 12:00:00",
        "bet_time": "2026-06-17 12:00:00",
        "bet_date": "2026-06-16",
        "league_name": "世界杯",
        "host_name_s": "奥地利",
        "guest_name_s": "约旦",
        "sale_status": "1",
        "rank": {
          "1": {"team_id": "0", "team_name": "奥地利", "rank": "24", "rank_league": "FIFA"},
          "2": {"team_id": "0", "team_name": "约旦", "rank": "63", "rank_league": "FIFA"}
        },
        "list": {
          "SportteryNWDL": {
            "bet_id": "1621171", "is_single": "1", "boundary": "0",
            "odds": {"0": "8.25", "1": "4.65", "3": "1.26"}
          },
          "SportteryWDL": {
            "bet_id": "1621170", "is_single": "0", "boundary": "-1",
            "odds": {"0": "3.16", "1": "3.88", "3": "1.80"}
          }
        }
      }
    }
  }
}
```

**关键字段：**
| 字段 | 含义 | 示例 |
|:-----|:-----|:------|
| `match_id` | 59itou内部比赛ID | 1260616020 |
| `match_id2` | 二级比赛ID（用途不明） | 2589461 |
| `rank.1.rank` | **主队FIFA排名** | "24" |
| `rank.2.rank` | **客队FIFA排名** | "63" |
| `list.SportteryNWDL` | 胜平负玩法（boundary=0即无让球） | odds: 0=客胜, 1=平, 3=主胜 |
| `list.SportteryWDL` | 让球胜平负（boundary=让球数） | odds: 0=客胜, 1=平, 3=主胜 |
| `sale_status` | 销售状态 | 1=可售, 0=不可售 |

**注：** `SportteryNWDL` 和 `SportteryWDL` 的 odds 键含义不同：
- `NWDL`: 0=客胜, 1=平, 3=主胜
- `WDL`: 0=客胜SP, 1=平SP, 3=主胜SP
- 让球数在 `boundary` 字段，正=主队让球，负=客队让球

## 未找到的API

以下数据在该域名下无对应端点（已验证）：
- 阵容/阵型/首发列表
- 伤停/情报数据
- H2H历史交锋记录
- 球队近10场完整对阵明细
- 赔率变化历史

这些数据仍在59itou详情页的innerText中，需浏览器采集。
