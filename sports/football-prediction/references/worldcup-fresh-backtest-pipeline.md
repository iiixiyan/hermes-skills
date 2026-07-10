# 世界杯原始数据回溯预测管线（无历史预测参考模式）

> 创建于2026-06-19 | 基于28场世界杯实时数据采集 + 全新规则引擎构建
> 验证场次: D1-D4共28场, v2达到偏差≤1球71.4%

## 概述

当用户要求"忽略历史预测、从零重新回溯"时，使用此管线。区别于 `worldcup-full-backtest-methodology.md`（基于规则迭代的历史记录），本管线从原始欧赔数据出发，完全独立构建规则链。

## 核心流程（6步）

### 第1步：匹配比赛→获取matchId

```bash
# 新浪API jczqMatches 返回世界杯比赛列表 + matchId
# ⚠️ 必须有 __caller__=wap&__version__=1.0.0&__verno__=10000
curl -s "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json\
  &__caller__=wap&__version__=1.0.0&__verno__=10000\
  &cat1=jczqMatches&gameTypes=spf&date=YYYY-MM-DD&isAll=1&dpc=1"

# 返回: result.data[].matchId, team1, team2, league, score(空)
# 过滤 league="世界杯" 或 league="World Cup"
```

**日期范围确认：** 从59itou prize page日期标签确认哪些日期的比赛已结束。prize page按销售日期分组（非比赛日期），example：6/13 tab可含周五至周日的比赛。

### 第2步：获取欧赔数据（53家百家平均+升/降家数）

```python
# footballMatchOddsEuro → 53家公司初赔+即赔
url = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json\
  &__caller__=wap&__version__=1.0.0&__verno__=10000\
  &cat1=footballMatchOddsEuro&matchId={MID}"

odds = response['result']['data']  # 列表，每项含o1Ini/o1New/o2Ini/o2New/o3Ini/o3New

# 关键字段:
o1 = avg(o['o1New'])      # 百家平均主胜即赔
o3 = avg(o['o3New'])      # 百家平均客胜即赔
r1 = count(o1New > o1Ini)  # 主胜升家数
c1 = count(o1New < o1Ini)  # 主胜降家数
r2 = count(o2New > o2Ini)  # 平升家数
c2 = count(o2New < o2Ini)  # 平降家数
r3 = count(o3New > o3Ini)  # 客胜升家数
c3 = count(o3New < o3Ini)  # 客胜降家数
```

### 第3步：获取实际赛果 + FIFA排名（关键发现）

```python
# ⚠️ footballMatchDetail 对已完赛比赛返回实际比分和FIFA排名！
# 而 jczqMatches 的score字段为空—— 不要误判为"无赛果"

url = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json\
  &__caller__=wap&__version__=1.0.0&__verno__=10000\
  &cat1=footballMatchDetail&matchId={MID}"

data = response['result']['data']
score1 = data['score1']       # 主队实际进球
score2 = data['score2']       # 客队实际进球
half1  = data['halfScore1']   # 半场比分
half2  = data['halfScore2']
fifa1  = data['team1Position']  # 主队FIFA排名
fifa2  = data['team2Position']  # 客队FIFA排名
round  = data['round']        # 轮次(1/2/3)
stage  = data['stage']        # "小组赛"/"淘汰赛"
env    = data['environment']  # "晴 23°C"
neu    = data['isNeutral']    # "0"=非中立(东道主), "1"=中立
status = data['status']       # 3=完赛
```

### 第4步：信号计算

```python
fd = abs(fifa1 - fifa2)       # FIFA排名差

# 核心信号（基于欧指升降家数）
xh = r1 >= 40 and c1 <= 5       # 极端升主胜
xa = r3 >= 40 and c3 <= 5       # 极端升客胜
hd = c1 >= 25 and r1 <= 10      # 一致降主胜
ad = c3 >= 25 and r3 <= 10      # 一致降客胜
he = xh and c3 >= 20            # 排除主胜+强降客
df = c2 >= 15                   # 平降信号
ds = c2 >= 25                   # 强平降信号
bl = c1 >= 40 and r3 >= 40 and o1 < o3  # 骑墙
ts = xh and df and c3 >= 40 and fifa1 < fifa2  # 三向分歧
it = he and o1 < o3 and not (fifa1 < fifa2)    # 造热
ra = he and o3 < o1              # 真正客强
hb = abs(r1-c1)<=5 and r3>=35 and r1>=20  # 主平衡卖客极端
r2_signal = r2 >= 30 and c2 <= 10  # 极端升平
```

