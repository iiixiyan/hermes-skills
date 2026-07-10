# 北单预测数据采集实战工作流

本文档整合 bjdc-prediction 分析体系与 59itou 数据采集（Playwright方式），提供从页面导航到最终预测的完整操作流程。

---

## 一、流程总览

```
北单列表(获取matchID+让球赔率) → 详情页导航(欧指+亚指+阵容/伤停) → 信号匹配 → 预测输出
```

### ⚠️ 域名状态（2026-07-07确认）

| 域名 | 状态 | 说明 |
|:----|:----|:-----|
| `www.59itou.com` | **❌ 已死亡** | 跳转"口袋资讯"新闻站，所有路径(beidan/jingcai/zucai等)返回404 |
| `kt.59itou.com` | **✅ 正常使用** | 带station前缀(883/202/378等)的子域名，北单/竞足列表页和详情页均可用 |

**操作建议**：始终使用 `kt.59itou.com` 作基域名，勿用 www。Playwright脚本中 page.goto() 不受证书影响。

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

## 五、Hermes浏览器环境下的采集限制与应对（2026-05-30验证）

### 已知问题

Hermes内置浏览器在采集59itou北单详情页时存在SPA tab切换问题：

| 问题 | 表现 | 原因 |
|:----|:----|:-----|
| 欧指Tab点击无效 | `browser_click(ref=@e5)` 点击欧指Tab后，页面保持"战绩"内容不变，或导航回列表页 | Vue SPA的tab切换通过框架路由处理，Hermes的click事件可能未正确触发Vue事件 |
| 亚指Tab同 | `browser_click(ref=@e6)` 同上 | 同上 |
| `page.evaluate`式click无效 | 通过`document.querySelectorAll(".van-tab")`找欧指并.click()，tab不切换 | 浏览器安全限制，Vue未捕获到dispatchEvent |
| API直接调用CORS | 通过`XMLHttpRequest`调用`stat-api.51aitou.com`等API被CORS拦截 | 跨域限制 |

### 应对策略

**可靠的采集方案（已验证）：**

0. **✅ URL参数切Tab（Hermes环境首选 — 2026-06-17验证）**
   - 在 `browser_navigate` 的URL中直接指定 `current_tab` 参数，完全绕过Vue SPA点击事件
   - `https://kt.59itou.com/202/match3/?current_tab=odds&matchid={id}&lotteryId=45` → 欧指Tab
   - `https://kt.59itou.com/202/match3/?current_tab=handicap&matchid={id}&lotteryId=45` → 亚指Tab
   - **无需点击、无需等待Vue渲染**，页面加载即显示目标Tab内容
   - ⚠️ 注意：`current_tab` 参数名使用下划线而非连字符，值为小写英文（`odds`/`handicap`/`lineup`/`history`/`info`/`rank`）
   - Hermes内置浏览器中此方式100%可靠（已验证瑞典甲/冰岛超/巴西乙北单详情页）

1. **战绩Tab（Always可靠）**
   - `browser_navigate(url)` → 详情页自动显示战绩Tab
   - `browser_snapshot()` 或 `browser_console` 获取innerText
   - 可获取：近10场战绩、主客战绩、等级战绩、H2H、近期赛程、综合实力

2. **初盘数据**
   - 从北单列表页获取（DIV.id=matchID + 胜/平/负三赔）
   - 获取方式：`browser_console` 执行 `document.body.innerText` 并从列表页HTML提取

3. **尝试不保证的方案（欧指/亚指Tab）**
   ```python
   # 先导航到详情页
   browser_navigate(url)
   # 尝试点击欧指Tab（可能失败）
   browser_click(ref=@e5)  # ref来自snapshot的欧指tab
   # 如果snapshot仍显示战绩内容，说明切换失败
   # 回退：仅用战绩数据 + 列表初盘做分析
   ```

4. **回退模式**
   - 当欧指/亚指Tab不可用时，分析只能基于：
     - 列表页初盘（三赔中最低=市场方向）
     - 战绩Tab（近10场、H2H、综合实力）
     - 排名差
   - **信号完整性受限**：无法判断4b一致升赔、12一致降赔等关键信号
   - **信心评级下调**：缺少欧指信号 → 降一星信心

### 与Playwright脚本对比

