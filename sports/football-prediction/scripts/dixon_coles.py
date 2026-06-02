"""
Dixon-Coles修正 + 指数衰减加权 + ELO评级 + Bayesian层次收缩
基于五大业界高分模型 + 3个实战开源模型方法论
"""

import math
from typing import Tuple, Optional


# ═══════════════════════════════════════════════
# 1. Dixon-Coles τ因子修正 (1997)
# 修正Poisson在低比分区域的系统性偏差
# ═══════════════════════════════════════════════

LEAGUE_RHO = {
    '日职联': -0.10, '日职': -0.10,
    '英超': -0.08,
    '西甲': -0.07, '意甲': -0.07, '法甲': -0.07,
    '德甲': -0.05,
    '瑞超': -0.09, '瑞典超': -0.09,
    '芬超': -0.08,
    '澳超': -0.06,
    '美职联': -0.06, '美职': -0.06,
}

def get_rho(league: str) -> float:
    """获取联赛Dixon-Coles修正系数"""
    for key, val in LEAGUE_RHO.items():
        if key in league:
            return val
    return -0.07  # 默认


def dc_tau_factor(x: int, y: int, lambda_h: float, lambda_a: float, rho: float) -> float:
    """
    Dixon-Coles τ修正因子
    仅修正 0-0, 1-0, 0-1, 1-1 四个低比分
    
    Args:
        x, y: 预测的主/客进球数
        lambda_h, lambda_a: 主/客预期进球
        rho: 联赛修正系数
    
    Returns:
        τ因子 (1.0 = 无修正, >1 = 概率提升, <1 = 概率降低)
    """
    if x == 0 and y == 0:
        return 1.0 - lambda_h * lambda_a * rho
    elif x == 0 and y == 1:
        return 1.0 + lambda_h * rho
    elif x == 1 and y == 0:
        return 1.0 + lambda_a * rho
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def poisson_pmf(k: int, lam: float) -> float:
    """Poisson概率质量函数"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def dc_score_prob(home_goals: int, away_goals: int,
                  lambda_h: float, lambda_a: float, league: str) -> float:
    """
    Dixon-Coles修正后的比分概率
    
    公式: P(x,y) = τ(x,y) × Poisson(x|λh) × Poisson(y|λa)
    """
    rho = get_rho(league)
    poisson_prob = poisson_pmf(home_goals, lambda_h) * poisson_pmf(away_goals, lambda_a)
    tau = dc_tau_factor(home_goals, away_goals, lambda_h, lambda_a, rho)
    return poisson_prob * tau


# ═══════════════════════════════════════════════
# 2. 指数衰减加权 (替代固定40/30/30)
# ═══════════════════════════════════════════════

def exp_decay_weights(matches_ago: int, half_life: int = 8) -> float:
    """
    指数衰减权重
    
    Args:
        matches_ago: 距今多少场 (1=最近一场)
        half_life: 半衰期(场数), 默认8场后权重减半
    
    Returns:
        权重系数
    """
    decay = math.log(2) / half_life
    return math.exp(-decay * (matches_ago - 1))


def weighted_lambda(recent_goals: list, season_avg: float,
                    half_life: int = 8) -> float:
    """
    指数衰减加权预期进球
    
    Args:
        recent_goals: 最近N场进球数列表 [最新, ..., 最旧]
        season_avg: 赛季场均进球
    
    Returns:
        加权后的预期进球 λ
    """
    if not recent_goals:
        return season_avg
    
    total_weight = 0.0
    weighted_sum = 0.0
    
    for i, goals in enumerate(recent_goals):
        w = exp_decay_weights(i + 1, half_life)
        weighted_sum += goals * w
        total_weight += w
    
    if total_weight == 0:
        return season_avg
    
    # 混合: 近期加权 + 赛季基准(10%)
    recent_avg = weighted_sum / total_weight
    return recent_avg * 0.90 + season_avg * 0.10


# ═══════════════════════════════════════════════
# 3. ELO评级模型
# ═══════════════════════════════════════════════

def elo_expected(home_elo: float, away_elo: float, hfa: float = 100) -> float:
    """ELO预期胜率"""
    return 1.0 / (1.0 + 10 ** ((away_elo - home_elo - hfa) / 400))


def elo_update(old_elo: float, expected: float, result: float, k: float = 20) -> float:
    """ELO评级更新"""
    return old_elo + k * (result - expected)


def elo_to_goal_ratio(home_elo: float, away_elo: float) -> Tuple[float, float]:
    """
    ELO差 → 预期进球比率
    每100ELO差 ≈ 0.35球优势
    """
    diff = home_elo - away_elo
    goal_advantage = diff * 0.0035  # 每100ELO = 0.35球
    base_rate = 1.30  # 联赛均值
    return max(0.3, base_rate + goal_advantage), max(0.3, base_rate - goal_advantage)


# ═══════════════════════════════════════════════
# 4. 综合: Dixon-Coles增强版比分预测
# ═══════════════════════════════════════════════

def predict_match_scores(lambda_h: float, lambda_a: float, league: str = '',
                         max_goals: int = 5) -> dict:
    """
    使用Dixon-Coles修正生成完整比分概率分布
    
    Returns:
        {score_probs: {score: prob}, win_prob, draw_prob, loss_prob,
         top_scores: [(score, prob)]}
    """
    results = {}
    total_prob = 0.0
    
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = dc_score_prob(h, a, lambda_h, lambda_a, league)
            results[f"{h}-{a}"] = prob
            total_prob += prob
    
    # 归一化
    for k in results:
        results[k] /= total_prob
    
    # 胜平负概率
    win_prob = sum(p for s, p in results.items() 
                   if int(s.split('-')[0]) > int(s.split('-')[1]))
    draw_prob = sum(p for s, p in results.items() 
                    if int(s.split('-')[0]) == int(s.split('-')[1]))
    loss_prob = 1.0 - win_prob - draw_prob
    
    # Top 4 比分
    sorted_scores = sorted(results.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'score_probs': results,
        'win_prob': win_prob,
        'draw_prob': draw_prob,
        'loss_prob': loss_prob,
        'top_scores': sorted_scores[:4],
        'lambda_h': lambda_h,
        'lambda_a': lambda_a,
    }


# ═══════════════════════════════════════════════
# 5. Bayesian层次收缩模型
# 基于 xzhangfox/Football-Prediction-by-Bayesian-Method (80%准确率)
# 核心: 小样本向联赛均值收缩, 防过拟合
# ═══════════════════════════════════════════════

# 联赛基准: (场均进球, 先验权重)
# 权重表示"等同于多少场比赛的观察量"
LEAGUE_PRIORS = {
    '日职联': (1.35, 8), '日职': (1.35, 8),
    '英超': (1.45, 10),
    '西甲': (1.30, 10),
    '意甲': (1.30, 10),
    '德甲': (1.50, 10),
    '法甲': (1.30, 10),
    '瑞超': (1.35, 6), '瑞典超': (1.35, 6),
    '芬超': (1.25, 5),
    '澳超': (1.30, 6),
    '美职联': (1.40, 8), '美职': (1.40, 8),
    '荷乙': (1.45, 6),
    '英冠': (1.20, 8),
    '沙职': (1.30, 5),
}


def get_league_prior(league: str) -> Tuple[float, float]:
    """获取联赛先验: (场均进球, 先验权重)"""
    for key, val in LEAGUE_PRIORS.items():
        if key in league:
            return val
    return (1.35, 5)  # 默认


def bayesian_shrink(observed_mean: float, n_games: int, league: str,
                    observed_sigma: float = 0.8) -> Tuple[float, float]:
    """
    Bayesian层次收缩: 向联赛均值回归
    
    后验均值 = (先验精度 × 先验均值 + 似然精度 × 观察均值) / (先验精度 + 似然精度)
    
    Args:
        observed_mean: 球队实际场均进球
        n_games: 已观察比赛场数
        league: 联赛名
        observed_sigma: 观察标准差(默认0.8)
    
    Returns:
        (收缩后的均值, 后验标准差)
    """
    prior_mean, prior_weight = get_league_prior(league)
    
    # 先验精度: 权重大→精度高→收缩强
    prior_precision = prior_weight / (observed_sigma ** 2)
    # 似然精度: 比赛多→精度高→收缩弱
    likelihood_precision = n_games / (observed_sigma ** 2)
    
    # 后验均值 = 加权平均
    total_precision = prior_precision + likelihood_precision
    posterior_mean = (prior_precision * prior_mean + 
                      likelihood_precision * observed_mean) / total_precision
    
    # 后验标准差
    posterior_sigma = math.sqrt(1.0 / total_precision)
    
    return posterior_mean, posterior_sigma


def bayesian_lambda(observed_goals_per_game: float, n_games: int, league: str,
                    base_lambda: Optional[float] = None) -> Tuple[float, dict]:
    """
    Bayesian修正后的预期进球λ
    
    结合: 观察数据 + 联赛先验 + 已有模型λ(如果提供)
    
    Returns:
        (修正后的λ, 诊断信息)
    """
    posterior_mean, posterior_sigma = bayesian_shrink(
        observed_goals_per_game, n_games, league
    )
    
    # 如果已有模型λ(如Poisson计算的结果), 再次融合
    if base_lambda is not None:
        # 加权: 后验75% + 模型25%
        final_lambda = posterior_mean * 0.75 + base_lambda * 0.25
    else:
        final_lambda = posterior_mean
    
    # 收缩率: 越小=越接近先验(越保守)
    prior_mean, _ = get_league_prior(league)
    shrinkage_pct = abs(final_lambda - observed_goals_per_game) / max(abs(observed_goals_per_game - prior_mean), 0.01)
    shrinkage_pct = min(shrinkage_pct, 1.0)
    
    return final_lambda, {
        'observed': observed_goals_per_game,
        'prior_mean': prior_mean,
        'posterior_mean': posterior_mean,
        'final_lambda': final_lambda,
        'shrinkage': shrinkage_pct,
        'confidence_68': (final_lambda - posterior_sigma, final_lambda + posterior_sigma),
        'confidence_95': (final_lambda - 2*posterior_sigma, final_lambda + 2*posterior_sigma),
        'n_games': n_games,
    }


def get_confidence_interval(lambda_val: float, n_games: int, league: str,
                            level: float = 0.68) -> Tuple[float, float]:
    """
    获取预测进球置信区间
    
    Args:
        lambda_val: 预期进球
        n_games: 已观察场数
        league: 联赛
        level: 置信水平 (0.68=1σ, 0.95=2σ)
    
    Returns:
        (下界, 上界)
    """
    prior_mean, prior_weight = get_league_prior(league)
    precision = prior_weight + n_games
    sigma = math.sqrt(1.0 / precision) if precision > 0 else 0.5
    
    if level >= 0.95:
        z = 2.0
    elif level >= 0.90:
        z = 1.645
    else:
        z = 1.0
    
    return (lambda_val - z * sigma, lambda_val + z * sigma)


# ═══════════════════════════════════════════════
# 6. 等级战绩 xG/xGA 代理（基于59itou数据）
# 利用对阵强队/弱队的实际进球表现平滑噪声，
# 近似xG效果
# ═══════════════════════════════════════════════

GRADE_WEIGHTS = {
    'attack': {'season': 0.50, 'vs_strong': 0.20, 'vs_weak': 0.30},
    'defense': {'season': 0.50, 'vs_strong': 0.30, 'vs_weak': 0.20},
}


def grade_xg_proxy(
    season_gf: float,         # 赛季场均进球
    season_ga: float,         # 赛季场均失球
    vs_strong_gf: float = None,  # 对阵强队场均进球
    vs_strong_ga: float = None,  # 对阵强队场均失球
    vs_weak_gf: float = None,    # 对阵弱队场均进球
    vs_weak_ga: float = None,    # 对阵弱队场均失球
    n_games_strong: int = 0,     # 对阵强队场数
    n_games_weak: int = 0,       # 对阵弱队场数
) -> dict:
    """
    等级战绩xG代理计算
    
    用"对阵强队/弱队"的实际进球表现来平滑赛季均值，
    近似xG的"预期进球"效果。
    
    原理：
    - 对阵强队进球多 → 硬仗能力强 → λ上修
    - 对阵弱队进球多 → 虐菜稳定 → λ略上修
    - 对阵强队失球多 → 防线抗压差 → λ_concede上修
    
    当等级战绩数据不完整时，降级回纯赛季均值。
    
    Returns:
        {
            'lambda_attack': float,      # xG代理进攻λ
            'lambda_defense': float,     # xGA代理防守λ
            'shrinkage_attack': float,   # 进攻收缩量（绝对值差）
            'shrinkage_defense': float,  # 防守收缩量
            'diagnostics': dict          # 诊断信息
        }
    """
    # 默认值
    vs_strong_gf = vs_strong_gf or season_gf
    vs_strong_ga = vs_strong_ga or season_ga
    vs_weak_gf = vs_weak_gf or season_gf
    vs_weak_ga = vs_weak_ga or season_ga
    
    # 可用性评分：0-1，越高代表等级战绩数据越可靠
    availability = min(1.0, (n_games_strong + n_games_weak) / 20)
    
    if availability < 0.3:
        # 样本太少，纯用赛季均值
        lambda_attack = season_gf
        lambda_defense = season_ga
        mode = 'fallback_season_only'
    else:
        # 混合: 赛季均值 + 等级战绩
        w = GRADE_WEIGHTS
        lambda_attack = (
            season_gf * w['attack']['season'] +
            vs_strong_gf * w['attack']['vs_strong'] +
            vs_weak_gf * w['attack']['vs_weak']
        )
        lambda_defense = (
            season_ga * w['defense']['season'] +
            vs_strong_ga * w['defense']['vs_strong'] +
            vs_weak_ga * w['defense']['vs_weak']
        )
        
        # 按可用性缩放到赛季均值附近（防极端值）
        max_deviation = 0.30  # 最大偏离赛季均值30%
        lambda_attack = _clamp_to_season(lambda_attack, season_gf, max_deviation)
        lambda_defense = _clamp_to_season(lambda_defense, season_ga, max_deviation)
        mode = f'blended_availability_{availability:.2f}'
    
    return {
        'lambda_attack': round(lambda_attack, 4),
        'lambda_defense': round(lambda_defense, 4),
        'shrinkage_attack': round(lambda_attack - season_gf, 4),
        'shrinkage_defense': round(lambda_defense - season_ga, 4),
        'diagnostics': {
            'mode': mode,
            'availability': availability,
            'season_gf': season_gf,
            'vs_strong_gf': vs_strong_gf,
            'vs_weak_gf': vs_weak_gf,
            'n_games_strong': n_games_strong,
            'n_games_weak': n_games_weak,
        }
    }


def _clamp_to_season(value: float, season_avg: float, max_dev_pct: float = 0.30) -> float:
    """将值限制在赛季均值的±max_dev_pct范围内"""
    lower = season_avg * (1 - max_dev_pct)
    upper = season_avg * (1 + max_dev_pct)
    return max(lower, min(value, upper))


# ═══════════════════════════════════════════════
# 7. 比赛级λ计算（攻击×防守交叉乘积）
# 标准泊松公式：λ₁ = 主队进攻λ × 客队防守λ / 联赛平均
# 这是所有模型计算的最终入口——必须用此函数生成 match-level λ
# ═══════════════════════════════════════════════

def compute_match_lambdas(
    attack_home: float,   # 主队进攻λ（经贝叶斯/xG代理等修正后）
    defense_home: float,  # 主队防守λ
    attack_away: float,   # 客队进攻λ
    defense_away: float,  # 客队防守λ
    league_avg: float = 1.35,  # 联赛平均预期进球
) -> dict:
    """
    将球队独立的进攻/防守λ转换为比赛级λ。

    标准泊松模型:
        λ₁ (主队预期进球) = attack_home × defense_away / league_avg
        λ₂ (客队预期进球) = attack_away × defense_home / league_avg

    含义:
        - 主队能否进球 = 主队进攻能力 × 客队防守脆弱程度 / 联赛基准
        - 客队能否进球 = 客队进攻能力 × 主队防守脆弱程度 / 联赛基准

    Args:
        attack_home: 主队进攻λ
        defense_home: 主队防守λ (每场预期失球)
        attack_away: 客队进攻λ
        defense_away: 客队防守λ
        league_avg: 联赛平均预期进球 (用于归一化)

    Returns:
        {
            'lambda_home': float,    # λ₁ — 主队90min预期进球
            'lambda_away': float,    # λ₂ — 客队90min预期进球
            'lambda_diff': float,    # λ差 (绝对值)
            'balance': str,          # 'home'|'away'|'balanced'
            'home_attack_factor': float,   # 主队进攻相对联赛倍数
            'away_defense_factor': float,  # 客队防守相对联赛倍数
        }
    """
    if league_avg <= 0:
        league_avg = 1.35

    lambda_home = attack_home * defense_away / league_avg
    lambda_away = attack_away * defense_home / league_avg

    diff = abs(lambda_home - lambda_away)

    if diff < 0.15:
        balance = 'balanced'
    elif lambda_home > lambda_away:
        balance = 'home'
    else:
        balance = 'away'

    return {
        'lambda_home': round(lambda_home, 4),
        'lambda_away': round(lambda_away, 4),
        'lambda_diff': round(diff, 4),
        'balance': balance,
        'home_attack_factor': round(attack_home / league_avg, 4),
        'away_defense_factor': round(defense_away / league_avg, 4),
    }


# ═══════════════════════════════════════════════
# 8. 完整λ计算管线（端到端）
# 整合：指数衰减 → 等级战绩xG代理 → 因子修正 → 贝叶斯收缩 → 交叉乘积 → DC比分
# ═══════════════════════════════════════════════

def full_lambda_pipeline(
    # 指数衰减输入
    recent_goals_for: list,     # 近N场进球 [最近,...,最旧]
    recent_goals_against: list, # 近N场失球 [最近,...,最旧]
    season_avg_for: float,      # 赛季场均进球
    season_avg_against: float,  # 赛季场均失球
    # 等级战绩输入（可选）
    vs_strong_gf: float = None,
    vs_strong_ga: float = None,
    vs_weak_gf: float = None,
    vs_weak_ga: float = None,
    n_strong: int = 0,
    n_weak: int = 0,
    # 参数
    league: str = '',
    half_life: int = 8,
    n_games_season: int = 10,
    # 修正系数
    home_advantage: float = 1.0,  # 主场加成（如1.12）
    is_friendly: bool = False,
    # 比赛级λ参数
    league_avg: float = None,  # 联赛均进球，None则从先验自动获取
) -> dict:
    """
    端到端λ计算管线
    
    Step 1: 指数衰减加权
    Step 2: 等级战绩xG代理修正
    Step 3: 贝叶斯层次收缩
    Step 4: 特殊因子修正（主场加成/友谊赛）
    Step 5: 攻击×防守交叉乘积 → 比赛级λ
    """
    # Step 1: 指数衰减加权
    lambda_exp_for = weighted_lambda(recent_goals_for, season_avg_for, half_life)
    lambda_exp_against = weighted_lambda(recent_goals_against, season_avg_against, half_life)
    
    # Step 2: 等级战绩xG代理
    xg_result = grade_xg_proxy(
        season_gf=lambda_exp_for,
        season_ga=lambda_exp_against,
        vs_strong_gf=vs_strong_gf,
        vs_strong_ga=vs_strong_ga,
        vs_weak_gf=vs_weak_gf,
        vs_weak_ga=vs_weak_ga,
        n_games_strong=n_strong,
        n_games_weak=n_weak,
    )
    lambda_xg_for = xg_result['lambda_attack']
    lambda_xg_against = xg_result['lambda_defense']
    
    # Step 3: 贝叶斯层次收缩（分别收缩进攻λ和防守λ）
    lambda_bayes_for, diag_for = bayesian_lambda(
        lambda_xg_for, n_games_season, league
    )
    lambda_bayes_against, diag_against = bayesian_lambda(
        lambda_xg_against, n_games_season, league
    )
    
    # Step 4: 主场加成（仅作用于模型λ，不含市场λ）
    # 进攻受益: ×home_advantage
    # 防守受益: ×(2-home_advantage)（主场防守也更强，失球减少）
    if home_advantage != 1.0:
        lambda_bayes_for *= home_advantage
        lambda_bayes_against *= (2 - home_advantage)
    
    # Step 4b: 友谊赛收兵
    if is_friendly:
        lambda_bayes_for *= 0.85
        lambda_bayes_against *= 0.85
    
    # Step 5: 攻击×防守交叉乘积 → 比赛级λ
    # 注意：lambda_bayes_for = 主队进攻λ，lambda_bayes_against = 客队防守λ
    # 但主队防守λ和客队进攻λ需要在外部传入
    # 这里用自身防守λ作为防守方——对外部调用者需要传入客队防守λ
    # 正确做法：主队用自己进攻λ和对方防守λ
    # 但本函数设计为单队管线，因此match_lambdas由外部调用compute_match_lambdas完成
    # 此处仅输出修正后的进攻λ和防守λ供外部组合
    
    # 自动获取联赛均进球
    if league_avg is None:
        league_avg, _ = get_league_prior(league)
    
    return {
        # 队内独立λ（进攻/防守分离）
        'attack_lambda': round(lambda_bayes_for, 4),     # ⚠️ 本队进攻λ（非比赛级）
        'defense_lambda': round(lambda_bayes_against, 4), # ⚠️ 本队防守λ（非比赛级）
        # 向后兼容键（标记为deprecated）
        'lambda_home': round(lambda_bayes_for, 4),
        'lambda_away': round(lambda_bayes_against, 4),
        # 联赛基准
        'league_avg': league_avg,
        'pipeline_steps': {
            'step1_exp_decay': (round(lambda_exp_for, 4), round(lambda_exp_against, 4)),
            'step2_grade_xg': (round(lambda_xg_for, 4), round(lambda_xg_against, 4)),
            'step3_bayesian': (round(lambda_bayes_for, 4), round(lambda_bayes_against, 4)),
            'step4_home_adj': home_advantage,
            'step4b_friendly': is_friendly,
        },
        'diagnostics': {
            'attack': diag_for,
            'defense': diag_against,
            'xg_proxy': xg_result['diagnostics'],
        }
    }
