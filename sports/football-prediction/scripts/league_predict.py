#!/usr/bin/env python3
"""芬超联赛预测管线 v1.0 — 竞彩官方API数据采集 + Dixon-Coles泊松λ"""
import sys, json, urllib.request, importlib.util
sys.path.insert(0, '/root/.hermes/skills/sports/football-prediction/scripts')

# 加载Dixon-Coles
spec = importlib.util.spec_from_file_location(
    'dc', '/root/.hermes/skills/sports/football-prediction/scripts/dixon_coles.py')
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)

# 竞彩官方API
URL_BASE = 'https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36',
    'Referer': 'https://webapi.sporttery.cn/',
    'Accept': 'application/json, text/plain, */*',
}

# 芬超球队简称映射（竞彩官方 → 我们用的名字）
TEAM_MAP = {
    '拉赫蒂': '拉赫蒂',
    'TPS图尔': 'TP图尔库',
    '库奥皮奥': '古比斯',
    '坦山猫': '埃尔维斯',
    '瓦萨': 'VPS瓦萨',
    'AC奥卢': '奥卢',
    '雅罗': '查路',
    '赫尔火花': '格尼斯坦',
    '国际图尔': '国际图尔库',
    '塞伊奈': '塞那乔其',
    '玛丽港': '玛丽港',
    '赫尔辛基': '赫尔辛基',
}

def fetch_league_results(league_keyword='芬超', days_back=30):
    """采集联赛历史赛果（全量）"""
    all_matches = []
    # 查全部日期范围
    for begin, end in [('2026-06-01','2026-06-10'), ('2026-06-10','2026-06-20'), ('2026-06-20','2026-06-28')]:
        try:
            url = f'{URL_BASE}?method=result&pageSize=100&pageNo=1&matchBeginDate={begin}&matchEndDate={end}'
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=10)
            d = json.loads(resp.read().decode('utf-8'))
            for dg in d.get('value', {}).get('matchInfoList', []):
                for m in dg.get('subMatchList', []):
                    league = m.get('leagueAbbName', '') or m.get('leagueAllName', '')
                    if league_keyword in league:
                        score = m.get('sectionsNo999','')
                        status = m.get('matchStatusName','')
                        if score and ':' in score and status == '已完成':
                            hg, ag = int(score.split(':')[0]), int(score.split(':')[1])
                            all_matches.append({
                                'date': dg.get('matchDate',''),
                                'home': m.get('homeTeamAbbName',''),
                                'away': m.get('awayTeamAbbName',''),
                                'hg': hg, 'ag': ag,
                            })
        except:
            pass
    return all_matches

def compute_team_stats(matches, team_name, max_games=10):
    """计算球队近N场场均进球/失球"""
    # 反向映射: 找API队名→我们的队名
    api_names = [k for k, v in TEAM_MAP.items() if v == team_name]
    if not api_names:
        return {'recent_gf': [1]*5, 'recent_ga': [1]*5,
                'avg_gf': 1.25, 'avg_ga': 1.25, 'n_games': 0}
    
    gf_list, ga_list = [], []
    for m in matches:
        if m['home'] in api_names:
            gf_list.append(m['hg'])
            ga_list.append(m['ag'])
        elif m['away'] in api_names:
            gf_list.append(m['ag'])
            ga_list.append(m['hg'])
    
    # 取最近max_games场
    gf_list = gf_list[-max_games:] if len(gf_list) > max_games else gf_list
    ga_list = ga_list[-max_games:] if len(ga_list) > max_games else ga_list
    
    n = len(gf_list)
    if n == 0:
        # 无数据时用联赛默认值
        return {
            'recent_gf': [1]*5, 'recent_ga': [1]*5,
            'avg_gf': 1.25, 'avg_ga': 1.25, 'n_games': 0
        }
    
    avg_gf = round(sum(gf_list) / n, 2)
    avg_ga = round(sum(ga_list) / n, 2)
    
    return {
        'recent_gf': gf_list[::-1],  # 最新在前
        'recent_ga': ga_list[::-1],
        'avg_gf': avg_gf,
        'avg_ga': avg_ga,
        'n_games': n,
    }

