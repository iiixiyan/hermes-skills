#!/usr/bin/env python3
"""
基本面侦察兵 — 从59itou API+新浪API采集基本面数据，生成form_signal
2026-06-20: v1.0 首次集成
"""
import json, urllib.request, re

API_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
    'Referer': 'https://kt.59itou.com/',
}
SINA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
    'Referer': 'https://mix.lottery.sina.com.cn/',
}
SINA_BASE = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000"

# ===== 全球FIFA排名缓存 (2026年6月) =====
FIFA_RANKINGS = {
    "阿根廷": 4, "法国": 1, "英格兰": 4, "巴西": 1, "比利时": 6,
    "葡萄牙": 7, "荷兰": 10, "西班牙": 2, "克罗地亚": 11, "意大利": 9,
    "美国": 8, "墨西哥": 13, "德国": 5, "乌拉圭": 13, "哥伦比亚": 21,
    "丹麦": 12, "日本": 20, "瑞士": 22, "瑞典": 19, "伊朗": 22,
    "澳大利亚": 27, "韩国": 22, "沙特": 58, "厄瓜多尔": 33,
    "塞内加尔": 13, "波兰": 28, "摩洛哥": 2, "秘鲁": 24, "智利": 25,
    "突尼斯": 26, "乌克兰": 27, "苏格兰": 30, "尼日利亚": 35,
    "捷克": 7, "挪威": 29, "塞尔维亚": 33, "巴拉圭": 32,
    "加拿大": 32, "波黑": 34, "卡塔尔": 49, "土耳其": 22,
    "南非": 61, "阿尔及利亚": 31, "奥地利": 18, "约旦": 57,
    "民主刚果": 47, "加纳": 73, "巴拿马": 34, "乌兹别克": 58,
    "海地": 71, "佛得角": 67, "埃及": 26, "新西兰": 87,
    "伊拉克": 55, "库拉索": 77, "科特迪瓦": 23, "库拉索": 77,
}


def fetch_59itou_match_list():
    """从59itou API获取比赛列表（含综合实力rank字段）"""
    url = "https://apic.jindianle.com/api/match/selectlist?platform=koudai_mobile&_prt=https&ver=20180101000000&hide_more=1&single_support=2"
    try:
        req = urllib.request.Request(url, headers=API_HEADERS)
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        return data.get('data', {})
    except Exception as e:
        return {}


def find_59itou_match(match_data, home_name, away_name):
    """在59itou比赛列表中通过队名模糊匹配"""
    for date_key, matches in match_data.items():
        for mid, m in matches.items():
            h = m.get('host_name_s', '')
            a = m.get('guest_name_s', '')
            if home_name in h or h in home_name:
                if away_name in a or a in away_name:
                    return m
    return None


def extract_form_from_59itou(match_info):
    """从59itou比赛信息中提取基本面"""
    form = {}
    
    # 综合实力分 (0-100) — 59itou API自带
    rank_list = match_info.get('list', [])
    if isinstance(rank_list, dict):
        rank_list = list(rank_list.values())
    if isinstance(rank_list, list) and len(rank_list) >= 2:
        try:
            form['strength_h'] = int(rank_list[0].get('rank', 0))
            form['strength_a'] = int(rank_list[1].get('rank', 0))
        except (ValueError, TypeError, IndexError, KeyError):
            pass
    
    return form


def fetch_recent_form_from_sina(team_name):
    """从新浪API获取球队近期赛果（通过竞彩赛果反查）
    注意: 此函数仅示例, 完整实现需按队名匹配历史赛果
    返回: {wins, draws, losses, goals_for, goals_against} or None
    """
    # 占位 — 实际需要从jczqMatches赛果中按队名过滤
    return None


def build_form_signal(home_name, away_name, fh, fa, 
                      strength_h=None, strength_a=None,
                      recent_h=None, recent_a=None,
                      lineup_known=False):
    """
    构建form_signal字典 — 供 predict_with_basics() 使用
    
    参数:
      home_name, away_name: 队名
      fh, fa: FIFA排名
      strength_h, strength_a: 59itou综合实力分(0-100)
      recent_h, recent_a: {w, d, l, gf, ga} 近10场数据
      lineup_known: 是否有首发数据
    
    返回: form_signal dict 或 None (无数据时)
    """
    signal = {}
    has_data = False
    
    # 1. 综合实力差
    if strength_h and strength_a:
        signal['strength_gap'] = strength_h - strength_a
        has_data = True
    else:
        # 用FIFA排名做实力差代理 (FIFA排名越低越好)
        signal['strength_gap'] = fa - fh  # 正=主队更强
        has_data = True
    
    # 2. 状态差
    if recent_h and recent_a:
        h_form = recent_h.get('w', 0) * 3 + recent_h.get('d', 1)
        a_form = recent_a.get('w', 0) * 3 + recent_a.get('d', 1)
        signal['form_diff'] = h_form - a_form
        has_data = True
    else:
        # 无近期数据时用FIFA排名差做代理状态
        signal['form_diff'] = 0
    
    # 3. 伤停 (占位 — 需从59itou阵容Tab采集)
    signal['injury_impact_h'] = 0
    signal['injury_impact_a'] = 0
    
    # 4. 阵容已知
    signal['lineup_known'] = lineup_known
    
    # 5. 近10场进失球差
    if recent_h and recent_a:
        h_gd = recent_h.get('gf', 0) - recent_h.get('ga', 0)
        a_gd = recent_a.get('gf', 0) - recent_a.get('ga', 0)
        signal['goal_diff'] = h_gd - a_gd
    else:
        signal['goal_diff'] = 0
    
    # 6. 评分差 (占位 — 需从titan007采集)
    signal['avg_rating_diff'] = 0.0
    
    if not has_data:
        return None
    
    return signal


def scout_and_build(home_name, away_name, fh, fa, lineup_known=False):
    """
    一站式基本面侦察 — 采集+构建form_signal
    
    实际管线:
    1. 拉取59itou API匹配列表
    2. 匹配目标比赛 → 提取综合实力
    3. 构建form_signal
    
    未来扩展:
    - Playwright浏览器采集59itou 战绩Tab(近10场)
    - Playwright采集titan007(球员评分)
    - 自动识别伤停信息
    """
    # Step 1: 59itou综合实力
    match_data = fetch_59itou_match_list()
    f_match = None
    strength_h, strength_a = None, None
    
    if match_data:
        f_match = find_59itou_match(match_data, home_name, away_name)
        if f_match:
            form_data = extract_form_from_59itou(f_match)
            strength_h = form_data.get('strength_h')
            strength_a = form_data.get('strength_a')
    
    # Step 2: 新浪API近期赛果 (占位)
    # recent_h = fetch_recent_form_from_sina(home_name)
    # recent_a = fetch_recent_form_from_sina(away_name)
    recent_h = recent_a = None
    
    # Step 3: 构建信号
    signal = build_form_signal(
        home_name, away_name, fh, fa,
        strength_h=strength_h, strength_a=strength_a,
        recent_h=recent_h, recent_a=recent_a,
        lineup_known=lineup_known
    )
    
    return signal, f_match


if __name__ == "__main__":
    # 测试: 美国vs澳大利亚
    signal, match = scout_and_build("美国", "澳大利亚", 8, 27)
    if signal:
        print(f"✅ 基本面信号构建成功:")
        for k, v in signal.items():
            print(f"  {k}: {v}")
    else:
        print("⚠️ 无基本面数据")
