# Playwright全自动采集模式（v5.7.0）

> 2026-06-20 实战总结。所有L2/L3数据源通过Playwright全自动采集，无需人工干预。

---

## 一、浏览器初始化

```python
from playwright.sync_api import sync_playwright

# ✅ 正确：使用 .start()
_p = sync_playwright()
playwright_obj = _p.start()
browser = playwright_obj.chromium.launch(
    executable_path='/usr/bin/chromium-browser',  # 系统Chromium
    headless=True,
    args=['--no-sandbox', '--disable-setuid-sandbox']
)

# 清理
browser.close()
playwright_obj.stop()

# ❌ 错误：不要用 __enter__() / __exit__()
# playwright_obj = sync_playwright()
# playwright_obj.__enter__()  # AttributeError!
```

## 二、系统Chromium路径

```bash
/usr/bin/chromium-browser --version
# Chromium 148.0.7778.215
```

Playwright缓存目录：`~/.cache/ms-playwright/`（系统chromium不在此目录，直接通过executable_path指定）

## 三、每个数据源的采集模式

### L2: titan007分析页

```python
def fetch_titan007(browser, analysis_id):
    """打开分析页 → 提取title+body → 解析"""
    page = browser.new_page()
    page.set_extra_http_headers({'User-Agent': 'Mozilla/5.0'})
    resp = page.goto(f"https://info.titan007.com/analysis/{analysis_id}cn.htm",
                     timeout=10000, wait_until='domcontentloaded')
    title = page.title()  # "澳大利亚 VS 土耳其(2026赛季世界杯)-..."
    body = page.inner_text('body')
    page.close()
    return {'title': title, 'body': body, ...}
```

**队名提取**：从 `page.title()` 提取，格式为 `"主队 VS 客队(赛季赛事名称)-数据分析-新球体育-球探体育"`
**分析ID范围**：首轮世界杯比赛在 **2906740-2906809** 区间（共70场）
**数据量**：每场约5500-7300 chars body text

### L3: 500彩票网 shuju页

```python
def find_500_id(browser, h_name, a_name):
    """从500.com首页赛程表自动匹配比赛ID"""
    page = browser.new_page()
    page.goto('https://odds.500.com/', timeout=15000)
    body = page.inner_text('body')
    
    # 找"主队 VS 客队"行，确定索引
    lines = body.split('\n')
    match_idx = next(i for i, l in enumerate(lines) 
                     if h_name in l and 'VS' in l and a_name in l)
    
    # 获取所有shuju链接（顺序与赛程一致）
    links = page.query_selector_all('a')
    shuju_ids = [re.search(r'shuju-(\d+)', l.get_attribute('href')).group(1)
                 for l in links if l.get_attribute('href') and 'shuju-' in l.get_attribute('href')]
    
    # 用匹配索引取对应ID
    matched_id = shuju_ids[vs_count]
    
    # 提取shuju页数据
    page2 = browser.new_page()
    page2.goto(f'https://odds.500.com/fenxi/shuju-{matched_id}.shtml')
    body = page2.inner_text('body')
    # 解析: FIFA3期/阵容/伤病/澳门心水/战绩/未来赛程/主客场
```

**ID范围**：当前世界杯比赛在 **13592xx** 范围
**数据量**：约6200 chars body text
**⚠️ 限制**：已完赛比赛返回"暂无该场比赛的数据"（9 chars），仅当前/未来比赛有效

### L3: 澳客网 match页

```python
def find_okooo_id(browser, h_name, a_name):
    """从澳客网世界杯赛程页匹配比赛ID"""
    page.goto('https://www.okooo.com/soccer/league/16/schedule/')
    body = page.inner_text('body')
    
    # 找"主队 VS 客队"行（Tab分隔）
    lines = body.split('\n')
    match_idx = next(i for i, l in enumerate(lines)
                     if f'{h_name}\tVS\t{a_name}' in l)
    
    # 获取所有match链接
    links = page.query_selector_all('a')
    match_ids = [re.search(r'/soccer/match/(\d+)/', l.get_attribute('href')).group(1)
                 for l in links if '/soccer/match/' in str(l.get_attribute('href'))]
    
    page2.goto(f'https://www.okooo.com/soccer/match/{matched}/odds/')
```

**ID范围**：当前世界杯比赛在 **1315877**+ 范围
**数据量**：约762 chars body text（较短，身价和积分榜是主要数据）

## 四、常见问题

### 1. Playwright Sync API + asyncio 冲突

```
Error: It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead.
```

**原因**：在已有Playwright上下文内创建新ContextManager。
**解决**：使用 `p.start()` 而不是 `with sync_playwright() as p:` 嵌套。

### 2. 已完赛比赛在500彩票网无数据

500彩票网的shuju页仅显示当前/未来比赛的数据。已完赛比赛统一返回"暂无该场比赛的数据"。
**策略**：L3数据仅在`--browser`模式下对赛前预测启用。

### 3. titan007分析ID非连续

世界杯比赛的titan007分析ID在2906740-2906809范围内，但并非所有ID都是世界杯比赛—中间混有泰国BGC杯等无关比赛。
**匹配策略**：通过 `page.title()` 提取队名后与目标队名前2-3个中文字符匹配。

### 4. 500彩票网ID匹配的行号估算

赛程表中shuju链接的排列顺序与"主队 VS 客队"行的顺序一致，可使用相同的`vs_count`索引定位。但需确保shuju链接数和VS行数一致。

## 五、full_pipeline.py 集成

```python
# 在worldcup-predict-all.py中:
# API-only模式
python3 worldcup-predict-all.py --date YYYY-MM-DD

# 全数据源模式 (L1+L2+L3)
python3 worldcup-predict-all.py --date YYYY-MM-DD --browser

# 代码路径:
# worldcup-predict-all.py → (--browser) → automated_all.collect_all()
# → automated_l2.fetch_titan007() (titan007)
# → automated_l3.find_500_id() + find_okooo_id() (500/澳客网)
# → merge_to_form_signal() → v10 engine.predict()
```
