# 国内体育数据站点WAF穿透模式

> 多个国内体育数据站点（okooo/500.com/澳客等）使用阿里云WAF或类似防护，常规HTTP请求会被拦截。本文档记录已验证通过的访问模式。

## 通用技巧

### 必需请求头
```bash
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Referer: https://www.<sitedomain>.com/
```
- **User-Agent**：必须模拟真实浏览器，裸curl/requests默认UA会被WAF拦截
- **Referer**：大部分WAF检查Referer来源，设为站点首页通过率最高

### 编码处理
多数老牌中国体育站点（澳客/500.com）仍使用**GBK/GB2312**编码，返回到终端后需转码：
```bash
curl -s ... | iconv -f GBK -t UTF-8
```

### 备选：通过browser_navigate
部分站点的WAF对浏览器更友好，但okooo（阿里云WAF）用browser_navigate也可能超时（60s无响应）。
此时：先用curl确认连通性，再用browser_navigate携带正确headers。

## 已验证站点模式

### 1. 澳客网 okooo（vxbf.okooo.com）
- **状态**：✅ 可用
- **防护**：阿里云WAF，裸请求返回405
- **验证命令**：
  ```bash
  curl -s --connect-timeout 10 --max-time 20 \
    -H "User-Agent: Mozilla/5.0 ..." \
    -H "Referer: https://www.okooo.com/" \
    "https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=SportteryScore&LotteryNo=2026-05-30" \
    | iconv -f GBK -t UTF-8
  ```
- **用途**：竞足开奖结果/赛果查询

### 2. kt.59itou.com
- **状态**：✅ 浏览器可直接访问
- **防护**：无WAF，但证书可能有问题
- **用途**：竞足/北单列表页、详情页多Tab数据采集

## 使用建议

| 场景 | 工具 | 备注 |
|:----|:----|:-----|
| 快速验证URL是否可达 | curl + UA/Referer头 | 先curl，再决定是否用浏览器 |
| 获取静态HTML赛果 | curl + 编码转换 | 最快，适合okooo这类查询页 |
| 采集动态JS页面 | browser_navigate + 等待 | 59itou详情页需要JS渲染Tab |
| 批量采集多场次 | Playwright Python API | 逐场串行，加30s超时控制 |

## 已知失效模式
- **裸curl无UA** → 阿里云WAF返回405页面 + "您的访问被阻断"
- **browser_navigate超时** → 该站点browser不可达时，curl可能仍可用（反之亦然）
- **未加Referer** → 部分WAF检查Referer白名单，返回403/405
