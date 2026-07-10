# 超长公众号文章的程序化排版

当文章超过 30,000 字符时（如 Hermes Agent 完整部署指南），手工逐段装配 HTML 不可行。本文档记录程序化排版的标准做法。

## 工作流

### 1. 在 `gzh-articles/` 下创建文章目录

```bash
mkdir -p ~/gzh-articles/{文章名}/
```

### 2. 准备 Markdown 原文

写入 `{文章名}.md`，确保至少有 30,000+ 字符（中文字符 + 英文 + 代码 + 空格）。

### 3. 编写程序化生成脚本

创建 `build_html.py`，结构如下：

```python
# ============================================
# 辅助函数（从主题组件库翻译而来）
# ============================================

def green_strong(text):
    """核心概念、品牌名 — 绿色加粗"""
    return '<strong style="color:#059669;"><span leaf="">' + text + '</span></strong>'

def green_underline(text):
    """正文关键词下划线 — 每段1-3处"""
    return '<span style="border-bottom:2px solid #A7F3D0;font-weight:600;"><span leaf="">' + text + '</span></span>'

def para(text):
    """正文段落 — 必须包 span leaf"""
    return '<p style="margin-bottom:16px;font-size:14px;line-height:1.9;text-align:justify;"><span leaf="">' + text + '</span></p>'

def code_block(lang, lines):
    """深色代码块 — 摸鱼绿主题"""
    line_html = ''
    for l in lines:
        line_html += '    <p style="margin:0;font-family:\'SF Mono\',Consolas,Monaco,monospace;font-size:13px;line-height:1.6;color:#E2E8F0;"><span leaf="">' + l + '</span></p>\\n'
    return '''<section style="margin:0 0 20px;border-radius:8px;overflow:hidden;background:#1E293B;box-shadow:0 4px 16px -8px rgba(15,23,42,0.4);">
  <section style="display:flex;align-items:center;padding:9px 14px;background:#0F172A;">
    <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#FF5F56;margin-right:7px;font-size:0;line-height:0;overflow:hidden;">.</span>
    <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#FFBD2E;margin-right:7px;font-size:0;line-height:0;overflow:hidden;">.</span>
    <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#27C93F;font-size:0;line-height:0;overflow:hidden;">.</span>
    <span style="margin-left:12px;font-size:12px;color:#64748B;font-family:Consolas,Monaco,monospace;letter-spacing:1px;"><span leaf="">''' + lang + '''</span></span>
  </section>
  <section style="padding:11px 14px;">
''' + line_html + '  </section>\\n</section>'

def step_label(num, title, content):
    """STEP 标签 — 注意 content 必须包 span leaf"""
    return '''<section style="margin-bottom:24px;">
  <section style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="display:inline-block;background:#111827;color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:12px;"><span leaf="">STEP ''' + num + '''</span></span>
    <h4 style="font-size:15px;font-weight:800;color:#111827;margin:0;"><span leaf="">''' + title + '''</span></h4>
  </section>
  <p style="font-size:14px;margin:0 0 16px;color:#4B5563;line-height:1.9;text-align:justify;"><span leaf="">''' + content + '''</span></p>
</section>'''

# 更多函数：table_component, ch_title, subtitle_highlight,
# pill_list, ordered_list, oneliner_card, quote_box,
# green_tip, warn_tip, footer_cta 等
```

### 4. 已知坑位检查清单

生成 HTML 后，必须手动检查以下 5 项再跑校验：

| # | 检查项 | 修复方法 |
|---|--------|---------|
| 1 | `step_label` 的 content 是否包了 `<span leaf="">` | 在函数模板中加死，不要在调用处加 |
| 2 | 中文文本中的逗号、句号、问号是否全角 | 生成后 `half-width -> full-width` 替换 |
| 3 | `oneliner_card` 的金句内容是否安全 | 检查是否有未闭合的 span |
| 4 | 封面/TOC/Footer 常量是否在脚本开头定义 | 维护在脚本顶部便于调整 |
| 5 | CSS 内的逗号是否被误替成全角 | 只替换 `<span leaf="">` 内的文本 |

### 5. 校验 → 预览 → 发布

```bash
# 校验
python3 ~/.hermes/skills/gzh-design/scripts/validate_gzh_html.py "输出.html"

# 预览
python3 ~/.hermes/skills/gzh-design/scripts/wrap_preview.py "输出.html"

# 发布到微信草稿箱（直接传HTML，不走markdown转换）
python3 -c "
import requests, json
# ...获取token → 上传封面(可选) → 直接提交html_content到draft/add
"
```

## 关键原理

- 摸鱼绿主题的组件库 (`theme-moyu-green.md`) 提供完整的 HTML 模板骨架和组件代码
- 通用增量库 (`common-components.md`) 提供代码块和图片组件
- Python 函数封装 = 可维护、可复用的组件抽象层
- 直接调用微信 API draft/add = 保留 gzh-design 全部排版样式
