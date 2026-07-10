# 预测保存→读取→清理工作流

> 本文件记录竞足和北单预测结果的保存、读取和清理全流程规范。

## 目录结构

```
~/.hermes/predictions/
├── jingzu/          # 竞足预测（每日18:30 cron）
│   └── YYYY-MM-DD.md
└── beidan/          # 北单预测（每日22:00 cron）
    └── YYYY-MM-DD.md
```

## 保存规则（覆盖模式）

- **竞足**：每日预测cron(cd0456f2c803) 18:30 → `cat > ~/.hermes/predictions/jingzu/YYYY-MM-DD.md`
- **北单**：晚场预测cron(99da379ec645) 22:00 → `cat > ~/.hermes/predictions/beidan/YYYY-MM-DD.md`
- 使用 `cat >`（单箭头覆盖）而非 `cat >>`（追加）
- 如果一天内有多次预测（如手动重做），每次覆盖前一次，只保留最后一次

### 保存内容要求

每场比赛必须包含（竞足）：
- λ值、因子检查结果、正常比分（双选）、爆冷比分（双选）、大比分（双选）
- 胜平负[单选]/[双选]、让球、信心评级

每场比赛必须包含（北单）：
- 推荐方向（让胜/让平/让负）、信心评级、偏重依据、SP三赔

## 读取规则（复盘用）

### 竞足复盘（f84b9cf8d1ef, 11:00）
1. **🥇 首选**：`cat ~/.hermes/predictions/jingzu/$(date -d 'yesterday' '+%Y-%m-%d').md`
2. **🥈 兜底**：`~/.hermes/cron/output/cd0456f2c803/` 下最近日期文件
3. **🥉 再兜底**：session_search 或用户微信历史

### 北单复盘（d7b9747e6206, 14:00）
1. **🥇 首选**：`cat ~/.hermes/predictions/beidan/$(date -d 'yesterday' '+%Y-%m-%d').md`
2. **🥈 兜底**：`~/.hermes/cron/output/99da379ec645/` 下最近日期文件

## 清理规则

- **竞足**：每周六08:00周复盘cron(9af717d3c89b)完成后自动清理
- **北单**：每周日08:00周复盘cron(6beabbc435d2)完成后自动清理
- 清理脚本：`~/.hermes/scripts/cleanup-predictions.sh`
- 同时清理 `jingzu/` 和 `beidan/` 两个目录

## 相关脚本

| 脚本 | 路径 | 说明 |
|:----|:-----|:------|
| save-prediction.sh | `~/.hermes/scripts/` | 手动保存预测到指定目录 |
| cleanup-predictions.sh | `~/.hermes/scripts/` | 清理已完成复盘的所有预测文件 |

## 覆盖模式说明

```
第1次预测 → cat > 文件（写入）
第2次预测 → cat > 文件（覆盖前一次）
…最后一次 → cat > 文件（最终保留）
```

核心机制：当天的最后一次竞足/北单预测输出才是复盘时使用的版本。
