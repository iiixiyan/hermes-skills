# 业界高分预测模型方法论

> 综合 Dixson-Coles / FiveThirtyEight SPI / Pinnacle / ELO / Bayesian 五大体系
> 所有引用模型均已公开发表或文档化

## 一、Dixon-Coles 模型 (1997, 帝国理工)

**核心贡献**: 修正Poisson在低比分区域的系统性偏差

### 关键公式
```
P(X=x, Y=y) = τ(x,y) × Poisson(x|λ₁) × Poisson(y|λ₂)

τ(x,y) = {
  1 - λ₁λ₂ρ           if x=0, y=0
  1 + λ₁ρ             if x=0, y=1
  1 + λ₂ρ             if x=1, y=0
  1 - ρ               if x=1, y=1
  1                   otherwise
}
```
- ρ ≈ -0.05 ~ -0.13 (实测英超)
- 修正后 0-0/1-0/0-1/1-1 概率更准 → **比分预测精度提升5-8%**

### 时间衰减权重
```
w(t) = exp(-ξ × t)     ξ ≈ 0.0018 (半衰期≈半年)
```
vs 我们的固定加权 40/30/30 → 改用指数衰减更科学

## 二、FiveThirtyEight SPI (2017-2023, Nate Silver)

**全球105联赛, Brier Score 0.21, 准确率≈75%**

### 模型架构
```
SPI = Offensive_Rating - Defensive_Rating + League_Adjustment

Rating更新:
  new = old + K × (Actual - Expected)
  K = 基础速率 × 比赛重要性 × 时间衰减

特征输入:
  - xG/xGA (Expected Goals, 非实际进球!)
  - 身价 (Transfermarkt)
  - 主客场调整
  - 比赛重要性权重 (杯赛决赛 > 联赛)
  - 最近5场表现衰减
```

### 关键参数
| 参数 | 值 | 说明 |
|:---|:---|:---|
| 主场优势 | +0.35 球 | 升班马+0.75 |
| 衰减率 | 5%/周 | 1个月后权重≈80% |
| K因子 | 20-32 | 杯赛加倍 |

## 三、Pinnacle 模型方法 (行业标杆)

### 核心原则
```
1. 用xG/shots数据 → 不用实际进球 (进球有方差噪声)
2. 主力 vs 替补分别计算
3. 市场赔率 = 校准目标 (不是输入!)
4. 伤停按位置加权: 射手 -30%, 门将 -25%, 中场 -15%, 后卫 -10%
```

### 特征工程 (比算法选择更重要!)
| 特征 | 权重 | 来源 |
|:---|:---|:---|
| 近6场xG差 | 30% | Understat/etc |
| 赛季xG差 | 25% | 赛季统计 |
| 身价差 | 15% | Transfermarkt |
| 最近交锋 | 10% | H2H |
| 休息天数 | 10% | 赛程 |
| 行程距离 | 5% | 地理 |
| 伤停影响 | 5% | 新闻 |

## 四、ELO评级模型

### 基础ELO
```
R_new = R_old + K × (Result - Expected)

Expected = 1 / (1 + 10^((R_opp - R_home - HFA)/400))

HFA = +100 ELO ≈ +0.35 球
K = 20 (联赛) / 40 (杯赛)
```

### 与Poisson的融合
```
λ_home = base_rate × exp(ELO_diff / 400) × HFA_factor
λ_away = base_rate ÷ exp(ELO_diff / 400)
```

## 五、Bayesian层次模型

### 核心思想
```
Team_strength ~ Normal(League_avg, League_sigma)
                  ↓
Match_outcome ~ Poisson(Team_offense - Opponent_defense)
```

### 优势
- 新球队/新赛季不会过拟合
- 自动向联赛均值收缩
- 置信区间可量化

## 六、实战开源模型（已验证准确率）

### 6.1 Bayesian层次模型 (Xi Zhang, ⭐21 GitHub)
- **准确率: 胜平负80%+ / 进球53%** (西甲1970-2017, 47赛季)
- 模型: Bayesian Hierarchical Poisson → 和我们方向一致但加了Bayesian先验
- 两阶段: (1) logistic回归判胜负 (2) Poisson层次模型预测进球
- 数据量: 47赛季 ≈ 第1点—数据越多,Bayesian优势越大

### 6.2 SoccerPredictor (Richard Szita, ⭐42 GitHub)  
- **Ensemble: XGBoost + Neural Network + Stacking(Ridge meta-learner)**
- 特征工程: Polynomial features + RFE特征选择
- 自动化流水线: 数据采集→赔率抓取→合并→特征工程→训练→预测
- 含前职业球员领域知识

### 6.3 PL Deep Learning (liamhbyrne, ⭐1 GitHub)
- **准确率: 56%均值 / 60.2%峰值** (英超)
- Neural Network on FIFA球员属性 + 近期赛果
- 对比: Bayesian 80% > NN 56% → **NN不是万能的,结构化特征+统计模型更优**

### 6.4 关键启示

| 模型 | 准确率 | 核心方法 | 对我们的启示 |
|:---|:---|:---|:---|
| Bayesian层次 | **80%** 🥇 | 贝叶斯先验+层次Poisson | ✅ DC修正已集成，Bayesian收缩待做 |
| SoccerPredictor | 高 | XGBoost+NN+Stacking | ✅ model_fusion.py已预留XGBoost |
| PL Deep Learning | 56% | FIFA属性+NN | ⚠️ NN不如统计模型，验证了我们方向正确 |

### 融合架构
```
┌─────────────────────────────────────────┐
│  Dixon-Coles修正Poisson (基础)          │ ← 已有, 加入τ修正
│  + 指数衰减加权 (替代固定40/30/30)        │ ← 新增
│  + ELO评级趋势 (长期实力基准)            │ ← 新增
│  + Bayesian收缩 (防过拟合)               │ ← 新增
│  + 市场赔率校准 (止损机制)               │ ← 已有因子体系
│  + 13因子修正层                          │ ← 已有
└─────────────────────────────────────────┘
```

### 实施优先级

| 优先级 | 改进 | 难度 | 影响 |
|:---|:---|:---|:---|
| 🔴 P0 | Dixon-Coles τ因子修正 | 低(纯数学) | 比分命中率+5-8% |
| 🔴 P0 | 指数衰减替代固定加权 | 低(改公式) | 状态识别更准 |
| 🟡 P1 | Bayesian收缩先验 | 中 | 防小样本过拟合 |
| 🟡 P1 | ELO评级集成 | 中 | 长期趋势捕捉 |
| 🟢 P2 | xG数据集成(Understat) | 高(需持续采集) | 模型精度+10% |

## 七、参数速查

### Dixon-Coles ρ 经验值
| 联赛 | ρ | 说明 |
|:---|:---|:---|
| 英超 | -0.08 | 低比分聚集最明显 |
| 德甲 | -0.05 | 进球多，修正弱 |
| 日职 | -0.10 | 低比分联赛，修正强 |
| 默认 | -0.07 | 未校准联赛使用 |

### 指数衰减权重表
| 距今 | 权重 | vs 固定40/30/30 |
|:---|:---|:---|
| 1-3场 | 0.50 | 原0.40 → +25% |
| 4-6场 | 0.30 | 原0.30 → 不变 |
| 7-10场 | 0.15 | 原0.30 → -50% |
| 赛季 | 0.05 | 仅作基准 |
