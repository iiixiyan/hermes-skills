# skill-evolver: 北单预测技能自进化框架

> 基于 Karpathy AutoResearch + Anthropic skill-creator + Stanford Meta-Harness

## 核心理念

**GT（Ground Truth）定义了"好的skill"的标准，loop让skill不断逼近那个目标。**

```
每次迭代 = 读trace → 改一行 → 评估 → 门控 → 保留/回滚 → 记录trace
```

## 三层突变

| 层 | 内容 | 代价 | 示例 |
|:---|:---|:---:|:---|
| Layer 1 | 触发条件/阈值/参数 | 低 | 修改信号阈值、水位区间、熔断参数 |
| Layer 2 | SKILL.md正文/分析流程 | 中 | 重写八步法描述、调整输出格式 |
| Layer 3 | 脚本/references | 高 | 修复bug、更新参考资料 |

**规则**：每轮只改一层。Layer 1改不动了再升级到Layer 2。

## 8阶段迭代循环

```
Phase 0: Setup → 建workspace + 评测计划 + baseline（一次性）
--- 以下每轮 ---
Phase 1: Review   → 读memory + trace → 找最大问题
Phase 2: Mutate   → 选一层 → 改一（最小改动）
Phase 3: Test     → 跑 GT 评估
Phase 4: Eval     → 3层评测（结构→单条→A/B对比）
Phase 5: Gate     → 5维AND门控：分数↑ × 无回归 × holdout不降 × trace干净 × 不跨层
Phase 6: Keep/Reject → 通过→checkpoint；失败→回滚
Phase 7: Memory   → 写memory记录本轮学到了什么
Phase 8: Trace    → 保存完整执行轨迹到 skill-evolver/traces/
```

## 启动方式

当我（Hermes Agent）被用户要求运行 skill-evolver 时：

```
1. 加载本文档
2. 读取 current GT: skill-evolver/gt/gt-manifest.json
3. 读取 current config: skill-evolver/config.json
4. 运行 evolver.py 做 baseline
5. 进入迭代循环（每轮用户确认）
```

## GT 评估指标

每个GT case含：expected_direction（让胜/让平/让负）+ gt_reasoning

评估时：
- direction_correct: 预测方向是否匹配（权重0.6）
- score_band_correct: 比分范围±1球（权重0.2）
- signal_match: 信号匹配（权重0.1）
- reasoning: 推理逻辑（权重0.1）

## 文件结构

```
skill-evolver/
├── gt/gt-manifest.json         # 标准答案库
├── traces/iter_XXX.json        # 完整执行轨迹
├── checkpoints/iter_XXX/       # 每轮建议保留的快照
│   ├── SKILL.md
│   └── meta.json
├── config.json                 # 演化参数
└── evolver.py                  # 循环骨架
```

## 历史GT扩展

每次复盘后，将新的正确预测案例加入GT manifest，持续扩充测试集。
