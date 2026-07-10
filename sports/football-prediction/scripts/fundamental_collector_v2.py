#!/usr/bin/env python3
"""
基本面综合采集器 v2.0 (2026-06-20)
从球探体育(titan007)分析页采集完整基本盘数据 → form_signal

数据源: titan007 分析页 (https://zq.titan007.com/analysis/{sid}sb.htm)
覆盖: 球员评分/阵容/伤停/小组排名/近期战绩/H2H/天气/数据对比

用法:
  from fundamental_collector_v2 import collect_basics
  signal = collect_basics("美国", "澳大利亚", 8, 27, sid=2907341)
"""

import re, json
from typing import Optional, Dict, Any

def parse_titan007_text(text: str) -> Dict[str, Any]:
    """从titan007分析页innerText提取基本盘数据"""
    data = {}
    
    # 1. 天气场地
    m = re.search(r'场地[：:]\s*(.+?)\s*天气[：:]\s*(.+?)\s*温度[：:]\s*(\S+)', text)
    if m:
        data['venue'] = m.group(1).strip()
        data['weather'] = m.group(2).strip()
        data['temperature'] = m.group(3).strip()
    
    # 2. 球员评分 (两队)
    ratings = {}
    # 找 "号码\t球员\t位置\t首发\t评分" 后的数据
    sections = re.split(r'(?:土耳其|巴拉圭|美国|澳大利亚|荷兰|瑞典|日本|英格兰|法国|阿根廷|巴西|西班牙|德国|葡萄牙|比利时)\n号码', text)
    for i, sec in enumerate(sections[1:], 1):
        team_name_guess = ['主队', '客队'][i-1] if i <= 2 else f'队{i}'
        # 提取评分行
        rating_lines = re.findall(r'\d+\t[\u4e00-\u9fff\s]+\t[\u4e00-\u9fff\s]+\t[\*]?\t?(\d+\.?\d*)', sec)
        if rating_lines:
            scores = [float(r) for r in rating_lines if float(r) > 0]
            if scores:
                ratings[team_name_guess] = {
                    'count': len(scores),
                    'avg': round(sum(scores)/len(scores), 2),
                    'min': min(scores),
                    'max': max(scores),
                }
    
    # 找 "平均评分" 
    avg_ratings = re.findall(r'平均评分\s*(\d+\.?\d*)', text)
    if avg_ratings:
        for i, avg in enumerate(avg_ratings):
            key = ['h_avg_rating', 'a_avg_rating'][i] if i < 2 else f'team{i}_avg'
            data[key] = float(avg)
    
    data['ratings'] = ratings
    
    # 3. 近10场评分序列
    rating_series = re.findall(r'主队近10场平均评分:([\d.]+)[\s\S]*?客队近10场平均评分:([\d.]+)', text)
    if rating_series:
        h_scores = re.findall(r'(\d+\.?\d*)', rating_series[0][0])
        a_scores = re.findall(r'(\d+\.?\d*)', rating_series[0][1])
        if h_scores:
            data['h_form_ratings'] = [float(s) for s in h_scores]
        if a_scores:
            data['a_form_ratings'] = [float(s) for s in a_scores]
    
    # 4. 小组积分排名
    rank_table = re.search(r'杯赛积分排名[\s\S]{1,800}', text)
    if rank_table:
        data['group_standing'] = rank_table.group(0)[:500]
    
    # 5. 数据对比 (胜率/场均进球等)
    data_compare = re.search(r'数据对比[\s\S]{1,600}', text)
    if data_compare:
        dc = data_compare.group(0)
        # 提取主客胜率
        h_win = re.search(r'土耳其[\s\S]{0,200}?胜\s*(\d+)%', dc)
        a_win = re.search(r'巴拉圭[\s\S]{0,200}?胜\s*(\d+)%', dc)
        if h_win: data['h_win_rate'] = int(h_win.group(1))
        if a_win: data['a_win_rate'] = int(a_win.group(1))
        
        # 场均进球
        h_goals = re.search(r'土耳其[\s\S]{0,200}?场均进球\s*([\d.]+)', dc)
        a_goals = re.search(r'巴拉圭[\s\S]{0,200}?场均进球\s*([\d.]+)', dc)
        if h_goals: data['h_avg_goals'] = float(h_goals.group(1))
        if a_goals: data['a_avg_goals'] = float(a_goals.group(1))
    
    # 6. 近期战绩简要
    recent = re.search(r'近10场,胜(\d+)平(\d+)负(\d+),\s*胜率:(\d+)%\s*赢率:(\d+)%\s*大:(\d+)%', text)
    if recent:
        data['h_recent'] = {'w': int(recent.group(1)), 'd': int(recent.group(2)), 'l': int(recent.group(3))}
        data['h_stats'] = {'win_rate': int(recent.group(4)), '赢率': int(recent.group(5)), 'big': int(recent.group(6))}
    
    # 7. 阵容伤停 (结构存在)
    injury_section = re.search(r'阵容情况[\s\S]{1,500}', text)
    if injury_section:
        data['has_lineup_section'] = True
        injury_text = injury_section.group(0)
        injuries = re.findall(r'[\u4e00-\u9fff]{2,10}\t([\u4e00-\u9fff\s,]+)', injury_text)
        if injuries:
            data['injuries'] = [i.strip() for i in injuries if i.strip()]
    
    return data


