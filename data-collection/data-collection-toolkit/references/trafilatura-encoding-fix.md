# Trafilatura 中文编码修复

## 问题现象

使用 `trafilatura.extract(resp.text, ...)` 提取中文网页时，输出中出现乱码：

```
title: å ³äºæ¬ç«  →  应为: 关于本站
description: Hermes Agent ä¸æç¤¾åº  →  应为: Hermes Agent 中文社区
```

这是 **UTF-8 双编码**：原始UTF-8字节被当Latin-1读取后重新输出。

## 根因

`trafilatura.extract(text=...)` 接收的是 Python 已解码的字符串（`resp.text`），在内部对中文字符编码再解码时出错。Trafilatura 在处理 raw bytes 时绕过此路径，编码正确。

## 修复方案

### ⭐ 方案一（推荐）：传入原始字节而非字符串

```python
# ❌ 错误：传入已解码字符串 → 中文乱码
resp = requests.get(url)
md = trafilatura.extract(resp.text, ...)  

# ✅ 正确：传入原始字节 → 中文正常
resp = requests.get(url)
md = trafilatura.extract(resp.content, ...)  # pass raw bytes, not string
```

### 备用方案二：后处理修复

如果已产出乱码文件，修复方法：

```python
# ❌ 错误：三重编码
text = content.decode("latin-1")  # 会让乱码变成三重编码

# ✅ 正确：encode("latin-1") → decode("utf-8")
text = content.decode("utf-8")
fixed = text.encode("latin-1").decode("utf-8")
```

## 验证方法

```python
def has_chinese(text, n=100):
    return any('\u4e00' <= c <= '\u9fff' for c in text[:n])

# 提取后验证
md = trafilatura.extract(resp.content, ...)
assert has_chinese(md), "提取结果无中文，编码可能错误"
```

## 参考

- 实战案例：2026-07-08 爬取 hermesagent.org.cn 全站423篇，初始用 `resp.text` 全部乱码，改为 `resp.content` 后正常
- Trafilatura 版本: 2.1.0
