# 竞足技能文件清理方法论

> **版本**: v10.37 清理行动 (2026-07-10)
> **结果**: 14个旧脚本 + 105个旧引用删除，目录200→91文件

## 系统性清理流程

### 1️⃣ 全景扫描
```bash
# 先看完整目录结构
find . -type f | sort
# 统计分布
echo "scripts:" && ls scripts/*.py | wc -l
echo "references:" && ls references/*.md | wc -l
echo "templates:" && ls templates/*.md | wc -l
```

### 2️⃣ SKILL.md交叉引用检查
```bash
# 看SKILL.md引用了哪些脚本/引用
grep -r "references/" SKILL.md | grep -oP 'references/[a-zA-Z0-9._/-]+' | sort -u
grep -r "scripts/" SKILL.md | grep -oP 'scripts/[a-zA-Z0-9._/-]+' | sort -u
```
未被SKILL.md引用的文件 → **候选删除**（注意SKILL.md可能只引用了关键文件，工具类脚本可能不显式引用）

### 3️⃣ 脚本依赖链分析
```bash
# 检查每个旧脚本是否被其他活跃脚本导入
for f in candidate_to_delete.py; do
  base=$(basename $f .py)
  grep -rl "$base" *.py | grep -v "$f" || echo "(not imported)"
done
```
**死集群检测**: 多个脚本只互相import、但无任何活跃脚本引用它们 → 整组可删

### 4️⃣ 重复内容检测
```bash
# md5相同 = 精准重复
md5sum file1.py file2.py
# 相似文件名对比
diff <(head -20 file1.py) <(head -20 file2.py)
```
典型重复模式：
- `file-v2.1.py` 是 `file.py` 的子集（同docstring但行数更少）
- `file_tracker.py` 与 `file-tracker.py` 完全重复（连字符vs下划线）

### 5️⃣ 版本号差距扫描
```bash
ls references/v10.*.md
```
**标准**: 当前版本v10.35+时，v10.8~v10.19（版本差>10）→ 可删
**保留**: 最近1-2个版本的回测 + 当前版本状态记录

### 6️⃣ review-findings 时效性修剪
只保留最近14天的复盘记录。更早的每日复盘中沉淀的规则已进入F因子表（SKILL.md §二）。

### 7️⃣ 编号文件检查
```bash
ls references/[0-9][0-9]-*.md
# 检查是否被SKILL.md引用
grep "01-factor-table\|02-abnormal" SKILL.md
```
未被引用 + 编号格式（如01-、05-、18-等）= 旧版系统文档，可删。

### 8️⃣ 验证
```
清理前总文件数 → 清理后总文件数 → 确认无错删
SKILL.md无悬挂引用（引用实际存在的文件）
git diff --stat 确认删除文件列表
```

## 适用场景
- 每个大版本(vX.0+)升级后执行
- 增量更新超过3版(如v10.35→v10.38)时执行
- 当目录文件 >150 时触发清理

## 铁律
- **先用 patch 不要用 write_file 改 SKILL.md**（write_file是全量覆盖会销毁）
- 依赖链不确定的文件先标记、观察2轮预测后再最终删除
- 保留数据源文档（sina/sporttery/59itou/okooo）独立于版本号
- 保留所有leagues配置（持续使用）
