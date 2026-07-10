# 球探体育 (titan007.com) 基本盘数据源

> 发现时间: 2026-06-19 | 验证: 4场世界杯分析页数据可采

## 用途

提供比赛的结构化基本盘数据（积分排名、近10场战绩明细、H2H历史、球员评分、伤停名单、数据对比表），弥补新浪API/59itou API缺少的球队状态数据。

## 与天天盈球的对比

| 数据项 | titan007 | 天天盈球 |
|:------|:--------:|:--------:|
| 积分排名 | ✅ 分组完整排名表 | ✅ |
| 近10场明细（含对手/比分/盘口/角球） | ✅ 结构化表格 | ⚠️ 散文描述 |
| H2H历史（含盘口水位） | ✅ 完整记录 | ⚠️ 只提一句 |
| 球员评分 | ✅ 首轮全部球员评分 | ❌ 无 |
| 伤停名单 | ✅ 结构化表格 | ✅ 散文 |
| 数据对比（胜率/场均进球/角球/黄牌） | ✅ 百分比+数值表格 | ❌ 无 |
| 综合实力分析（散文） | ❌ 无 | ✅ 详细 |
| 有利/不利因素 | ❌ 无 | ✅ 每条分析 |

**titan007强在量化结构化数据，天天盈球强在定性分析。两者互补。**

## URL结构

```
即时比分（世界杯）: https://live.titan007.com/oldIndexall.aspx
分析页面:           https://info.titan007.com/analysis/{schedule_id}cn.htm
赛程ID列表:         https://data.titan007.com/soccer_scheduleid.js
```

## 数据提取方法

### 方式1：浏览器导航（推荐 — 完整数据）

1. `browser_navigate('https://live.titan007.com/oldIndexall.aspx')`
   → 点击"世界杯"标签 → 找到目标比赛行
2. 点击"析"链接（每行第1个） → 进入分析页
3. `browser_console(expression='document.body.innerText')`
   → 提取全部内容，包含:
     - 杯赛积分排名（分组排名表）
     - 数据对比（近N场胜率/场均进球/场均角球/场均黄牌）
     - 阵容情况（球员/缺阵原因）
     - 球员上一场出场评分（号码/位置/首发/评分）
     - 对赛往绩（H2H完整记录含盘口水位）
     - 近期战绩（每场明细含对手/比分/半场/角球/盘口）

### 方式2：curl分析页（部分数据）

```bash
curl -s "https://info.titan007.com/analysis/{schedule_id}cn.htm" \
  -H 'User-Agent: Mozilla/5.0'
```

注: 需先获取赛程对应schedule_id，需浏览器从live.titan007.com页面上提取链接。

## 数据提取模板（JavaScript）

```javascript
var text = document.body.innerText;
var rankSection = text.match(/杯赛积分排名[\s\S]{1,400}/)?.[0] || '';
var dataSection = text.match(/数据对比[\s\S]{1,600}/)?.[0] || '';
var lineupSection = text.match(/阵容情况[\s\S]{1,500}/)?.[0] || '';
var ratingSection = text.match(/球员上一场出场评分[\s\S]{1,2000}/)?.[0] || '';
var h2hSection = text.match(/对赛往绩[\s\S]{1,800}/)?.[0] || '';
var recentSection = text.match(/近期战绩[\s\S]{1,2000}/)?.[0] || '';
```

## 限制

- 需要浏览器（curl对分析页面返回404）
- 赛程ID（schedule_id）需每次从live.titan007.com页面解析，非固定值
- 编码为GB2312（浏览器自动处理，curl需手动转码）
- 分析页数据量大（~30-50KB），需按段提取避免超限
