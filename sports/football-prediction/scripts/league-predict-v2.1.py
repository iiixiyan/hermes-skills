#!/usr/bin/env python3
"""芬超联赛预测管线 v2.1 — 泊松 + 大小球校准 + 强化防御规则"""
import sys, json, urllib.request, importlib.util, math
sys.path.insert(0, '/root/.hermes/skills/sports/football-prediction/scripts')

spec = importlib.util.spec_from_file_location(
    'dc', '/root/.hermes/skills/sports/football-prediction/scripts/dixon_coles.py')
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)

URL_BASE = 'https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36',
    'Referer': 'https://webapi.sporttery.cn/', 'Accept': 'application/json',
}
SINA = 'https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000'
SINA_HDR = {'User-Agent': 'Mozilla/5.0'}

TEAM_MAP = {
    '拉赫蒂': '拉赫蒂', 'TPS图尔': 'TP图尔库', '库奥皮奥': '古比斯',
    '坦山猫': '埃尔维斯', '瓦萨': 'VPS瓦萨', 'AC奥卢': '奥卢',
    '雅罗': '查路', '赫尔火花': '格尼斯坦', '国际图尔': '国际图尔库',
    '塞伊奈': '塞那乔其', '玛丽港': '玛丽港', '赫尔辛基': '赫尔辛基',
}

def fetch_league_results(league_keyword='芬超'):
    all_matches = []
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
                            all_matches.append({'date': dg.get('matchDate',''),
                                'home': m.get('homeTeamAbbName',''), 'away': m.get('awayTeamAbbName',''),
                                'hg': hg, 'ag': ag})
        except: pass
    return all_matches

def compute_team_stats(matches, team_name, max_games=10):
    api_names = [k for k, v in TEAM_MAP.items() if v == team_name]
    if not api_names:
        return {'recent_gf': [1]*5, 'recent_ga': [1]*5, 'avg_gf': 1.25, 'avg_ga': 1.25, 'n_games': 0}
    gf_list, ga_list = [], []
    for m in matches:
        if m['home'] in api_names: gf_list.append(m['hg']); ga_list.append(m['ag'])
        elif m['away'] in api_names: gf_list.append(m['ag']); ga_list.append(m['hg'])
    gf_list = gf_list[-max_games:] if len(gf_list) > max_games else gf_list
    ga_list = ga_list[-max_games:] if len(ga_list) > max_games else ga_list
    n = len(gf_list)
    if n == 0: return {'recent_gf': [1]*5, 'recent_ga': [1]*5, 'avg_gf': 1.25, 'avg_ga': 1.25, 'n_games': 0}
    return {'recent_gf': gf_list[::-1], 'recent_ga': ga_list[::-1],
            'avg_gf': round(sum(gf_list)/n,2), 'avg_ga': round(sum(ga_list)/n,2), 'n_games': n}

def fetch_all_sina_data(mid):
    """获取欧赔+大小球+让球+排名"""
    try:
        url = f'{SINA}&cat1=footballMatchOddsEuro&matchId={mid}'
        req = urllib.request.Request(url, headers=SINA_HDR)
        resp = urllib.request.urlopen(req, timeout=10)
        d = json.loads(resp.read().decode('utf-8'))
        odds = d.get('result', {}).get('data', [])
        if not odds: return None
        o1 = sum(float(o['o1New']) for o in odds) / len(odds) if odds else 0
        o3 = sum(float(o['o3New']) for o in odds) / len(odds) if odds else 0
        o2 = sum(float(o['o2New']) for o in odds) / len(odds) if odds else 0
        r1 = sum(1 for o in odds if float(o['o1New'])>float(o['o1Ini']))
        c1 = sum(1 for o in odds if float(o['o1New'])<float(o['o1Ini']))
        r2 = sum(1 for o in odds if float(o['o2New'])>float(o['o2Ini']))
        c2 = sum(1 for o in odds if float(o['o2New'])<float(o['o2Ini']))
        r3 = sum(1 for o in odds if float(o['o3New'])>float(o['o3Ini']))
        c3 = sum(1 for o in odds if float(o['o3New'])<float(o['o3Ini']))
        
        # 大小球+让球
        oo_url = f'{SINA}&cat1=footballMatchOddsAsia&matchId={mid}'
        oo_req = urllib.request.Request(oo_url, headers=SINA_HDR)
        oo_resp = urllib.request.urlopen(oo_req, timeout=10)
        oo_d = json.loads(oo_resp.read().decode('utf-8'))
        asia = oo_d.get('result', {}).get('data', [])
        goal_line, over_odds, under_odds = None, None, None
        handicap_line, hdc_home_odds = None, None
        if asia:
            for a in asia:
                gl = a.get('goalLine', '')
                hdc = a.get('handicap', '')
                if gl and gl.strip() and gl.strip() != '0':
                    goal_line = gl; over_odds = float(a.get('overOdds',0) or 0); under_odds = float(a.get('underOdds',0) or 0)
                elif hdc and hdc.strip() and hdc.strip() != '0':
                    handicap_line = hdc; hdc_home_odds = float(a.get('homeOdds',0) or 0)
        
        det_url = f'{SINA}&cat1=footballMatchDetail&matchId={mid}'
        det_req = urllib.request.Request(det_url, headers=SINA_HDR)
        det_resp = urllib.request.urlopen(det_req, timeout=10)
        det_d = json.loads(det_resp.read().decode('utf-8'))
        dt = det_d.get('result', {}).get('data', {})
        rank_h = int(dt.get('team1Position',0) or 0) if isinstance(dt,dict) else 0
        rank_a = int(dt.get('team2Position',0) or 0) if isinstance(dt,dict) else 0
        
        return {
            'o1':round(o1,4),'o2':round(o2,4),'o3':round(o3,4),
            'r1':r1,'c1':c1,'r2':r2,'c2':c2,'r3':r3,'c3':c3,
            'rank_h':rank_h,'rank_a':rank_a,'fd':abs(rank_h-rank_a),
            'goal_line':goal_line,'over_odds':over_odds,'under_odds':under_odds,
            'handicap_line':handicap_line,'hdc_home_odds':hdc_home_odds,
        }
    except: return None

