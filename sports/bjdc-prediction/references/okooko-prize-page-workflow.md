# 北单Prize Page数据采集 — okooko主链 + 59itou备链

> 2026-07-05新增。okooko为北单赛果采集**首选数据源**，59itou为备选。

---

## 数据源优先级

```
1️⃣ okooko（主） → curl解析HTML → 快速、稳定、无需browser
2️⃣ 59itou（备） → browser prize page → 当okooko无数据时回退
```

---

## 1️⃣ okooko赛果API（主数据源）

### URL格式
```
https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=WDL&LotteryNo={期号}
```

### 请求参数
| 参数 | 值 | 说明 |
|:----|:---|:-----|
| `LotteryType` | `WDL` | 让球胜平负 |
| `LotteryNo` | 26073 | 北单期号，递增尝试 |

### Headers
```
User-Agent: Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36
Referer: https://www.okooo.com/
```

### 编码处理
返回GBK编码 → 需 `iconv -f GBK -t UTF-8//IGNORE` 转换

### HTML结构解析

```
<tr>
  <td>编号</td>
  <td class="txtright">主队名<cite class="fontred2 font10">(让球数)</cite></td>
  <td width="10%" class="nobd">VS</td>
  <td class="txtleft">客队名</td>
  <td>比分<p>半场比分</p></td>
  <td><p><b class="fontred">主/客/平</b></p><span class="gray9">SP</span></td>
</tr>
```

### 字段映射

| HTML元素 | 含义 | 映射 |
|:---------|:-----|:-----|
| `<td>`编号 | 北单场次号 | #36-#67 |
| `<cite>`(±N) | 让球数 | -2=主队让2球, +1=客队让1球 |
| `fontred">主` | 北单结果 | 主→让胜, 客→让负, 平→让平 |
| `fontred">`为空 | 未开奖 | 待开奖 |
| `gray9">数字` | 北单SP | SP赔率 |

### 批次号递增规律
- 每日递增约1（如26072→26073→26074）
- 遍历26073~26082找到有数据的批次
- 2026-07-05实测：26073返回67场（45场已开奖+22场待开奖）

### 参考脚本
`~/.hermes/scripts/bjdc_prize_fetch.py` — 封装okooko数据获取+解析+JSON输出

---

## 2️⃣ 59itou prize page（备选数据源）

当okooko返回0场已开奖时，回退到59itou browser采集。

### 访问方式
```python
URL: https://kt.59itou.com/kaijiang/beijingsingle/{批次}
方法: browser_navigate → 遍历 `.prizenav p` 所有批次 → 提取比赛数据
```

### 提取方法
- 遍历所有 `.prizenav p` 元素切换批次
- 在innerText中匹配 `(-1)胜`, `(+2)平`, `(0)负` 等模式
- 提取比分、让球数、北单结果

---

## 3️⃣ 赛果与预测对比流程

### Step 1: 获取okooko数据
```python
python3 ~/.hermes/scripts/bjdc_prize_fetch.py 26073
```

### Step 2: 获取预测数据
- **首选**: 从 `~/.hermes/cron/output/1fc1d31b6726/` 读取昨日晚场预测输出
- **备选**: `session_search` 搜索预测session
- **兜底**: 预测数据不可获取时仅输出赛果统计

### Step 3: 逐场对比
对比预测(双选+单选) vs 实际赛果，标注：
- ✅✅ = 双选覆盖 + 单选正确
- ✅✗ = 双选覆盖 + 单选错误  
- ❌❌ = 双选未覆盖

### Step 4: 统计输出
- 双选命中率（双选至少1方向=实际）
- 单选命中率（单选方向=实际）
- 按联赛分组统计
- 偏差根因分析

---

## 4️⃣ 时间窗口规律

| 比赛时段 | 开奖时间 | 建议 |
|:--------|:---------|:-----|
| 22:00-00:00（早场） | 赛后2-4小时 | 约02:00-04:00可查 |
| 00:00-03:00（中场） | 赛后2-4小时 | 约04:00-07:00可查 |
| 03:00-06:00（后场） | 赛后2-4小时 | 约06:00-10:00可查 |
| **全部出齐** | **约10:00-11:00** | **复盘cron宜安排在11:00~13:00** |

---

## 5️⃣ 常见问题

### okooko返回200但无数据
- 该批次尚未有比赛完赛
- 等待2-4小时再查
- 可能批次号不对，继续尝试后续批次

### 队名显示乱码
- 编码未正确转换：`iconv -f GBK -t UTF-8//IGNORE`
- Python中：`response.decode('gbk', errors='replace')`

### 让球数始终显示(0)
- 如果解析时先调用了 `re.sub(r'<[^>]+>', '', home_raw)` 再提取让球数，会让球数丢失
- 正确顺序：**先在原始home_raw中提取让球数，再清理HTML标签**
