# League Pipeline v2.1 — Architecture Reference

> Created: 2026-06-24 (芬超6/6=100% milestone)

## Pipeline Flow

```
fetch_league_results()  ← 竞彩官方API (全量历史)
       ↓
compute_team_stats()    ← 近N场场均进球/失球
       ↓
Dixon-Coles Pipeline    ← full_lambda_pipeline()
       ↓
compute_match_lambdas() ← 攻击×防守交叉乘积 (λ_home, λ_away)
       ↓
fetch_all_sina_data(mid) ← 新浪API: 欧赔 + 大小球(Asia goalLine) + 排名
       ↓
apply_all_corrections(λ_h, λ_a, sina, stats)  ← 10层修正链
       ↓
predict_with_poisson(λ_h_final, λ_a_final)   ← 泊松Top6比分
```

## 10-Layer Correction Chain (in order)

### Layer 1: 欧赔市场信号
| Condition | Action |
|-----------|--------|
| c1≥30 && o1<2.0 | λ_h × 1.10 (c1≥40→×1.15) |
| r3≥30 && o3<2.0 | λ_a × 1.10 (r3≥40→×1.15) |
| rank_h<rank_a && o1<o3 | λ_h × 1.05 (排名确认) |
| rank_h>rank_a && o3<o1 | λ_a × 1.05 (排名确认) |
| rank_h<rank_a && o3<o1 && r3≥20 | λ_h×0.95 / λ_a×1.05 (跟市场) |
| rank_h>rank_a && o1<o3 && c1≥20 | λ_h × 1.15 (跟市场) |

### Layer 2: 大小球校准
- Parse goal_line from Asia odds (e.g. "2/2.5|2.5|3")
- Convert over/under odds to implied probability
- Compare market expected total vs model λ_total
- Over@<1.85 (prob>55%): λ × 1.05~1.25
- Under@>2.20 (prob<42%): λ × 0.80~0.95

### Layer 3: 双攻击型大比分
- Both teams avg_gf ≥ 1.5 → λ × 1.10~1.25
- Rank_h<rank_a (home better) → home +0.05 extra
- Rank_h>rank_a (away better) → away +0.05 extra

### Layer 4: 极攻扩展
- Both attack AND (λ_h+λ_a) ≥ 5.0 → λ × 1.10 both

### Layer 5: 主场狗守和
- rank_h>rank_a (weaker home) && fd≥3 && r3≥30 && o3<2.5
- → λ_h = max(λ_h, 0.6), λ_a = min(λ_a, λ_h×2.0)

### Layer 6: 沉默市场主场狗 ⭐
- rank_h>rank_a && fd≥3 && (c1+r3)<15 && λ_h<0.8
- → λ_h = max(λ_h, 0.75), λ_a = min(λ_a, max(λ_h×1.8, 1.2))
- Case: 查路#11 vs 格尼斯坦#5 (both c1&r3=0) → 1-1 draw ✅

### Layer 7: 弱主买
- rank_h>rank_a && fd≥2 && c1≥20 && o1<2.5
- → λ_h × 1.10

### Layer 8: 极端买主
- c1≥40 && o1<2.5 → λ_h × 1.12
- Case: VPS瓦萨(c1=47) → 5-0/5-1 ✅

### Layer 9: 市场分歧均衡
- fd≤2 && c1≥20 && r3≥20 → λ_h=λ_a=(λ_h+λ_a)/2

### Layer 10: 排名优但λ倒挂 ⭐
- rank_h<rank_a (home better ranked) && λ_a>λ_h && (λ_h+λ_a)≥3.0
- → avg=(λ_h+λ_a)/2, λ_h=avg×1.05, λ_a=avg×0.95
- Case: 古比斯#3(#7FIFA?) vs 埃尔维斯#8 — NB/泊松λ逆转为客队高 → 4-3入Top2 ✅

## Key Architecture Decisions

1. **Poisson > Negative Binomial**: NB overdisperses (theta=1.5 gives P(X=0|λ=2.59)=22% vs Poisson 7.5%). Football variance ~1.1-1.3× mean, not 2-3×.

2. **Market signals always win over historical stats**: When the market shows consensus (c1≥30 or r3≥30), it's more predictive than 10-game averages.

3. **Asymmetric boosts**: Home advantage in corrections is real. Same conditions produce different λ adjustments for home vs away.

4. **Silent market is dangerous**: When c1+r3=0 (no market opinion), the historical model over-relies on small samples. The home underdog must be protected with a floor λ.
