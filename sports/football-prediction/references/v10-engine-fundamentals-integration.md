# v10引擎基本盘数据注入方案

> 2026-06-20 | 用于世界杯/联赛预测时集成球队基本面数据(fundamental/basics data)

## 为什么需要基本面注入

纯赔率信号在市场极端一致时会被扭曲：
- **过热交易**：散户跟风买入大热强队 → 赔率方向失真（阿根廷3-0阿尔及利亚）
- **市场误解**：世界杯首轮强队慢热 → 赔率示弱（西班牙0-0佛得角）
- **数据反转**：已赛比赛赔率被重置 → 实时数据不可靠（德国7-1库拉索）

基本面数据（FIFA排名/近10场状态/伤停/阵容完整度）提供**独立于市场信号**的判断基准。

## form_signal 接口

v10引擎的`predict()`函数接受`form_signal`可选的字典参数：

```python
from worldcup_predict_v10 import predict, predict_with_basics

# 基本用法（纯赔率）
h, a, rule, conf = predict(h="德国", g="库拉索", fh=5, fa=77,
    o1=1.05, o3=15.0, r1=0, c1=29, r2=0, c2=29, r3=25, c3=0, rd=1)

# 基本面注入用法
form_signal = {
    'injury_impact_h': 0,      # 0=无伤停 1=轻伤 2=核心缺阵
    'injury_impact_a': 1,      # 客队主力伤停
    'form_diff': 3,            # 主队近10场净胜差 - 客队近10场 = 3
    'strength_gap': 15,        # 综合实力差 (主-客)
    'lineup_known': True,      # 首发已公布
    'avg_rating_diff': 0.5,    # 球员评分差
}
h, a, rule, conf = predict_with_basics(form_signal, h="德国", g="库拉索", ...)
```

## 基本面数据源

| 数据类型 | 推荐源 | 采集方式 |
|:--------|:------|:---------|
| FIFA排名 | 新浪API footballMatchDetail | API直连 |
| 近10场战绩 | 59itou战绩Tab | Playwright浏览器 |
| 综合实力(0-100) | 59itou战绩Tab "综合实力"段 | Playwright → regex提取 |
| 伤停信息 | 59itou阵容Tab "预计伤停以及影响" | Playwright浏览器 |
| 首发阵容&阵型 | 59itou阵容Tab | Playwright浏览器 |
| 球员评分 | 球探体育 titan007 分析页 | 浏览器 |

## 基本面修正规则

### 优先级：纯赔率规则链 > 基本面微调

基本面不改变规则选择，仅在赔率规则链确定比分后做**最多±1球**微调：

```python
# 顺序
1. predict() → 纯赔率规则链 → (主场球, 客场球, 规则名, 信心)
2. predict_with_basics() → 叠加基本面修正

# 基本面修正幅度
伤停核心缺阵(level=2):  受影响方 -1球, 信心 -1
伤停轻伤(level=1):      受影响方(if ≥2球) -1球
状态碾压(form_diff≥6):  强势方 +1球
实力差≥30+首发已知:      强势方 +1球
评分差≥1.0:              强势方 +1球

# 防守型规则豁免(R1-/R0-/R3-Slow/R6-BL/R15-)
# 不应用状态/实力/评分修正，仅应用伤停修正
```

### R0.5: FIFA排名基本面锚定（最重要）

当FIFA差距极大(fd≥65)时，FIFA排名优势方实力碾压不可否认，即使市场赔率反转：

```
德国(FIFA5) vs 库拉索(FIFA77):  o1=5.49(市场认为库拉索胜?!)
→ 但FIFA差72+德国FIFA前5 → 基本面锚定: 德国7-1胜 ✅

西班牙(FIFA2) vs 佛得角(FIFA67): fd=65
→ 但首轮强队慢热 → R0.5首轮豁免 → R1-Fish: 0-0 ✅
```

## 采集代码模板

```python
# 从59itou战绩Tab提取综合实力
def extract_strength(text):
    idx = text.find('综合实力')
    if idx < 0: return None
    nums = re.findall(r'(\d+)', text[idx:idx+200])
    return (int(nums[0]), int(nums[1])) if len(nums) >= 2 else None

# 从阵容Tab提取伤停
def extract_injuries(text):
    idx = text.find('预计伤停以及影响')
    if idx < 0: return None
    section = text[idx:idx+500]
    fatal = any(kw in section for kw in ['缺阵', '赛季报销', '核心'])
    important = any(kw in section for kw in ['伤疑', '出战成疑', '累计黄牌'])
    return {'fatal': fatal, 'important': important}
```

## v10.5验证集基本面修复案例

| 比赛 | 问题 | 修复方式 |
|:----|:-----|:---------|
| 德国7-1库拉索 | 赛后赔率反转(德国o1=5.49) | R0.5 FIFA差72基本面锚定 |
| 西班牙0-0佛得角 | fd=65但首轮强队慢热 | R0.5首轮豁免+R1-Fish防平 |
| 阿根廷3-0阿尔及利亚 | xa极端升客(47升)造热 | P11-B: FIFA4基本面>市场热度 |
| 伊拉克1-4挪威 | 市场误判主队(伊拉克)胜 | R12E: FIFA排名方向修正 |