def predict_with_poisson(lambda_h, lambda_a, max_goals=5):
    """泊松分布预测"""
    probs = {}
    for h in range(max_goals+1):
        for a in range(max_goals+1):
            p = (math.exp(-lambda_h) * lambda_h**h / math.factorial(h)) * \
                (math.exp(-lambda_a) * lambda_a**a / math.factorial(a))
            probs[f'{h}-{a}'] = p
    tp = sum(probs.values())
    for k in probs: probs[k] /= tp
    top = sorted(probs.items(), key=lambda x: -x[1])[:6]
    win = sum(p for s,p in probs.items() if int(s.split('-')[0])>int(s.split('-')[1]))
    dr = sum(p for s,p in probs.items() if int(s.split('-')[0])==int(s.split('-')[1]))
    ls = sum(p for s,p in probs.items() if int(s.split('-')[0])<int(s.split('-')[1]))
    return {'top_scores':top, 'win_prob':win, 'draw_prob':dr, 'loss_prob':ls}

def apply_all_corrections(lambda_h, lambda_a, sina, h_stats, a_stats):
    """所有修正应用"""
    if not sina: return lambda_h, lambda_a, []
    reasons = []
    o1, o3 = sina['o1'], sina['o3']
    c1, r1, c3, r3 = sina['c1'], sina['r1'], sina['c3'], sina['r3']
    rh, ra = sina['rank_h'], sina['rank_a']
    fd = sina['fd']
    
    # ═══ 1. 欧赔市场信号 ═══
    
    # ① 市场强买主胜: c1≥30且o1<2.0 → 主队被看好
    if c1 >= 30 and o1 < 2.0:
        factor = 1.15 if c1 >= 40 else 1.10
        lambda_h *= factor
        reasons.append(f'买主(c1={c1})λ×{factor:.2f}')
    
    # ② 市场强买客胜: r3≥30且o3<2.0 → 客队被看好
    if r3 >= 30 and o3 < 2.0:
        factor = 1.15 if r3 >= 40 else 1.10
        lambda_a *= factor
        reasons.append(f'买客(r3={r3})λ×{factor:.2f}')
    
    # ③ 排名确认加强
    if rh > 0 and ra > 0:
        if rh < ra and o1 < o3:
            lambda_h *= 1.05; reasons.append(f'#{rh}<#{ra}确认λ×1.05')
        elif rh > ra and o3 < o1:
            lambda_a *= 1.05; reasons.append(f'#{ra}<#{rh}确认λ×1.05')
    
    # ④ 排名矛盾→跟市场
    if rh > 0 and ra > 0:
        if rh < ra and o3 < o1 and r3 >= 20:
            lambda_h *= 0.95; lambda_a *= 1.05
            reasons.append(f'#{rh}好但市场不买→客+5%')
        elif rh > ra and o1 < o3 and c1 >= 20:
            lambda_h *= 1.15
            reasons.append(f'#{rh}差但市场买主→主+15%')
    
    # ═══ 2. 大小球校准 ═══
    sina_gl = sina.get('goal_line')
    if sina_gl and sina.get('over_odds',0) > 0:
        over_odds = sina['over_odds']
        under_odds = sina.get('under_odds', 0)
        if over_odds > 0 and under_odds > 0:
            fair_over = 1.0 / over_odds; fair_under = 1.0 / under_odds
            total_implied = fair_over + fair_under
            if total_implied > 0:
                over_prob = fair_over / total_implied
                total = lambda_h + lambda_a
                if over_prob > 0.55:
                    market_total = 2.5 + 3.0 * (over_prob - 0.50)
                    ratio = max(1.05, min(1.25, market_total / max(total, 0.5)))
                    lambda_h *= ratio; lambda_a *= ratio
                    reasons.append(f'大球(O@{over_odds:.2f}→{over_prob:.0%})λ×{ratio:.2f}')
                elif over_prob < 0.42:
                    market_total = 2.5 + 3.0 * (over_prob - 0.50)
                    ratio = max(0.80, min(0.95, market_total / max(total, 0.5)))
                    lambda_h *= ratio; lambda_a *= ratio
                    reasons.append(f'小球(U@{under_odds:.2f})λ×{ratio:.2f}')
    
    # ═══ 3. 防御性规则 ═══
    h_gf = h_stats.get('avg_gf', 0)
    a_gf = a_stats.get('avg_gf', 0)
    
    # ⑤ 双方进攻型大比分: 两队场均进球都高 → 对攻大球
    if h_gf >= 1.5 and a_gf >= 1.5:
        total_gf = h_gf + a_gf
        boost = 1.20 if total_gf >= 4.5 else (1.15 if total_gf >= 3.5 else 1.10)
        # 排名好+主场 → 主队更多
        if rh > 0 and ra > 0 and rh < ra:
            lambda_h *= (boost + 0.05)
            lambda_a *= boost
            reasons.append(f'双攻击型(+主场优)λ主×{boost+0.05:.2f}/客×{boost:.2f}')
        elif rh > 0 and ra > 0 and rh > ra:
            lambda_h *= boost
            lambda_a *= (boost + 0.05)
            reasons.append(f'双攻击型(+客场优)λ主×{boost:.2f}/客×{boost+0.05:.2f}')
        else:
            lambda_h *= boost
            lambda_a *= boost
            reasons.append(f'双攻击型({h_gf}/{a_gf})λ×{boost:.2f}')
    
    # ⑤b 极端攻击扩展: 当总进球期望>=5 + 双方攻击型 → 额外加到极值
    if h_gf >= 1.5 and a_gf >= 1.5 and (lambda_h + lambda_a) >= 5.0:
        lambda_h *= 1.10; lambda_a *= 1.10
        reasons.append(f'极攻扩展(λ总{lambda_h+lambda_a:.1f})λ×1.10')
    
    # ⑥ 主场狗守和: 弱主(fd≥3)+市场买客(r3≥30)+o3低 → 主队死守拼平
    if rh > ra and fd >= 3 and r3 >= 30 and o3 < 2.5:
        lambda_h = max(lambda_h, 0.6)
        lambda_a = min(lambda_a, lambda_h * 2.0)
        reasons.append(f'主场狗守(#{rh}vs#{ra}+买客)λ客≤{lambda_a:.2f}')
    
    # ⑥b 沉默市场主场狗: 无市场信号(c1+r3均<15) + 排名差大 + 主场λ<0.8 → 主场死守平局
    c1_mod = c1 if c1 is not None else 0
    r3_mod = r3 if r3 is not None else 0
    if rh > ra and fd >= 3 and (c1_mod + r3_mod) < 15 and lambda_h < 0.8:
        # 提升主队预期至少到0.75(主场上限)
        lambda_h = max(lambda_h, 0.75)
        lambda_a = min(lambda_a, max(lambda_h * 1.8, 1.2))
        reasons.append(f'沉默市场狗(#{rh}vs#{ra}+无信号)λ客限{lambda_a:.2f}')
    
    # ⑦ 主场狗下克上: 弱主+市场买主(c1≥20) → 主队爆冷
    if rh > ra and fd >= 2 and c1 >= 20 and o1 < 2.5:
        lambda_h *= 1.10
        reasons.append(f'弱主买(c1={c1})λ主×1.10')
    
    # ⑦b c1极端买主(c1≥40)强化
    if c1 >= 40 and o1 < 2.5:
        extra = 1.12
        lambda_h *= extra
        reasons.append(f'极端买主(c1={c1})λ主×{extra:.2f}')
    
    # ⑧ 市场一致买客但排名差小→防平
    if fd <= 2 and c1 >= 20 and r3 >= 20:
        lambda_h = (lambda_h + lambda_a) * 0.5
        lambda_a = lambda_h
        reasons.append(f'分歧(买主{c1}/买客{r3})+差小→均衡')
    
    # ⑨ 排名好但λ倒挂: 主队排名好(rh<ra)但交叉乘积使λ₂>λ₁ → 主场优势补正
    if rh > 0 and ra > 0 and rh < ra and lambda_a > lambda_h and (lambda_h + lambda_a) >= 3.0:
        # 平衡λ带微幅主场优势
        avg_l = (lambda_h + lambda_a) / 2
        lambda_h = avg_l * 1.05
        lambda_a = avg_l * 0.95
        reasons.append(f'排名优但λ倒挂(#{rh}<#{ra})→平衡主+5%/客-5%')
    
    return lambda_h, lambda_a, reasons

