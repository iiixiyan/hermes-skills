---
name: hermes-agent-skill-authoring
description: "Author in-repo SKILL.md: frontmatter, validator, structure."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, authoring, hermes-agent, conventions, skill-md]
    related_skills: [writing-plans, requesting-code-review, bjdc-prediction]
---

# Authoring Hermes-Agent Skills (in-repo)

## Overview

There are two places a SKILL.md can live:

1. **User-local:** `~/.hermes/skills/<maybe-category>/<name>/SKILL.md` — personal, not shared. Created via `skill_manage(action='create')`.
2. **In-repo (this skill is about this case):** `/home/bb/hermes-agent/skills/<category>/<name>/SKILL.md` — committed, shipped with the package. Use `write_file` + `git add`. `skill_manage(action='create')` does NOT target this tree.

## When to Use

- User asks you to add a skill "in this branch / repo / commit"
- You're committing a reusable workflow that should ship with hermes-agent
- You're editing an existing skill under `/home/bb/hermes-agent/skills/` (use `patch` for small edits, `write_file` for rewrites; `skill_manage` still works for patch on in-repo skills, but not for `create`)

## Required Frontmatter

Source of truth: `tools/skill_manager_tool.py::_validate_frontmatter`. Hard requirements:

- Starts with `---` as the first bytes (no leading blank line).
- Closes with `\n---\n` before the body.
- Parses as a YAML mapping.
- `name` field present.
- `description` field present, ≤ **1024 chars** (`MAX_DESCRIPTION_LENGTH`).
- Non-empty body after the closing `---`.

Peer-matched shape used by every skill under `skills/software-development/`:

```yaml
---
name: my-skill-name               # lowercase, hyphens, ≤64 chars (MAX_NAME_LENGTH)
description: Use when <trigger>. <one-line behavior>.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [short, descriptive, tags]
    related_skills: [other-skill, another-skill]
---
```

`version` / `author` / `license` / `metadata` are NOT enforced by the validator, but every peer has them — omit and your skill sticks out.

## Size Limits

- Description: ≤ 1024 chars (enforced).
- Full SKILL.md: ≤ 100,000 chars (enforced as `MAX_SKILL_CONTENT_CHARS`).
- **Effective upper bound for SKILL.md body (Level 2): under 5K tokens** (~20K chars, ~400-600 lines). This is the Anthropic-recommended limit — exceeding it means the skill body dilutes model attention by consuming context on every trigger invocation.
- Peer skills in `software-development/` sit at **8-14k chars**. If you're pushing past 20k chars / 500 lines, **do not keep adding to SKILL.md**. Split into `references/*.md` and reference them from SKILL.md via Progressive Disclosure (see below).

### Token Budget by Level

| Level | Content | Token cost | Load timing |
|:------|:--------|:----------:|:-----------|
| **Level 1** (YAML frontmatter) | `name` + `description` + tags | ~100/skill | Always (system startup) |
| **Level 2** (SKILL.md body) | Trigger conditions, decision tree, reference index | **Under 5K tokens** | On skill trigger |
| **Level 3** (references/scripts) | Detailed rules, examples, templates, executable scripts | Unlimited | On-demand via bash read |

Level 3 files are only read when the model encounters a `see references/xxx.md` or `run scripts/xxx.py` instruction. Files not referenced never enter context.

## Progressive Disclosure Architecture

Progressive Disclosure is the organizing principle behind Level 1/2/3. A skill should load information in stages as needed, rather than consuming context upfront.

### What the Main SKILL.md (Level 2) Should Contain

The SKILL.md body should be **only**:

1. **Trigger conditions** — when this skill activates (as a table or bullet list)
2. **Decision tree / workflow skeleton** — numbered steps, each 1-2 sentences. This is the model's "map" of what to do.
3. **Reference index** — a table pointing to each Level 3 file with a brief description and WHEN to read it (e.g., "Step 3: read this for factor checking")

