## 📊 预测记录追踪 + 凯利配比

> 集成自虾评「足彩盈利系统」v1.0.0（钱多来/A3-1）

该技能附带 `scripts/prediction-tracker.py`，提供三大能力。⚠️ 注意：文件名含连字符无法直接Python import，已创建symlink `prediction_tracker.py` → `prediction-tracker.py`，导入时用 `from prediction_tracker import ...` 即可。

### 1. 预测记录器（SQLite持久化）

**每次做出预测后，调用此模块记录**，赛后可通过复盘更新实际结果，自动统计命中率。

```python
from prediction_tracker import get_tracker

tracker = get_tracker()

# 预测时：记录
tracker.add_prediction({
    'match_num': '5001',
    'home_team': '町田泽维', 'away_team': '浦和红钻',
    'league': '日职联', 'date': '2026-05-22',
    'prediction_1': '1-1', 'prediction_2': '2-1',       # 正常比分
    'prediction_3': '0-0', 'prediction_4': '1-2',       # 异常比分
    'confidence': 3,  # 1-5星
    'lambda_1': 1.23, 'lambda_2': 1.58,
    'home_odds': 2.20, 'draw_odds': 3.00, 'away_odds': 2.93
})

# 赛后：更新结果
tracker.update_result(match_num='5001', actual_score='1-1', home_goals=1, away_goals=1)

# 查看统计
stats = tracker.get_statistics(days=7)
print(stats['direction_rate'])  # 方向命中率
```

**命中判定规则**：精确比分=2分，方向命中=1分，异常区域命中额外标记。

### 2. 凯利公式配比

当需要推荐**投注金额建议**时使用（如串关优化）：

```python
from prediction_tracker import kelly_analysis

kelly = kelly_analysis(
    poisson_home=0.41, poisson_draw=0.30, poisson_away=0.29,  # 我们的概率
    odds_home=2.20, odds_draw=3.00, odds_away=2.93,           # 百家即赔
    bankroll=10000  # 本金
)

if kelly['home']['recommendation'] == '推荐':
    print(f"主胜 投¥{kelly['home']['bet_amount']}")  # 优势1.2%, 投¥120
```

### 3. 联赛差异化EV阈值

```python
from prediction_tracker import league_ev_threshold

# 英超0.25最严 → 法甲0.22 → 日职联0.22 → 德乙/法国杯0.18
threshold = league_ev_threshold('日职联')  # 0.22
```

### 4. 自动比分命中率复盘（scripts/review-score-analyzer.py）

> **用于每日10:00复盘任务**。集成在 cron 任务 f84b9cf8d1ef 的第一阶段。

`scripts/review-score-analyzer.py` 是一个独立的自动化脚本，核心流程：

```
读取 tracker DB 中的昨日预测
    ↓
Playwright 采集开奖结果页实际赛果
    ↓
逐场判定命中状态（精确/方向/异常）
    ↓
生成完整报告：对比表 + 偏差分布 + 缺陷分析
    ↓
更新 tracker DB 中日结记录
```

**用法**：
```bash
# 分析昨天
python3 review-score-analyzer.py

# 分析指定日期
python3 review-score-analyzer.py --date 2026-05-23

# 跳过 Playwright 采集（仅用 DB 数据）
python3 review-score-analyzer.py --date 2026-05-23 --skip-html
```

**输出示例**：
```
## 🎯 比分命中率复盘（2026-05-23）
### 精确命中率：1/1 = 100.0%
### 方向命中率（含精确）：1/1 = 100.0%

| 场次 | 对阵 | 预测 | 实际 | 结果 | 偏差说明 |
|:---:|:----|:----|:---:|:---:|:--------|
| 3001 | 主vs客 | 🛜2-0/3-0 🔥1-1/1-2 | **2-0** | ✅ | 精确命中 |
```

### 5. Cron 集成模式（预测→DB→复盘自动闭环）

每日竞足自动化流水线（2026-05-25精简为单任务）：

```
20:00 每日预测 (cd0456f2c803)
    → 获取全部竞足数据 → 逐场预测
    → 预测完成后调 tracker.add_prediction() 写入 DB
    ↓
次日 10:00 复盘 (f84b9cf8d1ef)
    → 运行 review-score-analyzer.py
    → 读取 DB + Playwright 采实际赛果
    → 生成比分命中率报告（放在复盘最前面）
    → 调 tracker.update_result() 更新命中状态
```

**同步规则**：
- 每场预测输出后立即保存到 DB（用 `execute_code` 运行 Python）
- 每日仅一次预测，无需 DELETE + INSERT 覆盖
- `predictions.db` 位置：`/root/.hermes/skills/sports/football-prediction/predictions.db`
- 复盘脚本会回退读取 cron 输出文件（存于 `~/.hermes/cron/output/<job_id>/`）当 DB 无数据时

⚠️ **复盘前必须验证预测来源**：执行复盘前检查DB中预测的 `created_at` 时间戳。若全部预测同一秒生成且cron任务会话记录显示被截断（「对话截断」），则该批预测可能为未完成版本——立即向用户确认，不可直接用不完整预测做复盘。

⚠️ **DB保存验证必备**：2026-05-26发现cron任务输出「Tracker DB已更新（7条记录）」但实际DB中无对应日期数据。预测写入后必须验证：
```python
# 写入后立即验证
cursor.execute("SELECT COUNT(*) FROM predictions WHERE date = ?", (today,))
saved = cursor.fetchone()[0]
assert saved == expected_count, f"DB保存失败！应{expected_count}条，实{saved}条"
```
**原因**：`execute_code` 环境可能成功执行Python代码但DB连接在环境关闭后丢失写操作（sqlite的auto-commit模式不保证跨进程可见性）。解决方案：每次写入后必须 `conn.commit()` + 验证读取确认。**只读不验证=没保存。**

### 何时使用

| 场景 | 调用 |
|:----|:-----|
| 预测完成后（cron任务） | `tracker.add_prediction(...)` 记录预测 |
| 复盘时（赛后第2天10:00） | 自动运行 `review-score-analyzer.py` |
| 查看待更新 | `tracker.get_pending()` |
| 导出CSV分析 | `tracker.export_csv('文件路径.csv', days=30)` |
| 生成回测报告 | `tracker.generate_report(days=7)` |
| 串关时建议投注额 | `kelly_analysis(...)` |
| 判断比赛价值 | `league_ev_threshold(联赛名)` 对比EV值 |
