# 欧指一致性信号分类方法论（v4.4.2 新增）

> 从原始欧指指数变化数据（升/降家数）到分类信号之间的转换方法。
> 数据采集层（59itou-data-fetch）产出 `[胜升, 平升, 负升]` 和 `[胜降, 平降, 负降]` 原始数组。
> 本文件定义如何将这些原始数组分类为可用的预测信号。

## 一、原始数据格式

从欧指Tab的"指数变化"段提取：

```python
# 通过 re.findall(r'(\d+)家', section) 从 innerText 提取
up = [胜升家数, 平升家数, 负升家数]   # 某结果赔率上升的公司数
down = [胜降家数, 平降家数, 负降家数] # 某结果赔率下降的公司数

# 示例: up=[22, 17, 1], down=[1, 2, 22]
# 含义: 22家公司升主胜, 17家升平局, 1家升客负
#       1家公司降主胜, 2家降平局, 22家降客负
```

## 二、信号阈值体系

### 2.1 严格追踪阈值（用于§16.2信号追踪表）

追踪表使用固定绝对阈值，锁定最强信号：

| 信号 | 阈值条件 | 含义 |
|:----|:--------|:----|
| 一致升主胜 | `up[0] >= 20 and down[0] <= 3` | ≥20家升主胜且≤3家降主胜 |
| 一致降主胜 | `down[0] >= 20 and up[0] <= 3` | ≥20家降主胜且≤3家升主胜 |
| 一致升客胜 | `up[2] >= 20 and down[2] <= 2` | ≥20家升客负且≤2家降客负 |
| 一致降客胜 | `down[2] >= 20 and up[2] <= 2` | ≥20家降客负且≤2家升客负 |
| 一致升平 | `up[1] >= 10 and down[1] <= 3` | ≥10家升平且≤3家降平（平局信号） |
| 欧指分歧(易平) | `up[0] > 10 and up[1] > 10 and up[2] > 10` | 胜平负升家数全部≥10，市场分歧大 |

### 2.2 弹性分析阈值（用于盘中分析和联赛特异性分析）

更灵活的阈值，按升降差额进行分类，适合做联赛级别的信号准确率统计：

```python
def classify_signals_flexible(up, down):
    """基于升降差额≥5的弹性分类"""
    signals = []
    
    home_diff = up[0] - down[0]   # 正=更多公司升主胜
    away_diff = up[2] - down[2]   # 正=更多公司升客负
    
    # 一致弱主（市场看弱主队）
    if home_diff >= 5:
        signals.append('一致弱主')
    
    # 一致强主（市场看好主队）  
    if home_diff <= -5:
        signals.append('一致强主')
    
    # 一致弱客（市场看弱客队）
    if away_diff >= 5:
        signals.append('一致弱客')
    
    # 一致强客（市场看好客队）
    if away_diff <= -5:
        signals.append('一致强客')
    
    # 欧指分歧（市场方向混乱，三种结果赔率都升）
    if up[0] > 10 and up[1] > 10 and up[2] > 10:
        signals.append('欧指分歧(易平)')
    
    return signals
```

### 2.3 阈值选择指南

| 场景 | 使用阈值 | 理由 |
|:----|:--------|:----|
| 追踪表更新（长期统计） | 严格阈值（§2.1） | 一致性高，噪声低 |
| 联赛特异性分析（复盘） | 弹性阈值（§2.2） | 样本更多，统计显著性更高 |
| 赛前预测（实时分析） | 先严格阈值、若未触发则弹性阈值补充 | 兼具精度和覆盖度 |

## 三、信号到预测方向的映射

### 3.1 基本映射规则

北单让球盘口下，信号的预测方向取决于让球数（handicap）：

#### hc ≤ 0（主队让球或平手盘）

| 信号 | 市场含义 | 预期方向 |
|:----|:--------|:--------|
| 一致弱主 | 赔率指向主队不被看好 | 预期主不胜 → 走下盘（负/平） |
| 一致强主 | 赔率指向主队被看好 | 预期主胜 → 走上盘（胜） |
| 一致弱客 | 赔率指向客队不被看好 | 预期客不胜 → 走上盘（胜/平） |
| 一致强客 | 赔率指向客队被看好 | 预期客胜 → 走下盘（负/平） |

#### hc > 0（主队受让）

| 信号 | 市场含义 | 预期方向 |
|:----|:--------|:--------|
| 一致弱主 | 主队赔率升 = 市场看弱主队(受让方) | 预期主队难以抵抗 → 走下盘（负） |
| 一致强主 | 主队赔率降 = 市场或看好受让方 | 预期主队不败 → 走上盘（胜/平） |
| 一致弱客 | 客队赔率升 = 市场不看好奇家的客队 | 预期客队难以穿盘 → 走上盘（胜/平） |
| 一致强客 | 客队赔率降 = 市场看好客队(让球方) | 预期客队穿盘 → 走下盘（负） |

### 3.2 预测方向判定函数