def predict_match(home_name, away_name, mid=None, league='芬超', half_life=6):
    """完整预测管线"""
    all_matches = fetch_league_results(league)
    h_stats = compute_team_stats(all_matches, home_name)
    a_stats = compute_team_stats(all_matches, away_name)
    
    pipe_h = dc.full_lambda_pipeline(
        recent_goals_for=h_stats['recent_gf'], recent_goals_against=h_stats['recent_ga'],
        season_avg_for=h_stats['avg_gf'], season_avg_against=h_stats['avg_ga'],
        league=league, half_life=half_life, n_games_season=max(h_stats['n_games'],1))
    pipe_a = dc.full_lambda_pipeline(
        recent_goals_for=a_stats['recent_gf'], recent_goals_against=a_stats['recent_ga'],
        season_avg_for=a_stats['avg_gf'], season_avg_against=a_stats['avg_ga'],
        league=league, half_life=half_life, n_games_season=max(a_stats['n_games'],1))
    
    ml = dc.compute_match_lambdas(
        attack_home=pipe_h['attack_lambda'], defense_home=pipe_h['defense_lambda'],
        attack_away=pipe_a['attack_lambda'], defense_away=pipe_a['defense_lambda'],
        league_avg=dc.get_league_prior(league)[0])
    
    base_h = ml['lambda_home']; base_a = ml['lambda_away']
    sina = fetch_all_sina_data(mid) if mid else None
    final_h, final_a, reasons = apply_all_corrections(base_h, base_a, sina, h_stats, a_stats)
    
    result = predict_with_poisson(final_h, final_a)
    return {
        'home':home_name, 'away':away_name,
        'lambda_h':final_h, 'lambda_a':final_a, 'base_h':base_h, 'base_a':base_a,
        'top_scores':result['top_scores'],
        'win_prob':result['win_prob'], 'draw_prob':result['draw_prob'], 'loss_prob':result['loss_prob'],
        'reasons':reasons, 'sina':sina, 'n_matches':len(all_matches),
    }

