# 北单预测数据采集实战工作流

本文档整合 bjdc-prediction 分析体系与 59itou 数据采集（Playwright方式），提供从页面导航到最终预测的完整操作流程。

---

## 一、流程总览

```
北单列表(获取matchID+让球赔率) → 详情页导航(欧指+亚指) → 信号匹配 → 预测输出
```

## 二、核心原则

### 北单数据源 ≠ 竞足数据源

| 维度 | 北单 | 竞足 |
|:----|:----|:----|
| 列表路径 | `/883/danchang/` | `/627/jingcai/` |
| 详情页URL | `...&lotteryId=45&lottery_style=dc` | `...&lotteryId=90&lottery_style=jczq` |
| 列表页赔率含义 | **让球胜平负赔率**（胜=让球胜/平=走水/负=受让胜） | 标准胜平负赔率 |
| 主分析依据 | 列表页让球赔率（三赔中最低的=市场真实看好方向） | 标准欧指变化 |

### ⚠️ 常见错误（2026-05-20教训）

- ❌ 不要用竞足详情页（lotteryId=90）的数据分析北单
- ❌ 不要以标准欧指（百家平均）作为北单方向的主要判断依据
- ❌ 不要混淆"北单胜=让球方胜"和"标准胜=主队胜"
- ✅ **北单列表页的让球胜平负赔率才是分析基准**
- ✅ 欧指仅用于判断市场热度方向（一致升/降信号）
- ✅ **逐场采集、逐场分析**，每场分析完再处理下一场

### 典型案例：北单赔率 vs 标准欧指

| 场次 | 标准欧指 | 让球 | 北单让球赔率 | 解读 |
|:----|:---------|:----|:------------|:----|
| 弗拉门戈 | 1.32(主胜大热) | -1 | 3.57/2.96/2.61 | 让平(2.96)最低 |
| 帕梅拉斯 | 1.17(极稳) | -2 | 4.02/4.55/1.88 | 让负(1.88)最低 |
| 弗赖堡vs维拉 | 1.68(客胜) | +1 | 2.29/3.33/3.78 | 让胜(2.29)最低 |

## 三、逐场操作步骤

### 第1步：获取北单列表数据（matchID + 让球赔率）

使用 Playwright 从北单列表页获取所有比赛的DIV.id（matchID）和让球赔率：

```python
import asyncio, json
from playwright.async_api import async_playwright

async def get_bjdc_list():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path="/usr/bin/chromium-browser")
        page = await browser.new_page()
        await page.goto("https://kt.59itou.com/883/danchang/", wait_until="networkidle")
        await page.wait_for_function('() => document.body.innerText.includes("北京单场") && document.body.innerText.length > 2000', timeout=10000)
        
        # 获取matchID映射
        ids_json = await page.evaluate("""
        ()=>{
            var items = document.querySelectorAll('[class*="item"]');
            var r = {};
            items.forEach(function(item){
                var id = item.id || item.getAttribute('data-id');
                var text = (item.textContent||'').trim().replace(/\\s+/g, ' ');
                if(id) r[id] = text.substring(0, 180);
            });
            return JSON.stringify(r);
        }
        """)
        all_ids = json.loads(ids_json)
        
        # 获取列表页innerText解析让球赔率
        text = await page.evaluate("document.body.innerText")
        # 从text中解析：数字行(22-75)→联赛→时间→[排名]→联赛→主队→VS→客队→[排名]→联赛→让球数→胜→赔率→平→赔率→负→赔率
        await browser.close()
        return all_ids, text
```

**matchID 在 DIV.id 上**（如 `id="2598601"`），**不是** data-id。北单列表的`[class*="item"]`元素才有id。

### 第2步：导航到北单详情页

```
URL: https://kt.59itou.com/202/match3/?matchid={matchid}&lotteryId=45&lottery_style=dc
```

使用 Playwright 加载页面，条件等待内容渲染：
```python
await page.goto(url, wait_until="networkidle")
await page.wait_for_function('() => document.body.innerText.includes("近10场战绩") && document.body.innerText.length > 500', timeout=10000)
```

### 第3步：采集亚指数据

