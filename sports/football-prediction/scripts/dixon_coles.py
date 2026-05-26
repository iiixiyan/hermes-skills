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
