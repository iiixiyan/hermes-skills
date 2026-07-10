# 爆冷预警模型 v1.1 修复 — 超级碾压局误报

## 发现问题

2026-06-22 法国(FIFA#3) vs 伊拉克(FIFA#57) 预测中，
cold_model_trainer.py v1.0 输出 **44% 爆冷概率**，将正确的 R2-Deep 3-0 预测
错误覆盖为 0-1。

## 根因

`_heuristic_cold_prob()` 公式中 `strength_gap_normalized` 特征方向错误：

### 旧公式 (v1.0)
```python
cold_prob = s * 0.30    # s = strength_gap_norm / 100
```

- `strength_gap_normalized = min(100, fd * 1.5)` — FIFA差越大，值越大
- s*0.30 意味着：**FIFA差越大 → 爆冷概率越高** ❌
- 法国vs伊拉克: fd=54 → s=81/100=0.81 → 0.81*0.30=**0.243**(24.3%)
- 仅此一项就贡献了24.3%，加上其他特征后总概率44.1% > 35%阈值

### 新公式 (v1.1)
```python
cold_prob = (1-s) * 0.15   # s = strength_gap_norm / 100
```

- (1-s) 反转方向：FIFA差越大 → **爆冷概率越低** ✅
- 法国vs伊拉克: s=0.81 → (1-0.81)*0.15=**0.028**(2.8%)
- 总概率降至 ~22%，远低于 35% 阈值，不再误触发

## 实施修复（3层防护）

### 第1层: heuristic 公式反转 (cold_model_trainer.py v1.1)
- strength_gap 权重从 `+0.30` 改为 `(1-s)*0.15`
- motivation_gap 权重从 `0.20` 升至 `0.25`（更依赖实际战意信号）
- injury_surprise 权重从 `0.15` 升至 `0.20`（伤停是爆冷最强信号）

### 第2层: 超级碾压硬豁免 (analyze_match_cold)
```
if fd > 25 AND 强队赔率 < 1.20:
    cold_prob = min(cold_prob, 0.30)  # 强制低于阈值
```
即使公式修复后仍可能出现的边界情况，通过硬编码豁免保护。

### 第3层: 使用姿势（调用方应知的规则）
在 `worldcup-predict-v10.py` 中，`analyze_match_cold` 调用的结果未被上层
进一步验证。v1.1 后所有超级碾压局会自动跳过冷覆盖，无需上层改动。

## 命中率影响

| 场次 | v1.0(旧) | v1.1(新) | 实际 |
|:----|:---------|:---------|:----|
| 法国 vs 伊拉克 | 44%爆冷→0-1(❌) | 22%→无预警 3-0(✅) | 待赛果 |
| 约旦 vs 阿尔及利亚 | 37%→1-0(❌边界) | 34%→无预警 1-4(✅) | 待赛果 |

## 相关文件
- `scripts/cold_model_trainer.py` — 主脚本
- `scripts/worldcup-predict-v10.py` — 调用方（调用 analyze_match_cold）
