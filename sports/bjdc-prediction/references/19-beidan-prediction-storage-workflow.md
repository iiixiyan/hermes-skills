# 预测保存→读取→清理工作流（北单版）

> 本文件记录北单预测结果的保存、读取和清理全流程规范。

## 目录结构

```
~/.hermes/predictions/beidan/    # 北单预测（每日22:00 cron）
    └── YYYY-MM-DD.md
```

## 保存规则（覆盖模式）

- **北单**：晚场预测cron(99da379ec645) 22:00 → `cat > ~/.hermes/predictions/beidan/YYYY-MM-DD.md`
- 使用 `cat >`（单箭头覆盖）而非 `cat >>`（追加）
- 如果一天内有多次预测（如手动重做），每次覆盖前一次，只保留最后一次

### 保存内容要求
每场必须包含：推荐方向（让胜/让平/让负）、信心评级、偏重依据、SP三赔

## 读取规则（复盘用）

### 北单复盘（d7b9747e6206, 14:00）
1. **🥇 首选**：`cat ~/.hermes/predictions/beidan/$(date -d 'yesterday' '+%Y-%m-%d').md`
2. **🥈 兜底**：`~/.hermes/cron/output/99da379ec645/` 下最近日期文件

## 清理规则
- **北单**：每周日08:00周复盘cron(6beabbc435d2)完成后自动清理
- 清理脚本：`~/.hermes/scripts/cleanup-predictions.sh`

## 相关脚本
- `~/.hermes/scripts/save-prediction.sh` — 手动保存预测
- `~/.hermes/scripts/cleanup-predictions.sh` — 清理两个目录

## 覆盖模式说明
```
第1次预测 → cat > 文件（写入）
第2次预测 → cat > 文件（覆盖前一次）
最后一次 → cat > 文件（最终保留）
```
