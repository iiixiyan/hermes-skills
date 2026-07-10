## Titan007 (球探体育) 访问细节

> 2026-06-20 验证更新

### 正确域名

| 用途 | 域名 | 可用性 |
|:----|:----|:------|
| **分析页** | `zq.titan007.com` | ✅ 当前可用 |
| ~~旧域名~~ | ~~`info.titan007.com`~~ | ❌ 有些URL可用但不稳定 |

### 分析页URL格式

```
https://zq.titan007.com/analysis/{analysisId}cn.htm
```

### 搜索接口不可用

`/Search/?Key=...&Type=Match` 返回 **404**（.NET Framework找不到资源）。

### 获取analysisId的正确方法

通过导航到世界杯/联赛页面，用JS从文档中提取「析」链接：

```javascript
// 在世界杯赛程页的浏览器console中执行
let links = Array.from(document.querySelectorAll('a'))
  .filter(a => a.textContent.trim() === '析');
links.map(a => {
  let m = a.href.match(/analysis\/(\d+)cn/);
  return m ? m[1] : '';
}).join('\n');
```

### 已确认的世界杯analysisId范围

| 轮次 | analysisId范围 | 说明 |
|:----|:--------------|:-----|
| R1(首轮) | 2906943-2906976 | 包含分组赛全部场次 |
| R2(第二轮) | 2907339-2907370 | 包含后续轮次 |
| 今天的比赛 | 2906951/2906947/2907361等 | 已完赛可查 |

### 分析页body特征

- 正常加载：**6000+字符**
- 拦截/空页：<300字符
- 包含字段：天气、温度、场地、杯赛积分排名、阵容情况(含伤停)、球员评分(含平均评分)、对赛往绩(H2H)、近期战绩、竞足数据(SP + 波胆)

### 采集注意事项

| 注意项 | 说明 |
|:------|:-----|
| 批量采集 | 需每页至少**3秒**间隔，过快会被限速 |
| 请求头 | 必须设置 `User-Agent: Mozilla/5.0` |
| 无搜索 | `/Search/` 404，只能从联赛页提取ID |
| 历史比赛 | 已完赛比赛分析页**仍有完整数据** |
| Headless Playwright | 可能被检测拦截，浏览器工具更好 |
