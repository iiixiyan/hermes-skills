# 赛后赛果验证 — match3 详情页快速查分法

> 用于复盘时获取实际比分。无需 prize page 的复杂DOM解析，直接导航到比赛详情页即可。

## 原理

比赛结束后，59itou match3 详情页的顶部 banner 区域会显示最终比分：
```
法国             摩洛哥
世3              世7
2-0    ← 比分在此
世界杯
```

比分以 `StaticText` 形式出现在页面 accessibility tree 中，介于主队名和客队名之间。

## 使用方法

### URL 格式
```
https://kt.59itou.com/{prefix}/match3/?matchid={match_id}&lotteryId={lid}&lottery_style={style}
```

| 参数 | 竞足 | 北单 |
|:----|:----|:----|
| lotteryId | `90` | `45` |
| lottery_style | `jczq` | `dc` |

### 提取比分

导航到 URL 后，页面 banner 中的比分（如"2-0""1-2""3-2"）可以通过 `browser_snapshot` 的 StaticText 直接读取。

**browser_snapshot 输出示例：**
```
- StaticText "法国"
- paragraph
  - StaticText "世3"
- StaticText "2-0"              ← 实际比分
- paragraph
  - StaticText "世界杯"
  - emphasis
- StaticText "摩洛哥"
```

### 验证前提
- 比赛**必须已结束**（否则显示"VS"而非比分）
- 竞足比赛一般在比赛结束后5分钟内更新比分
- 无需登录，无需切Tab，直接导航即可

### 批量验证（复盘场景）

```python
matches = [
    (match_id1, "lotteryId=90&lottery_style=jczq"),  # 竞足
    (match_id2, "lotteryId=45&lottery_style=dc"),     # 北单
]
for match_id, params in matches:
    url = f"https://kt.59itou.com/379/match3/?matchid={match_id}&{params}"
    # navigate → 从snapshot提取比分
    # 比分在banner中作为独立StaticText
```

### 与 prize page 的对比

| 方式 | 耗时 | 复杂度 | 适用场景 |
|:----|:---:|:------:|:---------|
| **match3 详情页（本方法）** | ~3秒/场 | ⭐简单 | 获取单场/少场比分 |
| **prize page DOM解析** | ~5秒/批 | ⭐⭐⭐复杂 | 批量获取+SP+让球数 |

> 复盘时优先使用 match3 详情页查分。如需同时获取 SP/让球数据，再降级到 prize page。
