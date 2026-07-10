# 北单每日复盘 Cron 流水线

> 适用于 cron job 每日赛后复盘。完整链路：okooko(主) → 59itou(备) → 预测数据三级链 → 数据对比 → 输出报告 → Skill反向优化。

---

## 一、流程总览

```
Prize Page (获取matchID+比分+让球+北单结果)
  → 多批次扫描（同一日期的比赛可能分布在多个batch code中）
  → 详情页欧指Tab采集（指数变化信号）
  → 联赛分组（意甲/巴西甲/挪超/西乙等）
  → 信号准确率统计（按联赛+总体）
  → 输出复盘报告
  → Skill patch（更新信号追踪表+联赛模板+更新日志）
```

---

## 二、数据采集（双数据源链）

### 2.1 okooko（主数据源）— 2026-07-05新增

**URL**: `https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=WDL&LotteryNo={batch}`
**方式**: curl + GBK转UTF-8
**脚本**: `~/.hermes/scripts/bjdc_prize_fetch.py` (已挂载到cron job)

**使用方式**: `python3 ~/.hermes/scripts/bjdc_prize_fetch.py 26073`
- 输出67场完整数据（含match编号/主客队/让球/比分/北单结果/开奖状态）
- 已开奖 vs 待开奖自动区分
- JSON格式可供cron job解析

**采集优势**:
- 无需浏览器（curl即可）
- 速度快（~3秒）
- 不触发59itou反爬
- 单页返回所有batch数据

### 2.2 59itou prize page（备选）

okooko无数据时回退到59itou：用浏览器打开59itou北单开奖页遍历所有可用批次。

---

## 三、预测数据获取（三级链）

### 3.1 预测文件（首选）
`~/.hermes/cron/output/1fc1d31b6726/` 目录下昨日预测输出

### 3.2 session_search（备选）
当预测文件被周度清扫删除后，使用 `session_search(query="日期 北单 晚场 预测 双选 单选")` 从历史会话恢复。

### 3.3 预测目录（兜底）
检查 `~/.hermes/predictions/beidan/` 目录（通常已被清理，仅做兜底）。

### ⏰ 问题0：同批次结果分批发布（trickle-in）—— 2026-07-04发现

**现象**：同一个batch code内的比赛结果**不是一次性全部发布的**。比赛结束后结果分批上线，早场（22:00-00:00）比赛结果出现早，晚场（03:00-06:00）比赛结果出现晚。

**实例**：2026-07-04 batch 126072 在 09:02 时仅显示18场比赛，约09:30后第19场(哥伦比亚vs加纳)才发布。41场预测中尚有22场在09:30仍未开奖。

**时间窗口规律**：
| 比赛时段 | 大致开奖时间 | 说明 |
|:--------|:------------|:-----|
| 22:00-00:00（早场） | 赛后2-4小时 | 约02:00-04:00可查 |
| 00:00-03:00（中场） | 赛后2-4小时 | 约04:00-07:00可查 |
| 03:00-06:00（后场） | 赛后2-4小时 | 约06:00-10:00可查 |
| **所有时段全部出齐** | **约10:00-11:00** | **建议复盘cron安排在11:00-12:00** |

**cron排期建议**：若复盘cron安排在09:00，部分后场(03:00-06:00)比赛可能尚未开奖。建议：
- **首选**：安排复盘cron在 **11:00-12:00**（所有时段结果约在10:00-11:00全部发布）
- **次选**：09:00先行生成初版报告，然后11:00再做增量刷新（扫描新出现场次，追加到报告）
- 若安排09:00，必须在报告中标注「部分后场比赛可能尚未开奖，报告为初版」

**检测方法**：每次采集prize page后，检查 `document.body.innerText` 中已开奖场次数量。对比预测文件总场次，如差异>5场，标注「尚有N场未开奖」。

### 问题1：同一日期的比赛分布在多个批次中

**核心模式：同一天比赛的match编号不连续，分布在不同批次中。**

例如2026-06-02（周二）的15场比赛分布在3个批次：
| Batch | 周二比赛编号 | 数量 |
|:-----|:-----------|:----:|
| **126062**（最新）| 周二1 | 1场 |
| **126061** | 周二130~132 | 3场 |
| **126057** | 周二195~205 | 11场 |

match编号（1→130→195）不连续，说明batch代码的切分点与match序号无关。**不能假定同一日期的比赛出现在连续编号范围内**，必须遍历所有可用批次。

2026-06-01（周一）61场比赛分布在两个不同的prize batch中：

| Batch | 覆盖比赛 | 说明 |
|:-----|:--------|:-----|
| **126061** | 周一129~周一107（22场）| 默认最新批次的周一比赛 |
| **126057** | 周一194~周一156（39场）| 需切换批次发现的周一比赛 |

