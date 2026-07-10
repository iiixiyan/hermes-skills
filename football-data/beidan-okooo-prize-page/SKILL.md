---
name: beidan-okooo-prize-page
version: 1.0.0
description: 北单（北京单场）开奖结果采集 — 通过okooo.com开奖页获取已开奖场次（比59itou快，无需等待奖期发布）。场景：日常复盘时59itou开奖页(prize/)尚未更新最新奖期时的替代数据源。
metadata:
  hermes:
    tags: [北单, 开奖, 复盘, 数据源]
    requires_toolsets: [terminal]
---

# 北单 OKOOO 开奖页数据源

> ⚡ 当59itou开奖页未发布最新奖期（如126072未生成）时，okooo已可查26072期结果。

## 数据源URL

**基础模式**：https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=WDL&LotteryNo={期号}

- `LotteryType=WDL` — 让球胜平负
- `LotteryType=OverUnder` — 上下单双
- `LotteryType=Score` — 比分
- `LotteryType=TotalGoals` — 总进球
- `LotteryType=HalfFull` — 半全场

## 期号对应关系

| 来源 | 格式 | 示例 | 说明 |
|:----|:----|:----:|:-----|
| 59itou prize batch | 1260xx | 126071 | 59itou奖期编码 |
| okoolo lotteryNo | 260xx | 26072 | 去掉前缀1即得 |
| 北单奖期 | 260xx | 26072 | 与okoolo一致 |

**转换公式**：okoolo期号 = 59itou批号去掉首位"1"（如126071→26071已损坏，实际为26072对应126072）

## 采集方法

```bash
# 直接curl + iconv转码（okooo页面为GBK编码）
curl -s 'https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=WDL&LotteryNo=26072' \
  -H 'User-Agent: Mozilla/5.0' \
  -H 'Referer: https://www.okooo.com/' | iconv -f GBK -t UTF-8

# 提取赛果表格（序号/对阵/比分/赛果）
curl -s '...' | iconv -f GBK -t UTF-8 | sed -n '/<table/,/<\/table>/p' | sed 's/<[^>]*>//g'
```

## 返回字段

| 字段 | 说明 | 示例 |
|:----|:-----|:-----|
| 序号 | 场次号 | 1~67 |
| 主队(让球) | 主队队名+让球数(-1/+1/0) | 阿根廷(-2) |
| 客队 | 客队队名 | 佛得角 |
| 比分 | 全场比分+半场比分 | 1:1半场1:0 |
| 赛果 | 北单让球胜平负结果 | 主/平/客 |
| matchstatus | 未开赛场次为空 | "" |

## 赛果解读

| 显示 | 含义 | 北单让球结果 |
|:----|:-----|:-----------|
| 主 | 主队胜出（含让球后） | 让胜 |
| 平 | 平局（含让球后） | 让平 |
| 客 | 客队胜出（含让球后） | 让负 |

## 与59itou prize页对比

| 维度 | 59itou prize | okoolo prize |
|:----|:------------|:-------------|
| 更新速度 | 慢（需等官方奖期发布） | 快（赛后即出） |
| 编码 | UTF-8 | **GBK**（需iconv转码） |
| 反爬 | 浏览器SPA渲染 | 直接curl可拿 |
| 批次显示 | 只有4个近期批号 | 20+期历史可查 |
| SP值 | ✅ 显示具体SP | ❌ 不显示SP（仅赛果） |

## 验证记录

2026-07-04验证：26072期已开奖18场，结果可正常提取。59itou同期126072奖期尚未发布。
