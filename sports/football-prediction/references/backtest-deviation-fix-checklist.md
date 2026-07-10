# 引擎偏差修复清单（v10.12+）

每次跑完全量回测发现偏差后，按此清单逐项检查，避免漏修。

## 🔴 P0 — 必须先检查的 3 项（优先级最高）

| # | 检查项 | 原因 | 涉及比赛 |
|:-:|:-------|:-----|:---------|
| 1 | **新规则名是否加入 `r3_safe_rules`** | R3无pts时lm×0.80静默降低比分。白名单是substring匹配，**已有规则名**也可能遗漏 | 挪威vs法国(0-1被降0-0)、土耳其vs美国(1-3被降0-2) |
| 2 | **新`return`是否放在旧`return`之前** | if-elif链中先return退出，后面的代码永不执行 | P11-Hot-H-Mid新规则插在旧return后变死代码 |
| 3 | **`__pycache__`是否清除** | `importlib.util.module_from_spec`使用缓存的`.pyc`，修改不生效 | 每次改引擎后必须 `rm -rf scripts/__pycache__/` |

## 🟡 P1 — 偏差类型对应的常见修复

| 偏差模式 | 症状 | 常见修复 |
|:---------|:-----|:---------|
| **R3造热陷阱误判** | R3+弱旅(FIFA≥55)+强信号(c1≥40+r3≥40)走1-1/2-2 | 插入R3+FIFA差≥30+鱼腩豁免 → 走真实方向 |
| **R3精英客队逆转** | xa+ds+fa≤5(客FIFA前5)走向主队爆冷 | 插入fa≤5时走精英客队小胜方向 |
| **东道主过度碾压** | 东道主(R0硬编码)在造热信号下仍出大比分 | 检查bl+hd+r2h同时触发+pts相同 → 走正常规则链 |
| **双方同分造热** | hd+r2h+双方pts≥3+fd<30预测2-1实际1-0 | 插入c1≥40+r3≥35造热检查 → (1,0)防过热 |
| **xh+df+FIFA接近** | 极端升主(45家)+降平但fd≤10预测2-1实际1-1 | 插入fd≤10+fh>fa(主FIFA更差) → (1,1) |
| **高温无信号闷平** | temp≥30+无极端信号+df走向1-1实际0-0 | 插入temp≥30+无xh/xa/hd/ad+fd≤10 → (0,0) |
| **弱旅主场安慰球** | 超弱主场(FIFA≥80)被预测0-x实际可进1球 | 插入fh≥80+fh>fa → 主队+1球 |

## 🟢 P2 — 验证步骤

```python
# 修复后必须按顺序执行:
# 1. 清缓存
rm -rf scripts/__pycache__/

# 2. 全量回测(31场实时API)
python3 scripts/worldcup-full-backtest-v8d.py

# 3. 特殊数据验证(6/26等非实时API场次)
python3 # 对6/26六场等手动验证

# 4. 检查回归: 原来命中的场次是否退步
#    - 对比上一次全量回测结果
#    - 重点检查R3场次(最容易回归)
```

## 📌 典型修复示例

```python
# 1. R0东道主规则前插入造热检查
if h == "加拿大" and rd == 2 and c1 >= 30 and o1 < 1.30:
    if bl and hd and r2_high and pts_h == pts_a and pts_h <= 2:
        return (1, 1, "R6-BL-HD-Mid-D", 2 + conf_mod)  # 非碾压

# 2. R10B-Home-Big前插入精英客队逆转
if fa <= 5:  # 客队FIFA前5
    return (0, 1, "R10B-Elite-Away", 3 + conf_mod)

# 3. R10-Trap-Draw前插入鱼腩豁免
if rd == 3 and max(fh, fa) >= 55 and fd >= 30 and ...:
    if hd: return (5, 0, "R10-Trap-Fish-HD", 4 + conf_mod)
```

## ⚠️ 常见陷阱

- **R3 pts=0 ≠ pts=-1**: `_calc_motivation(0, fh)`返回「已淘汰×0.80」。未知积分必须传-1
- **Sina API matchId回收**: 历史比赛的matchId可能已分配给新比赛，API返回错误数据
- **先修dev≥3再修dev=1**: 先解决大偏差(≥3球)，再精细调优(1球)，防止回归
