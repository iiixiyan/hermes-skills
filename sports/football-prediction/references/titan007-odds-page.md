# 球探体育(titan007)欧赔页 — 历史百家平均数据源

> 2026-06-20新增。解决新浪API matchId回收导致无法拉取历史欧赔数据的问题。

## 用途

对已完赛的历史比赛，获取**比赛前的百家平均欧赔**和**升/降家数**(r1/c1/r2/c2/r3/c3)，用于引擎回测和偏差分析。

## 数据源URL

```
欧赔页: https://zq.titan007.com/analysis/{analysisId}oucn.htm
```

- `{analysisId}` 从世界杯赛程表的"析"链接中提取 (`href` 匹配 `/analysis/(\d+)cn`)
- 页面加载179家博彩公司的完整欧赔数据

## 提取方法

### 初赔(initial odds) — 百家平均计算

1. 打开 `https://zq.titan007.com/analysis/{analysisId}oucn.htm`
2. 切换显示模式为"初"（初赔）：
   ```javascript
   let s = document.querySelector('select');
   for (let opt of s.options) {
     if (opt.text.includes('初')) { s.value = opt.value; s.dispatchEvent(new Event('change')); break; }
   }
   ```
3. 提取所有公司的主胜/平/客胜初赔：
   ```javascript
   let rows = document.querySelectorAll('table:nth-of-type(2) tr');
   let odds = [];
   for (let i = 1; i < rows.length; i++) { // skip header
     let cells = rows[i].querySelectorAll('td');
     if (cells.length >= 4) {
       let o1 = parseFloat(cells[2]?.textContent);
       let o2 = parseFloat(cells[3]?.textContent);
       let o3 = parseFloat(cells[4]?.textContent);
       if (o1 && o2 && o3) odds.push({o1, o2, o3});
     }
   }
   ```
4. 计算百家平均：
   - `avg_o1 = sum(o1)/count` 
   - `avg_o2 = sum(o2)/count`
   - `avg_o3 = sum(o3)/count`

### 即赔(current odds) — 升/降家数计算

1. 切换回"即"模式：
   ```javascript
   let s = document.querySelector('select');
   for (let opt of s.options) {
     if (opt.text.includes('即')) { s.value = opt.value; s.dispatchEvent(new Event('change')); break; }
   }
   ```
2. 提取所有公司的即赔数据（同上方法）
3. 逐公司对比初赔vs即赔：
   - `r1 = count(o1_即赔 > o1_初赔)` — 升主胜家数
   - `c1 = count(o1_即赔 < o1_初赔)` — 降主胜家数
   - `r2 = count(o2_即赔 > o2_初赔)` — 升平家数
   - `c2 = count(o2_即赔 < o2_初赔)` — 降平家数
   - `r3 = count(o3_即赔 > o3_初赔)` — 升客胜家数
   - `c3 = count(o3_即赔 < o3_初赔)` — 降客胜家数

## 与其他数据源配合

| 数据 | 来源 |
|:----|:-----|
| **欧赔百家平均+升/降家数** | titan007欧赔页(初赔/即赔) |
| **实际比分/天气/温度/中立** | titan007分析页(`{id}cn.htm`) |
| **球员评分/伤停** | titan007分析页正文 |
| **FIFA排名** | 新浪API `footballMatchDetail` 或硬编码 |

## 注意事项

- titan007欧赔页对机器人有限速，批量采集需加3-5秒间隔
- 需要使用完整浏览器UA头(`Mozilla/5.0`)绕过简单反爬
- 179家公司中可能包含重复或不完整数据，建议过滤掉无效值(如o1>100的异常值)
- 初赔时间可能远早于比赛日(有些公司一个月前就开出初赔)，不影响百家平均计算
