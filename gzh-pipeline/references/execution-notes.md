# gzh-pipeline 实战执行笔记

本文件记录从实际执行中发现的流程细节、坑点和经验，供后续运行参考。

## 第一阶段：选题（实战经验）

### aihot 数据拉取要点
```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&take=30"
```
- 按 category 分组展示，用户更容易看出选题方向
- 时间显示必须转北京时间：`UTC + 8`

### 选题方向生成
- 4 个选题中至少 1 个「工具使用经验」方向
- 如果是系列文章，先做系列规划（参考 `references/hermes-tutorial-series.md`）

## 第二阶段：调研（实战经验）

### 实用技巧
- 工具类文章（如 Hermes 教程）：主要数据来源是 GitHub API（Star 数、Fork、描述）+ 官方文档
- 调研文件保存到 `_knowledge_base/` 目录

## 第三阶段：写作 + 审校（实战经验）

### 花叔风格写作要点
- 开头用「数据冲击」比「概念引入」更抓人（如「21 万 Star，跟 Linux 内核掰手腕」）
- 用类比帮助理解（「像个实习生，第一天啥都不会，干了一个月独当一面了」）
- 用对比烘托差异（「你用 Claude Code，今天会的，明天还只会这些。用 Codex，这周会的，下周不会多出什么。但 Hermes 会」）

### 审校要点
- 第二遍 AI 腔检查最花时间，重点检查：套话连篇、书面词汇、细节缺失
- 中文引号检查是最终交付前容易漏的：全角 `" " ' '` 代替半角 `" '`

## 第四阶段：配图（实战经验）

### HTML 封面生成
```html
<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body { width:1800px; height:766px; ... }
</style></head><body>...</body></html>
```
- 封面尺寸：1800×766px（2.35:1）
- 封面安全区：核心内容在中央正方形 766×766px 内
- 字体栈：`"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif`

### Playwright 截图
```bash
npx playwright screenshot "file:///path/to/cover.html" cover.png --viewport-size=1800,766 --wait-for-timeout=1500
```
- **坑点**：Playwright 浏览器需要提前安装（`npx playwright install`），新环境不一定有
- **兜底方案**：保存 HTML 文件，提示用户浏览器打开后手动截图

## 第五阶段：排版 + 校验（实战经验）

### gzh-design 摸鱼绿主题工作流

1. **读取主题库**：`references/theme-moyu-green.md`
2. **读取通用增量库**：`references/common-components.md`
3. **装配 HTML**：
   - 封面 → 目录 → 章节标题 → 正文 → 代码块 → 引用框 → 签名 → 三连区
   - 注意：每个 `<span leaf="">` 包裹所有文字节点
   - 装饰性空元素（圆点、分割线、竖线）需要 `<span leaf=""><br></span>` 占位
4. **映射关系示例**：

| Markdown 元素 | 摸鱼绿组件 |
|---|---|
| `## 章节标题` | 组件 4 chapter-title（PART 01/02...） |
| 正文段落 | 组件 5 paragraph（含 6e 绿色下划线） |
| ` ``` bash ``` ` | 通用库 1a 深色代码块（每行 `<p style="margin:0">`） |
| 单行命令 | 组件 8b cmd-block（CMD 标签 + 行内代码） |
| 金句 | 组件 9b oneliner-card（虚线框 + 黄底高亮） |
| 警告 | 组件 10c yellow-warning |
| 列表 | 组件 11g ordered-list（绿色圆形编号） |
| 表格 | 组件 11f table（绿色表头 + 偶数行浅灰底） |
| 目录 | 组件 3 toc-scroll（横向滚动） |
| 签名 + 三连 | 签名段 + 组件 13a footer-cta |

### 校验脚本
```bash
python3 ~/.hermes/skills/gzh-design/scripts/validate_gzh_html.py <html文件>
```
- ERROR 必须清零
- WARNING（半角标点）同样要修复到 0
- 常见 WARNING：命令行示例中的半角引号和中文全角不一致

### 预览页生成
```bash
python3 ~/.hermes/skills/gzh-design/scripts/wrap_preview.py <html文件>
```
- 产出 `{原文件名}_预览.html`
- 浏览器打开 → 点右上角「复制到公众号」→ 公众号编辑器粘贴

## 第六阶段：发布 + 分发（实战经验）

### ⚠️ 凭证配置大坑：AppSecret 截断

**问题**：使用 `echo 'WECHAT_APPSECRET=...' >> ~/.hermes/.env` 写入时，终端输出会被系统自动脱敏，导致实际写入的内容被截断（如 32 位 secret 被截成 `78013150a0...`）。

**正确做法**：

```bash
# 方法 1：用 Python 分段写入（避免终端 echo 截断）
python3 << 'PYEOF'
import os
env_path = os.path.expanduser('~/.hermes/.env')
with open(env_path) as f:
    lines = f.readlines()
with open(env_path, 'w') as f:
    for line in lines:
        if 'WECHAT_APPSECRET' not in line:
            f.write(line)
    f.write('WECHAT_APPSECRET=...完整32位secret...\n')
PYEOF

# 方法 2：用 write_file 工具
```

**验证方法**：
```python
# 检查长度
with open('/root/.hermes/.env') as f:
    for line in f:
        if 'APPSECRET' in line:
            val = line.split('=')[1].strip()
            print(f'Length: {len(val)}, OK: {len(val) == 32}')
```

### 发布流程

```
环境变量 OK？→ IP 白名单 OK？→ 获取 token → 上传封面 → 创建草稿
```

**推荐脚本**：`scripts/publish_draft.py`

### 封面图生成兜底方案

**首选**（有 Playwright 浏览器）：
```bash
npx playwright screenshot "file:///cover.html" cover.png --viewport-size=1800,766
```

**兜底**（无 Playwright 浏览器，用 Python PIL）：
```python
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGB', (900, 383), color=(15, 23, 42))
draw = ImageDraw.Draw(img)
# ...绘制文字和装饰...
img.save("cover.png")
```

封面尺寸：900×383px 或 1800×766px（2.35:1），微信封面建议用 900×383 以减少上传体积。

### 社交推广文案
3 种切入角度：
- **数据冲击型**：以文章中的最惊人数据开头（21万Star、跟Linux内核差不多）
- **金句开头型**：以文章核心观点开头
- **价值主张型**：直接说明工具能做什么
- 每个平台 200-500 字，保持口语化

## 文件命名规范

| 文件类型 | 命名规则 | 示例 |
|---------|---------|------|
| Markdown 初稿 | `{主题}-{篇号}.md` | `hermes-guide-01.md` |
| 排版 HTML | `{原文件名}_排版_{主题中文名}({英文标识}).html` | `hermes-guide-01_排版_摸鱼绿(moyu-green).html` |
| 预览页 | `{排版HTML}_预览.html` | `hermes-guide-01_排版_摸鱼绿(moyu-green)_预览.html` |
| 封面 HTML | `{主题}-cover.html` | `hermes-cover.html` |
| 封面 PNG | `{主题}-cover.png` | `hermes-cover.png` |
| 推广文案 | `{原文件名}_推广文案.md` | `hermes-guide-01_推广文案.md` |

## 产物目录结构

建议所有文章产物放在统一目录下：

```
~/gzh-articles/
├── hermes-guide-01.md
├── hermes-guide-01_排版_摸鱼绿(moyu-green).html
├── hermes-guide-01_排版_摸鱼绿(moyu-green)_预览.html
├── hermes-cover.html
├── hermes-cover.png
└── hermes-guide-01_推广文案.md
```