| 维度 | Playwright独立脚本 | Hermes内置浏览器 |
|:----|:-----------------|:----------------|
| Tab切换 | ✅ `page.evaluate('.van-tab')` 可靠 | ❌ 不可靠，Vue事件不触发 |
| 网络拦截 | ✅ 可拦截API响应 | ❌ 不可用 |
| 执行速度 | ~5-8秒/场 | ~10-15秒/场（含导航） |
| 内存消耗 | ~200MB/实例 | ~500MB+（Hermes自身） |
| 最佳实践 | 批量采集用Playwright脚本 | 单场快速查阅用Hermes浏览器 |

### 后续可能方案

- 通过 `browser_navigate` 直接访问API URL（需找到正确的鉴权参数）
- 从JS bundle中提取API签名算法
- 使用 `networkidle` 等待策略确保页面完全渲染后再点击Tab

## 六、北单列表页 SPA 门控绕过（2026-06-30实战验证）

### 现象

访问 `https://kt.59itou.com/883/danchang/`（或任意station前缀）时，`browser_navigate` 截图和 `browser_snapshot` 只显示 **"欢迎到店"** 登录门控页面，无比赛数据。

### 绕过方法

尽管snapshot受限，底层SPA框架已渲染了完整比赛列表。直接通过 `browser_console` 提取 innerText 即可获取全部数据：

```javascript
// 在 Hermes 浏览器中，页面显示"欢迎到店"时执行
browser_console({expression: 'document.body.innerText'})
```

返回内容示例（完整北单列表页数据）：
```
北京单场
胜平负   总进球   半全场   比分   上下单双

6月30日 周二  共5场比赛
1  芬兰杯  22:55  [5]芬超 瓦萨 VS 国际图尔库  [2]芬超  0
  胜 3.75  平 3.23  负 2.35
2  世界杯  00:55  [33]FIFA 科特迪瓦 VS 挪威  [31]FIFA  0
  胜 5.00  平 3.61  负 1.91
...
```

### 注意事项

1. **仅列表页有此效果**：详情页（欧指/亚指/战绩Tab）的SPA路由切换仍受限制（见§五 Hermes浏览器环境下的采集限制）
2. **日期懒加载**：超过当前视图的日期（如北单列表中第三天及以后的比赛）可能因懒加载未被渲染，需先滚动到日期标题触发加载
3. **innerText与截图差异**：`browser_snapshot` 仅显示accessibility tree暴露的元素，"欢迎到店"是Vue未挂载前的占位内容。实际数据在Vue挂载后渲染但未被AT抓到
4. **station前缀无关**：无论station=378/883/223/37/175/379/456，统一指向同一北单数据

### 数据解析规则

从innerText提取各字段：

| 字段 | 提取模式 | 示例 |
|:----|:---------|:----|
| 编号 | 日期标题后的第一行数字 | `1` |
| 联赛 | 编号行后的文字 | `芬兰杯` / `世界杯` / `巴西乙` |
| 时间 | 联赛名后的数字时间 | `22:55` |
| 排名 | `[...]` 包围的数字 | `[5]` = FIFA或联赛排名 |
| 主队 | 排名后的队名，到 `VS` 前止 | `瓦萨` |
| 客队 | `VS` 后的队名，到 `[` 排名前止 | `国际图尔库` |
| 让球 | 最后一行数字（负数为让球方） | `0` / `-2` / `-1` |
| SP三赔 | `胜`/`平`/`负` 后的数字 | 胜3.75 平3.23 负2.35 |

⚠️ 北单 SP 为**让球胜平负赔率**（非标准欧指）：
- `胜` = 让球方胜（主队让X球后赢 = 让胜）
- `平` = 走水（让球方赢X球 = 让平）
- `负` = 受让方不败（让球方未穿盘 = 让负）

---

## 六、效率优化提示

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

1. **赛后亚指Tab不可用**：取参数错误或空数据，只采欧指Tab
2. **北单详情页前缀回退**：默认 /202/，不行则试 /62/、/37/、/175/、/378/、/379/、/456/
3. **欧指数据提取**：仅需指数变化段（上升/降低家数），百家平均可选
4. **32场 ≈ 3.3分钟**（每场~6秒），一次性ExecuteCode可完成
5. **按联赛分组**：从prize page的league名直接获取

## 七、批量详情页采集：完整Python Playwright脚本模板（2026-07-07实战验证）

### 适用场景
一次采集10-40场北单详情页的全部数据（欧指+亚指+阵容），输出结构化JSON供后续分析。

