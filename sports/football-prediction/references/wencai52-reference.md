# 文彩52 交叉验证源

> 最后更新：2026-05-24 | football-prediction v3.9

## 接入方式

**URL**（含店铺token，直达今日推荐）：
```
https://match.wencai52.cn/index.html#/match?mt=8707f9b9-204b-41c1-a01f-9ef227205db3
```

**采集流程**（Playwright Python）：
```python
await page.goto(url, wait_until="networkidle", timeout=30000)
await asyncio.sleep(5)
# 点击"赛事分析"Tab
await page.evaluate('document.querySelectorAll("*").forEach(function(el){if(el.textContent.trim()==="赛事分析")el.click()})')
await asyncio.sleep(3)
# 滚动加载全部
await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
await asyncio.sleep(2)
text = await page.evaluate("document.body.innerText")
```

## 数据格式

每场4维推荐：
```
周日00420:00 瑞超 未开赛 [2]哈马比 索尔纳 [11]
胜              ← 胜平负方向（可组合：平/负、胜/平）
2球/3球         ← 总进球范围
胜胜/平胜       ← 半全场
2:0/2:1         ← 比分推荐（2个）
```

## 近期战绩

| 日期 | 命中 | 比赛 | 命中率 |
|:--|:--|:--|:--|
| 05-23 | 30/25 | 28场 | 89% |
| 05-22 | 6/6 | 9场 | 100% |
| 05-21 | 8/8 | ? | 100% |
| 05-20 | 12/10 | ? | 83% |
| 05-19 | 5/4 | ? | 80% |
| 近7天 | 68/81 | ? | **84%** |

## 交叉验证规则

| 场景 | 行动 |
|:--|:--|
| 方向一致 | 信心+1★，比分微调为文彩比分 |
| 方向分歧 | 标记冲突，供用户裁决 |
| 因子4b≥25升 vs 文彩反向 | **文彩优先**（84% > 4b单信号） |
| 因子4b 20-24升 vs 文彩反向 | **等权标记** |
| 不可达 | 向用户索取，信心封顶★★★ |

## 反爬处理

该站有反爬保护（curl 403 + headless SPA空白）。Playwright headless有时不可达。
兜底：向用户索取今日推荐截图/文本。