Everything else — detailed rules, case studies, template text, long examples, calculation methods, configuration — goes to Level 3.

### What Level 3 Files Should Contain

| Directory | Purpose | Example |
|:----------|:--------|:--------|
| `references/<topic>.md` | Detailed methodology, rules, case studies, research excerpts, domain notes | `references/01-factor-table.md` |
| `templates/<name>.<ext>` | Boilerplate files to be copied and modified | `templates/report.md` |
| `scripts/<name>.<ext>` | Statically re-runnable actions (not ad-hoc code) | `scripts/validate.py` |

### Split Priority (from most urgent to least)

1. **Examples and templates first** — these are longest, least-frequently accessed, and consume the most token budget
2. **Detailed rules next** — rule tables, edge cases, lengthy conditions
3. **Long workflows last** — encapsulate as scripts rather than inline prose

**Do NOT split out**: the decision tree itself. If the model reads the main file and doesn't know what step to take next, the skill is broken.

### Good References vs Bad References

**Good reference:**
```markdown
### Step 3: Review
Run style checks against references/style-guide.md.
Key checks: tone, length, opening hook.
```
→ The model knows what to expect and can decide whether to read.

**Bad reference:**
```markdown
### Step 3: Review
See references/style-guide.md.
```
→ The model doesn't know what's in the file or when it's worth reading. It may skip it or read it every time, defeating Progressive Disclosure.

### Circular References

Sub-files must NOT reference each other. All Level 3 files are indexed by SKILL.md only. A → B → A creates a cascade that loads all files into context simultaneously, negating the "on-demand" advantage.

### User-Preference Embedding

When a user corrects your style, format, output structure, or workflow approach during a session (e.g., "stop doing X", "this is too verbose", "format like Y"), that correction belongs in the **skill that governs that class of task**, not just in memory. Memory captures *who the user is*; skills capture *how to do this class of task for this user*. If you update a skill to embed the preference, future sessions start already knowing the correct approach without needing to be corrected again.

After making a preference-based update, note it in session memory as a cross-reference so the curator can verify the skill was properly updated.

## Peer-Matched Structure

Every in-repo skill follows roughly:

```
# <Title>

## Overview
One or two paragraphs: what and why.

## When to Use
- Bulleted triggers
- "Don't use for:" counter-triggers

## <Topic sections specific to the skill>
- Quick-reference tables are common
- Code blocks with exact commands
- Hermes-specific recipes (tests via scripts/run_tests.sh, ui-tui paths, etc.)

## Common Pitfalls
Numbered list of mistakes and their fixes.

## Verification Checklist
- [ ] Checkbox list of post-action verifications

## One-Shot Recipes (optional)
Named scenarios → concrete command sequences.
```

Not every section is mandatory, but `Overview` + `When to Use` + actionable body + pitfalls are the minimum for the skill to feel like a peer.

## Directory Placement

```
skills/<category>/<skill-name>/SKILL.md
```

Categories currently in repo (confirm with `ls skills/`): `autonomous-ai-agents`, `creative`, `data-science`, `devops`, `dogfood`, `email`, `gaming`, `github`, `leisure`, `mcp`, `media`, `mlops/*`, `note-taking`, `productivity`, `red-teaming`, `research`, `smart-home`, `social-media`, `software-development`.

Pick the closest existing category. Don't invent new top-level categories casually.

## Workflow

1. **Survey peers** in the target category:
   ```
   ls skills/<category>/
   ```
   Read 2-3 peer SKILL.md files to match tone and structure.
2. **Check validator constraints** in `tools/skill_manager_tool.py` if unsure.
3. **Draft** with `write_file` to `skills/<category>/<name>/SKILL.md`.
4. **Validate locally**:
   ```python
   import yaml, re, pathlib
   content = pathlib.Path("skills/<category>/<name>/SKILL.md").read_text()
   assert content.startswith("---")
   m = re.search(r'\n---\s*\n', content[3:])
   fm = yaml.safe_load(content[3:m.start()+3])
   assert "name" in fm and "description" in fm
   assert len(fm["description"]) <= 1024
   assert len(content) <= 100_000
   ```
