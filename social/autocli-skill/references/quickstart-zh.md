# autocli 常用平台命令速查（中文）

## 公共模式（无需浏览器，即装即用）

```bash
# 全球热点
autocli hackernews top --limit 20 --format json    # HackerNews 热门
autocli bbc news --limit 10 --format json           # BBC 头条
autocli v2ex hot --limit 20 --format json           # V2EX 热门话题
autocli arxiv search --query "deep learning" --limit 10  # arXiv 论文搜索

# 搜索
autocli google search --query "关键词" --limit 10   # Google 搜索
autocli stackoverflow search --query "python async" --limit 10  # StackOverflow
autocli wikipedia search --query "机器学习"         # Wikipedia 搜索
```

## 浏览器模式（需要 Chrome + 扩展 + 已登录）

```bash
# B站
autocli bilibili hot --limit 20 --format json           # B站热门
autocli bilibili search --keyword "黑神话悟空" --limit 10  # 搜索
autocli bilibili subtitle --bvid BV1xx... --lang zh      # 视频字幕

# 知乎
autocli zhihu hot --limit 20 --format json         # 知乎热榜
autocli zhihu search --keyword "大模型" --limit 10   # 搜索

# 微博
autocli weibo hot --limit 30 --format json         # 微博热搜
autocli weibo search --keyword "热点" --limit 10

# 雪球
autocli xueqiu hot-stock --limit 20                # 热门股票
autocli xueqiu stock --symbol SH600519              # 茅台行情

# YouTube
autocli youtube search --query "machine learning" --limit 10
autocli youtube transcript --id VIDEO_ID

# 推特/X
autocli twitter trending --limit 20                # 推特趋势
autocli twitter search "关键词" --limit 10
autocli twitter timeline --limit 20                # 时间线
```

## 网页正文提取

```bash
# 任意网页 → 纯净 Markdown（基于 Mozilla Readability）
autocli read https://example.com/article            # 输出 Markdown
autocli read https://example.com/article -f text    # 纯文本（适合喂LLM）
autocli read https://example.com/article -f json    # 结构化 JSON
autocli read https://example.com/article -o article.md  # 保存到文件
```

## 环境适配

```bash
# 中国服务器：GitHub 下载用代理
curl -sL "https://ghproxy.net/https://github.com/..." -o file.tar.gz

# 首次使用前必做
autocli doctor    # 检查所有渠道状态
```
