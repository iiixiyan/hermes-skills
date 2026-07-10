#!/usr/bin/env python3
"""
全站基本盘采集引擎 v1.0 (2026-06-20)
一站式采集: titan007(球员评分/阵容/伤停/排名/战绩/天气/H2H)
           + 500彩票网(FIFA排名3期/预计阵容/伤病停赛/澳门心水)
           + 中国足彩网(40场走势/赛季排名对比/赔率方差)
           + 澳客网(球员身价/进球助攻)
汇聚 → 完整form_signal → 注入v10.5预测引擎

适配Hermes浏览器: browser_navigate + browser_console 采集模式
"""
import re, json
from typing import Dict, Any, Optional, List

# ============================================================
#  第1步: 从titan007分析页innerText提取全部基本盘数据
#  入口: browser_navigate → browser_console → innerText
# ============================================================
def parse_titan007(inner_text: str) -> Dict[str, Any]:
    """从titan007分析页innerText提取13类基本盘数据"""
    data = {}
    t = inner_text
    
    # ① 天气场地 (titan007独家-精确到℃)
    m = re.search(r'场地[：:]\s*(.+?)\s*天气[：:]\s*(.+?)\s*温度[：:]\s*(\S+)', t)
    if m:
        data['venue'] = m.group(1).strip()
        data['weather'] = m.group(2).strip()
        data['temperature'] = m.group(3).strip()
    
    # ② 杯赛/小组积分排名
    idx = t.find('杯赛积分排名')
    if idx >= 0:
        data['group_standings'] = t[idx:idx+500]
    
    # ③ 联赛排名 (含总/主/客)
    idx = t.find('联赛积分排名')
    if idx >= 0:
        data['league_standings'] = t[idx:idx+500]
    
    # ④ 球员评分 (两种格式)
    avg_ratings = re.findall(r'平均评分\s*(\d+\.?\d*)', t)
    if avg_ratings:
        data['h_avg_rating'] = float(avg_ratings[0]) if len(avg_ratings) > 0 else 0
        data['a_avg_rating'] = float(avg_ratings[1]) if len(avg_ratings) > 1 else 0
        data['avg_rating_diff'] = data.get('h_avg_rating', 0) - data.get('a_avg_rating', 0)
    
    # ⑤ 近10场评分序列 
    m = re.search(r'主队近10场平均评分:([\d.]+)', t)
    if m:
        scores = re.findall(r'(\d+\.?\d*)', m.group(0))
        if scores:
            data['h_form_ratings'] = [float(s) for s in scores]
    m = re.search(r'客队近10场平均评分:([\d.]+)', t)
    if m:
        scores = re.findall(r'(\d+\.?\d*)', m.group(0))
        if scores:
            data['a_form_ratings'] = [float(s) for s in scores]
    
    # ⑥ 阵容情况 (伤停)
    idx = t.find('阵容情况')
    if idx >= 0:
        section = t[idx:idx+600]
        injuries = re.findall(r'([\u4e00-\u9fff]{2,8})\t([\u4e00-\u9fff\s,()]+)', section)
        if injuries:
            data['injuries'] = [f'{p}: {r}' for p, r in injuries]
            data['has_injury_data'] = True
    
    # ⑦ 近期战绩汇总
    m = re.search(r'近(\d+)场,胜(\d+)平(\d+)负(\d+),\s*胜率:(\d+)%\s*赢率:(\d+)%\s*大:(\d+)%', t)
    if m:
        data['recent_matches'] = {
            'total': int(m.group(1)), 'w': int(m.group(2)),
            'd': int(m.group(3)), 'l': int(m.group(4)),
            'win_rate': int(m.group(5)), '赢率': int(m.group(6)), 'big': int(m.group(7))
        }
    
    # ⑧ 数据对比 (胜率/场均进球/角球/黄牌)
    idx = t.find('场均进球')
    if idx >= 0:
        section = t[max(0,idx-200):idx+300]
        goal_nums = re.findall(r'场均进球\s*([\d.]+)', section)
        if len(goal_nums) >= 2:
            data['h_avg_goals'] = float(goal_nums[0])
            data['a_avg_goals'] = float(goal_nums[1])
    
    # ⑨ 对赛往绩 (H2H)
    idx = t.find('对赛往绩')
    if idx >= 0:
        data['h2h_section'] = t[idx:idx+300]
    
    # ⑩ 首发名单 (球员评分行含*标记)
    starters = re.findall(r'(\d+)\t([\u4e00-\u9fff\s]+)\t([\u4e00-\u9fff\s]+)\t\*\t(\d+\.?\d*)', t)
    if starters:
        data['starters_count'] = len(starters)
        data['avg_starter_rating'] = round(sum(float(s[3]) for s in starters) / len(starters), 2)
    
    data['data_source'] = 'titan007'
    return data


