# aihot 选题灵感获取工作流

当用户说「帮我写一篇公众号文章」且未指定方向时，用此流程获取今日 AI 热点作为选题灵感。

## 标准命令

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&take=30"
```

- `mode=selected`：精选模式（主菜单），不用于日报
- `take=30`：拉 30 条，足够覆盖所有 category
- **必须带 User-Agent**，否则 403

## category 分组（固定 5 类）

| API category | 中文标签 | 选题侧重 |
|-------------|---------|---------|
| `ai-models` | 🤖 模型发布/更新 | 新模型、新能力 |
| `ai-products` | 📱 产品发布/更新 | 新产品、新功能上线 |
| `industry` | 🏭 行业动态 | 政策、投资、社会影响 |
| `paper` | 📄 论文研究 | 学术突破、苹果/Google 研究 |
| `tip` | 💡 技巧与观点 | 使用技巧、行业分析、争议话题 |

## 选题生成策略

从以上 5 类中挑 3-4 条最有讨论价值的条目，组合成 3-4 个选题方向：

1. **争议话题**（如 YC CEO 3.7 万行代码争议）→ 自带流量，讨论度高
2. **行业信号**（如微软去OpenAI化、中国限制AI出口）→ 深度分析，信息量大
3. **产品盘点**（如 NotebookLM/Claude Cowork/Grok 同日更新）→ 信息盘点类，易传播
4. **硬核话题**（如首例AI勒索软件、无人战车参战）→ 冲击力强

## 时间转换

`publishedAt` 是 ISO 8601 UTC，展示时必须转北京时间 + 人话：

```python
dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
bj = dt + timedelta(hours=8)
```

## 已规避的坑

- ❌ 不得从聊天历史猜测选题（如之前聊了 GitHub 热榜就直接拿它写文章）
- ❌ 不得在用户没说「日报」时走 /api/public/daily 端点
- ❌ 不得在输出中暴露 `mode=selected` / `take=30` 等 raw 参数
