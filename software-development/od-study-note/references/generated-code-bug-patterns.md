# 生成代码中的常见Bug模式（华为OD学习文档经验）

> 本文档记录从华为OD学习文档生成和复审中发现的代码错误模式，供后续生成和审核时参考。

## 模式1：BFS缺少空根检查

**发现时间**：2026-06-02 (Day22复审)
**位置**：考场必背模板·BFS精简版
**错误代码**：
```python
def bfs(root):
    q = deque([root])   # root=None时 → deque([None])
    while q:
        node = q.popleft()  # node = None
        if node.left: ...   # AttributeError!
```
**修复**：加 `if not root: return []` 在函数开头
**关键词**：BFS, deque, None, 空根

## 模式2：Optional类型注解缺导入

**发现时间**：2026-06-02 (Day22复审)
**位置**：LeetCode题解代码（maxDepth, isSameTree等）
**错误代码**：
```python
def maxDepth(root: Optional[TreeNode]) -> int:  # NameError!
```
**修复**：在代码块开头加 `from typing import Optional`
**关键词**：Optional, typing, NameError, 类型注解

## 模式3：模板代码使用未定义函数/变量

**发现时间**：2026-06-02 (Day22复审)
**位置**：路径传递模板（path_dfs_template）
**错误代码**：
```python
new_state = update_state(state, node.val)   # update_state未定义
dfs(root, initial_state)                     # initial_state未定义
```
**修复**：替换为真实示例代码，如 `state + [node.val]` 和 `[]`
**关键词**：模板, 占位符, NameError, undefined

## 模式4：BFS代码无返回值（仅遍历不产出）

**发现时间**：2026-06-02 (Day22复审)
**位置**：考场必背模板·BFS版
**描述**：BFS模板只遍历不返回结果，初学者可能困惑
**修复**：加返回值或明确注释 `# 在此处理/收集节点值`
**关键词**：BFS, 返回值, 模板

## 触发检查规则

每次生成新文档后，用以下启发式规则扫描：

```python
checks = {
    'deque无None保护': lambda c: 'deque(' in c and 'if not root' not in c.split('def ')[-1][:300],
    'Optional缺导入': lambda c: 'Optional[' in c and 'from typing import Optional' not in c,
    '未定义函数调用': lambda c: has_undefined_calls(c),
}
```
