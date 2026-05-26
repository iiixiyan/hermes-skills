"""
特征工程模块 — 从59itou详情页innerText提取结构化特征
基于「特征工程比算法选择更重要」原则设计
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MatchFeatures:
    """一场比赛的结构化特征"""
    match_num: str = ""
    home_team: str = ""
    away_team: str = ""
    league: str = ""

    # === 阵容Tab特征 ===
    home_value: float = 0.0         # 身价(万€)
    away_value: float = 0.0
    home_avg_age: float = 0.0
    away_avg_age: float = 0.0
    home_avg_height: float = 0.0
    away_avg_height: float = 0.0
    home_shots_per_game: float = 0.0   # 场均射门
    away_shots_per_game: float = 0.0
    home_goals_per_game_20: float = 0.0  # 近20场场均进球
    away_goals_per_game_20: float = 0.0
    home_conceded_per_game_20: float = 0.0
    away_conceded_per_game_20: float = 0.0
    home_possession: float = 0.0    # 控球率%
    away_possession: float = 0.0
    home_forward_value: float = 0.0  # 前锋身价
    away_forward_value: float = 0.0
    home_midfield_value: float = 0.0
    away_midfield_value: float = 0.0
    home_defender_value: float = 0.0
    away_defender_value: float = 0.0

    # === 战绩Tab特征 ===
    home_wins_10: int = 0
    home_draws_10: int = 0
    home_losses_10: int = 0
    home_goals_10: int = 0
    home_conceded_10: int = 0
    away_wins_10: int = 0
    away_draws_10: int = 0
    away_losses_10: int = 0
    away_goals_10: int = 0
    away_conceded_10: int = 0
    home_home_wins_10: int = 0
    home_home_draws_10: int = 0
    home_home_losses_10: int = 0
    home_home_goals_10: int = 0
    home_home_conceded_10: int = 0
    away_away_wins_10: int = 0
    away_away_draws_10: int = 0
    away_away_losses_10: int = 0
    away_away_goals_10: int = 0
    away_away_conceded_10: int = 0
    # 近6场(需要从详细赛程提取, 暂无则用近10场近似)
    home_wins_6: int = 0
    home_goals_6: int = 0
    home_conceded_6: int = 0
    away_wins_6: int = 0
    away_goals_6: int = 0
    away_conceded_6: int = 0
    # H2H
    h2h_home_wins: int = 0
    h2h_home_draws: int = 0
    h2h_home_losses: int = 0

    # === 欧指Tab特征 ===
    home_odds_init: float = 0.0     # 百家平均初赔
    draw_odds_init: float = 0.0
    away_odds_init: float = 0.0
    home_odds_live: float = 0.0     # 百家平均即赔
    draw_odds_live: float = 0.0
    away_odds_live: float = 0.0
    home_odds_change: float = 0.0   # 赔率变化率 (即赔/初赔 - 1)
    draw_odds_change: float = 0.0
    away_odds_change: float = 0.0
    home_prob_live: float = 0.0     # 即赔转概率
    draw_prob_live: float = 0.0
    away_prob_live: float = 0.0
    home_rise_count: int = 0        # 升赔公司数
    home_fall_count: int = 0        # 降赔公司数
    draw_rise_count: int = 0
    draw_fall_count: int = 0
    away_rise_count: int = 0
    away_fall_count: int = 0
    # 离散度(升赔公司数/总公司数)
    home_dispersion: float = 0.0

    # === 亚指Tab特征 ===
    home_cover_rate: float = 0.0    # 赢盘率%
    away_cover_rate: float = 0.0
    up_disk_count: int = 0          # 升盘公司数
    down_disk_count: int = 0        # 降盘公司数
    high_water_count: int = 0       # 高水公司数
    low_water_count: int = 0        # 低水公司数

    # === 排名Tab特征 ===
    home_rank: int = 0
    away_rank: int = 0
    home_rank_diff: int = 0         # 排名差(客-主, 正=客排名更高)
    home_season_wins: int = 0
    home_season_draws: int = 0
    home_season_losses: int = 0
    away_season_wins: int = 0
    away_season_draws: int = 0
    away_season_losses: int = 0
    league_home_win_rate: float = 0.0  # 联赛主胜率

    # === 盈亏Tab特征 ===
    total_volume: float = 0.0       # 总交易量
    home_volume: float = 0.0
    draw_volume: float = 0.0
    away_volume: float = 0.0
    home_pnl: float = 0.0           # 庄家盈亏
    draw_pnl: float = 0.0
    away_pnl: float = 0.0
    home_hot_index: float = 0.0     # 冷热指数(正=热)
    draw_hot_index: float = 0.0
    away_hot_index: float = 0.0

    # === 衍生特征(自动计算) ===
    home_form_score: float = 0.0    # 近10场积分率(胜3平1)
    away_form_score: float = 0.0
    home_attack_power: float = 0.0  # 攻击力(近10场场均进球)
    away_attack_power: float = 0.0
    home_defense_strength: float = 0.0  # 防守力(近10场场均失球, 越低越好)
    away_defense_strength: float = 0.0
    value_ratio: float = 0.0        # 身价比(主/客)
    attack_diff: float = 0.0        # 攻击力差(主-客)
    defense_diff: float = 0.0       # 防守力差(客-主, 正=主防守更好)
    odds_prob_gap: float = 0.0      # 主胜概率-次高概率
    hot_diff: float = 0.0           # 热度差(主热-客热)
    factor_4b_triggered: bool = False  # 一致升赔信号
    factor_4b_direction: str = ""    # 升赔方向 (home/draw/away)
    factor_6_triggered: bool = False  # 排名倒挂
    factor_12_triggered: bool = False # 共识陷阱
    factor_13_triggered: bool = False # 双边极端分歧


def extract_features(tabs: dict, match_info: dict = None) -> MatchFeatures:
    """
    从各Tab的innerText中提取结构化特征
    
    Args:
        tabs: {tab_name: innerText} 字典
        match_info: {match_num, home_team, away_team, league} 
    """
    f = MatchFeatures()
    if match_info:
        for k, v in match_info.items():
            if hasattr(f, k):
                setattr(f, k, v)
    
    if '阵容' in tabs:
        _extract_lineup(tabs['阵容'], f)
    if '战绩' in tabs:
        _extract_form(tabs['战绩'], f)
    if '欧指' in tabs:
        _extract_odds(tabs['欧指'], f)
    if '亚指' in tabs:
        _extract_asian(tabs['亚指'], f)
    if '排名' in tabs:
        _extract_standings(tabs['排名'], f)
    if '盈亏' in tabs:
        _extract_pnl(tabs['盈亏'], f)
    
    # 计算衍生特征
    _compute_derived_features(f)
    
    return f


def _extract_lineup(text: str, f: MatchFeatures):
    """从阵容Tab提取特征"""
    # 身价
    vals = re.findall(r'(\d+\.?\d*)万?\s*\n?\s*身价€', text)
    if len(vals) >= 2:
        f.home_value = float(vals[0].replace(',', ''))
        f.away_value = float(vals[1].replace(',', ''))
    
    # 年龄
    ages = re.findall(r'(\d+)\s*岁\s*\n?\s*平均年龄', text)
    if len(ages) >= 2:
        f.home_avg_age = float(ages[0])
        f.away_avg_age = float(ages[1])
    
    # 身高
    heights = re.findall(r'(\d+)\s*cm\s*\n?\s*平均身高', text)
    if len(heights) >= 2:
        f.home_avg_height = float(heights[0])
        f.away_avg_height = float(heights[1])
    
    # 技术统计
    shots = re.findall(r'(\d+\.?\d*)\s*次\s*\n?\s*场均射门', text)
    if len(shots) >= 2:
        f.home_shots_per_game = float(shots[0])
        f.away_shots_per_game = float(shots[1])
    
    goals = re.findall(r'(\d+\.?\d*)\s*个\s*\n?\s*场均进球', text)
    if len(goals) >= 2:
        f.home_goals_per_game_20 = float(goals[0])
        f.away_goals_per_game_20 = float(goals[1])
    
    conceded = re.findall(r'(\d+\.?\d*)\s*个\s*\n?\s*场均失球', text)
    if len(conceded) >= 2:
        f.home_conceded_per_game_20 = float(conceded[0])
        f.away_conceded_per_game_20 = float(conceded[1])
    
    # 控球率
    poss = re.findall(r'(\d+\.?\d*)\s*%\s*\n?\s*场均控球率', text)
    if len(poss) >= 2:
        f.home_possession = float(poss[0])
        f.away_possession = float(poss[1])
    
    # 各位置身价
    fwd = re.findall(r'(\d+\.?\d*)万?\s*\n?\s*前锋', text)
    if len(fwd) >= 2:
        f.home_forward_value = float(fwd[0])
        f.away_forward_value = float(fwd[1])
    
    mid = re.findall(r'(\d+\.?\d*)万?\s*\n?\s*中场', text)
    if len(mid) >= 2:
        f.home_midfield_value = float(mid[0])
        f.away_midfield_value = float(mid[1])

    # Try defender too
    def_vals = re.findall(r'(\d+\.?\d*)万?\s*\n?\s*后卫', text)
    if len(def_vals) >= 2:
        f.home_defender_value = float(def_vals[0])
        f.away_defender_value = float(def_vals[1])


def _extract_form(text: str, f: MatchFeatures):
    """从战绩Tab提取特征"""
    # 主队近10场
    m = re.search(r'主队近10场(\d+)胜(\d+)平(\d+)负', text)
    if m:
        f.home_wins_10, f.home_draws_10, f.home_losses_10 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    
    # 客队近10场
    m = re.search(r'客队近10场(\d+)胜(\d+)平(\d+)负', text)
    if m:
        f.away_wins_10, f.away_draws_10, f.away_losses_10 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    
    # 进球/失球 - 在近10场战绩段
    # 格式: 进14 失9 (在主队下方) 和 进19 失15 (在客队下方)
    goals_section = text[:text.find('近10场主客战绩')] if '近10场主客战绩' in text else text[:500]
    all_goals = re.findall(r'进(\d+)\s*失(\d+)', goals_section)
    if len(all_goals) >= 2:
        f.home_goals_10 = int(all_goals[0][0])
        f.home_conceded_10 = int(all_goals[0][1])
        f.away_goals_10 = int(all_goals[1][0])
        f.away_conceded_10 = int(all_goals[1][1])
    
    # 主场/客场战绩
    m = re.search(r'主场(\d+)胜(\d+)平(\d+)负', text)
    if m:
        f.home_home_wins_10, f.home_home_draws_10, f.home_home_losses_10 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.search(r'客场(\d+)胜(\d+)平(\d+)负', text)
    if m:
        f.away_away_wins_10, f.away_away_draws_10, f.away_away_losses_10 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    
    # 主场/客场 进失球 — 查找 "近10场主客战绩" 段之后的进失球数字
    h2h_section = text[text.find('近10场主客战绩'):] if '近10场主客战绩' in text else text
    all_home_away_gl = re.findall(r'进(\d+)\s*失(\d+)', h2h_section)
    if len(all_home_away_gl) >= 2:
        f.home_home_goals_10 = int(all_home_away_gl[0][0])
        f.home_home_conceded_10 = int(all_home_away_gl[0][1])
        f.away_away_goals_10 = int(all_home_away_gl[1][0])
        f.away_away_conceded_10 = int(all_home_away_gl[1][1])


def _extract_odds(text: str, f: MatchFeatures):
    """从欧指Tab提取特征"""
    # 概率转换
    m = re.search(r'(\d+)%\s*[↓↑]?\s*\n?\s*胜\s*\n?\s*(\d+)%\s*[↓↑]?\s*\n?\s*平\s*\n?\s*(\d+)%\s*[↓↑]?\s*\n?\s*负', text)
    if m:
        f.home_prob_live = float(m.group(1)) / 100
        f.draw_prob_live = float(m.group(2)) / 100
        f.away_prob_live = float(m.group(3)) / 100
    
    # 百家平均赔率
    bajia_idx = text.find('百家平均')
    if bajia_idx >= 0:
        chunk = text[bajia_idx:bajia_idx + 400]
        nums = re.findall(r'(\d+\.\d+)', chunk)
        if len(nums) >= 6:
            f.home_odds_init = float(nums[0])
            f.draw_odds_init = float(nums[1])
            f.away_odds_init = float(nums[2])
            f.home_odds_live = float(nums[3])
            f.draw_odds_live = float(nums[4])
            f.away_odds_live = float(nums[5])
            # 变化率
            if f.home_odds_init > 0:
                f.home_odds_change = f.home_odds_live / f.home_odds_init - 1
            if f.draw_odds_init > 0:
                f.draw_odds_change = f.draw_odds_live / f.draw_odds_init - 1
            if f.away_odds_init > 0:
                f.away_odds_change = f.away_odds_live / f.away_odds_init - 1
    
    # 指数变化 - 上升/降低公司数
    # ⚠️ 两标签可能紧挨着（"上升指数公司\n降低指数公司"），数字全部在后
    # 格式: 上升指数公司[\\n]降低指数公司[\\n]27家 胜 4家 平 1家 负 1家 胜 17家 平 26家 负
    change_idx = text.find('指数变化')
    if change_idx >= 0:
        change_section = text[change_idx:change_idx + 400]
        nums = re.findall(r'(\d+)家', change_section)
        if len(nums) >= 6:
            f.home_rise_count = int(nums[0])
            f.draw_rise_count = int(nums[1])
            f.away_rise_count = int(nums[2])
            f.home_fall_count = int(nums[3])
            f.draw_fall_count = int(nums[4])
            f.away_fall_count = int(nums[5])
    
    # 离散度
    total_companies = f.home_rise_count + f.home_fall_count
    if total_companies > 0:
        f.home_dispersion = f.home_rise_count / total_companies


def _extract_asian(text: str, f: MatchFeatures):
    """从亚指Tab提取特征"""
    # 赢盘率
    m = re.search(r'(\d+)%\s*\n?\s*主队\s*\n?\s*(\d+)%\s*\n?\s*客队', text)
    if m:
        f.home_cover_rate = float(m.group(1)) / 100
        f.away_cover_rate = float(m.group(2)) / 100
    
    # 升降盘
    up = re.search(r'(\d+)家\s*\n?\s*升盘', text)
    down = re.search(r'(\d+)家\s*\n?\s*降盘', text)
    if up: f.up_disk_count = int(up.group(1))
    if down: f.down_disk_count = int(down.group(1))
    
    # 水位
    high = re.search(r'(\d+)家\s*\n?\s*高水', text)
    low = re.search(r'(\d+)家\s*\n?\s*低水', text)
    if high: f.high_water_count = int(high.group(1))
    if low: f.low_water_count = int(low.group(1))


def _extract_standings(text: str, f: MatchFeatures):
    """从排名Tab提取特征"""
    # 联赛排名 - 从"本赛季"行提取
    m = re.search(r'(\d+)\s*\n?\s*本赛季', text)
    if m:
        # This is home team's rank
        f.home_rank = int(m.group(1))
    
    # Find the away rank after the second "本赛季"
    seasons = list(re.finditer(r'(\d+)\s*\n?\s*本赛季', text))
    if len(seasons) >= 2:
        f.away_rank = int(seasons[1].group(1))
    
    f.home_rank_diff = f.away_rank - f.home_rank
    
    # 赛季战绩
    home_rec = re.search(r'(\d+)\s*\n?\s*(\d+)\s*\n?\s*(\d+)\s*\n?\s*.*?\s*\n?\s*本赛季', text)
    # 更精确匹配
    lines = text.split('\n')
    # 联赛主胜率
    m = re.search(r'(\d+)%\s*\n?\s*胜', text)
    if m:
        f.league_home_win_rate = float(m.group(1)) / 100


def _extract_pnl(text: str, f: MatchFeatures):
    """从盈亏Tab提取特征"""
    if len(text) < 100:
        return
    
    # 总交易量
    m = re.search(r'交易量\s*\n?\s*(\d[\d,]*)', text)
    if m:
        f.total_volume = float(m.group(1).replace(',', ''))
    
    # 各选项交易量
    vol_section = text[text.find('交易量'):] if '交易量' in text else ''
    vol_nums = re.findall(r'(\d[\d,]*)', vol_section)
    if len(vol_nums) >= 3:
        f.home_volume = float(vol_nums[1].replace(',', ''))  # skip total
        f.draw_volume = float(vol_nums[2].replace(',', ''))
        f.away_volume = float(vol_nums[3].replace(',', ''))
    
    # 盈亏
    pnl = re.findall(r'盈亏\s*\n?\s*(-?\d[\d,]*)', text)
    if len(pnl) >= 3:
        f.home_pnl = float(pnl[0].replace(',', ''))
        f.draw_pnl = float(pnl[1].replace(',', ''))
        f.away_pnl = float(pnl[2].replace(',', ''))
    
    # 冷热指数
    hot = re.findall(r'冷热\s*\n?\s*(-?\d+)', text)
    if len(hot) >= 3:
        f.home_hot_index = float(hot[0])
        f.draw_hot_index = float(hot[1])
        f.away_hot_index = float(hot[2])


def _compute_derived_features(f: MatchFeatures):
    """计算衍生特征"""
    # 状态评分(近10场, 胜3分平1分)
    f.home_form_score = (f.home_wins_10 * 3 + f.home_draws_10) / 30 if f.home_wins_10 + f.home_draws_10 + f.home_losses_10 > 0 else 0
    f.away_form_score = (f.away_wins_10 * 3 + f.away_draws_10) / 30 if f.away_wins_10 + f.away_draws_10 + f.away_losses_10 > 0 else 0
    
    # 攻击力
    f.home_attack_power = f.home_goals_10 / 10 if f.home_goals_10 > 0 else f.home_goals_per_game_20
    f.away_attack_power = f.away_goals_10 / 10 if f.away_goals_10 > 0 else f.away_goals_per_game_20
    
    # 防守力
    f.home_defense_strength = f.home_conceded_10 / 10 if f.home_conceded_10 > 0 else f.home_conceded_per_game_20
    f.away_defense_strength = f.away_conceded_10 / 10 if f.away_conceded_10 > 0 else f.away_conceded_per_game_20
    
    # 身价比
    if f.away_value > 0:
        f.value_ratio = f.home_value / f.away_value
    
    # 攻防差
    f.attack_diff = f.home_attack_power - f.away_attack_power
    f.defense_diff = f.away_defense_strength - f.home_defense_strength  # 正=主队防守好
    
    # 赔率概率差
    if f.home_prob_live > 0:
        second = max(f.draw_prob_live, f.away_prob_live)
        f.odds_prob_gap = f.home_prob_live - second
    
    # 热度差
    f.hot_diff = f.home_hot_index - f.away_hot_index
    
    # === 因子检测 ===
    
    # 因子4b: 一致升赔 (≥20家升, ≤2家降)
    for direction, rise, fall in [('home', f.home_rise_count, f.home_fall_count), 
                                   ('draw', f.draw_rise_count, f.draw_fall_count),
                                   ('away', f.away_rise_count, f.away_fall_count)]:
        if rise >= 20 and fall <= 2:
            f.factor_4b_triggered = True
            f.factor_4b_direction = direction
            break
    
    # 因子6: 排名倒挂 (客队排名比主队高3+)
    if f.home_rank_diff >= 3:
        f.factor_6_triggered = True
    
    # 因子12: 共识陷阱 (≥20家降赔且≤2家升赔, 且初赔均衡或主场差)
    for direction, rise, fall in [('home', f.home_rise_count, f.home_fall_count),
                                   ('draw', f.draw_rise_count, f.draw_fall_count)]:
        if fall >= 20 and rise <= 2:
            if f.home_odds_init > 0 and f.home_odds_init > 1.80:  # 初赔均衡
                f.factor_12_triggered = True
                break
    
    # 因子13: 双边极端分歧
    if ((f.home_rise_count >= 20 and f.home_fall_count <= 5 and 
         f.away_fall_count >= 20 and f.away_rise_count <= 5) or
        (f.home_fall_count >= 20 and f.home_rise_count <= 5 and
         f.away_rise_count >= 20 and f.away_fall_count <= 5)):
        if 5 <= f.draw_rise_count <= 15 and 5 <= f.draw_fall_count <= 15:
            f.factor_13_triggered = True


def features_to_dict(f: MatchFeatures) -> dict:
    """转为字典，便于传入ML模型"""
    return {k: v for k, v in f.__dict__.items() if not k.startswith('_')}