### 核心技术
- **`current_tab=odds/handicap/lineup`** URL参数绕过Vue SPA tab切换（Hermes环境仍推荐逐个browser_navigate）
- 正则表达式提取：百家平均、指数变化(升/降家数)、亚盘(升降盘数/高水低水/赢盘率)、阵容/伤停数据
- **单场约5-8秒**，10场约1分钟

### 完整脚本模板

```python
import asyncio, json, re
from playwright.async_api import async_playwright

async def collect_matches(matches: list):
    """
    matches: [{"n":1, "id":"2724089", ...}, ...]
    返回每场的 dict: {
        n, id,
        bj_initial: [胜, 平, 负], bj_current: [胜, 平, 负],
        up: {胜, 平, 负}, down: {胜, 平, 负},
        pay_ctrl: {胜, 平, 负},
        up_pan, down_pan, high_water, low_water,
        win_rate: {主, 客},
        lineup_text: 原始阵容数据(含伤停)
    }
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path="/usr/bin/chromium-browser")
        page = await browser.new_page()
        results = []
        
        for m in matches:
            mid = m["id"]
            r = {"n": m["n"], "id": mid}
            
            # === 欧指 Tab (current_tab=odds) ===
            await page.goto(
                f"https://kt.59itou.com/202/match3/?current_tab=odds&matchid={mid}&lotteryId=45",
                wait_until="networkidle", timeout=20000
            )
            await asyncio.sleep(1)
            text = await page.evaluate("document.body.innerText")
            
            # 百家平均初赔→即赔
            bj_m = re.search(
                r'百家平均\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', text
            )
            if bj_m:
                r["bj_initial"] = [float(bj_m.group(1)), float(bj_m.group(2)), float(bj_m.group(3))]
                r["bj_current"] = [float(bj_m.group(4)), float(bj_m.group(5)), float(bj_m.group(6))]
            
            # 指数变化(升/降家数)
            idx = text.find('指数变化')
            if idx >= 0:
                nums = re.findall(r'(\d+)\s*家', text[idx:idx+300])
                if len(nums) >= 6:
                    r["up"] = {"胜": int(nums[0]), "平": int(nums[1]), "负": int(nums[2])}
                    r["down"] = {"胜": int(nums[3]), "平": int(nums[4]), "负": int(nums[5])}
            
            # 赔付控制
            pc_m = re.search(
                r'赔付控制.*?(\d+)\s*家\s*\n.*?胜.*?\n.*?(\d+)\s*家\s*\n.*?平.*?\n.*?(\d+)\s*家\s*\n.*?负',
                text, re.DOTALL
            )
            if pc_m:
                r["pay_ctrl"] = {"胜": int(pc_m.group(1)), "平": int(pc_m.group(2)), "负": int(pc_m.group(3))}
            
            # === 亚指 Tab (current_tab=handicap) ===
            await page.goto(
                f"https://kt.59itou.com/202/match3/?current_tab=handicap&matchid={mid}&lotteryId=45",
                wait_until="networkidle", timeout=20000
            )
            await asyncio.sleep(1)
            text2 = await page.evaluate("document.body.innerText")
            
            # 盘位水位升降(前4个数字：升盘/降盘/高水/低水)
            idx2 = text2.find('盘位水位升降')
            if idx2 >= 0:
                nums2 = re.findall(r'(\d+)\s*家', text2[idx2:idx2+200])
                if len(nums2) >= 4:
                    r["up_pan"] = int(nums2[0])
                    r["down_pan"] = int(nums2[1])
                    r["high_water"] = int(nums2[2])
                    r["low_water"] = int(nums2[3])
            
            # 赢盘率(主/客)
            win_m = re.search(r'(\d+)%.*主队.*\n.*?(\d+)%.*客队', text2, re.DOTALL)
            if win_m:
                r["win_rate"] = {"主": int(win_m.group(1)), "客": int(win_m.group(2))}
            
            # === 阵容 Tab (current_tab=lineup) 获取伤停数据 ===
            await page.goto(
                f"https://kt.59itou.com/202/match3/?current_tab=lineup&matchid={mid}&lotteryId=45",
                wait_until="networkidle", timeout=20000
            )
            await asyncio.sleep(1)
            text3 = await page.evaluate("document.body.innerText")
            
            # 提取伤停段落 - 位于"预计伤停以及影响"之后
            r["lineup_available"] = len(text3) > 500
            injury_idx = text3.find('预计伤停以及影响')
            if injury_idx >= 0:
                r["injury_section"] = text3[injury_idx:injury_idx+1000]
            elif r["lineup_available"]:
                # 至少获取阵容数据用于身价/阵型对比
                r["lineup_snippet"] = text3[:800]
            
            results.append(r)
            print(f"✅ #{m['n']} (id={mid}) OK")
        
        await browser.close()
        return results

# 使用示例
if __name__ == "__main__":
    MATCHES = [
        {"n":1, "id":"2724089"}, {"n":2, "id":"2719627"},
        {"n":3, "id":"2724072"}, {"n":4, "id":"2645553"},
        {"n":5, "id":"2719630"}, {"n":6, "id":"2645589"},
        {"n":7, "id":"2719681"}, {"n":8, "id":"2719747"},
        {"n":9, "id":"2719688"}, {"n":10,"id":"2724070"},
    ]
    results = asyncio.run(collect_matches(MATCHES))
    print(json.dumps(results, ensure_ascii=False, indent=2))
```

