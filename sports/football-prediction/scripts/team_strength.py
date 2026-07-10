#!/usr/bin/env python3
"""
队伍实力对比系统 v1.1 (2026-06-21)
综合: FIFA排名 + 59itou综合实力 + 球员总身价 + 近期状态(指数衰减加权) + 球员评分 + 伤停
输出: 实力分(0-100), 实力差, 更强方, 进球修正建议

v1.1 时效性衰减改进:
  - 新增 exp_decay_weights(): 按半衰期生成指数衰减权重
  - compute_team_strength() 新增 match_dates 参数支持日期加权
  - 新增 get_recent_weighted_form(): 按时间衰减计算加权状态评分
  - 近期状态得分从简单平均改为指数衰减加权平均

用法:
  from team_strength import compute_team_strength, apply_strength_to_prediction
  strength = compute_team_strength(fh=8, fa=34, gap_59itou=26, squad_values={'h':6.5,'a':2.5})
  h, a, reason = apply_strength_to_prediction(2, 0, strength, 'home')
"""

import math
from datetime import datetime, date

# 世界杯32强总身价（亿€, 2026年数据）
# 数据来源: Transfermarkt (公开数据, 非实时API)
SQUAD_VALUES = {
    '巴西': 12.0, '英格兰': 11.0, '法国': 10.0, '德国': 8.5,
    '西班牙': 8.0, '葡萄牙': 7.5, '荷兰': 6.5, '意大利': 6.0,
    '阿根廷': 5.5, '比利时': 4.5, '美国': 3.5, '日本': 2.8,
    '瑞士': 2.8, '瑞典': 2.5, '丹麦': 2.5, '乌拉圭': 2.2,
    '克罗地亚': 2.0, '科特迪瓦': 1.8, '奥地利': 1.8, '厄瓜多尔': 1.5,
    '澳大利亚': 1.5, '挪威': 1.5, '土耳其': 1.5, '苏格兰': 1.5,
    '波黑': 1.2, '捷克': 1.2, '沙特': 1.0, '波兰': 1.0, '韩国': 1.0,
    '摩洛哥': 0.9, '佛得角': 0.8, '卡塔尔': 0.8, '爱尔兰': 0.8,
    '以色列': 0.8, '伊朗': 0.7, '新西兰': 0.6, '阿尔及利亚': 0.6,
    '突尼斯': 0.5, '埃及': 0.5, '加纳': 0.4, '巴拉圭': 0.4,
    '芬兰': 0.4, '伊拉克': 0.3, '约旦': 0.3, '乌兹别克': 0.3,
    '塞内加尔': 0.3, '南非': 0.3, '民主刚果': 0.2, '加拿大': 0.2,
    '巴拿马': 0.2, '库拉索': 0.1, '海地': 0.05,
}


def exp_decay_weights(half_life=7, num_matches=10):
    """
    生成指数衰减权重数组，越近的比赛权重越高。

    参数:
        half_life: 半衰期（天），默认7天。7天前的比赛权重减半，14天前再减半。
        num_matches: 比赛场次数，默认10。

    返回:
        list[float]: 长度为 num_matches 的权重数组，
                      索引0（最近一场）权重最高，索引-1（最远一场）权重最低。
                      权重自动归一化使得 sum(weights) = 1.0。
    """
    if num_matches <= 0:
        return []
    # 天数差数组：最近一场0天前，第二近half_life天前，依次类推
    days_diff = [i * half_life for i in range(num_matches)]
    raw_weights = [0.5 ** (d / half_life) for d in days_diff]
    total = sum(raw_weights)
    if total == 0:
        return [1.0 / num_matches] * num_matches
    return [w / total for w in raw_weights]


