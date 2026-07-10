# Playwright全自动数据采集指南

## 适用场景

当数据源需要浏览器渲染（JS动态加载/WAF防护/反爬）且API不可用时，使用Playwright+系统Chromium自动导航→提取innerText→解析。

## 环境配置

```python
import os
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/usr/bin'
from playwright.sync_api import sync_playwright

# 启动方式（注意：不用'with'上下文管理器做持久化，用start/stop）
p_obj = sync_playwright().start()
browser = p_obj.chromium.launch(
    executable_path='/usr/bin/chromium-browser',  # 系统Chromium
    headless=True,
    args=['--no-sandbox', '--disable-setuid-sandbox']
)
# ... 使用 ...
browser.close()
p_obj.stop()
```

## 常用技巧

### 页面标题提取队名
titan007分析页标题格式：`主队 VS 客队(赛季赛事名称)-数据分析-新球体育-球探体育`
```python
title = page.title()
m = re.match(r'^(.+?)\s*VS\s*(.+?)\(', title)
h_name = m.group(1).strip()
a_name = m.group(2).strip()
```

### 获取纯文本（比page.content()更干净）
```python
body = page.inner_text('body')  # 去掉HTML标签，仅可见文本
```

### 提取页面数据模式
```python
# 天气场地
re.search(r'场地[：:]\s*(.+?)\s*天气[：:]\s*(.+?)\s*温度[：:]\s*(\S+)', body)
# 比分
re.search(r'(\d+)\s*完\s*\((\d+-\d+)\)\s*(\d+)', body)
# 球员评分
re.findall(r'平均评分\s*(\d+\.?\d*)', body)
# 伤停
body.find('阵容情况')
# 近期战绩
re.search(r'近(\d+)场,胜(\d+)平(\d+)负(\d+),\s*胜率:(\d+)%', body)
```

### 自定义HTTP头
```python
page.set_extra_http_headers({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://info.titan007.com/',
})
```

## 已知可采集站点

| 站点 | URL模式 | 内容 | 状态 |
|:----|:--------|:-----|:-----|
| titan007 | `info.titan007.com/analysis/{id}cn.htm` | 天气/评分/伤停/杯赛排名/场均进球/H2H | ✅ 自动 |
| 500彩票网 | `odds.500.com/fenxi/shuju-{sid}.shtml` | FIFA排名3期/伤病/澳门心水 | ⏳ 仅限未开赛比赛 |
| 中国足彩网 | `www.zgzcw.com` | 赛季排名/40场走势/赔率方差 | 🔧 待验证 |
| 澳客网 | `www.okooo.com/jingcai/` | 球员身价/进球/助攻 | 🔧 待验证 |
