# SkillLens 实证基线 + darwin-skill 本机验证数据

> SKILL.md 在「评估 Rubric」章节会引用本文件。需要查论文细节、controlled study 数据、HL 实战案例的具体数字时读这里。

---

## SkillLens 论文实证（外部证据）

**论文**：From Raw Experience to Skill Consumption: A Systematic Study of Model-Generated Agent Skills
**作者**：Microsoft Research + 复旦大学 + 上海交大（16 作者）
**arXiv**：2605.23899（2026-05-22，与 SkillOpt 同期发布）
**实验规模**：5 domains（ALFWorld / SpreadsheetBench / SWE-bench-Verified / SEAL-0 / BFCL-v4）× 6 targets × 5 extractors

### 关键发现

1. **75% 案例 skill 有正收益，25% 出现 negative transfer**——即「加 skill 比不加还差」
2. **强 agent 不一定是好 extractor**（Gemini-3.1-FL 在 skill 提取效率上反超 GPT-5.4）
3. **LLM-as-judge 准确率仅 46.4%**——给 LLM judge 两份 skill，让它选哪份更好，**比扔硬币（50%）还差**
4. **meta-skill rubric 把准确率提升到 73.8%**——加入三个维度：
   - **Failure-mechanism encoding**（必须显式编码失败模式）
   - **Actionable specificity**（禁止"考虑/可能"软化措辞）
   - **Risk-action blacklist**（必须有反例清单）
5. 所有 domain 一致 +1.55pp 提升（meta-rubric 不是某个 domain 的特例）

### 对 darwin-skill 的意义

旧 8 维 rubric 全部由 LLM judge 打分 → 系统性乐观偏差 → 本机 results.tsv 早期 40 次 0 revert / 67% dry_run 印证。

v2 9 维 rubric 强化 dim3/dim5 + 新增 dim9 是 SkillLens 验证过的方向。**但即使 73.8%，每 4 次决策仍错 1 次——重要决策必须人审确认。**

---

## 本机 controlled study（2026-05-27）

### 实验设计

- **目标 skill**：huashu-research（170 行，独立度高）
- **V1**：当前 GitHub 仓库最新版（被 darwin-skill 优化过 +33 分的版本）
- **V2 (degraded)**：在 V1 基础上应用 4 类明确质量劣化
- **5 个独立 judge agent** 盲测打分，一半 V1→V2 一半反序

### 结果

| Judge | 顺序 | V1 总分 | V2 总分 | Δ | Verdict |
|---|---|---|---|---|---|
| 1 | V1→V2 | 89.5 | 41.7 | +47.8 | V1>V2 |
| 2 | V2→V1 | 90.2 | 46.7 | +43.5 | V1>V2 |
| 3 | V1→V2 | 89.5 | 37.6 | +51.9 | V1>V2 |
| 4 | V2→V1 | 89.5 | 48.4 | +41.1 | V1>V2 |
| 5 | V1→V2 | 89.5 | 41.4 | +48.1 | V1>V2 |
| **均值** | — | **89.6** | **43.2** | **+46.5** | **5/5 V1>V2** |

### 结论

**rubric 能识别 gross degradation（5/5 high confidence）**，但细粒度判别仍有失效风险。**重要决策仍需人审。**

---

## HL 实战案例

| HL | Skill | 改动 | 分数变化 |
|:---|:------|:-----|:--------:|
| HL-1 视觉标记 | huashu-gpt-image | 4行加🔴/🛑 | dim4 6.0→9.5 |
| HL-2 fallback表 | huashu-gpt-image | 23条三段式 | dim3 6.5→10 |
| HL-3 维度相关 | huashu-gpt-image | 修dim3→dim2自动跟涨 | 7.5→9 |
| HL-4 触顶停手 | huashu-gpt-image | R2仅+0.15→break | — |

## 历史优化记录摘要

| skill | 起分 | 终分 | Δ |
|---|---|---|---|
| claude-design | 74.5 | 91.0 | +16.5 |
| huashu-gpt-image | 80.8 | 91.65 | +10.85 |
| huashu-weread-advisor | 76.5 | 91.4 | +14.9 |
| darwin-skill (self-fix) | 86.05 | 92.05 | +6.0 |