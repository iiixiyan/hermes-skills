# 59itou 北单 matchID 发现技巧

> 2026-05-31 发现 | 驱动场景：北单89 AC奥卢vs查路 matchID 定位

## 问题

北单列表页 `kt.59itou.com/883/danchang/` 使用 Vue 虚拟滚动渲染，match 89+ 的匹配项不会自动加载到 DOM 中。`document.querySelectorAll('.gotoMatchbtn')` 返回 0，无法通过点击进入详情页获取 matchID。

## 解决方法：竞足→北单 matchID 桥接

### 原理

同一场比赛在 竞足 (lotteryId=90) 和 北单 (lotteryId=45) 中使用相同的 **matchID**。竞足列表页 `kt.59itou.com/627/jingcai/` 的 DOM 加载更完整，可以从竞足页面获取 matchID，然后构造北单 URL。

### 步骤

```
1. 打开竞足列表页: https://kt.59itou.com/627/jingcai/
2. 找到目标比赛（如 AC奥卢在竞足中编号通常是 700X 系列）
3. 点击"分析"按钮获取 matchID（从 URL 中提取）
4. 构造北单URL:
   https://kt.59itou.com/{route}/match3/?matchid={matchID}&lotteryId=45&lottery_style=dc
```

### 已知 matchID 映射（2026-05-31）

| 比赛 | 竞足ID | 北单ID | matchID |
|:----|:------:|:------:|:-------:|
| 赫根vs哈马比 | 7005 | 85 | 2600937 |
| 代格福什vs布鲁马波 | 7006 | 86 | 2600934 |
| 韦斯特罗vs哥德堡 | 7004 | 87 | 2600930 |
| 瑞士vs约旦 | 7007 | 88 | 2676839 |
| AC奥卢vs查路 | 7008 | 89 | 2598621 |

### 注意

- 竞足和北单的编号不同（竞足用 4位数字如 7008，北单用 2位数字如 89）
- 但 matchID 是同一套 ID 体系，在两种 lotteryId 下共享
- 友谊赛（如瑞士vs约旦）的 matchID 与联赛比赛（如瑞超）的 matchID 不连续
- `route` 参数（URL中的 3位数字如 /918/）对同一场比赛在竞足和北单中可能不同