def predict_league_match(home_name, away_name, league='芬超', half_life=6):
    """用Dixon-Coles预测一场联赛"""
    # 1. 采集历史赛果
    all_matches = fetch_league_results(league)
    
    # 2. 计算主客队统计
    h_stats = compute_team_stats(all_matches, home_name)
    a_stats = compute_team_stats(all_matches, away_name)
    
    # 3. 全流水线
    pipe_h = dc.full_lambda_pipeline(
        recent_goals_for=h_stats['recent_gf'],
        recent_goals_against=h_stats['recent_ga'],
        season_avg_for=h_stats['avg_gf'],
        season_avg_against=h_stats['avg_ga'],
        league=league,
        half_life=half_life,
        n_games_season=max(h_stats['n_games'], 1),
    )
    pipe_a = dc.full_lambda_pipeline(
        recent_goals_for=a_stats['recent_gf'],
        recent_goals_against=a_stats['recent_ga'],
        season_avg_for=a_stats['avg_gf'],
        season_avg_against=a_stats['avg_ga'],
        league=league,
        half_life=half_life,
        n_games_season=max(a_stats['n_games'], 1),
    )
    
    # 4. 交叉乘积
    ml = dc.compute_match_lambdas(
        attack_home=pipe_h['attack_lambda'],
        defense_home=pipe_h['defense_lambda'],
        attack_away=pipe_a['attack_lambda'],
        defense_away=pipe_a['defense_lambda'],
        league_avg=dc.get_league_prior(league)[0],
    )
    
    # 5. DC比分概率
    result = dc.predict_match_scores(
        ml['lambda_home'], ml['lambda_away'],
        league=league, max_goals=5
    )
    
    return {
        'home': home_name,
        'away': away_name,
        'lambda_h': ml['lambda_home'],
        'lambda_a': ml['lambda_away'],
        'balance': ml['balance'],
        'top_scores': result['top_scores'],
        'win_prob': result['win_prob'],
        'draw_prob': result['draw_prob'],
        'loss_prob': result['loss_prob'],
        'h_stats': h_stats,
        'a_stats': a_stats,
        'n_matches': len(all_matches),
    }


if __name__ == '__main__':
    # 测试：回测芬超6场
    test_matches = [
        (3635516, '拉赫蒂', 'TP图尔库', '0:0'),
        (3635515, '古比斯', '埃尔维斯', '4:3'),
        (3635517, 'VPS瓦萨', '奥卢', '5:1'),
        (3635519, '查路', '格尼斯坦', '1:1'),
        (3635518, '国际图尔库', '塞那乔其', '1:1'),
        (3635520, '玛丽港', '赫尔辛基', '0:4'),
    ]
    
    print("芬超6场回测 — Dixon-Coles + 真实历史数据")
    print(f"联赛先验: {dc.get_league_prior('芬超')}")
    print("="*70)
    
    total = exact = 0
    for mid, h_name, a_name, ok_score in test_matches:
        result = predict_league_match(h_name, a_name)
        top = result['top_scores']
        
        sh, sa = int(ok_score.split(':')[0]), int(ok_score.split(':')[1])
        hit = any(int(s.split('-')[0])==sh and int(s.split('-')[1])==sa for s,_ in top[:2])
        if hit: exact += 1
        total += 1
        
        s1, p1 = top[0]
        s2, p2 = top[1] if len(top) > 1 else ('?-?', 0)
        st = '✅' if hit else '❌'
        
        print(f"{st} {h_name:<8}vs{a_name:<8} 实际{ok_score}")
        print(f"   λ₁={result['lambda_h']:.3f} λ₂={result['lambda_a']:.3f} | "
              f"胜{result['win_prob']:.1%}平{result['draw_prob']:.1%}负{result['loss_prob']:.1%}")
        print(f"   Top: {s1}({p1:.1%}) {s2}({p2:.1%}) | "
              f"主近{result['h_stats']['n_games']}场{result['h_stats']['avg_gf']}/{result['h_stats']['avg_ga']} "
              f"客近{result['a_stats']['n_games']}场{result['a_stats']['avg_gf']}/{result['a_stats']['avg_ga']}")
    
    print(f"\n结果: {exact}/{total} = {100*exact/total:.1f}% (Top2命中)")