5. **Git add + commit** on the active branch.
6. **Note:** the CURRENT session's skill loader is cached — `skill_view` / `skills_list` will not see the new skill until a new session. This is expected, not a bug.

## Cross-Referencing Other Skills

`metadata.hermes.related_skills` unions both trees (`skills/` in-repo and `~/.hermes/skills/`) at load time. You CAN reference a user-local skill from an in-repo skill, but it won't resolve for other users who clone the repo fresh. Prefer referencing only in-repo skills from in-repo skills. If a frequently-referenced skill lives only in `~/.hermes/skills/`, consider promoting it to the repo.

## Editing Existing In-Repo Skills

- **Small fix (typo, added pitfall, tightened trigger):** `skill_manage(action='patch', name=..., old_string=..., new_string=...)` works fine on in-repo skills.
- **Major rewrite:** `write_file` the whole SKILL.md. `skill_manage(action='edit')` also works but requires supplying the full new content.
- **Adding supporting files:** `write_file` to `skills/<category>/<name>/references/<file>.md`, `templates/<file>`, or `scripts/<file>`. `skill_manage(action='write_file')` also works and enforces the references/templates/scripts/assets subdir allowlist.
- **Always commit** the edit — in-repo skills are source, not runtime state.

## Optimizing Existing Skills (Skill Maintenance Workflow)

When a user asks you to review, optimize, or fix gaps in an existing skill, follow this workflow:

### Step 1: Audit the Current State
```text
skill_view(name='<skill>')           # Read full SKILL.md + linked files list
skill_view(name='<skill>', file_path='references/<file>.md')  # Read reference files
skills_list(category='<cat>')         # Check for peer/overlapping skills
```

### Step 2: Evaluate Each Improvement Point
For each proposed change, determine:
- Is it **already in the skill** (just buried elsewhere)?
- Is it **duplicative** of another skill (merge or reference instead)?
- Does it **conflict** with existing rules (document the override priority)?
- What's the **effort** (single patch vs multi-section rewrite)?

### Step 3: Apply Patches — Strategy & Tactics

**Batch independent patches in parallel** — changes in different sections of the file can be applied simultaneously via separate `skill_manage(action='patch')` calls:

```text
# GOOD — sections 五, 八, 十三 are independent → parallel calls
skill_manage(action='patch', name='skill', old_string='≥20家→≥15家')  # section 五
skill_manage(action='patch', name='skill', old_string='duplicate heading → enhanced')  # section 八  
skill_manage(action='patch', name='skill', old_string='≥20家→≥15家')  # section 十三
```

**Dependency order for sequential patches** — if Patch B touches the same area Patch A modified, wait:

```text
# BAD — section 九 change means the next patch's old_string no longer matches
patch(九)→patch(九, different part)  # FAIL: old_string gone
# GOOD
patch(九, first_part)→patch(九, second_part, after first run)
```

**Choosing what to modify:**

| Change scope | Method | When |
|:------------|:-------|:-----|
| Single value/number/text change | `skill_manage(action='patch', old_string, new_string)` | Quick threshold tweaks, typos |
| New section between existing sections | `skill_manage(action='patch', old_string=end_of_prev_section, new_string=insertion)` | Adding major new content |
| Full section rewrite | `skill_manage(action='patch', old_string=start_of_section→end, new_string=replacement)` | Replacing outdated content |
| Duplicate heading / structural fix | `skill_manage(action='patch')` to remove or renumber | Cleanup duplicates, numbering gaps |
| Entire skill overhaul | `skill_manage(action='edit')` | Rare — prefer patches for traceability |

### Step 4: Patch old_string Hygiene