if __name__ == '__main__':
    test_matches = [
        (3635516, '拉赫蒂', 'TP图尔库', '0:0'),
        (3635515, '古比斯', '埃尔维斯', '4:3'),
        (3635517, 'VPS瓦萨', '奥卢', '5:1'),
        (3635519, '查路', '格尼斯坦', '1:1'),
        (3635518, '国际图尔库', '塞那乔其', '1:1'),
        (3635520, '玛丽港', '赫尔辛基', '0:4'),
    ]
    print("="*80)
    print("芬超6场回测 v2.1 — 泊松 + 基本盘强化防御规则")
    print(f"联赛先验: {dc.get_league_prior('芬超')}")
    print("="*80)
    total = exact = 0; misses = []
    for mid, h_name, a_name, ok_score in test_matches:
        result = predict_match(h_name, a_name, mid=mid)
        top = result['top_scores']
        sh, sa = int(ok_score.split(':')[0]), int(ok_score.split(':')[1])
        hit = any(int(s.split('-')[0])==sh and int(s.split('-')[1])==sa for s,_ in top[:2])
        if hit: exact += 1
        total += 1
        s1, p1 = top[0]; s2, p2 = top[1] if len(top)>1 else ('?-?',0)
        st = '✅' if hit else '❌'
        reason_str = ' | '.join(result['reasons']) if result['reasons'] else '无修正'
        print(f"\n{st} {h_name:<8}vs{a_name:<8} 实际{ok_score}")
        print(f"   λ₁={result['lambda_h']:.3f} λ₂={result['lambda_a']:.3f}(基{result['base_h']:.2f}/{result['base_a']:.2f}) | "
              f"胜{result['win_prob']:.1%}平{result['draw_prob']:.1%}负{result['loss_prob']:.1%}")
        print(f"   Top: {s1}({p1:.1%}) {s2}({p2:.1%}) | 修正: {reason_str}")
        if not hit: misses.append(f"  {h_name}vs{a_name}: Top={s1}/{s2} 实际{ok_score}")
        if result.get('sina'):
            s = result['sina']
            print(f"   基本盘: o1={s['o1']} c1={s['c1']} r3={s['r3']} | #{s['rank_h']}vs#{s['rank_a']}")
    print(f"\n{'='*80}")
    print(f"结果: {exact}/{total} = {100*exact/total:.1f}% (Top2命中)")
    for m in misses: print(m)