def compute_team_strength(fh, fa, gap_59itou=None, ratings=None, forms=None, injuries=None,
                          squad_values=None, h_name='', a_name='',
                          match_dates=None, half_life=7):
    """
    综合实力评分 (v1.1 时效性衰减改进)

    参数:
        fh, fa: 主客FIFA排名 (1-210)
        gap_59itou: 59itou综合实力差 (主-客, 范围-100~100)
        ratings: dict {h:x, a:x} 球员评分
        forms: dict {h_w:x, a_w:x} 近10场胜场
        injuries: dict {h:x, a:x} 伤停人数
        squad_values: dict {h_name:x, a_name:x} 两队身价(亿€)，不传则从对照表取
        h_name, a_name: 队名，用作身价查询的备选
        match_dates: list[str], 按时间倒序的比赛日期列表（最近一场在前），
                     有值时对近期状态应用指数衰减加权，为空时回退简单平均。
        half_life: 半衰期天数（默认7天），用于指数衰减权重计算。

    返回:
        dict: 实力评分详情
    """
    # 1. FIFA排名分 (排名越低越强)
    fifa_score_h = max(0, 100 - (fh - 1) * 0.5)
    fifa_score_a = max(0, 100 - (fa - 1) * 0.5)

    # 2. 59itou综合实力分
    if gap_59itou is not None:
        base = 50
        s59_h = min(100, max(0, base + gap_59itou / 2))
        s59_a = min(100, max(0, base - gap_59itou / 2))
    else:
        s59_h = fifa_score_h
        s59_a = fifa_score_a

    # 3. 球员评分 (7.0=50分基准)
    if ratings:
        rh = ratings.get('h', 7.0)
        ra = ratings.get('a', 7.0)
        rating_h = 50 + (rh - 7.0) * 50
        rating_a = 50 + (ra - 7.0) * 50
    else:
        rating_h = 50
        rating_a = 50

    # 4. 近期状态 (近10场胜率，支持指数衰减加权)
    if forms:
        fw_h = forms.get('h_w', 5)
        fw_a = forms.get('a_w', 5)
        if match_dates and len(match_dates) > 0:
            # 指数衰减加权计算
            num_m = len(match_dates)
            weights = exp_decay_weights(half_life=half_life, num_matches=num_m)
            weighted_wins_h = sum((1.0 if i < fw_h else 0.0) * weights[i] for i in range(num_m))
            weighted_wins_a = sum((1.0 if i < fw_a else 0.0) * weights[i] for i in range(num_m))
            weighted_win_rate_h = weighted_wins_h / max(sum(weights), 0.001)
            weighted_win_rate_a = weighted_wins_a / max(sum(weights), 0.001)
            form_h = weighted_win_rate_h * 100
            form_a = weighted_win_rate_a * 100
        else:
            # 简单平均（原有逻辑）
            form_h = fw_h * 10
            form_a = fw_a * 10
    else:
        form_h = 50
        form_a = 50

    # 5. 身价（优先传入值，否则从对照表取）
    if squad_values:
        sv_h = squad_values.get('h', 1.0)
        sv_a = squad_values.get('a', 1.0)
    else:
        sv_h = SQUAD_VALUES.get(h_name, 1.0)
        sv_a = SQUAD_VALUES.get(a_name, 1.0)
    if sv_h <= 0: sv_h = 1.0
    if sv_a <= 0: sv_a = 1.0

    # 对数缩放: 10亿€→100分, 1亿€→50分, 0.1亿€→20分
    value_score_h = 50 + math.log2(max(0.1, sv_h)) * 15
    value_score_a = 50 + math.log2(max(0.1, sv_a)) * 15
    value_score_h = max(0, min(100, value_score_h))
    value_score_a = max(0, min(100, value_score_a))

    # 6. 伤停惩罚 (每1个核心伤停-3分)
    injury_penalty_h = 0
    injury_penalty_a = 0
    if injuries:
        injury_penalty_h = injuries.get('h', 0) * 3
        injury_penalty_a = injuries.get('a', 0) * 3

    # 加权综合
    weights = {'fifa': 0.30, 'strength_59': 0.25, 'rating': 0.10, 'form': 0.15, 'value': 0.20}

    total_h = (fifa_score_h * weights['fifa'] +
               s59_h * weights['strength_59'] +
               rating_h * weights['rating'] +
               form_h * weights['form'] +
               value_score_h * weights['value'] -
               injury_penalty_h)

    total_a = (fifa_score_a * weights['fifa'] +
               s59_a * weights['strength_59'] +
               rating_a * weights['rating'] +
               form_a * weights['form'] +
               value_score_a * weights['value'] -
               injury_penalty_a)

    gap = round(total_h - total_a, 1)

    # 判定等级与进球修正
    if gap >= 25:
        level = '碾压'
        goal_adj = 2
    elif gap >= 8:
        level = '明显优势'
        goal_adj = 1
    elif gap >= 3:
        level = '小幅优势'
        goal_adj = 0
    elif gap >= -3:
        level = '接近'
        goal_adj = 0
    elif gap >= -8:
        level = '小幅劣势'
        goal_adj = 0
    elif gap >= -25:
        level = '明显劣势'
        goal_adj = -1
    else:
        level = '被碾压'
        goal_adj = -2

    return {
        'home_total': round(total_h, 1),
        'away_total': round(total_a, 1),
        'gap': gap,
        'stronger': 'home' if total_h > total_a else 'away',
        'level': level,
        'goal_adjustment': goal_adj,
        'breakdown': {
            'fifa': {'h': round(fifa_score_h, 1), 'a': round(fifa_score_a, 1)},
            'strength_59': {'h': round(s59_h, 1), 'a': round(s59_a, 1)},
            'rating': {'h': round(rating_h, 1), 'a': round(rating_a, 1)},
            'form': {'h': round(form_h, 1), 'a': round(form_a, 1)},
            'value': {'h': round(value_score_h, 1), 'a': round(value_score_a, 1)},
            'injury_penalty': {'h': injury_penalty_h, 'a': injury_penalty_a}
        }
    }


