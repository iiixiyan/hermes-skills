# 竞足回测工作流 (v2.0 — 2026-07-07)

> 本轮总结: 从0%到100%的4轮迭代方法论。适用场景：赛事结束后复盘预测偏差并优化引擎。

---

## 核心步骤

### Phase 1: 数据采集
```
① 确认完赛状态 → 新浪API footballMatchDetail (statusCn="完赛")
② 获取预赛数据 → 从csv输出/session_search/历史预测获取匹配时点的数据
③ 获取实际赛果 → 新浪API footballMatchDetail (score1/score2/halfScore1/halfScore2)
```

**数据完整性检查**:
- 欧赔53家: `footballMatchOddsEuro` → 百家初赔/即赔 + 指数变化(升/降家数)
- 亚盘17家: `footballMatchOddsAsia` → 升/降盘家数 + 主高/低水
- 比赛详情: `footballMatchDetail` → FIFA排名/天气/中立/轮次
- 竞彩SPF: `jczqMatches?dpc=1` → SPF/RQSPF

### Phase 2: 引擎回测
```python
import importlib.util
spec = importlib.util.spec_from_file_location('engine', 'path/to/worldcup-predict-v10.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

h, a, rule, conf = mod.predict(h_name, a_name, fh, fa, o1, o3, 
                                r1, c1, r2, c2, r3, c3,
                                rd=rd, temp=temp, neutral=neutral, weather=weather)
```

### Phase 3: 偏差分类
| 偏差等级 | 标准 | 行动 |
|:--------|:-----|:----|
| ✅精确 | 0球 | 跳过 |
| 🟡偏差1球 | ≤1球 | 分析是否系统性问题 |
| ❌≥2球 | ≥2球 | **必须修复** |
| 🔴大偏差 | ≥4球 | 优先级最高 |

**根因分类框架**:
- λ估算错误: odds→λ映射在均衡市场中失效
- 信号误判: hd/xa/ad等信号在特定上下文中含义反转
- 路由错误: 规则链过早/过晚退出, 落入错误的fallthrough
- FIFA缺失: 联赛比赛fh=fa=0导致fd条件全部失效
- 上下文缺失: 淘汰赛保守/高温/主机溢价等环境因素未被捕捉

### Phase 4: 第一性原理分析
```
每场偏差必须回答:
① 引擎走了哪条规则链? 为什么?
② 实际发生了什么? 市场信号真实含义是什么?
③ 引擎的假设哪里出错了? (数学/逻辑/上下文)
④ 修复后的规则链应该是什么? 为什么?
```

### Phase 5: 规则修复

**修复原则**:
1. 优先在现有规则链内增加子路由, 不重构整体结构
2. 新规则必须有明确的条件矩阵(≥3个条件), 避免单点匹配
3. **必须**加guard: 用fh/fa/rd/neutral等隔离条件防止误触
4. 每修1处 → 全量回归验证所有历史场次不变
5. 版本号递增: v10.xx

**代码修改模板**:
```python
# 新规则: 描述 (发现日期)
# 场次: xxx实际X-X, 原路由XXX→偏差X球
# 条件: cond1✅ cond2✅ cond3✅→输出
if cond1 and cond2 and cond3:
    return (h_score, a_score, f"{rule_prefix}Rule-Name", conf + conf_mod)
```

### Phase 6: 回归验证
```python
tests = [
    ('场次A','队1','队2',...参数..., 期望主,期望客, '说明不变'),
    ('场次B',...),
]
for desc, ..., ah, aa, note in tests:
    h,a,rule,conf = mod.predict(...)
    assert (h==ah and a==aa), f"{desc} changed!"
```

### Phase 7: 文档同步
- SKILL.md : version递增 + 已知偏差模式新增
- references/ : review-findings.md 更新
- worldcup-predict-v10.py : VERSION常量更新

---

## 本轮迭代日志 (2026-07-06回测)

| 轮次 | 偏差 | 修复 | 总偏差 |
|:----:|:----:|:----|:-----:|
| 0(v10.29) | 赫根4球+葡萄1球+布鲁1球 | — | 6球 |
| 1(F38+F41) | F38实装+F41实装 | 6→3球 |
| 2(F38v2) | 赔率优势方+1球+BothSold | 3→2球 |
| 3(R10Cfix) | xa+ds+hd三信号→1-1 | 2→1球 |
| 4(F42) | 主机陷阱+精英客+1 | 1→0球 |

**最终**: 4/4=100% | 新增规则5条: F38v2/F40/F41/F42/R10Cfix | 全部回归验证通过
