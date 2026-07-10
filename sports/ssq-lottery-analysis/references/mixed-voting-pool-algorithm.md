# 混合投票池算法模式

> 从"独立生产线"到"共享票池+优选"的通用彩票预测架构
> 开发者: Hermes Agent, 2026-06-24
> 应用: SSQ v2.6.0, DLT v3.0.0

## 问题描述

**旧模式（独立生产线）：**
```
策略A → 注1  (6个号, 全部来自策略A)
策略B → 注2  (6个号, 排除注1后从策略B选)
策略C → 注3  (排除注1+注2后从策略C选)
...
```
**缺陷：** 正确号被分散在不同策略的注里，无法"串在一注"。

**新模式（混合投票池）：**
```
所有策略贡献TOP候选 → 共享票池(综合评分排序)
注1: 从TOP40中蒙特卡洛600次采样, 技巧评分选最优
注2: 排除注1号, 从剩余TOP40中同样优选
注3~5: 依次递推
```
**优势：** 每注含多种策略精华，正确号集中命中。

## 算法结构

### 1. 投票池构建

```
for each 策略:
   贡献TOP N个号 → 加入pool
   每个号: {score: 综合评分, sources: [策略列表]}
```

**通用评分公式：**
```
每个策略赋予权重w_i
pool[number].score += w_i * (pool_size - rank_i)
```

**典型权重：**
| 策略类型 | 权重 | 贡献数 |
|:--------|:----|:------|
| 综合评分TOP | 递减x3 | 15个 |
| 热号/高频 | 递减x2 | 10个 |
| 分散/两极 | 固定+3 | 各区两端 |
| 易理/卦象 | 固定+8 | 全部 |
| 短期动量 | 频率x4 | 10个 |

### 2. 顺序排除

```
exclude_set = {}
for i in 5:
    available = pool - exclude_set
    candidates = available[:40]
    pick = monte_carlo(candidates, i)  # 每注不同种子
    exclude_set.update(pick)
```
确保5注不重叠，最大化覆盖。

### 3. 蒙特卡洛优选

```
for 600次采样:
    combo = random.sample(candidates, N)  # N=6(SSQ)或5(DLT)
    score = 0
    
    # 和值评分
    if sum_in_ideal_range(combo): score -= bonus
    else: score += abs(sum - ideal_sum) / divisor
    
    # 区间/分区均衡
    zones_covered = count_zones(combo)
    score -= zone_bonus[zones_covered]
    
    # 奇偶平衡
    odds = count_odd(combo)
    score += odd_penalty[odds]
    
    # 连号
    if has_consecutive(combo): score -= consec_bonus
    
    # 尾数多样性
    tails = set(n%10 for n in combo)
    score += tail_diversity_penalty[len(tails)]
    
    # 龙头凤尾 (首尾号范围)
    if min(combo) <= low_head: score -= head_bonus
    if max(combo) >= high_tail: score -= tail_bonus
    
    # 其他领域特定约束
    # - SSQ: 黄金分割点, 码距多样性, 恒值号保护
    # - DLT: 质数(1-2个), 五区覆盖(≥4个)
    
    if score < best_score:
        best_score, best_combo = score, combo
```

## 领域参数速查

| 参数 | SSQ (6红球) | DLT (5前区) |
|:----|:-----------:|:-----------:|
| 理想和值 | 102 (均值) | 100 (范围85-115) |
| 区间数 | 3 (一/二/三区) | 5 (一~五区) |
| 每区间上限 | 3个 | 2个 |
| 龙头范围 | ≤5 | ≤5 |
| 凤尾范围 | ≥29 | ≥30 |
| 连号加分 | -4 | -4 |
| 龙头加分 | -8 | -4 |
| 凤尾加分 | -8 | -4 |
| 尾数多样加分 | ≥4种(-3), ≤2种(+5) | ≥4种(-3), ≤2种(+4) |
| 特殊加分 | 黄金分割(-4/个), 码距≥4(-3) | 质数1-2个(-3) |

## 实现模板

```python
def get_voting_pool(self, period):
    """各策略贡献TOP候选 → 共享票池"""
    pool = {}  # number -> {score, sources}
    
    # 策略1: 综合高分TOP15
    for rank, (n, s) in enumerate(top15):
        pool.setdefault(n, {'score':0,'sources':[]})
        pool[n]['score'] += (15-rank)*3
        pool[n]['sources'].append('高分')
    
    # 策略2: 热号TOP10
    for rank, n in enumerate(hot_top10):
        pool.setdefault(n, ...)
        pool[n]['score'] += (10-rank)*2
        pool[n]['sources'].append('热号')
    
    # ... 更多策略
    
    ranked = sorted(pool.items(), key=lambda x: -x[1]['score'])
    return ranked, pool

def get_5sets(self, period):
    ranked, pool = self.get_voting_pool(period)
    ranked_nums = [n for n,_ in ranked]
    exclude_set = set()
    sets = []
    
    for i in range(5):
        available = [n for n in ranked_nums if n not in exclude_set]
        candidates = available[:40]
        pick = self._monte_carlo(candidates, seed=42+i*777)
        sets.append(pick)
        exclude_set.update(pick)
    
    return sets
```

## 优化循环

遇到性能瓶颈时的诊断流程：

1. **跑100期回测 → 分析命中分布**
2. **检查策略贡献**：哪些策略的号在最佳组合中出现最多？
3. **调整权重**：弱策略降权，强策略升权
4. **增加约束维度**：遗漏的命中区间可能需要新的评分维度
5. **重跑回测对比**：只有回测提升才算改进
6. **重复**：每次小步+5%改进

**已知问题：**
- 顺序排除导致后注候选池变小 → 第4-5注质量下降（不可完全避免，但蒙特卡洛优选可以缓解）
- 权重太高导致多样性损失 → 固定+3/号的分散策略可保证基础多样性
