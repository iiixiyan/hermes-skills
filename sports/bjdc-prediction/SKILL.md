---
name: bjdc-prediction
version: 4.5.0
description: 北单（北京单场）让球胜平负综合预测体系。双模并行（八维预测法+实力盘定位法）+进球数预测。仅适用于北单，不适用竞足。
metadata:
  hermes:
    tags: [北单, 让球胜平负, 八维预测, 实力盘, 泊松, Edge检测]
    requires_toolsets: [browser, terminal, code]
---

# 北单让球胜平负综合预测体系（v4.5.0）

> ⚡ Level 1 路由文档。详细方法论见 references/（Level 2 按需加载）。

---

## 与 skill-evolver 的关系

| 层级 | 范围 | 可改方 |
|:---:|:-----|:-------|
| **Layer 1** | 触发条件/阈值/参数（Edge≥5%、偏重判定8级优先级） | evolver 可自动调 |
| **Layer 2** | 本文件正文（流程描述/输出格式） | evolver 可重写段落，不改变核心流程 |
| **Layer 3** | scripts/ + references/ | evolver 仅在 Layer 2 改不动时才升级到此层 |

---

## 何时使用

| 优先级 | 触发场景 |
|:------:|:---------|
| ⭐⭐⭐ | 用户要求预测北单让球胜平负 |
| ⭐⭐⭐ | 用户询问上下盘方向判断 |
| ⭐⭐ | 用户要求识别诱盘/阻盘 |
| ⭐⭐ | 用户要求分析特定盘口类型 |
| ⭐ | 用户询问数据分析方法 |

---

## 边界与铁纪

- ✅ **仅北单**（lotteryId=45），竞足问题请转 `football-prediction`
- ❌ 禁止北单分析中输出精确比分（如2-1、1-0）
- ❌ 禁止北单分析使用 λ 公式/xG 模型/竞足输出格式
- ❌ 禁止批量输出多场 — 每场单独发送
- ✅ 北单三赔中最低 = 市场最看好方向（但需Edge验证，不可盲信）
- ✅ 逐场采集逐场分析，不可批量
- ✅ 终选前必须重新拉取欧指数据

---

## 快速参考

| 项目 | 内容 |
|:----|:------|
| **数据源** | 列表页 `kt.59itou.com/883/danchang/` → matchID（DIV.id）|
| **详情页** | `lotteryId=45&lottery_style=dc` → 6Tab innerText |
| **北单赔率** | 胜=让球方胜/平=走水/负=受让方不败 |
| **双模** | 模式一(八维基本面) + 模式二(实力盘定位) |
| **Edge** | 模型概率 vs 市场概率，差价≥5%才出击 |

---

## 流程（精简版8步）

1. **数据采集** — 列表页→matchID+三赔→详情页6Tab
2. **模式一：八维预测法**（基本面主导）→ `references/09-prediction-methods.md`
3. **模式二：实力盘定位法**（盘口主导）→ `references/09-prediction-methods.md`
4. **泊松模型基础计算** — 市场校准λ+统计λ+双变量泊松+DC τ修正
5. **信号检查与Edge检测** — 因子检查+联赛阈值+Edge≥5%出击
6. **诱上阻上与盘口验证** — 降水不升盘=诱上，升盘中高水=阻上
7. **进阶工具交叉验证** — 必发交易量+凯利排雷+大小球协同
8. **双模交叉验证与输出** — 两模一致→单选，分歧→并列+偏重/放弃

> 详细8步含进球数预测：`references/12-goal-prediction.md`

### 偏重判定8级优先级

按顺序检查，命中即停：

