# 联赛模式预测流程

## 完整管线

```python
from league_predict import fetch_league_results, compute_team_stats
all_matches = fetch_league_results('芬超')
h_stats = compute_team_stats(all_matches, '赫尔辛基')
a_stats = compute_team_stats(all_matches, '玛丽港')

from dixon_coles import full_lambda_pipeline, compute_match_lambdas, predict_match_scores
pipe_h = full_lambda_pipeline(
    recent_goals_for=h_stats['recent_gf'],
    recent_goals_against=h_stats['recent_ga'],
    season_avg_for=h_stats['avg_gf'],
    season_avg_against=h_stats['avg_ga'],
    league='芬超', half_life=8, n_games_season=9,
)
ml = compute_match_lambdas(
    attack_home=pipe_h['attack_lambda'],
    defense_home=pipe_h['defense_lambda'],
    attack_away=pipe_a['attack_lambda'],
    defense_away=pipe_a['defense_lambda'],
    league_avg=1.25,
)
result = predict_match_scores(ml['lambda_home'], ml['lambda_away'], league='芬超')
```

## 一键预测

```python
from league_predict import predict_league_match
r = predict_league_match('拉赫蒂', 'TP图尔库')
print(f'{r["home"]}vs{r["away"]}: λ₁={r["lambda_h"]:.3f} λ₂={r["lambda_a"]:.3f}')
for s, p in r['top_scores'][:3]:
    print(f'  {s}: {p:.1%}')
```

## 发动机核心升级

| 修正层 | 规则 | 数据源 |
|:-------|:-----|:-------|
| ① 欧赔市场信号 | 买主/买客(λ×1.10~1.15)、排名确认(λ×1.05)、排名矛盾跟市场(主+15%) | 新浪API footballMatchOddsEuro |
| ② 大小球校准 | Over/Under赔率校准总进球期望(大球Over@<1.85→λ+15~25%) | 新浪API footballMatchOddsAsia |
| ③ 双攻击型大比分 | 双方avg_gf≥1.5时λ×1.10~1.25(含排名主场优加权) | 历史数据 |
| ④ 极攻扩展 | 总进球期望≥5时额外λ×1.10 | 综合 |
| ⑤ 主场狗防守 | 弱主vs强客+市场买客→λ客受限(≤主λ×2.0) | 排名+欧赔 |
| ⑥ 沉默市场主场狗 | 无市场信号+排名差大+主λ<0.8→主队死守至少0.75球 | 综合 |
| ⑦ 弱主买 | 弱主+市场买主(c1≥20)→λ主×1.10 | 欧赔 |
| ⑧ 极端买主 | c1≥40→λ主×1.12 | 欧赔 |
| ⑨ 市场分歧均衡 | c1+r3都高+排名差小→平局均衡λ | 欧赔+排名 |
| ⑩ 排名优但λ倒挂 | 排名好但交叉乘积使λ₂>λ₁→主场优势补正 | 综合 |
| ⑪ **极端百家反转豁免造热(因子41)** | 主胜降幅≥35%+客胜升幅≥30%→真实市场重评估,豁免R6-BL造热处理,走主队方向 | 百家平均初赔vs即赔 |
