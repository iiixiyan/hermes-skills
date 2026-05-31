# SkillOpt — Agent Skill 的受控训练方法论

> 来源：Microsoft Research + 上海交通大学 + 同济大学 + 复旦大学
> 论文：https://arxiv.org/abs/2605.23904
> 代码：https://github.com/microsoft/SkillOpt

## 一句话

把 skill 文档当作 frozen agent 的**可训练外部状态**，用训练算法的纪律管理自然语言编辑：rollout batch 提供证据、minibatch reflection 找共性失败、文本 learning rate 控制步长、validation gate 决定接受/拒绝、rejected buffer 保留长期经验。

## 核心框架 — 三个角色

| 角色 | 职责 | 部署状态 |
|:----|:-----|:--------|
| **目标模型** 🎯 | 冻结，按当前 skill 执行任务 | 部署时唯一在线的 |
| **执行框架** ⚙️ | direct chat / Codex / Claude Code 等 | 部署时正常使用 |
| **优化器模型** 🧠 | 离线读轨迹，提 skill 编辑建议 | **训练时出现，部署时不调用** |

最终交付的仍是一份小型 best_skill.md（通常 <2000 tokens），目标模型正常读取。

## 五个训练动作（直接对应维护步骤）

### ① Rollout — 带当前 skill 跑一批任务
记录完整轨迹：消息、工具调用、观测结果、命令输出、验证器反馈。
- 批量太小→优化器抓住偶然错误
- 批量够大→重复失败模式浮出来
- 支持 accumulation（多个 rollout batch 分别反思，再合并一次更新）

**→ 对应我们的复盘动作：收集足够场次（10+）再下结论，不因单场偏差改规则**

### ② 分池反思 — 失败/成功分开
失败样本→提出缺失规则、修正规则
成功样本→保留已有效的做法
minibatch 暴露**可迁移的程序性错误**：总是查错来源、总是漏掉格式约束、总是不验证工具调用结果

**→ 对应我们复盘时按联赛分区、按偏差类型归类分析**

### ③ 受控编辑 — 文本版 learning rate
每步最多应用 Lₜ 条编辑（append / insert / replace / delete）。
- 无约束重写会把 skill 推得太远：今天为一个失败样本写一大段规则，明天又覆盖掉
- 受控编辑让相邻技能版本保持接近，优化历史才有意义
- 默认 Lₜ=4，cosine decay

**→ 对应我们每次只 patch 1-2 条规则，不整份 rewrite**

### ④ 验证集门控 — 严格高于才接受
每个候选 skill 在 held-out selection split 上重新评估。
- 必须**严格高于**当前 selection score 才接受
- **打平也拒绝**（避免 skill 悄悄漂移）
- 文本诊断看起来合理≠真实执行会变好

**→ 对应我们复盘后确认涨分才保留改动，而非"感觉对"**

### ⑤ 拒绝记账 — 被拒的编辑也保留
失败编辑和导致的分数下降记录到 epoch-local **rejected buffer**。
后续反思时优化器看到哪些方向已试过、为什么没通过→减少重复犯错。
不增加部署成本（只存在于训练期）。

**→ 建议我们新增：复盘时把"尝试过但放弃的方向"也记录一笔**

## 慢更新 + Meta Skill

每个 epoch 结束时：
1. 用**上一个 epoch 的 skill** 和**当前 skill** 在同一批任务上对比
2. 把样本分为：改进 / 退化 / 持续失败 / 稳定成功
3. 优化器据此写入一段**长期指导**

**两类状态**：
- **slow update** → skill 里的受保护区域（仍要经过验证集门控）
- **meta skill** → 只给优化器自己看，总结哪些编辑方向有效、哪些被拒绝

设计意图：训练期需要丰富历史，**部署期却需要简洁**。

**→ 对应我们的日复盘→周复盘→技能优化 pipeline，但欠缺"受保护区域"概念**

## 对我们实践的评估

| 已有实践 | 对应 SkillOpt | 成熟度 |
|:--------|:-------------|:------:|
| 复盘采集→分析偏差→patch skill | 轨迹反馈→受控编辑→验证门控 | ✅ |
| 日复盘/周复盘/月复盘多层拆分 | slow/meta update | ✅ |
| 反向优化 skill | 验证集门控 | ✅ |
| 每次只改 1-2 条规则 | 编辑预算 Lₜ | ✅ |
| ❌ 未记录被拒绝的编辑方向 | rejected buffer | ✅ **已实现** — football-prediction `references/10-rejected-edits-buffer.md` + bjdc-prediction `references/16-rejected-edits-buffer.md` |
| ❌ 部分规则缺乏严格 hold-out 验证 | selection split | ✅ **已实现** — football-prediction `references/11-validation-report.md`（S_old vs S_new 完整记录） |
| 多 skill 独立优化 | 技能冲突管理 | 未来 |

## 关键实验数据

- **52/52 评测单元全部最好或并列最好**
- GPT-5.5 direct chat 平均提升 **+23.5 分**
- SpreadsheetBench +38.9，OfficeQA +39.0（程序性任务涨幅最大）
- 最终 skill 通常 <2000 tokens，只需 **1-4 次被接受编辑**
- **跨模型迁移**：GPT-5.4 训练的 skill 可迁移至 GPT-5.4-mini/nano 仍有正收益
- **跨执行框架迁移**：Codex→Claude Code +59.7（反超本地训练）

## 实际工程启发

1. **高频 Agent 任务先走 skill 优化，不必直接微调** — 更便宜、更可控
2. **skill 应有版本、评测和回滚机制** — edit report + selection gate + rejected buffer = 工程治理
3. **训练期复杂，部署期简单** — 这是正确方向，不要反过来
4. **迁移性应成为 skill 资产化的核心** — 一份 skill 不应绑定单模型/单框架
