# 59itou 基本面数据提取方法

> 通过59itou.com 战绩Tab提取近10场状态、综合实力、H2H等基本面数据
> 适用: 世界杯/联赛/杯赛的赛前预测增强

## URL结构

```
https://kt.59itou.com/{station}/match3/?current_tab=history&matchid={match_id2}&lotteryId=90
```

- `{station}` = 可用379（已验证通过）
- `{match_id2}` = 从59itou API `apic.jindianle.com/api/match/selectlist` 获取
- `{tab}` = history（战绩Tab，含近10场+H2H+综合实力）

## 获取match_id2

```bash
curl -s 'https://apic.jindianle.com/api/match/selectlist?platform=koudai_mobile&_prt=https&ver=20180101000000&hide_more=1&single_support=2' \
  -H 'User-Agent: Mozilla/5.0' -H 'Referer: https://kt.59itou.com/'
# → 解析 d.data 字段, 每场含 match_id2, host_name_s, guest_name_s, league_name
```

## 数据提取（从page innerText）

用 `browser_navigate` 进入详情页后，用 `browser_console(expression='document.body.innerText')` 获取全文本。

### 关键正则提取

```python
import re

def parse_form(text):
    d = {}
    # 主队近10场: "主队近10场 6 胜 1 平 3 负"
    m = re.search(r'主队近10场\s*(\d+)\s*胜\s*(\d+)\s*平\s*(\d+)\s*负', text)
    if m: d['hW'],d['hD'],d['hL'] = int(m[1]),int(m[2]),int(m[3])
    
    # 客队近10场
    m = re.search(r'客队近10场\s*(\d+)\s*胜\s*(\d+)\s*平\s*(\d+)\s*负', text)
    if m: d['aW'],d['aD'],d['aL'] = int(m[1]),int(m[2]),int(m[3])
    
    # 主队主场: "主场 5 胜 1 平 3 负"
    m = re.search(r'主场\s*(\d+)\s*胜\s*(\d+)\s*平\s*(\d+)\s*负', text)
    if m: d['hhW'],d['hhD'],d['hhL'] = int(m[1]),int(m[2]),int(m[3])
    
    # 客队客场
    m = re.search(r'客场\s*(\d+)\s*胜\s*(\d+)\s*平\s*(\d+)\s*负', text)
    if m: d['aaW'],d['aaD'],d['aaL'] = int(m[1]),int(m[2]),int(m[3])
    
    # 综合实力: "主队\n60\n40\n客队"
    m = re.search(r'主队\n\s*(\d+)\s*\n\s*(\d+)\s*\n\s*客队', text)
    if m: d['hSt'],d['aSt'] = int(m[1]),int(m[2])
    
    # H2H: "主队近3场 2 胜 0 平 1 负"
    m = re.search(r'主队近\d+场\s*(\d+)\s*胜\s*(\d+)\s*平\s*(\d+)\s*负', text)
    if m: d['h2hW'],d['h2hD'],d['h2hL'] = int(m[1]),int(m[2]),int(m[3])
    
    return d
```

## 基本面增强规则

当基本面信号与赔率信号背离时:

```python
str_diff = f['hSt'] - f['aSt']  # 综合实力差
form_adv = f['hW'] - f['hL'] - (f['aW'] - f['aL'])  # 近10场净胜差

if str_diff > 15 and v8预测防平:
    # 实力碾压 → 走强队胜方向
    v8预测应修正为3-0/4-0或2-0/3-0
    
if str_diff < -15 and v8预测主胜:
    # 实力客强 → 走客队不败方向
    v8预测应修正为1-1/0-1或0-2/1-2
    
if abs(str_diff) <= 5 and form_adv > 3:
    # 实力接近但状态差距大 → 状态优先
    v8预测向状态好的方向倾斜
```

## 完整提取示例（美国vs澳大利亚）

```
主队近10场 6 胜 1 平 3 负 → hW=6, hD=1, hL=3
客队近10场 5 胜 1 平 4 负 → aW=5, aD=1, aL=4
综合实力 主队60 客队40   → hSt=60, aSt=40
H2H: 主队近3场 2胜0平1负 → h2hW=2, h2hD=0, h2hL=1
```

## 注意事项

- 已完赛比赛的59itou页面在完赛后一段时间可能下架（不再出现在API列表中）
- 赛前预测时，基本面数据包含该队近期已赛的世界杯比赛（已反映真实状态），是有效信号
- 综合实力分(0-100)由59itou根据近期战绩、进失球、身价等数据综合计算
