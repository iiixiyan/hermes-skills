# 复盘数据重构工作流 — 当预测文件不完整时

> 创建: 2026-07-01（由6月月度复盘cron实践总结）
> 场景: 月度/周度复盘时，`~/.hermes/predictions/jingzu/` 下预测文件只有部分日期有保存

## 问题

专用预测目录 `~/.hermes/predictions/jingzu/` 中的 `.md` 文件可能因以下原因不完整：
- cron 启动失败（DeepSeek API 401, 采集超时等）
- 文件被周度清理（每周六复盘后自动清理）
- 预测生成时写入失败
- **用户临场重拉覆盖但未保存**（2026-06-23阿根廷教训）

## 多源数据重构流程

当预测文件不全时，按以下**5层优先级**逐步重构：

### Layer 1：已保存的预测文件

```python
# 直接读取
import glob
files = sorted(glob.glob('/root/.hermes/predictions/jingzu/2026-06-*.md'))
# → 可能只有少量文件（如仅 06-27, 06-29, 06-30）
```

**优点**：最精确，含完整λ/因子/规则链
**缺点**：覆盖率不稳定，可能大量缺失

### Layer 2：Review Findings 文件

```python
# review-findings 文件中已记录逐场对比和准确率
import glob
files = sorted(glob.glob('/root/.hermes/skills/sports/football-prediction/references/review-findings-2026*.md'))
for f in files:
    with open(f) as fh:
        content = fh.read()
        # 提取"## O 准确率统计"或"偏差表"段
        # 已记录的项目可以直接复用，不需要重新采集
```

**优点**：复盘时已记录的数据可直接复用
**缺点**：只包含已复盘的日子，非每日

### Layer 3：Cron 输出文件的末尾部分

```python
# Cron 输出文件包含完整预测 + skill 内容，预测在文件末尾
# 使用 tail 读取最后几十行
import os
for dirpath in ['/root/.hermes/cron/output/f6e7f112d98a/',  # 竞足每日预测(18:30)
                 '/root/.hermes/cron/output/3b4fb5b68dbf/',  # 复盘/预测
                 '/root/.hermes/cron/output/d7b9747e6206/']: # 北单复盘
    if os.path.isdir(dirpath):
        for fn in sorted(os.listdir(dirpath)):
            fpath = os.path.join(dirpath, fn)
            if fn.endswith('.md'):
                stat = os.stat(fpath)
                # 读取最后2000字符
                with open(fpath, 'rb') as f:
                    f.seek(max(0, stat.st_size - 2000))
                    tail = f.read().decode('utf-8', errors='replace')
                    # tail 中包含预测输出
```

**注意**：文件很大（200~300KB），因为包含完整skill内容。
**读取方式**：先 `stat.st_size` 获取大小，再 `seek` 到末尾附近。

### Layer 4：Session 历史搜索

```python
# 使用 session_search API 查找特定日期的预测
# 查询模式："{日期} 预测"、"{日期} 竞足"、"{日期} 世界杯"
# ⚠️ 结果可能被大session（如6/30）淹没，需要 scroll 查看
```

**注意**：session_search 在大session上千条消息时返回可能不完全。
**技巧**：使用 `sort='oldest'` + `limit=5` 获取最早的匹配会话。

### Layer 5：Engine Backtest 数据（仅参考，不计入赛前准确率）

```python
# v10.8k 54场回测 96.3%
# v10.10 46场回测 100%
# v10.12 37场回测 100%
# ⚠️ 这些是事后修正引擎的后验结果，不是赛前预测准确率
# 必须在报告中明确标注"纯后验不计入赛前准确率"
```

## 数据整合规则

### 去重

同一场比赛的同一版本预测出现在多个源中 → 只计1次
同一场比赛的不同版本预测 → 以**最后版本**为准（同multiversion验证铁律）

### 准确率合并

```python
# 有明确记录的数据点 > 需合并计算的数据
# Layer 1 > Layer 2 > Layer 3 > Layer 4
# 如果Layer1只有5天数据（共60场但只有30场可验证）:
# → 标注为 "30场有记录，方向XX%"
# → 不加"共60场XX%"
```

### 报告标注

```markdown
**⚠️ 数据完整性说明：**
- 预测文件仅保存了N天（共M天）
- 部分准确率数据来自复盘文件（review-findings）
- 标注为"有记录场次"的准确率
- 总场次为估算值（含非保存日期的cron输出）
```

## 特殊值处理

| 数据源 | 优先级 | 说明 |
|:-------|:------:|:------|
| 保存的预测文件 | 🥇 | 最精确 |
| review-findings | 🥇 | 已记录的直接复用 |
| cron输出文件末尾 | 🥈 | 需定位tail |
| session历史 | 🥉 | 可能不完整 |
| 引擎后验回测 | ❌ | 不用于赛前准确率 |

## 实际案例：2026年6月月度复盘

```
预测文件: 仅06-27, 06-29, 06-30 (3份)
Review findings: 06-15, 06-22, 06-27, 06-28 (4份含逐场准确率)
Cron输出(f6e7f112d98a): 06-24 ~ 06-30 (7天)
→ 实际可重构约85场中的60场(70%)
→ 标注"总85场中有记录约60场"
```

> **关键判断**：如果某个时间段的预测数据完全不可重构（如6月1-14日预测文件全缺失且review-findings无记录），则在报告中标注"6/1-6/14数据不可重构"并跳过该时段，**不要**编造数据填补。