# ============================================================
#  第2步: 从500彩票网shuju页面提取 (需scheduleId)
#  入口: browser_navigate → shuju-{sid}.shtml → innerText
# ============================================================
def parse_500(inner_text: str) -> Dict[str, Any]:
    """从500彩票网shuju页面提取FIFA排名3期+预计阵容+伤病停赛+澳门心水"""
    data = {}
    t = inner_text
    
    # ① FIFA排名 (3期+变化+积分)
    idx = t.find('FIFA排名')
    if idx >= 0:
        section = t[idx:idx+500]
        lines = [l.strip() for l in section.split('\n') if l.strip()]
        data['fifa_section'] = ' | '.join(lines[:15])
        # 提取数字排名
        nums = re.findall(r'世界排名[:：\s]*(\d+)', section)
        if nums:
            data['fifa_rank_h'] = int(nums[1]) if len(nums) > 1 else int(nums[0])
        nums = re.findall(r'排名变化[:：\s]*([+-]?\d+)', section)
        if nums:
            data['fifa_change_h'] = int(nums[0])
            if len(nums) > 1:
                data['fifa_change_a'] = int(nums[1])
    
    # ② 预计阵容 (阵型+首发11人+替补)
    idx = t.find('预计阵容')
    if idx >= 0:
        section = t[idx:idx+800]
        data['predicted_lineup'] = section[:500]
    
    # ③ 伤病名单
    idx = t.find('伤病')
    if idx >= 0:
        section = t[idx:idx+300]
        data['injuries_500'] = section[:300]
    
    # ④ 停赛名单
    idx = t.find('停赛')
    if idx >= 0:
        section = t[idx:idx+300]
        data['suspensions'] = section[:300]
    
    # ⑤ 澳门心水 (文字分析+推介方向)
    idx = t.find('澳门心水')
    if idx >= 0:
        section = t[idx:idx+500]
        data['macau_analysis'] = section[:500]
    
    # ⑥ 近期战绩 (主客场分开)
    idx = t.find('近期战绩')
    if idx >= 0:
        section = t[idx:idx+800]
        data['form_500'] = section[:500]
    
    # ⑦ 交战历史 (含盘路)
    idx = t.find('交战历史')
    if idx >= 0:
        section = t[idx:idx+500]
        data['h2h_500'] = section[:500]
    
    # ⑧ 未来赛程
    idx = t.find('未来赛事')
    if idx >= 0:
        section = t[idx:idx+500]
        data['future_fixtures'] = section[:500]
    
    data['data_source'] = '500'
    return data


# ============================================================
#  第3步: 从中国足彩网提取
#  入口: browser_navigate → zgzcw.com比赛页 → innerText
# ============================================================
def parse_zgzcw(inner_text: str) -> Dict[str, Any]:
    """中国足彩网: 赛季排名对比+40场走势+赔率方差"""
    data = {}
    t = inner_text
    
    idx = t.find('赛季排名对比')
    if idx >= 0:
        data['season_rank_compare'] = t[idx:idx+300]
    
    idx = t.find('近40场走势')
    if idx >= 0:
        data['trend_40'] = t[idx:idx+500]
    
    idx = t.find('赔率方差')
    if idx >= 0:
        data['odds_variance'] = t[idx:idx+300]
    
    # FIFA排名(中国足彩网也有)
    nums = re.findall(r'FIFA[排名]*[:：]\s*(\d+)', t)
    if nums:
        data['fifa_zgzcw'] = nums
    
    data['data_source'] = 'zgzcw'
    return data


