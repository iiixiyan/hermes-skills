# SKILL.md 灾难恢复指南

> 2026-06-21 实战记录：`write_file` 覆盖事故后的完整恢复流程。

## 事故场景

使用 `write_file` 尝试修复 SKILL.md 的 YAML frontmatter 时，整文件被替换为仅 11 行（660 字节）的 stub。原文件 2129 行（150KB+）全部丢失。

**根因**：`write_file` 是**全量覆盖**操作。当文件被 `read_file` 以 offset/limit 分页读取后，Hermes 发出警告 `"was last read with offset/limit pagination (partial view). Re-read the whole file before overwriting it."`。该警告被忽略。

**铁律**：❌ 禁止用 `write_file` 做小范围 frontmatter 修复。✅ 必须用 `patch` 做精确替换。

## 恢复方法

### 方法A：从腾讯文档恢复（推荐）

用户已备份到腾讯文档时：

```python
# 1. 打开文档
browser_navigate(url='https://docs.qq.com/markdown/<doc_token>')

# 2. 提取完整 innerText
result = browser_console(expression='document.body.innerText')
content = result['result']  # 71K-120K 字符

# 3. 重建 frontmatter + 内容写回
write_file(path='SKILL.md', content=frontmatter + ...)
# 然后用 terminal 的 Python 脚本逐段追加剩余内容
```

### 方法B：从会话记录恢复

如果文件是在本会话中被覆盖（patch 日志仍在 session DB 中）：

```python
# 从 session_search 找到覆盖前的 patch 记录
# 找到成功应用的旧版 patch diff → 逆向还原原内容
session_search(query='write_file SKILL.md overwrite')
```

### 方法C：从 cron 输出目录恢复

cron job 执行时会将完整 skill 文本注入 prompt，输出文件保留历史 skill 内容：

```bash
# 找到事故日期前的最近一次 cron 输出
cat ~/.hermes/cron/output/<job_id>/<datetime>.md
# 前 500 行是 skill 文本，后 500 行是预测输出
```

## 预防措施

1. **修改 SKILL.md 永远使用 `skill_manage(action='patch')`**，按 skill 名称操作，不直接写文件路径
2. **`write_file` 只用于创建全新文件**，从不用于编辑已有文件
3. **定期备份**：将 SKILL.md 全文保存到腾讯文档（`docs.qq.com`）作为恢复点
4. **子代理冲突**：`delegate_task` 子代理如果在后台修改了父进程正在修改的文件，父进程的 `write_file`/`patch` 可能全部丢失。关键文件（SKILL.md）的修改必须在主会话中串行完成。
