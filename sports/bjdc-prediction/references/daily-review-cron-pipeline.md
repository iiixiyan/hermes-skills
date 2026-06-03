# 北单每日复盘 Cron 流水线

> 适用于 cron job 每日赛后复盘。完整链路：prize page → 多批次扫描 → 详情页信号采集 → 联赛分组统计 → 输出报告 → Skill反向优化。

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

## 二、Prize Page 多批次扫描（关键发现）

### 问题：同一日期的比赛分布在多个批次中

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

## 三、详情页欧指批量采集

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
                "挪超","挪甲","丹甲","K2联赛","西乙","阿职联",
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