# ============================================================
#  第4步: 从澳客网提取
#  入口: browser_navigate → okooo.com比赛详情页 → innerText
# ============================================================
def parse_okooo(inner_text: str) -> Dict[str, Any]:
    """澳客网: 球员身价+进球/助攻/红黄牌"""
    data = {}
    t = inner_text
    
    # 身价
    values = re.findall(r'身价[:：]\s*(\d+[万亿]?[€$]?)', t)
    if values:
        data['player_values'] = values
    
    # 进球/助攻
    goals = re.findall(r'进球[:：]\s*(\d+)', t)
    if goals:
        data['goals_stats'] = [int(g) for g in goals]
    assists = re.findall(r'助攻[:：]\s*(\d+)', t)
    if assists:
        data['assists_stats'] = [int(a) for a in assists]
    
    data['data_source'] = 'okooo'
    return data


# ============================================================
#  汇聚引擎: 合并所有源 → form_signal
# ============================================================
def merge_to_form_signal(sources: Dict[str, Dict]) -> Optional[Dict]:
    """将多个数据源的提取结果汇聚为一个form_signal"""
    signal = {
        'strength_gap': 0,
        'form_diff': 0,
        'injury_impact_h': 0,
        'injury_impact_a': 0,
        'lineup_known': False,
        'avg_rating_diff': 0.0,
        'goal_diff': 0,
        'weather': '',
        'temperature': '',
        'sources_used': [],
    }
    
    # === 球员评分差 (titan007) ===
    t7 = sources.get('titan007', {})
    if t7.get('avg_rating_diff'):
        signal['avg_rating_diff'] = t7['avg_rating_diff']
        signal['sources_used'].append('titan007_ratings')
    
    # === 近10场评分趋势 → form_diff ===
    h_form = t7.get('h_form_ratings', [])
    a_form = t7.get('a_form_ratings', [])
    if len(h_form) >= 3 and len(a_form) >= 3:
        h_trend = sum(h_form[:3])/3 - sum(h_form)/len(h_form)
        a_trend = sum(a_form[:3])/3 - sum(a_form)/len(a_form)
        signal['form_diff'] = int((h_trend - a_trend) * 10)
    
    # === 伤停 (titan007 + 500) ===
    if t7.get('has_injury_data'):
        signal['injury_impact_h'] = 1
        signal['injury_impact_a'] = 1
        signal['sources_used'].append('titan007_injuries')
    
    # === 首发已知 ===
    if t7.get('starters_count', 0) > 0:
        signal['lineup_known'] = True
        signal['sources_used'].append('titan007_starters')
    
    # === 天气温度 ===
    if t7.get('temperature'):
        signal['temperature'] = t7['temperature']
        signal['weather'] = t7.get('weather', '')
        signal['sources_used'].append('titan007_weather')
    
    # === FIFA排名/实力差 (500彩票网) ===
    f500 = sources.get('500', {})
    if f500.get('fifa_section'):
        signal['sources_used'].append('500_fifa')
    
    # === 澳门心水分析 ===
    if f500.get('macau_analysis'):
        signal['macau_tip'] = f500['macau_analysis']
        signal['sources_used'].append('500_macau')
    
    # === 未来赛程 ===
    if f500.get('future_fixtures'):
        signal['sources_used'].append('500_fixtures')
    
    # === 中国足彩网赛季排名 ===
    zg = sources.get('zgzcw', {})
    if zg.get('season_rank_compare'):
        signal['sources_used'].append('zgzcw_rank')
    
    if not signal['sources_used']:
        return None
    
    signal['sources_used'] = list(set(signal['sources_used']))
    return signal


# ============================================================
#  CLI用法示例
# ============================================================
if __name__ == "__main__":
    print("全站基本盘采集引擎 v1.0")
    print()
    print("采集流程:")
    print("  1. browser_navigate -> titan007 分析页")
    print("     → parse_titan007(innerText) -> 球员评分/阵容/伤停/排名/天气")
    print("  2. browser_navigate -> 500彩票网 shuju-{sid}.shtml")
    print("     → parse_500(innerText) -> FIFA排名3期/预计阵容/伤病/澳门心水")
    print("  3. browser_navigate -> 中国足彩网 比赛分析页")
    print("     → parse_zgzcw(innerText) -> 赛季排名/40场走势/赔率方差")
    print("  4. browser_navigate -> 澳客网 比赛详情")
    print("     → parse_okooo(innerText) -> 球员身价/进球助攻")
    print("  5. merge_to_form_signal({titan007, 500, zgzcw, okooo})")
    print("     → 完整form_signal -> v10.5 predict(form_signal=signal)")
