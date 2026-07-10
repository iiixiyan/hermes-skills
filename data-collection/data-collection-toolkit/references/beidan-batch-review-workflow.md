# 北单批量回溯预测复盘工作流 — 数据采集部分

> 完整源技能被吸收至此。仅保留与**数据采集**相关的部分（59itou详情页提取、批量并行采集策略）。
> 预测方法论（信号表、联赛规则、命中率）请参见 `football-prediction` skill。

## 适用场景

用户要求对上周/上月的全部北单比赛做回溯复盘预测。场次规模：20~70场。
核心策略：拆分成子任务并行采集欧指数据。

---

## 一、总览

```
Prize page获取所有期次的matchID+赛果
  → 按日期分片（每片10~15场）
  → delegate_task并行处理（每片一个子任务）
  → 每个子任务独立采集59itou详情页欧指/亚指数据
  → 合并所有分片结果
  → 输出总报告
```

---

## 二、数据源：59itou 详情页采集

### 2.1 Prize page — 获取matchID和实际赛果

URL: `https://kt.59itou.com/danchang/prize/`

**期次切换：** 页面顶部有4个期次tab（如126066, 126065, 126064, 126063），通过点击`.prizenav p:nth-child(N)`切换。

**提取matchID：** 每个prizeitem div的id属性即为matchID。
```javascript
document.querySelectorAll('.prizeitem').forEach(el => console.log(el.id))
```

**提取标签（编号+联赛+比分+让球+结果）：**
```javascript
Array.from(document.querySelectorAll('.prizeitem')).map(el => {
    var label = el.querySelector('.timetxt');
    var league = el.querySelector('.liansai');
    return (label?label.textContent:'?') + '|' + (league?league.textContent:'?') + '|' + el.id;
})
```

### 2.2 详情页 — 欧指/亚指数据

**欧指Tab（核心）：**
```
https://kt.59itou.com/202/match3/?current_tab=odds&matchid={matchID}&lotteryId=45
```

**亚指Tab（辅助）：**
```
https://kt.59itou.com/202/match3/?current_tab=handicap&matchid={matchID}&lotteryId=45
```

**提取关键数据（从document.body.innerText解析）：**
- 百家平均初赔（初始）和即赔（最新）→ 从"百家平均"后的数字提取
- 指数变化：胜/平/负的上升公司数和降低公司数 → 从"指数变化"和"上升指数公司"/"降低指数公司"段提取
- 升降盘公司数 → 从"升降盘公司数"后的数字提取
- 高水/低水公司数 → 从"主队水位公司数"后的数字提取

### 2.3 lotteryId 区分

| 彩种 | lotteryId | 说明 |
|:----|:---------:|:-----|
| 北单 | 45 | 北京单场 |
| 竞足 | 90 | 竞彩足球 |

---

## 三、分片与并行采集策略

### 3.1 分片策略

| 场次量 | 分片数 | 每片场次 | 总耗时参考 |
|:-----:|:------:|:--------:|:---------:|
| 20~30场 | 2片 | 10~15场 | ~5min |
| 30~50场 | 3~4片 | 10~13场 | ~6min |
| 50~70场 | 5~7片 | 10场 | ~8min |

### 3.2 子任务结构

每个子任务的context必须包含：
```python
1. 完整的比赛列表（编号+主客队+联赛+让球+实际赛果+matchID）
2. 采集流程说明（访问欧指Tab→提取数据→访问亚指Tab→提取数据）
3. 输出格式模板
```

**关键参数：** 每个子任务的toolsets必须包含`["browser", "terminal"]`（需要浏览器采集59itou详情页数据）。

### 3.3 子任务约束

- 每个子任务处理10~15场
- 每场需要2次browser_navigate（欧指+亚指）
- 总tool calls约 = 场次×2 + 开场白 + 输出
- 建议软上限：50次tool call以内

### 3.4 分片结果合并

子任务返回后，按日期顺序合并所有结果。

合并后的报告结构：
```
## 📊 总命中率
方向命中率：X/Y = Z%

## 📅 逐日详情
### 月X日（周X）✅ X/Y = Z%
逐场输出（简化版）

## 🔍 关键发现
按重要程度列出
```

---

## 四、性能参考

| 阶段 | 时间 | 说明 |
|:----|:----|:-----|
| Prize page数据提取 | 1~3min | 多期次切换提取 |
| 详情页欧指采集（50场） | ~6min | 每场约7秒（含导航+Tab切换） |
| 预测+对比分析 | 并行完成 | 在采集过程中同时进行 |
| 总耗时 | 8~12min | 50场规模 |