def apply_strength_to_prediction(h_pred, a_pred, strength):
    """
    用实力对比修正预测比分

    参数:
        h_pred, a_pred: 引擎原始预测
        strength: compute_team_strength()返回值
    返回:
        (h_mod, a_mod, reason)
    """
    if strength['goal_adjustment'] == 0:
        return h_pred, a_pred, '无修正'

    adj = strength['goal_adjustment']
    stronger = strength['stronger']

    if stronger == 'home':
        h_pred = min(7, max(0, h_pred + adj))
        return h_pred, a_pred, f'实力{strength["level"]}:主+{adj}'
    else:
        a_pred = min(7, max(0, a_pred + adj))
        return h_pred, a_pred, f'实力{strength["level"]}:客+{adj}'


def get_recent_weighted_form(team_name, match_history, half_life=7):
    """
    对传入的比赛历史记录按日期指数衰减，输出加权状态评分(0-100)。

    参数:
        team_name: 队名（仅用于日志/调试）
        match_history: list[dict], 每场比赛包含:
            - 'date': str, 日期 'YYYY-MM-DD'
            - 'result': str, 'W'/'D'/'L' 或 '胜'/'平'/'负'
            - 'opponent': str (可选)
        half_life: 半衰期天数，默认7天

    返回:
        float: 加权状态评分 0-100
               (加权胜率 × 100)
    """
    if not match_history:
        return 50.0

    today = date.today()
    total_weight = 0.0
    weighted_wins = 0.0

    for match in match_history:
        d_str = match.get('date', '')
        try:
            match_date = datetime.strptime(d_str, '%Y-%m-%d').date()
            days_ago = max(0, (today - match_date).days)
        except (ValueError, TypeError):
            days_ago = 7  # 默认7天前

        weight = 0.5 ** (days_ago / half_life)
        total_weight += weight

        result = match.get('result', '')
        if result in ('W', '胜'):
            weighted_wins += weight * 1.0
        elif result in ('D', '平'):
            weighted_wins += weight * 0.5  # 平局算0.5胜

    if total_weight == 0:
        return 50.0

    weighted_win_rate = weighted_wins / total_weight
    return round(min(100.0, max(0.0, weighted_win_rate * 100)), 1)


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 5:
        h_name, a_name = sys.argv[1], sys.argv[2]
        fh, fa = int(sys.argv[3]), int(sys.argv[4])
        s = compute_team_strength(fh=fh, fa=fa, h_name=h_name, a_name=a_name)
        print(f'{h_name} vs {a_name}')
        print(f'  身价: {s["breakdown"]["value"]["h"]:.0f} vs {s["breakdown"]["value"]["a"]:.0f} (分)')
        print(f'  总实力分: {s["home_total"]} vs {s["away_total"]}')
        print(f'  实力差: {s["gap"]} ({s["level"]})')
        print(f'  更强方: {s["stronger"]}')
        print(f'  进球修正: {s["goal_adjustment"]}')