### 输出JSON字段说明

| 字段 | 来源 | 用途 |
|:----|:-----|:-----|
| `bj_initial` | 欧指Tab-"百家平均"首行 | 初赔→即赔变化计算(主胜升降百分比) |
| `bj_current` | 欧指Tab-"百家平均"次行 | 即赔用于规则#26信号矛盾检测 |
| `up` / `down` | 欧指Tab-"指数变化" | 4b/4c/极端一致信号判定核心 |
| `pay_ctrl` | 欧指Tab-"赔付控制" | 辅助信号(控制方方向) |
| `up_pan` / `down_pan` | 亚指Tab-"盘位水位升降" | 强升盘(≥8)/强降盘(≥8)检测 |
| `high_water` / `low_water` | 亚指Tab-"盘位水位升降" | 极端高水(≥15)/极端低水(≥15)检测 |
| `win_rate` | 亚指Tab-"亚盘赢盘率" | 基本面辅助(主客赢盘能力) |
| `injury_section` | 阵容Tab-"预计伤停以及影响" | 伤停姓名+身价+缺阵/出场胜率比较 |

### 解析注意事项

1. **百家平均提取**：正则依赖 `\s+` 分隔，文本中百家平均行格式固定为 `百家平均 \n X.XX \n X.XX \n X.XX \n X.XX \n X.XX \n X.XX`
2. **指数变化**：前3个数字= 胜/平/负的上升家数，后3个=降低家数。顺序固定
3. **阵容Tab空数据**：当阵容数据不可用时(`lineup_available=False`)，伤停信号完全依赖列表页等级信息
4. **伤停数据结构**：`球员名 \n 身价€X万 \n 待定 \n 缺阵：X胜X平X负 \n 出场：X胜X平X负`
北单开奖页的批次码只显示到某个日期，更新批次返回404，意味着目标奖期尚未发布。

#### 原因
北单奖期通常在比赛全部结束后2-4小时才发布到prize page。早场和中场的奖期发布速度较快，而深夜/凌晨场因比赛结束时间晚，奖期可能延迟到次日上午甚至中午才发布。

#### 处理流程
在Hermes内置浏览器中：
1. 查当前最新批次：`document.querySelector('.prizenav .active span')?.innerText`
2. 尝试递增批次码直到404：逐一访问 `prize/{n+1}`，`prize/{n+2}` 等
3. 查批次导航DOM：`Array.from(document.querySelectorAll('.prizenav p')).map(p => p.innerText.trim())`
4. 若目标奖期不存在 → 输出「奖期未发布，完整复盘待更新」，先呈现预测回顾而非虚构赛果

#### Hermes浏览器SPA交互模式（prize page专用）
Prize page的批次导航是Vue SPA组件，不能用browser_click，必须用JS触发点击：
- 切换到第N个批次：`document.querySelectorAll('.prizenav p')[N]?.click()`
- 确认激活的批次：`document.querySelector('.prizenav .active span')?.innerText`
- 触发懒加载（奖期中有大量比赛时需滚动到底部）：`window.scrollTo(0, document.body.scrollHeight)`
- 等待2-3秒后提取数据

#### 可尝试的替代方案
1. 使用cron输出目录中的历史输出
2. 切换到Playwright独立脚本（不受Hermes浏览器限制）
3. 等待2-4小时后重试（特别是深夜/凌晨场的复判）