- **Include 3-5 lines of context** around your target so the match is unique (avoid accidental matches on similar text elsewhere).
- **For section insertions**, use the `---` separator plus the following section heading as the anchor.
- **For duplicate sections**, include enough surrounding markdown (table rows, adjacent headings) to disambiguate.
- **After each patch**, the `diff` in the response shows you exactly what changed — read it to confirm intent.

### Step 5: Verify Changes

Use terminal to run grep for structural verification:
```bash
grep -n '<new-concept>' SKILL.md       # Confirm new content exists
grep -c '<old-threshold>' SKILL.md      # Confirm old value purged (should be 0)
grep -n '^## ' SKILL.md                 # Check section numbering for duplicates/holes
grep -n '<removed-heading>' SKILL.md    # Verify removed heading gone
```

Also verify:
- No duplicate section headings (same number appears twice)
- No "..." placeholder text left dangling from incomplete sections
- Cross-references in signal tables / numerical reference tables are updated to match renamed sections
- Version bumped (major.minor.patch reflex: new features→minor, thresholds only→patch)

### Step 6: Update Reference Files

If the skill has linked reference files (`skill_view` shows `linked_files`), update them for consistency:
- New signals or thresholds → update any signal matching tables
- New data collection steps → add to workflow documents
- New analysis patterns → add to pattern reference files

### When to Bump the Version

| Change | Version bump | Example |
|:-------|:------------|:--------|
| Typo fix, wording change | Patch (3.0.0→3.0.1) | Fixing example text |
| Threshold adjustment | Patch (3.0.0→3.0.1) | ≥20→≥15 |
| New subsection in existing section | Minor (3.0.0→3.1.0) | Adding 凯利方差 |
| Entire new section added | Minor (3.0.0→3.1.0) | Adding 联赛基因模板 |
| Removed/changed major rules | Minor (3.0.0→3.1.0) | Deprecating a signal type |
| Incompatible restructuring | Major (3.0.0→4.0.0) | Replacing the entire methodology |

### Refactoring Case Study: 2105→214 Lines (−90%)

**Problem:** Two sports-prediction skills (`bjdc-prediction`, `football-prediction`) had SKILL.md files at 2105 lines/96KB and 1240 lines/55KB — 3-4× above the 5K token limit. All content was inline, bloating the context on every trigger.

**Refactoring steps:**

1. **Audit section structure** — grep section headings to identify independent modules
2. **Extract** each module into a standalone `references/XX-topic.md` file, preserving all content verbatim
3. **Write compact SKILL.md** with only: trigger conditions + decision tree (numbered steps) + reference index table
4. **Add "good references"** — each index entry tells the model WHEN in the workflow to read it (e.g., "Step 3: read for factor checking")

**Before vs After:**

| Skill | Before | After | Reduction |
|:------|:------:|:-----:|:---------:|
| bjdc-prediction | 2105 lines / 96KB | 214 lines / 10KB | **−90%** |
| football-prediction | 1240 lines / 55KB | 146 lines / 7KB | **−88%** |

**Results:**
- Main files now at ~1.7-2.6K tokens — well under 5K limit ✅
- All 30+ reference files loaded on-demand, not upfront
- Trigger accuracy expected to improve (no more irrelevant detail diluting attention)
- Maintenance easier: edit a single reference file instead of finding the right spot in a 2000-line monolith

**Key lesson:** The decision tree (workflow steps + branch logic) stays in the main file. Everything else — rules, examples, tables, calculations — goes to references. This is the opposite of instinct (which is to put everything inline "so the model can see it").

### Skill Audit Framework (5 Dimensions)

When a user requests a skill review or optimization, use this structured framework to identify improvement areas, prioritized by impact:

| Priority | Dimension | Audit Questions |
|:--------:|:----------|:---------------|
| **P0** | **架构 — Architecture** | ① 分析链路过长？能否压缩到5步以内？ ② 核心公式阈值在references跳转过多？应内联到SKILL.md ③ 硬编码单一数据源？需fallback容灾 |
| **P0** | **执行 — Execution** | ① AI推理惯性违反规则（如比分反推）？增加推导路径声明强制自我校验 ② 数据可能过期？增加时间戳+自动警告 ③ 缺少可量化的校验机制？ |
| **P1** | **方法论 — Methodology** | ① 固定权重不适配所有场景？需动态化 ② 阈值过于刚性？下沉到子类/联赛模板 ③ 缺少交叉验证/协同校验？ |
| **P1** | **输出 — Output** | ① 每项预测是否附带可验证的推导依据？ ② 是否有风险分级/置信度标注？ ③ 是否有"禁止项"明确列出常见错误？ |
| **P2** | **维护 — Maintenance** | ① 复盘闭环依赖外部DB？简化为结构化文本 ② 跨技能信号可共享？ ③ 版本日志清晰记录变更动机？ |

**Application Rule:** Run 架构→执行→方法论→输出→维护 in order. Within each, find the single highest-ROI change and apply it before moving on. Skip dimensions with no issues found.

### SkillOpt Training Methodology (Methodological Reference)

The paper *SkillOpt: Making Agent Skills Optimizable* (Microsoft Research, 2025) formalizes skill editing as a training loop with gradient-like discipline. A dedicated summary is at `references/skillopt-optimization-methodology.md`.

**Key principles for skill maintenance work:**

| Principle | Our equivalent | How to apply |
|:----------|:--------------|:-------------|
| **Rollout** (batch of task executions) | 复盘采集足够场次 | Don't edit rules based on 1-2 anomalies; wait for 10+ samples |
| **Separate reflection** (failures vs successes) | 按偏差类型分区分析 | Keep what works; add what's missing; don't mix the two |
| **Edit budget** (text learning rate Lₜ) | 每次只 patch 1-2 条规则 | Apply edits in small batches; avoid full rewrites |
| **Validation gate** (strict improvement on held-out data) | 复盘确认涨分才保留 | Reject if scores are flat, not just if they drop; "looks right" ≠ works |
| **Rejected buffer** (track failed edits) | **待补 — 记录被拒绝的编辑** | Add a line in review notes: "tried X, rejected because Y" |

**When to read the full reference:** When planning a multi-session skill improvement campaign, or when audit reveals unstable edits (rules that get added and removed across versions).

### Optimization-Specific Pitfalls

1. **Section numbering drift.** Patches that insert or remove sections can leave duplicate numbers or gaps. Always run `grep -n '^## '` at the end to audit.
2. **Duplicate section content.** The old section may still exist elsewhere in the file if your `old_string` only matched part of it. Check that the removed content is truly gone, not just orphaned.
3. **Cross-reference staleness.** When you rename a section, every signal table, numerical reference, and cross-reference (`§六`, `§三`, etc.) needs updating. Search for the old section number.
4. **Reference file mismatch.** The data workflow in `references/*.md` may describe steps or signals that no longer match the SKILL.md. Patch references symmetrically.
5. **Over-patching.** If a single edit touches 10+ scattered locations, consider `skill_manage(action='edit')` with the full new content instead of 10 separate patches. Patches are surgical; edits are sweeping.

## Emergency SKILL.md Recovery

When a SKILL.md is accidentally truncated or overwritten (e.g., `write_file` only wrote the frontmatter, erasing the rest), follow this recovery procedure.

**⚠️ Recovery tool restriction:** in restricted-tool contexts (e.g., archival review loops) where only `skill_manage` and `memory` are available, you CANNOT use `terminal`/`read_file`/`write_file`/`patch` directly. In such cases, save the lost content as `skill_manage(action='write_file', name='<skill>', file_path='references/recovery-notes.md')` reference files under the damaged skill, and alert the user that a tool-unrestricted session is needed for actual file restoration.