```python
def predict_direction(up, down, handicap):
    """
    根据欧指信号和让球数，预测让球胜平负方向。
    返回: '胜', '平', '负' 或 None (无明确信号)
    """
    signals = classify_signals_flexible(up, down)
    
    if not signals:
        return None
    
    # 检查最强信号（优先级：一致弱主/强主 > 一致弱客/强客）
    home_signals = [s for s in signals if '主' in s]
    away_signals = [s for s in signals if '客' in s and '主' not in s]
    
    # 主队信号优先级高于客队信号
    for sig in home_signals:
        if sig == '一致弱主':
            return '平' if handicap == 0 else ('平' if handicap < 0 else '负')
        elif sig == '一致强主':
            return '胜' if handicap <= 0 else '平'
    
    for sig in away_signals:
        if sig == '一致强客':
            return '负' if handicap >= 0 else '胜'
        elif sig == '一致弱客':
            return '胜' if handicap <= 0 else '平'
    
    return None
```

## 四、联赛特异性修正

### 已知信号-联赛反指规则

某些信号在特定联赛中不能按上述映射规则使用：

| 联赛 | 信号 | 修正 | 依据 |
|:----|:----|:----|:-----|
| 解放者杯 | 一致强客(降客胜) | **反指**使用：信号看好客队→走主队不败 | 0/4=0%准确率(2026-05-28) |
| 解放者杯 | 一致升主胜 | **禁用**：14%(1/7)准确率 | 2026-05-29更新：⛔淘汰 |
| **解放者杯** | **一致降主胜** | **恢复使用(当降主胜≥20)**：67%(2/3)有效 | 2026-05-29更新：逆势有效 |
| 南俱杯 | 一致弱主(升主胜) | **升级**：降权至0.6倍 → 恢复1.0倍 | 4/4=100%准确率(2026-05-28) |
| 南俱杯 | 一致强客 | 维持反指 | 南美杯赛通用规律 |
| J1联赛 | 所有欧指信号 | **禁用**：仅依赖基本面+北单赔率 | 全部熔断 |
| 爱超 | 所有欧指信号 | **降权至0.3倍** | 历史准确率<30% |
| 爱甲 | 所有欧指信号 | **降权至0.3倍** | 历史准确率<20% |
| 瑞典超/瑞典甲 | 一致强主 | 正常使用，可加权重至1.2倍 | 历史100%可靠 |
| **挪甲** | **所有欧指一致性信号** | **降权至0.5倍** | 2026-05-29更新：信号参差 |
| **巴西乙** | 所有欧指信号 | **降权至0.7倍**，优先考虑下盘方向 | 强下盘联赛 |
| **希腊超** | **一致降主胜** | **恢复使用**：67%(2/3)有效 | 2026-05-29新发现 |
| **希腊超** | **主胜降赔** | **升级为强信号**：100%(2/2) | 2026-05-29新发现 |

### 执行规则

1. 分析联赛 → 查询修正表
2. 若信号在该联赛需反指 → 反转预测方向
3. 若信号在该联赛禁用 → 跳过该信号
4. 其余信号按§3.1映射规则使用

## 五、从原始数据到分类信号的完整流程

```python
import re

def extract_and_classify(innerText, handicap=0, league=''):
    """
    从欧指Tab的innerText到信号分类，一次完成。
    返回: {signal_types: [], predicted: str, raw: {up: [], down: []}}
    """
    # Step 1: 提取原始数据
    idx = innerText.find('指数变化')
    if idx < 0:
        return {'signal_types': [], 'raw': None}
    
    section = innerText[idx:idx+200]
    nums = re.findall(r'(\d+)家', section)
    if len(nums) < 6:
        return {'signal_types': [], 'raw': None}
    
    up = [int(n) for n in nums[:3]]
    down = [int(n) for n in nums[3:6]]
    
    # Step 2: 信号分类
    signals = classify_signals_flexible(up, down)
    
    # Step 3: 方向预测
    direction = predict_direction(up, down, handicap)
    
    # Step 4: 联赛修正
    corrected_direction = apply_league_correction(league, signals, direction)
    
    return {
        'signal_types': signals,
        'predicted': corrected_direction,
        'corrected_from': direction if direction != corrected_direction else None,
        'raw': {'up': up, 'down': down}
    }


def apply_league_correction(league, signals, direction):
    """应用联赛特异性修正"""
    corrections = {
        '解放者杯': {'一致强客': None},  # None = invert
        '巴西乙': {'一致弱主': None},
    }
    
    if league not in corrections:
        return direction
    
    for sig in signals:
        if sig in corrections[league]:
            # 反转方向: 胜↔负, 平不变
            return {'胜': '负', '负': '胜', '平': '平'}.get(direction, direction)
    
    return direction
```

## 六、与复盘流程的衔接

在赛后复盘中，信号分类后需完成以下步骤：

1. **分类** → `classify_signals_flexible(up, down)` → 得到 signals 列表
2. **预测** → `predict_direction(up, down, handicap)` → 得到预期方向
3. **验证** → 对比预期方向 vs 实际让球结果 → 标记正确/错误
4. **联赛分组** → 按联赛聚合 → 计算各联赛信号准确率
5. **追踪表更新** → 使用严格阈值(§2.1)更新 §16.2 追踪表
6. **联赛阈值修正** → 如果弹性阈值(§2.2)在某联赛准确率 > 刚性阈值 → 识别出特异性规律
