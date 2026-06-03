# Darwin Skill — Hermes Agent Adaptation

> Darwin.skill 原设计用于 Claude Code 生态（`.claude/skills/`），在 Hermes Agent 中需要以下适配。

## Skill 路径差异

| Runtime | 技能路径 | Git 上下文 |
|:--------|:---------|:-----------|
| Claude Code | `.claude/skills/<category>/<name>/SKILL.md` | 项目 git repo |
| **Hermes Agent** | `~/.hermes/skills/<category>/<name>/SKILL.md` | `~/.hermes/hermes-agent/` git repo |
| In-repo (Hermes) | `/home/bb/hermes-agent/skills/<category>/<name>/SKILL.md` | 同上 |

**约束**：`~/.hermes/skills/` 本身不是 git 仓库。git 操作必须在 `~/.hermes/hermes-agent/` 中执行。回滚使用文件备份（`cp SKILL.md SKILL.md.bak.YYYYMMDD-HHMM`）而非 `git revert`。

## Phase 0 初始化适配

```diff
- 创建 git 分支：auto-optimize/YYYYMMDD-HHMM
+ 不在 git 仓库则 use 文件备份：cp SKILL.md SKILL.md.bak.YYYYMMDD-HHMM
```

## Phase 1 子agent评分适配

Hermes 没有原生 subagent spawn 能力。替代方案：
1. **优先**：用 `delegate_task` 模拟独立 judge，传递 test prompt + skill 路径
2. **降级**（当 delegate_task 不可用）：干跑验证（dry_run），基于经验数据打分（如 football-prediction 的 5/31 实测方向 77.8%/精确 33.3%）
3. **标注**：在 results.tsv `eval_mode` 列标注 `dry_run` 或 `hermes_internal`

## Phase 2 编辑适配

| Claude Code 方式 | Hermes 替代 |
|:----------------|:------------|
| `git add + commit` | `skill_manage(action='patch')` 直接编辑 |
| `git revert HEAD` 回滚 | 手动恢复：`cp SKILL.md.bak.YYYYMMDD-HHMM SKILL.md` |
| 对比 diff | `skill_manage(action='patch')` 返回的 diff 输出 |

## 结果卡片生成

`screenshot.mjs` 需要 `playwright-core`。在 Hermes 环境中如果 playwright 不可用：
1. 跳过截图，用 markdown 表格替代视觉卡片
2. 或安装 playwright：`npm install -g playwright-core`
3. 浏览器路径：`/usr/bin/chromium` 或 `npx playwright install chromium`