### Step 1: Check Available Backups

| Source | How to check | Recovery method |
|:-------|:-------------|:----------------|
| Session history (current session) | `session_search(query='SKILL.md write_file')` — find the truncation event | Look for patch commands BEFORE the write_file — those show what content existed |
| Session history (prior sessions) | `session_search(query='<skill-name> SKILL.md')` — find earlier versions | Extract content from tool responses (patch diffs, read_file outputs) |
| User-provided cloud backup | Ask the user if they have a copy (Tencent Docs, Gist, Pastebin, email) | `browser_navigate(url)` + `browser_console(expression='document.body.innerText')` to extract |
| Cron output directory | `~/.hermes/cron/output/<job_id>/` — if the skill was used by a cron job | The cron output may include embedded skill content at the top of the output file |
| Git repository (skills dir) | `cd ~/.hermes/skills && git log --oneline -- <skill-path>/SKILL.md` | `git checkout -- <skill-path>/SKILL.md` for HEAD, or `git show <commit>:<skill-path>/SKILL.md > temp.md` for an older commit. Also check `git stash list` for WIP saves |
| Reference files reconstruction | If SKILL.md is gone but `references/` + `scripts/` survive, the methodology can be rebuilt from consolidated reference files (e.g. `references/v*-hardening-scheme.md`) plus the update log entries in any partial backup | Read each reference file → extract key upgrade descriptions → rebuild SKILL.md sections from those descriptions |
| Manual backup | `ls ~/.hermes/skills/<category>/<name>/SKILL.md.bak` or `*~` | Direct `cp` restore |

### Step 2: Extract Content from Tencent Docs (most common backup source)

When the user provides a Tencent Docs link containing the SKILL.md content:

```text
# Navigate to the document
browser_navigate(url)

# Extract the full text — Tencent Docs renders everything in innerText
browser_console(expression='document.body.innerText')

# The result contains the full content including tables, code blocks, and formatting.
# Tables will use tab-separators, code blocks will lose language markers.
# This is acceptable for restoration.
```

### Step 3: Reconstruct the SKILL.md (preferred method)

For files over 50KB, the most reliable approach is **build the full file in `/tmp/` via chunked `write_file`, then `cp` to the final path**:

```text
# 1. Write each section as a separate temp file (write_file handles smaller content fine)
write_file(path='/tmp/skill_part1.md', content='---\\nname: ...\\nversion: ...\\n---\\n\\n...section one content...')
write_file(path='/tmp/skill_part2.md', content='...section two content...')
write_file(path='/tmp/skill_partN.md', content='...section N content...')

# 2. Concatenate into a complete file via terminal
terminal('cat /tmp/skill_part1.md /tmp/skill_part2.md /tmp/skill_partN.md > /tmp/skill_complete.md')

# 3. Copy to the skill directory (cp is a raw byte copy, no truncation risk)
terminal('cp /tmp/skill_complete.md <skill>/SKILL.md')
```

**Why this is better than `write_file` for the final write:**
- `write_file` can silently **truncate** large content (observed: only ~1200 bytes written for an 87KB file). If you pass more content than its buffer handles, the excess is silently discarded.
- `write_file` does NOT raise an error on truncation — you won't know the file is damaged until you check the size.
- `skill_manage(action='edit')` also has a `content` parameter with potential size limits.
- `terminal('cp ...')` is a raw byte copy — it preserves the full content exactly.

**Do NOT use this terminal-write approach:**
```bash
cat > SKILL.md << 'EOF'
...content...
EOF
```
→ Long markdown with backticks and special chars causes escaping issues. Build in temp files instead.

### Step 4: Verify Restoration

```text
# Check total size matches expectations
terminal('wc -l -c <skill>/SKILL.md')

# Verify frontmatter loads correctly
skill_view(name='<skill>')

# Check end of file (update log should be intact)
terminal('tail -5 <skill>/SKILL.md')

# Spot-check key sections
terminal('head -20 <skill>/SKILL.md')  # frontmatter
grep -n '^## ' <skill>/SKILL.md       # section structure
```