def build_form_signal_from_titan007(titan_data: Dict, fh: int, fa: int) -> Optional[Dict]:
    """将titan007数据转换为form_signal"""
    if not titan_data:
        return None
    
    signal = {
        'strength_gap': fa - fh,  # FIFA排名差 (正=主队更强)
        'form_diff': 0,
        'injury_impact_h': 0,
        'injury_impact_a': 0,
        'lineup_known': False,
        'avg_rating_diff': 0.0,
        'goal_diff': 0,
        'weather': titan_data.get('weather', ''),
        'temperature': titan_data.get('temperature', ''),
    }
    
    # 球员评分差
    h_avg = titan_data.get('h_avg_rating')
    a_avg = titan_data.get('a_avg_rating')
    if h_avg and a_avg:
        signal['avg_rating_diff'] = round(h_avg - a_avg, 2)
        # 评分差>0.5 → 实力修正
        if signal['avg_rating_diff'] > 0.5:
            signal['strength_gap'] = max(signal['strength_gap'], int(signal['avg_rating_diff'] * 10))
        elif signal['avg_rating_diff'] < -0.5:
            signal['strength_gap'] = min(signal['strength_gap'], int(signal['avg_rating_diff'] * 10))
    
    # 近10场评分趋势 (最后3场 vs 整体)
    h_form = titan_data.get('h_form_ratings', [])
    a_form = titan_data.get('a_form_ratings', [])
    if len(h_form) >= 3 and len(a_form) >= 3:
        h_recent = sum(h_form[:3]) / 3
        h_all = sum(h_form) / len(h_form)
        a_recent = sum(a_form[:3]) / 3
        a_all = sum(a_form) / len(a_form)
        # 状态趋势: 近3场 > 整体平均 = 状态上升
        signal['form_diff'] = int((h_recent - h_all) * 10 - (a_recent - a_all) * 10)
    
    # 场均进球差
    h_g = titan_data.get('h_avg_goals')
    a_g = titan_data.get('a_avg_goals')
    if h_g and a_g:
        signal['goal_diff'] = int((h_g - a_g) * 10)
    
    # 伤停信息
    injuries = titan_data.get('injuries', [])
    if injuries:
        # 粗略: 有伤停名单即标记
        signal['injury_impact_h'] = 1
        signal['lineup_known'] = True
    
    return signal


# ===== 独立采集函数 (供终端使用) =====
def extract_from_url(html_text):
    """从已获取的HTML文本中直接提取"""
    return parse_titan007_text(html_text)


if __name__ == "__main__":
    # 测试
    pass
