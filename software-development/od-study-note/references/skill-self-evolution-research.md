# Skill 自进化研究 — 三种前沿方案

来源：微信公众号文章《如何更科学、方向可控的实现 Skill 的"自进化"?》（阿里技术团队，2026）
原文链接：https://mp.weixin.qq.com/s/2Cq0QR3vcKlMHkI0XyYYrw

## 核心痛点

当前 Skill 自动沉淀机制大多基于单轮 Agent 轨迹 — 容易过拟合到极端 Case → 方向跑偏 → 越优化越差 → 企业不敢在线用。

个人场景影响有限（任务多样、复用率低），但企业级场景（每日重复同类任务、海量 Query）则严重受限。

## 方案一：Trace2Skill（归纳推理学派）

- **来源**：阿里千问团队，论文 + 开源
- **核心思路**：并行看大量轨迹 → 分层合并 → "被多人提到的才进报告"
- **三步流程**：
  1. 轨迹生成：用初始 Skill 跑一批任务，分离成功/失败轨迹
  2. 并行提案：每条轨迹配一个 Sub-Agent 分析师 → 输出补丁提案
     - Success Analyst (A+)：成功经验提取，一次调用 LLM，低成本
     - Error Analyst (A−)：失败根因挖掘，多轮 ReAct 循环推理，找准根因
  3. 无冲突归纳：层次化归并所有补丁，持续检查引用/冲突/格式
- **类比**：专家开会，分头看案例，再合并意见
- **优势**：一次成型，效率高，最终 Skill 简洁可读
- **风险**：合并器要够强，否则丢细节
- **代码**：https://github.com/Qwen-Applications/Trace2Skill
- **论文**：https://arxiv.org/pdf/2603.25158

## 方案二：EvoSkill（自验证选择学派）

- **来源**：Sentient Labs，论文 + 开源
- **核心思路**：Skill 慢慢长出来，每轮对一个具体失败提出改进，验证后保留
- **三个角色闭环**：
  - Executor：跑任务产生轨迹
  - Proposer：分析轨迹，诊断失败根因，提出优化提案
  - Builder：把提案落实为 Skill 修改
- **验证机制**（核心创新）：
  - 在独立验证集上评估新 Skill
  - 只有表现优于旧版本才保留
  - 失败案例存入历史库 H，供后续学习
- **前沿集合（Frontier）**：固定容量 k 的精英池，始终保留得分最高的 k 个程序
- **类比**：自然选择进化，适应度（验证分数）高的延续下来
- **优势**：自然生长出 Skill 库，每个 Skill 对应具体失败模式，可解释性强
- **风险**：每轮只改一处，收敛慢；不同轮次结果差异大
- **代码**：https://github.com/sentient-agi/EvoSkill
- **论文**：https://arxiv.org/pdf/2603.02766

## 方案三：SkillOpt（训练优化器学派）

- **来源**：微软 + 上海交大、同济、复旦，论文 + 开源
- **核心思路**：把 Skill 当神经网络参数一样训练，有学习率约束 + 验证门控 + 动量
- **六大组件**：
  1. **前向传播**：Batch Size=40 执行任务，全量记录轨迹
  2. **反向传播**：分 Minibatch（默认8）反思失败，产出一组原子编辑
  3. **学习率约束**：每步只允许 Lt 条编辑生效（Cosine/Constant/Linear 调度）
  4. **验证门控**：严格优于当前最优才接受（平局也拒绝），被拒入 Rejected-Edit Buffer
  5. **慢更新 + 元更新**：每 Epoch 四类样本归因（提升/退步/持续失败/稳定成功），受保护区域 + Meta-Skill
  6. **Harness 无关部署**：最终仅一个 best_skill.md（300-2000 Tokens），零依赖
- **关键设计类比**：
  - Skill 文本 = 模型权重
  - 验证反馈 = 梯度
  - LLM 改写引擎 = 优化器（SGD/Adam）
  - 编辑数限制 = 学习率
- **优势**：可控性最强，每步只动一点点
- **风险**：组件太多，强依赖稳定验证集和打分函数
- **官网**：https://microsoft.github.io/SkillOpt/
- **论文**：https://arxiv.org/pdf/2605.23904
- **代码**：https://github.com/microsoft/SkillOpt

## 三者对比速查

| 对比项 | Trace2Skill | EvoSkill | SkillOpt |
|--------|-------------|----------|----------|
| 优化对象 | 单份 SKILL.md + Reference | 可多个 Skill 文档 | 单份 best_skill.md |
| 数据采集 | 一次性跑完训练集 | 每轮跑 batch 收集失败样本 | 每步 rollout batch（默认40） |
| 更新粒度 | 并行 patch，层次归并 | 每轮一个新 Skill | 每步多个 bounded 原子编辑 |
| 验证 | 格式校验 + 冲突检测 | 验证集得分超前沿最弱者 | 严格大于当前最优 |
| 学习率 | ❌ | ❌ | ✅ 每次 Lt 条 |
| 动量 | ❌ | ❌ | ✅ |
| 元学习 | ❌ | 累计历史 H | Meta-Skill |

## 选型建议

- **快速落地、规律性强** → Trace2Skill（性价比最高）
- **有完善自动化评估体系** → EvoSkill / SkillOpt
- **混合策略**：Trace2Skill 快速生成基线 → EvoSkill 持续扩充 → SkillOpt 精细打磨核心瓶颈

## 与 Hermes Agent 的关联

Hermes Agent 的 Skill 自动沉淀当前基于**单轮轨迹**方式。上述三种方案提供了更科学的替代思路：

- 引入 **验证机制**（EvoSkill/SkillOpt 的思路）能有效防止 Skill 质量飘忽不定
- **批处理聚合**（Trace2Skill 的思路）能避免单点轨迹带偏方向
- **学习率约束**（SkillOpt 的思路）能防止 Skill 越改越臃肿