切换Tab到亚指（条件等待，非固定sleep）：

```python
await page.evaluate("""
() => {
    document.querySelectorAll(".van-tab").forEach(t => {
        if (t.textContent.includes("亚指")) t.click();
    });
}
""")
await asyncio.sleep(0.3)
await page.wait_for_function('() => document.body.innerText.includes("盘位水位升降")', timeout=5000)
text = await page.evaluate("document.body.innerText")
```

关注字段：
- **升降盘公司数**：升盘X家 / 降盘X家（核心信号）
- **主队水位公司数**：高水X家 / 低水X家
- **典型亚盘**表格：每家公司初盘盘口+水位 vs 即盘盘口+水位
- **盘口走势**：主队/客队连续盘路

### 第4步：采集欧指数据

切换Tab到欧指：

```python
await page.evaluate("""
() => {
    document.querySelectorAll(".van-tab").forEach(t => {
        if (t.textContent.includes("欧指")) t.click();
    });
}
""")
await asyncio.sleep(0.3)
await page.wait_for_function('() => document.body.innerText.includes("概率转换")', timeout=5000)
text = await page.evaluate("document.body.innerText")
```

关注字段：
- **百家平均初赔与即赔**（用于判断热度变化趋势）
- **指数变化**：胜/平/负 各上升X家 / 降低X家（核心信号！≥15家一致升=大热）
- **赔付控制**：X家控制胜/X家控制平/X家控制负
- **概率转换**：胜X%↑/↓ 平X%↑/↓ 负X%↑/↓

### 第5步：信号匹配（核心分析框架）

#### 步骤A：看北单让球赔率 → 确定市场基准方向

北单三赔中**最低的选项** = 市场真实看好方向。例如：
- 3.57/2.96/2.61 → 让平(2.96)最低 → 市场最看好让平
- 4.02/4.55/1.88 → 让负(1.88)最低 → 市场最看好让负
- 2.29/3.33/3.78 → 让胜(2.29)最低 → 市场最看好让胜

#### 步骤B：看欧指一致性 → 判断热度与风险

| 信号 | ≥15家阈值 | 含义 | 北单方向 |
|:----|:---------:|:----|:--------|
| 一致升主胜 | 升≥15家/降≤3家 | 主胜大热→市场不看衰主队 | 下盘方向 |
| 一致降主胜 | 降≥15家/升≤3家 | 主胜一致看好+升盘阻上 | 上盘方向 |
| 一致升客胜 | 升≥15家/降≤3家 | 客胜大热 | 主队不败方向 |
| 一致降客胜 | 降≥15家/升≤3家 | 客胜一致看好 | 客队方向 |

#### 步骤C：综合判定

- 北单最低赔方向 + 欧指一致看好 = **强信号**
- 北单最低赔方向 + 欧指一致看衰（大热）= **降低信心或反向**
- 北单三赔接近 + 欧指无明显一致 = **信号不明，建议放弃**

---

## 四、预测输出格式

每场必须按以下格式输出，**无比分预测**：

```
## 📊 第X场｜主队 VS 客队（联赛 时间）
**北单让球：±N｜联赛X vs 联赛X**

📊 数据摘要：综合实力X-Y...（3行内）

🔍 核心分析：
① 欧指变化：百家平均初→即...
② 亚指分析：盘口、升降盘、水位...
③ 信号匹配：[信号名称]触发...
④ 方向判定...

📌 北单推荐：让胜 / 让平 / 让负（或胜/平/负当北单0时）
⭐ 信心评级：★★★☆☆
```

---

## 五、效率优化提示

1. **Playwright单场速度**：约5-8秒/场（含导航+2次Tab切换+条件等待）
2. **一次性分析多场**：用 `batch_collect()` 一次浏览器会话采集多场，避免重复打开浏览器
3. **条件等待替代固定sleep**：使用 `page.wait_for_function()` + 特征词检测，速度快1-2倍
4. **matchID缓存**：一次获取全部matchID，避免为每场比赛重新加载北单列表页

---

## 六、赛后复盘数据采集（新增·适配§16复盘方法论）

### 适用场景
- 每日北单复盘（赛后统计信号准确率）
- 联赛基因分析（同一联赛多场数据汇总）
- 信号准确率追踪表更新