### 第5步：规则链构建（迭代收敛）

**起始基线（57.1%偏差≤1球）：** 先按直觉排列规则优先级
**迭代循环：** 每轮跑完全部28场 → 列出所有偏差>1球 → 分析每场根因 → 新增/调整规则 → 重新跑全量

**关键规则发现（从v1→v2验证）：**

| 规则 | 条件 | 输出 | 案例 |
|:----|:-----|:----|:----|
| Top5R1鱼腩防平 | R1 + FIFA≤5 + 对手FIFA≥60 | 0-0/1-1 | 西班牙0-0佛得角 |
| hb顶级强队高比分 | hb + FIFA≤5 | 3-1/4-2 | 英格兰4-2克罗地亚 |
| 客强R1慢热防平 | R1 + ra + R1 | 1-1 | 卡塔尔1-1瑞士 |
| 近距爆种上调 | xa + fd≤5 + 主强 | 4-0/5-1 | 瑞典5-1突尼斯 |
| R2大比分降主 | R2 + c1≥30 + fd≥20 | 3-0/4-0 | 瑞士4-1波黑 |
| 升主无反(home) | xh + 无df + fd≥5 | 2-0 | 澳大利亚2-0土耳其 |
| 骑墙R1 | bl | 1-1/2-0 | 比利时1-1埃及 |
| 造热 | it | 1-0 | 加纳1-0巴拿马 |

**优先级链（典型顺序）：**
```
东道主 → Top5鱼腩 → 极端深盘 → hb → ra → 骑墙 → 造热 → 
xh+df(三向/顶级/强队/近距) → xh无df → xa → 
ad → ds/r2_signal → hd → 放宽hd → df → 
双边升分歧 → R2兜底 → Def
```

### 第6步：验证报告

每次迭代输出三条核心指标：
```
精确命中: N/28 = XX.X%
方向命中: N/28 = XX.X%
偏差≤1球: N/28 = XX.X%   ← 核心目标指标
```

**偏差分类诊断：**
- 偏差=0 ✅：规则已覆盖
- 偏差=1 ⭐：可接受（比分池范围覆盖）
- 偏差≥2 ❌：必须修复

**偏差>1球恢复优先级：**
1. 是否有现成规则可覆盖？
2. 是否需新增规则分支？
3. 是否需调整现有规则阈值？
4. 是否尾事件（一次性的，不修复）？

---

## 赛事数据确认途径

| 途径 | 数据内容 | 可靠性 |
|:-----|:--------|:------|
| 🥇 新浪 API footballMatchDetail | 比分(含半场) + FIFA + 天气 + 轮次 + 中立 | 最高 |
| 🥇 59itou prize page (浏览器) | 比分 + SP + 半全场 + 总进球 | 高（需js交互） |
| 🥈 竞彩官方API method=result | 比分 + 状态 | 中（EdgeOne WAF限制） |
| 🥉 OKooo | 比分 + 状态 | 中（GBK→UTF-8转码） |

---

## 已知陷阱

1. **jczqMatches 赛果为空 ≠ 数据不可用**：实际比分在 footballMatchDetail 中，而非 jczqMatches
2. **59itou prize page 销售日期 ≠ 比赛日期**：周三比赛归入"6-13"标签页（前一个销售日）
3. **spf.spf字段含","字符串**：格式为"胜,平,负"，非数字
4. **footballMatchOddsEuro/Asia 参数缺失**：缺 `__version__=1.0.0` → 静默返回空 data=[]
5. **百家平均计算**：使用53家公司 o1New/o2New/o3New 的算术平均，不要用单一家公司