**扫描规则**：
1. 始终从默认批次开始（默认显示最新批次）
2. 遍历所有可用批次（从batch list的`<p>`元素提取）
3. 在每个批次中查找目标日期的比赛（`周一N` / `周二N` 等前缀）
4. 合并所有批次中的目标日期比赛
5. 删除重复matchID

### 批次切换代码

```python
batches = ['126061', '126058', '126057', '126056']  # 动态发现
for batch in batches:
    # 点击批次切换
    click_js = """
    (function() {
        var ps = document.querySelectorAll('p');
        for(var i=0; i<ps.length; i++){
            if(ps[i].textContent.trim() === 'BATCH'){
                ps[i].click();
                return 'clicked';
            }
        }
        return 'not found';
    })()
    """.replace('BATCH', batch)
    await page.evaluate(click_js)
    await asyncio.sleep(2)
    
    # 提取 matchID + 比分 + 联赛
    match_data = await page.evaluate("""
    (function() {
        var all = document.querySelectorAll('a');
        var result = {};
        for(var i=0; i<all.length; i++){
            if(all[i].textContent.trim() === '析'){
                var parentDiv = all[i].parentElement;
                var grandparent = parentDiv ? parentDiv.parentElement : null;
                var matchId = grandparent ? grandparent.id : '';
                
                var spans = parentDiv ? parentDiv.querySelectorAll('span') : [];
                var matchNum = '';
                for(var j=0; j<spans.length; j++){
                    if(spans[j].textContent.match(/周[一二三四五六日]\\d+/)){
                        matchNum = spans[j].textContent.trim(); break;
                    }
                }
                
                var pTags = parentDiv ? parentDiv.querySelectorAll('p') : [];
                var league = '', home = '', away = '';
                var b = parentDiv ? parentDiv.querySelector('b') : null;
                var score = b ? b.textContent.trim() : '';
                
                for(var j=0; j<pTags.length; j++){
                    var cls = pTags[j].className || '';
                    if(cls.includes('liansai')) league = pTags[j].textContent.trim();
                    else if(cls.includes('textr')) home = pTags[j].textContent.trim();
                    else if(cls.includes('textl')) away = pTags[j].textContent.trim();
                }
                
                if(matchId && matchNum.includes('周一')) {
                    result[matchNum] = {id: matchId, league: league, 
                      home: home, score: score, away: away};
                }
            }
        }
        return result;
    })()
    """)
```

### ⚠️ 让球数+北单结果提取

让球数和北单结果在innerText中，需要逐行解析：

```python
# 从innerText中查找 handicap results
text = await page.evaluate("document.body.innerText")
lines = text.split('\n')
for line in lines:
    # 模式1: (-1)胜, (+2)平, (-2)负 → 非零让球
    hm = re.match(r'\(([+-]?\d+)\)(胜|平|负)', line)
    if hm:
        handicap = hm.group(1)
        bjdc_result = hm.group(2)
        continue
    # 模式2: 单独的 胜/平/负 → 让球为0
    hm2 = re.match(r'^(胜|平|负)$', line)
    if hm2:
        handicap = '0'
        bjdc_result = hm2.group(1)
```

---

## 四、详情页欧指批量采集

赛后复盘只需采集欧指Tab（亚指Tab赛后不可用；战绩Tab可选但非必须）。

### 北单详情页前缀

```python
bjdc_prefixes = ["202", "37", "175", "378", "379", "456"]
for prefix in bjdc_prefixes:
    url = f"https://kt.59itou.com/{prefix}/match3/?matchid={mid}&lotteryId=45&lottery_style=dc"
    try:
        await page.goto(url, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(1)
        content = await page.evaluate("document.body.innerText")
        if len(content) > 500:
            break  # 有效加载
    except:
        continue
```

### 欧指信号提取

```python
# 提取指数变化段
idx_start = odds_text.find('指数变化')
signals = {}
if idx_start > -1:
    section = odds_text[idx_start:idx_start+300]
    nums = re.findall(r'(\d+)家', section)
    if len(nums) >= 6:
        signals['up_win'] = int(nums[0])    # 胜升
        signals['up_draw'] = int(nums[1])   # 平升
        signals['up_lose'] = int(nums[2])   # 负升
        signals['down_win'] = int(nums[3])  # 胜降
        signals['down_draw'] = int(nums[4]) # 平降
        signals['down_lose'] = int(nums[5]) # 负降

# 提取百家平均初赔vs即赔
bi = odds_text.find('百家平均')
baijia = {}
if bi > -1:
    odds_nums = re.findall(r'\d+\.\d+', odds_text[bi:bi+400])
    if len(odds_nums) >= 6:
        baijia['init'] = odds_nums[:3]      # [胜初, 平初, 负初]
        baijia['current'] = odds_nums[3:6]  # [胜即, 平即, 负即]

# 提取综合实力（默认Tab已有）
si = default_text.find('综合实力')
if si > -1:
    nums = re.findall(r'(\d+)', default_text[si:si+200])
    if len(nums) >= 2:
        strength = (int(nums[0]), int(nums[1]))
```