### Prevention

- **Back up before editing**: `cp SKILL.md SKILL.md.bak` before structural changes
- **Use `patch` not `write_file`** for targeted frontmatter edits — `patch` preserves the rest of the file
- **Check git first**: before asking the user for a backup, run `cd ~/.hermes/skills && git log --oneline -- <path>` to see if the skill is version-controlled. `git checkout` is the fastest recovery path
- **Keep a cloud copy** of large mission-critical skills (120KB+) in Tencent Docs or a Gist
- **Heed the guard warning**: the system says *"was last read with offset/limit pagination (partial view)"* — this means your write will destroy unseen content

## Common Pitfalls

1. **Using `skill_manage(action='create')` for an in-repo skill.** It writes to `~/.hermes/skills/`, not the repo tree. Use `write_file` for in-repo creation.

2. **Leading whitespace before `---`.** The validator checks `content.startswith("---")`; any leading blank line or BOM fails validation.

3. **Description too generic.** Peer descriptions start with "Use when ..." and describe the *trigger class*, not the one task. "Use when debugging X" > "Debug X".

4. **Forgetting the author/license/metadata block.** Not validator-enforced, but every peer has it; omitting makes the skill look half-finished.

5. **Writing a skill that duplicates a peer.** Before creating, `ls skills/<category>/` and open 2-3 peers. Prefer extending an existing skill to creating a narrow sibling.

6. **Expecting the current session to see the new skill.** It won't. The skill loader is initialized at session start. Verify in a fresh session or via `skill_view` using the exact path.

7. **Linking to skills that don't exist in-repo.** `related_skills: [some-user-local-skill]` works for you but breaks for other clones. Prefer only in-repo links.

8. **Using `write_file` to "fix" frontmatter on a large SKILL.md.** `write_file` OVERWRITES the entire file — if you only pass the frontmatter, the rest of the file is erased. This is how SKILL.md truncation accidents happen. Always use `patch` (find-and-replace) for targeted frontmatter edits. If you must use `write_file`, first read the full file with `read_file(path, offset=1, limit=9999)` to confirm its total size, then construct the full content including everything that should survive.

9. **Reading a large SKILL.md with offset/limit pagination then writing back.** The system warns: *"was last read with offset/limit pagination (partial view). Re-read the whole file before overwriting it."* This is a critical guard. Before any `write_file` on a skill file, call `read_file(path, offset=1, limit=<total_lines>)` to get the full view, or accept that you're about to destroy unseen content.

11. **Sibling subagent conflict — `write_file` silently overwrites.** When a skill file carries a warning *"was modified by sibling subagent... after this agent's last read"*, `patch` detects and rejects stale reads, but `write_file` does not check and will silently destroy the sibling's changes. Always re-read via `skill_view()` before any `write_file` on a skill that a sibling may have touched.

## Verification Checklist

- [ ] File is at `skills/<category>/<name>/SKILL.md` (not in `~/.hermes/skills/`)
- [ ] Frontmatter starts at byte 0 with `---`, closes with `\n---\n`
- [ ] `name`, `description`, `version`, `author`, `license`, `metadata.hermes.{tags, related_skills}` all present
- [ ] Name ≤ 64 chars, lowercase + hyphens
- [ ] Description ≤ 1024 chars and starts with "Use when ..."
- [ ] Total file ≤ 100,000 chars (aim for 8-15k)
- [ ] Structure: `# Title` → `## Overview` → `## When to Use` → body → `## Common Pitfalls` → `## Verification Checklist`
- [ ] `related_skills` references resolve in-repo (or are explicitly OK to be user-local)
- [ ] `git add skills/<category>/<name>/ && git commit` completed on the intended branch