| 优先级 | 条件 | 偏重 |
|:---:|:---|:---:|
| 1️⃣ | 因子4b触发 | → 偏模式二 |
| 2️⃣ | 实力盘偏离≥1档 | → 偏模式二 |
| 3️⃣ | 联赛=瑞典超/挪超/瑞典甲 | → 偏模式二 |
| 4️⃣ | H2H压倒性压制（≥4连胜或≥80%胜率） | → 偏模式一 |
| 5️⃣ | 保级/争冠战意差（赛季末5轮） | → 偏模式一 |
| 6️⃣ | 联赛=爱超/爱甲/J1/丹甲（信号不可靠） | → 偏模式一 |
| 7️⃣ | 模式二无信号 | → 偏模式一 |
| 8️⃣ | 以上均不命中 | → 放弃 |

---

## 输出格式

```
📌 推荐：[方向A] / [方向B]  ➡ 偏重[方向A]
  ⚽ 进球数：[总进球1]球 / [总进球2]球 / [总进球3]球
  🏋️ 偏重依据：[因子4b触发→偏模式二]
  ⭐ 信心：★★★☆☆
```

### 结构化数据（供evolver解析）
```
<!-- BJDC_STRUCT_START
direction: 让胜
confidence: 4
edge: 0.08
model1: 让胜
model2: 让胜
signals: ["4b一致升赔", "降水不升盘"]
BJDC_STRUCT_END -->
```

---

## 详细方法论（references/ 按需 Level 2 加载）

| 编号 | 文件 | 内容 | 引用时机 |
|:---:|:-----|:-----|:-------:|
| 01 | `references/01-poisson-models.md` | 泊松分布、双变量泊松（ρ修正）、DC τ修正 | Step 4 |
| 02 | `references/02-fundamentals.md` | 基本面：状态趋势、伤停量化、战意评估 | Step 2 |
| 03 | `references/03-market-edge.md` | 市场校准模型、Edge检测三步法 | Step 4+5 |
| 04 | `references/04-common-mistakes.md` | 7大常见误区（欧指一致性误读等） | Step 5 |
| 05 | `references/05-league-templates.md` | 18个联赛基因模板 | Step 5 |
| 06 | `references/06-trap-clv.md` | 诱上阻上识别、CLV监控 | Step 6 |
| 07 | `references/07-handicap-guide.md` | 盘口技术手册、小盘定胆 | Step 6 |
| 08 | `references/08-betfair-kelly-ou.md` | 必发交易量、凯利排雷、大小球 | Step 7 |
| 09 | `references/09-prediction-methods.md` | 八维预测法、实力盘定位法 | Step 2+3 |
| 10 | `references/10-review-methodology.md` | 复盘方法论、信号熔断 | Step 10 |
| 11 | `references/11-review-insights.md` | 复盘优化经验、联赛规律 | Step 10 |
| 12 | `references/12-goal-prediction.md` | 进球数预测完整方法 | Step 8 |
| 13 | `references/13-ouzhi-signal-classification.md` | 欧指一致性信号分类 | Step 5+10 |

---

## 与数据层/工程层的协同

- **数据采集** → `scripts/ingest_bjdc.py`（Level 3，封装采集+缓存+重试）
- **DB追踪** → `scripts/bjdc_prediction_tracker.py`（bjdc_predictions + bjdc_daily_summary 表）
- **Cron任务** → 每天22:00自动拉数据→跑双模→写DB→更新Memory
- **Memory协同** → 联赛/盘口规律、历史命中率写入长期记忆
- **skill-evolver** → GT驱动迭代：复盘→扩展GT manifest→自动评测

---

## 更新日志

| 版本 | 日期 | 变更 |
|:----|:----|:-----|
| v4.5.0 | 2026-05-28 | **SKILL.md瘦身+Layer区分+工程层补全**：①主文档压缩为路由+快速参考 ②显式区分Layer2/Layer3 ③新增结构化数据段供evolver解析 ④对齐Progressive Disclosure架构 |
| v4.4.2 | 2026-05-28 | 复盘2026-05-27周三18场；信号追踪表更新；熔断表新增解放者杯/南俱杯/冰岛超/芬甲 |