### 性能参考

| 场次量 | 耗时（单次ExecuteCode） | 说明 |
|:-----:|:---------------------:|:-----|
| 22场 | ~75秒 | 北单前缀202 + 欧指Tab切换 |
| 39场 | ~130秒 | 含批次切换 |
| 61场 | ~204秒 | 全部比赛，含多批次 |
| ≈3.3秒/场 | — | 每场含导航+Tab切换+信号提取 |

---

## 五、预测准确率统计（复盘第0步）

### ⚠️ 核心铁律：双选+单选分离统计

复盘的第一件事不是采集数据，而是**先算昨天的预测命中率**。**双选和单选必须分开统计、分开优化。**

### 数据来源

1. **首选**：`~/.hermes/cron/output/1fc1d31b6726/` 目录下昨日日期的预测输出文件
   - 文件命名：`YYYY-MM-DD_HH-MM-SS.md`
   - 提取所有 `📌 双选：[方向A] / [方向B]    单选：[方向C]` 行及对应的场次号/联赛/信心
2. **备选**：`session_search` 搜索昨日北单预测cron的session
3. **兜底**：若两处均不可获取 → 标注「预测数据暂不可获取，仅输出赛果统计」

### 字段解析规则（新格式 v5.8.0+）

从预测输出中提取以下结构化信息：

| 字段 | 提取规则 | 示例 |
|:----|:---------|:-----|
| 场次号 | `### #[编号]` | #1 |
| 联赛 | 同上行中提取 | 芬甲 |
| 双选方向 | `📌 双选：[方向A] / [方向B]` | 让胜/让平 |
| 单选方向 | `📌 ... 单选：[方向C]` | 让胜(偏重) |
| 信心 | `⭐ ★★★★☆ / ★★★☆☆`（双选/单选分别） | ★★★★☆/★★★☆☆ |
| 无单选标志 | 无单选时显示 `—` | — |

### 比对流程

```
预测输出文件 → 解析每场的双选+单选+信心+联赛
     ↓
prize page 实际赛果 → 提取每场的实际让胜/让平/让负
     ↓
按 matchID 或 主客队名+联赛 配对
     ↓
统计:
  ① 双选命中率（双选两个方向至少1个=实际结果）✅ 宽口径
  ② 单选命中率（单选方向=实际结果）✅ 严口径
  ③ 双选缺口（双选均≠实际结果）❌ → 需要优化
  ④ 单选偏差（单选方向≠实际结果）❌ → 需要优化
  ⑤ 按联赛/信心分别统计双选+单选
  ⑥ 偏差归因分析（双选缺口和单选偏差分开处理）
```

### 双选缺口 vs 单选偏差 → 不同优化方向

| 类型 | 含义 | 优化方向 |
|:----|:-----|:---------|
| 双选缺口 | 双选2个方向均未覆盖实际结果 | 双选策略问题：漏掉了某个盘型方向 |
| 单选偏差 | 单选方向≠实际结果 | 偏重判定问题：强度过度/方向错误 |

### 输出位置

预测准确率统计放在复盘报告的**最前面**（在总览和联赛分组之前）。

### 输出格式

详见 `daily-review-output-format.md`（双选+单选双优化版）。

---

## 四、联赛分组统计框架

### 信号判定函数

```python
def is_4b(m):
    """一致升主胜：≥20家升且≤3家降"""
    return m['up_win'] >= 20 and m['down_win'] <= 3

def is_reverse_4b(m):
    """一致降主胜：≤3家升且≥20家降"""
    return m['up_win'] <= 3 and m['down_win'] >= 20

def is_away_up(m):
    """一致升客胜：≥20家升且≤3家降"""
    return m['up_lose'] >= 20 and m['down_lose'] <= 3

def is_away_down(m):
    """一致降客胜：≤3家升且≥20家降"""
    return m['up_lose'] <= 3 and m['down_lose'] >= 20

def is_extreme_4b(m):
    """极端升主胜：≥25家升且≤1家降"""
    return m['up_win'] >= 25 and m['down_win'] <= 1
```

### 信号方向 vs 北单结果一致性