### 数据源切换
复盘时**不用北单列表页**（赛后已消失），改用**北单开奖结果页**：

```
https://kt.59itou.com/danchang/prize/
```

### 数据采集流程（已验证32场，2026-05-22）

```python
import asyncio, re, json
from playwright.async_api import async_playwright

async def collect_review_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path="/usr/bin/chromium-browser")
        page = await browser.new_page()
        
        # Step 1: 获取昨日北单比赛结果
        await page.goto("https://kt.59itou.com/danchang/prize/", wait_until="networkidle")
        await asyncio.sleep(3)
        
        matches = await page.evaluate('''
        (function(){
          var items = document.querySelectorAll('[class*="item"]');
          var result = [];
          items.forEach(function(item){
            var id = item.id;
            if(!id) return;
            result.push({id: id, text: item.innerText.replace(/\\s+/g,' ')});
          });
          return JSON.stringify(result);
        })()
        ''')
        
        # Step 2: 解析每场比赛（比分、让球数、北单结果）
        # 从文本中提取：league → date_code → home → score → away → 析 → hcap_option → ...
        # 让球选项如 "(-1)胜"、"(+1)负"、"胜"(=让0)
        
        parsed_matches = []
        for m in json.loads(matches):
            parts = m['text'].split()
            xi_idx = parts.index('析')
            league = parts[0]
            score = None
            for i in range(1, xi_idx):
                if re.match(r'\d+-\d+', parts[i]):
                    score = parts[i]
                    home_team = ' '.join(parts[2:i])
                    away_team = ' '.join(parts[i+1:xi_idx])
                    break
            
            if not score: continue
            
            # 解析让球
            option = parts[xi_idx + 1]
            hcap_match = re.match(r'\(([+-]?\d+)\)(\S+)', option)
            handicap = int(hcap_match.group(1)) if hcap_match else 0
            
            hg, ag = map(int, score.split('-'))
            diff = (hg + handicap) - ag
            beidan = '让胜' if diff > 0 else ('让平' if diff == 0 else '让负')
            
            parsed_matches.append({
                'id': m['id'], 'league': league,
                'home': home_team, 'away': away_team,
                'score': score, 'handicap': handicap,
                'beidan': beidan
            })
        
        # Step 3: 采集欧指数据（仅欧指Tab，赛后亚指Tab不可用）
        for pm in parsed_matches:
            url = f"https://kt.59itou.com/202/match3/?matchid={pm['id']}&lotteryId=45&lottery_style=dc"
            await page.goto(url, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(1.5)
            
            # 切换到欧指Tab
            await page.evaluate('''
            document.querySelectorAll(".van-tab").forEach(t => {
                if (t.textContent.includes("欧指")) t.click();
            })
            ''')
            try:
                await page.wait_for_function('() => document.body.innerText.includes("概率转换")', timeout=5000)
            except:
                await asyncio.sleep(2)
            
            ou_text = await page.evaluate("document.body.innerText")
            
            # 提取指数变化（核心信号数据）
            idx = ou_text.find('指数变化')
            if idx >= 0:
                section = ou_text[idx:idx+200]
                nums = re.findall(r'(\d+)家', section)
                if len(nums) >= 6:
                    pm['up_home'] = int(nums[0])
                    pm['down_home'] = int(nums[3])
                    pm['up_draw'] = int(nums[1])
                    pm['down_draw'] = int(nums[4])
                    pm['up_away'] = int(nums[2])
                    pm['down_away'] = int(nums[5])
        
        await browser.close()
        return parsed_matches
```

### 复盘数据采集要点

1. **赛后亚指Tab不可用**：取"参数错误"或空数据，只采欧指Tab
2. **北单详情页前缀回退**：默认 /202/，不行则试 /37/、/175/、/378/、/379/、/456/
3. **欧指数据提取**：仅需"指数变化"段（上升/降低家数），百家平均可选
4. **32场 ≈ 3.3分钟**（每场~6秒），一次性ExecuteCode可完成
5. **按联赛分组**：从prize page的`parts[0]`（联赛名）直接获取
