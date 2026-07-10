# 确定性回测方法论 v1.0

> 2026-06-20 创建 — 解决Sina API matchID不稳定问题

## 痛点

Sina API `footballMatchDetail` 和 `footballMatchOddsEuro` 的 matchID **会被定期回收并重新分配给不同的比赛**。例如：
- 2026-06-19 时 matchId=3625106 返回"墨西哥vs南非"
- 2026-06-20 时 matchId=3625106 返回"葡萄牙vs民主刚果"

这意味着：
- 硬编码 matchID + 队名的回测会使用错误的数据
- 依赖API实时数据的回测结果不可复现
- 声称的"XX%准确率"可能实际对应的是不同的比赛

## 解决方案：确定性固定测试集

### 步骤

1. **一次性锁定数据**：在单次运行中同时采集 `footballMatchDetail`(队名/FIFA/天气/比分) + `footballMatchOddsEuro`(欧赔8参数)，输出为Python dict保存到文件

2. **冻结测试集**：`/tmp/fixed_testset.py` 包含 `FIXED_MATCHES` 字典，每场的完整数据硬编码

3. **确定性回测**：从冻结文件读数据，不调用API，结果完全可复现

### Python模板

```python
# freeze_testset.py — 锁定测试集
import json

DATA = {}
for mid in ALL_MIDS:
    d = fetch_detail(mid)  # 从API采集
    odds = fetch_odds(mid) 
    DATA[mid] = {
        'h': d['team1'], 'g': d['team2'], 
        'fh': int(d['team1Position']), 'fa': int(d['team2Position']),
        'rd': int(d['round']),
        'sh': int(score1), 'sa': int(score2),  # 实际比分
        'o1': o1, 'o3': o3, 'r1': r1, ...  # 欧赔8参数
        'weather': weather, 'temp': temp, 'neutral': neutral,  # 基本盘
    }

with open('/tmp/fixed_testset.py', 'w') as f:
    f.write("FIXED_MATCHES = {\n")
    for mid, d in sorted(DATA.items()):
        f.write(f"    {mid}: {json.dumps(d, ensure_ascii=False)},\n")
    f.write("}\n")
```

```python
# fixed_backtest.py — 确定性回测
from fixed_testset import FIXED_MATCHES
# 加载v10引擎
for mid in sorted(FIXED_MATCHES.keys()):
    d = FIXED_MATCHES[mid]
    h_pred, a_pred, rule, conf = v10.predict(
        d['h'], d['g'], d['fh'], d['fa'],
        d['o1'], d['o3'], d['r1'], d['c1'],
        d['r2'], d['c2'], d['r3'], d['c3'], d['rd'],
        weather=d['weather'], temp=d['temp'], neutral=d['neutral'])
    # 对比 d['sh']/d['sa'] vs h_pred/a_pred
```

### 注意事项

- 每天重新锁定一次（数据源可能变化）
- 新旧测试集需分开保存，不能混用
- 赛前预测仍用实时API数据（冻结集仅用于回测验证）