| 信号 | 预测方向 | 与结果一致 |
|:----|:--------|:----------|
| 一致升主胜(4b) | 走下盘(让负) | `result == '负'` |
| 一致降主胜 | 走上盘(让胜) | `result == '胜'` |
| 一致升客胜 | 主队方向(让胜/让平) | `result in ['胜','平']` |
| 一致降客胜 | 客队方向(让负) | `result == '负'` |
| 极端升主胜 | 走下盘(让负) | `result == '负'` |

### 联赛特异性分析模板

```python
league_order = ["意甲","西甲","巴西甲","巴西乙","智利甲","美职",
                "挪超","挪甲","丹甲","K2联赛","芬甲","西乙","阿职联",
                "比甲","冰岛超","阿根廷杯","友谊赛","英乙"]

for league in league_order:
    league_matches = [m for m in all_matches if m['league'] == league]
    if not league_matches:
        continue
    
    # 上盘率
    shang = sum(1 for m in league_matches if m['result'] == '胜')
    xia = sum(1 for m in league_matches if m['result'] == '负')
    zoushui = sum(1 for m in league_matches if m['result'] == '平')
    
    # 各信号准确率
    for sig_name, sig_fn in signal_defs:
        triggered = [m for m in league_matches if sig_fn(m)]
        correct = ...  # 按方向匹配
        acc = len(correct) / len(triggered) * 100 if triggered else 0
```

---

## 五、Skill 反向优化工作流

复盘后对 bjdc-prediction 技能做三个修改：

### 5.1 追加信号追踪表

在 `5/31单日关键信号发现` 下面追加 `#/1（周一）N场复盘信号发现` 段落：

| 信号 | 触发 | 正确 | 准确率 | 评估 |
|:----|:----:|:----:|:-----:|:-----|
| 一致升主胜(4b) | X | Y | Y/X% | ⚠️/✅/⛔ |
| ... | ... | ... | ... | ... |

### 5.2 更新联赛特性警告

在 `联赛特性警告` 表格中新增/修改联赛行：

| 联赛 | 本日发现 | 规则 |
|:----|:---------|:-----|
| **挪甲** | 上盘率88%，一致降主胜3/3 | 升级优先联赛 |
| **巴西乙** | 一致升主胜3/3=100% | 升级优先信号 |
| **美职** | 一致升主胜0/2=0% | 反信号标注 |
| **丹甲** | 6/1恢复33% | 保持禁用 |

### 5.3 追加更新日志

```
| v5.0.N | YYYY-MM-DD | **MM/DD复盘（N场）**：①新增信号表 ②联赛模板更新 ③... |
```

### 5.4 （可选）更新反例与黑名单

如发现新的反模式，追加到 `🚫 反例与黑名单` 表。

---

## 六、输出报告模板

### 联赛分组输出

```
### 总览：
北单总场次：X场
上盘（让胜）：X场（Y%）
下盘（让负）：X场（Y%）
走水（让平）：X场（Y%）

### 各联赛表现：
| 联赛 | 场次 | 上盘 | 下盘 | 走水 | 上盘率 | 主要信号 |
|:----|:---:|:---:|:---:|:---:|:-----:|:---------|
| ... | ... | ... | ... | ... | ... | ... |

### 联赛内逐场明细（推荐格式）：

对每个联赛，输出包含 欧指信号+亚指数据+结果 的逐场明细表，便于定位具体失效场次：

```markdown
**联赛名**：N场，上盘X(Y%) | 下盘X(Y%) | 走水X(Y%)
| 场次 | 主队 | 比分 | 客队 | 让球 | 结果 | 欧指信号 | 亚指 |
|:----|:----|:----:|:----|:---:|:----:|:---------|:----:|
| 周五N | 主队 | X-X | 客队 | ±N | ⬇️/⬆️ | 4b升主胜N/N / 4c降主胜N/N | 升N/降N 高N/低N |
```

信号方向标注：
- `⬇️` = 下盘（让负）
- `⬆️` = 上盘（让胜/让平）
- `➖` = 走水

信号结果判定：
- ✅ = 信号指向与结果一致
- ❌ = 信号指向与结果相反
- ⛔ = 信号完全失效（多次触发均错误）

### 信号准确率（按联赛）：
| 信号 | 总触发 | 正确 | 准确率 | 高效联赛 | 低效联赛 |
|:----|:-----:|:----:|:-----:|:---------|:---------|
| ... | ... | ... | ... | ... | ... |
```

### 技能优化摘要

```
### 技能优化更新：
| 编号 | 修改内容 | 类型 |
|:---:|:---------|:----:|
| ✓ | §5.3 新增MM/DD信号数据表 — N场完整统计 | 新增段落 |
| ✓ | §3-D [联赛]模板更新 — [具体发现] | 联赛模板 |
| ✓ | 更新日志 — 新增vX.X.X | 日志更新 |
```
