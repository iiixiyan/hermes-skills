# 彩票历史数据源

## 源A: cjcp.cn（彩经网）— 推荐（浏览器可直接访问）

大乐透最新开奖 + 近5期历史数据采集。

### URL
- **最新开奖**: https://m.cjcp.cn/kaijiang/dlt/

### 采集方法
浏览器导航到URL，用console提取：
```javascript
let allLis = document.querySelectorAll('li');
let draws = [];
for (let li of allLis) {
  if (li.textContent.includes('第2026') && li.textContent.includes('期')) {
    draws.push(li.textContent.replace(/\s+/g, ' ').trim());
  }
}
JSON.stringify(draws);
```

### 页面结构
- 顶部大号数字 = 最新一期开奖号码（5红球+2蓝球）
- 下方列表 = 历史开奖（滚动加载）
- 同时显示：开奖日期、销量、奖池

## 源B: GitHub (yangxb919/lottery-data) — 前置采集

```bash
curl -sL --max-time 60 "https://ghproxy.net/https://raw.githubusercontent.com/yangxb919/lottery-data/main/data/dlt.json"
```

## 已失效源（勿用）
- okokoo — 405/JS动态填充
- 500.com — WAF拦截
- lottery.gov.cn — iframe跨域不可采集
- webapi.sporttery.cn — WAF拦截