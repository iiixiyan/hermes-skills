# 独孤八招v2升级详情（2026-06-25）

## 升级背景

从500期回测反推，发现原始八招存在以下问题：
- **招❶(间隔状态)**: 纯用遗漏评分，忽略了盘面结构(空白区间)
- **招❷(冷热转换)**: 冷号和热号权重相近，但热号实际重复概率38.2% vs 冷号回补仅12.7%
- **招❸(上期参考)**: 未强制考虑重号(68.7%概率出1-3个)和斜连号(>60%出现频率)
- **招❺(相同尾数)**: 纯选热尾，未区分尾数搭配(小+大/中+大)
- **招❽(冷码必备)**: 极端冷号效率低(12.7%)，温号(遗漏5-9期)更优(28.3%)

## 逐一改动

### 招❶: 间隔状态 → 空白间隔补漏

```python
# 旧逻辑
top_interval = sorted(ctx['oi'].items(), key=lambda x: -x[1]['interval'])[:8]
# 取遗漏最久的号

# 新逻辑
# 找上期前区间隔≥10的空白区(如04和15之间间隔11→空白区5-14)
# 选能填补该空白区的号码
gaps = []
if last_draw[0] > 10:  # 开头空白
    gaps.append((1, last_draw[0]-1))
for i in range(4):
    gap = last_draw[i+1] - last_draw[i]
    if gap >= 10:
        gaps.append((last_draw[i]+1, last_draw[i+1]-1))
if 35 - last_draw[-1] >= 10:  # 结尾空白
    gaps.append((last_draw[-1]+1, 35))
# 从空白区中选评分最高的号
```

### 招❷: 冷热转换 → 追热弃冷

```python
# 热号(30期≥10次)权重+2(翻倍)
super_hot = [n for n in FRONT if hot_30.get(n, 0) >= 10]
# 极端冷号(遗漏≥15期)检查斜连号支撑，无则降权
if om >= 15:
    prev2 = 上两期开奖号
    has_diag = any(abs(n - p) in [2, 3] for p in prev2)
    if not has_diag:
        votes[n] -= 1  # 降权
```

### 招❸: 上期参考 → 重码与斜连

```python
# 重号：上期所有号码直接+1票
prev_nums = self.data[-1]['front']
for n in prev_nums: votes[n] += 1
# 斜连号：上期号码±2或±3
diag_cands = []
for p in prev_nums:
    for d in [2, 3]:
        if 1 <= p-d <= 35: diag_cands.append(p-d)
        if 1 <= p+d <= 35: diag_cands.append(p+d)
# 选评分最高的斜连号
```

### 招❺: 相同尾数 → 同尾搭配

```python
# 尾数分类：小尾(0-3) 中尾(4-6) 大尾(7-9)
# 优先小+大或中+大搭配
for st in small_tails[:2]:
    for bt in big_tails[:2]:
        prefer_tails.add(st); prefer_tails.add(bt)
# 3个以上同尾号→剔除（代码层面通过限制每注最多2个同尾）
```

### 招❽: 冷码必备 → 温号过渡

```python
# 改为选遗漏5-9期的温号
warm_cands = [n for n in FRONT if 5 <= om <= 9]
if warm_cands:
    pick = sorted(warm_cands, key=lambda n: -scores[n])[:1]
# 无温号时退而求其次选遗漏最少的冷号
```

## 核心过滤新增

```python
# 防连号
if abs(n - core[0]) <= 1: continue
# 防同尾
if str(n)[-1] == str(core[0])[-1]: continue
```

## 卫星过滤新增

```python
# 奇偶平衡(3:2或2:3)
odd_cnt = sum(1 for n in note if n % 2 == 1)
if odd_cnt not in [2, 3]: 换卫星修正

# 和值60-130
note_sum = sum(note)
if note_sum < 60 or note_sum > 130: 换卫星修正

# 跨度10-35
span = note[-1] - note[0]
if span < 10 or span > 35: 换卫星修正
```

## 后区过滤新增

```python
def is_valid_back_pair(pair):
    a, b = pair
    if abs(a - b) == 1: return False       # 排除连号
    s = a + b
    if s < 6 or s > 18: return False        # 和值过滤
    if not ((a<=6 and b>=7) or (b<=6 and a>=7)): return False  # 一大一小
    if a % 2 == b % 2: return False          # 一奇一偶
    return True
```

## 回测对比

| 指标 | 升级前 | 升级后(v2) | 变化 |
|:----|:------:|:----------:|:----:|
| 每注≥2 | 17.6% | 18.0% | +0.4% |
| 期≥2 | 56.0% | 46.0% | -10% ⚠️ |
| 奇偶合规 | — | 80.4% | ✅ |
| 后区合规 | — | 100.0% | ✅ |

期≥2下降说明校验过于严格，有时把好注也过滤了。后续可在校验逻辑上加"强校验只过滤极端、弱校验仅提示"。
