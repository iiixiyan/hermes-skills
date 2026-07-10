# 独孤八招投票系统

大乐透选号"独孤八招"投票系统 — 每招独立给号码投票，得票最高的号码选为核心。

## 八招详细定义

| 招数 | 名称 | 投票规则 | 票数上限 | 源码位置 |
|:----|:----|:---------|:--------:|:--------|
| ❶ | 间隔状态选号 | 遗漏间隔TOP8超期号 | 8票 | `oi.interval` |
| ❷ | 冷热转换选号 | 升温信号TOP6 | 6票 | `transition` |
| ❸ | 上期参考选号 | 重/邻/隔号TOP10 | 10票 | `prev_ref` |
| ❹ | 多期参考选号 | 近10期≥2次活跃号 | ~10票 | `f10` Counter |
| ❺ | 相同尾数选号 | 近30期TOP4尾数所有号 | ~14票 | `tail_freq` |
| ❻ | 缩小选号范围 | 近5期出现过的号 | ~19票 | `pool5` |
| ❼ | 连码重码 | TOP8连号对+上期所有号 | 21票 | `tcp` + 上期 |
| ❽ | 冷码必不可少 | 遗漏≥15期冷号 | ~10票 | `oi.omission` |

## 投票机制

```python
votes = a._eight_techniques_vote(scores, ctx)
# votes[n] = 0~8票 (实际最大~20票因为每招可投多号)
core = a.pick_set(a.FRONT_RANGE, votes, n_pick=3)
```

- 每招**独立投票**，符合条件的号各+1票
- 核心号 = 得票最高的3个号（经区域平衡+连号控制）
- 卫星号 = 评分最高的10个剩余号

## 实测对比

### 26070期（开奖04 05 15 21 32 + 02 11）

| 方法 | 核心号 | 最优注 | 说明 |
|:----|:------|:------|:-----|
| 纯评分TOP3 | [1,8,9] | 1个前区❌ | 全错 |
| 八招投票 | **[4,12,21]** | **3前区+1后区=4个🚀** | 4号热号+连号候选, 21号重号 |

### 500期回测

| 策略 | 均 | ≥2号 | ≥3号 | 唯一号 |
|:----|:-:|:----:|:----:|:-----:|
| 原始(非重叠评分) | 1.76 | 66.6% | 8.8% | 25/35 |
| TOP15聚类(模式A) | 1.73 | 63.6% | 8.8% | 25/35 |
| 八招核心+卫星(模式B) | 1.34 | 37.2% | 3.6% | **13/35** |

**结论：** 八招投票选核在开奖号与八招信号一致时极其精准（26070期4个总命中），但核心+卫星模式的13/35号覆盖导致整体统计表现下降。建议在八招信号高度一致时手动采用模式B，默认使用模式A。

## 实现

```python
def _eight_techniques_vote(self, scores, ctx, period=100):
    votes = {n: 0 for n in self.FRONT_RANGE}
    last_5 = self._last_n(5)
    last_10 = self._last_n(10)

    # 招❶: 间隔状态
    for n, _ in sorted(ctx['oi'].items(), key=lambda x: -x[1]['interval'])[:8]:
        votes[n] += 1

    # 招❷: 冷热转换
    for n, _ in sorted(ctx['transition'].items(), key=lambda x: -x[1])[:6]:
        votes[n] += 1

    # 招❸: 上期参考
    for n, _ in sorted(ctx['prev_ref'].items(), key=lambda x: -x[1])[:10]:
        votes[n] += 1

    # 招❹: 多期参考
    f10 = Counter()
    for rec in last_10:
        for n in rec['front']: f10[int(n)] += 1
    for n, c in f10.items():
        if c >= 2: votes[n] += 1

    # 招❺: 尾数
    tail_freq = Counter()
    for rec in self._last_n(30):
        for n in rec['front']: tail_freq[n[-1]] += 1
    for n in self.FRONT_RANGE:
        if str(n)[-1] in set(t for t, _ in tail_freq.most_common(4)):
            votes[n] += 1

    # 招❻: 近5期
    for rec in last_5:
        for n in rec['front']: votes[int(n)] += 1

    # 招❼: 连码重码
    for (a, b) in ctx['tcp']:
        votes[a] += 1; votes[b] += 1
    for n in [int(x) for x in self.data[-1]['front']]:
        votes[n] += 1

    # 招❽: 冷码
    for n in self.FRONT_RANGE:
        if ctx['oi'].get(n, {}).get('omission', 0) >= 15:
            votes[n] += 1

    return votes
```
