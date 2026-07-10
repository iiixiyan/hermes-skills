#!/usr/bin/env python3
"""芬超联赛预测管线 v2.0 — 大小球校准 + 让球信号 + 负二项分布 + 基本盘硬修正"""
import sys, json, urllib.request, importlib.util, math
sys.path.insert(0, '/root/.hermes/skills/sports/football-prediction/scripts')

# 加载Dixon-Coles
spec = importlib.util.spec_from_file_location(
    'dc', '/root/.hermes/skills/sports/football-prediction/scripts/dixon_coles.py')
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)

# 竞彩官方API
URL_BASE = 'https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36',
    'Referer': 'https://webapi.sporttery.cn/',
    'Accept': 'application/json',
}

SINA = 'https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000'
SINA_HDR = {'User-Agent': 'Mozilla/5.0'}

# 芬超队名映射
TEAM_MAP = {
    '拉赫蒂': '拉赫蒂', 'TPS图尔': 'TP图尔库', '库奥皮奥': '古比斯',
    '坦山猫': '埃尔维斯', '瓦萨': 'VPS瓦萨', 'AC奥卢': '奥卢',
    '雅罗': '查路', '赫尔火花': '格尼斯坦', '国际图尔': '国际图尔库',
    '塞伊奈': '塞那乔其', '玛丽港': '玛丽港', '赫尔辛基': '赫尔辛基',
}

def fetch_league_results(league_keyword='芬超'):
    """采集联赛历史赛果"""
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
    api_names = [k for k, v in TEAM_MAP.items() if v == team_name]
    if not api_names:
        return {'recent_gf': [1]*5, 'recent_ga': [1]*5, 'avg_gf': 1.25, 'avg_ga': 1.25, 'n_games': 0}
    gf_list, ga_list = [], []
    for m in matches:
        if m['home'] in api_names:
            gf_list.append(m['hg']); ga_list.append(m['ag'])
        elif m['away'] in api_names:
            gf_list.append(m['ag']); ga_list.append(m['hg'])
    gf_list = gf_list[-max_games:] if len(gf_list) > max_games else gf_list
    ga_list = ga_list[-max_games:] if len(ga_list) > max_games else ga_list
    n = len(gf_list)
    if n == 0:
        return {'recent_gf': [1]*5, 'recent_ga': [1]*5, 'avg_gf': 1.25, 'avg_ga': 1.25, 'n_games': 0}
    return {
        'recent_gf': gf_list[::-1], 'recent_ga': ga_list[::-1],
        'avg_gf': round(sum(gf_list)/n, 2), 'avg_ga': round(sum(ga_list)/n, 2),
        'n_games': n,
    }

def fetch_all_sina_data(mid):
    """从新浪API获取: 欧赔 + 大小球 + 让球 + 排名 + 比赛详情"""
    try:
        # 欧赔
        url = f'{SINA}&cat1=footballMatchOddsEuro&matchId={mid}'
        req = urllib.request.Request(url, headers=SINA_HDR)
        resp = urllib.request.urlopen(req, timeout=10)
        d = json.loads(resp.read().decode('utf-8'))
        odds = d.get('result', {}).get('data', [])
        if not odds: return None
        
        o1 = sum(float(o['o1New']) for o in odds) / len(odds)
        o3 = sum(float(o['o3New']) for o in odds) / len(odds)
        o2 = sum(float(o['o2New']) for o in odds) / len(odds)
        r1 = sum(1 for o in odds if float(o['o1New']) > float(o['o1Ini']))
        c1 = sum(1 for o in odds if float(o['o1New']) < float(o['o1Ini']))
        r2 = sum(1 for o in odds if float(o['o2New']) > float(o['o2Ini']))
        c2 = sum(1 for o in odds if float(o['o2New']) < float(o['o2Ini']))
        r3 = sum(1 for o in odds if float(o['o3New']) > float(o['o3Ini']))
        c3 = sum(1 for o in odds if float(o['o3New']) < float(o['o3Ini']))
        
        # 大小球(亚指) — 提取goalline/over/under
        oo_url = f'{SINA}&cat1=footballMatchOddsAsia&matchId={mid}'
        oo_req = urllib.request.Request(oo_url, headers=SINA_HDR)
        oo_resp = urllib.request.urlopen(oo_req, timeout=10)
        oo_d = json.loads(oo_resp.read().decode('utf-8'))
        asia = oo_d.get('result', {}).get('data', [])
        
        goal_line, over_odds, under_odds = None, None, None
        handicap_line, hdc_home_odds, hdc_away_odds = None, None, None
        
        # 亚指第一项通常是让球盘，第二项是大小球盘
        # 检查各条目：goalline有值的是大小球，handicap有值的是让球
        if asia:
            for a in asia:
                gl = a.get('goalLine', '')
                hdc = a.get('handicap', '')
                if gl and gl != '0' and gl != '':  # 大小球盘口
                    goal_line = gl
                    over_odds = float(a.get('overOdds', 0) or 0)
                    under_odds = float(a.get('underOdds', 0) or 0)
                elif hdc and hdc != '0' and hdc != '':  # 让球盘口
                    handicap_line = hdc
                    hdc_home_odds = float(a.get('homeOdds', 0) or 0)
                    hdc_away_odds = float(a.get('awayOdds', 0) or 0)
        
        # 排名
        det_url = f'{SINA}&cat1=footballMatchDetail&matchId={mid}'
        det_req = urllib.request.Request(det_url, headers=SINA_HDR)
        det_resp = urllib.request.urlopen(det_req, timeout=10)
        det_d = json.loads(det_resp.read().decode('utf-8'))
        dt = det_d.get('result', {}).get('data', {})
        rank_h = int(dt.get('team1Position', 0) or 0) if isinstance(dt, dict) else 0
        rank_a = int(dt.get('team2Position', 0) or 0) if isinstance(dt, dict) else 0
        # 球队名用于确认
        team1 = dt.get('team1', '') if isinstance(dt, dict) else ''
        team2 = dt.get('team2', '') if isinstance(dt, dict) else ''
        
        return {
            'o1': round(o1, 4), 'o2': round(o2, 4), 'o3': round(o3, 4),
            'r1': r1, 'c1': c1, 'r2': r2, 'c2': c2, 'r3': r3, 'c3': c3,
            'rank_h': rank_h, 'rank_a': rank_a, 'fd': abs(rank_h - rank_a),
            'n_odds': len(odds),
            'goal_line': goal_line, 'over_odds': over_odds, 'under_odds': under_odds,
            'handicap_line': handicap_line, 'hdc_home_odds': hdc_home_odds, 'hdc_away_odds': hdc_away_odds,
            'team1': team1, 'team2': team2,
        }
    except Exception as e:
        return None

# ── 负二项分布概率计算 ──
def ln_gamma(x):
    """Lanczos approximation of ln(gamma)"""
    g = 7
    c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028,
         771.32342877765313, -176.61502916214059, 12.507343278686905,
         -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7]
    x -= 1
    s = c[0]
    for i in range(1, g+2):
        s += c[i] / (x + i)
    t = x + g + 0.5
    return 0.5 * math.log(2*math.pi) + (x+0.5)*math.log(t) - t + math.log(s)

def nbinom_prob(k, mu, theta=1.5):
    """负二项分布概率: 比泊松更好的离散度(方差>均值)"""
    if k < 0: return 0.0
    r = theta  # 离散度参数
    p = r / (r + mu)
    # P(X=k) = C(k+r-1, k) * p^r * (1-p)^k
    # 用log计算防止溢出
    log_prob = ln_gamma(k+r) - ln_gamma(k+1) - ln_gamma(r) + r*math.log(p) + k*math.log(1-p)
    return math.exp(log_prob)

def poisson_prob(k, lam):
    """泊松分布概率"""
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def predict_with_nbinom(lambda_h, lambda_a, max_goals=5, theta=1.5, use_poisson=False):
    """用负二项分布(或泊松)预测比分，返回Top比分"""
    probs = {}
    total_prob = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            if use_poisson:
                p = poisson_prob(h, lambda_h) * poisson_prob(a, lambda_a)
            else:
                p = nbinom_prob(h, lambda_h, theta) * nbinom_prob(a, lambda_a, theta)
            probs[f'{h}-{a}'] = p
            total_prob += p
    # 归一化
    for k in probs: probs[k] /= total_prob
    
    top = sorted(probs.items(), key=lambda x: -x[1])[:6]
    
    win_p = sum(p for s,p in probs.items() if int(s.split('-')[0]) > int(s.split('-')[1]))
    draw_p = sum(p for s,p in probs.items() if int(s.split('-')[0]) == int(s.split('-')[1]))
    loss_p = sum(p for s,p in probs.items() if int(s.split('-')[0]) < int(s.split('-')[1]))
    
    return {'top_scores': top, 'win_prob': win_p, 'draw_prob': draw_p, 'loss_prob': loss_p}

# ── 大小球校准 ──
def calibrate_with_over_under(lambda_h, lambda_a, sina):
    """用大小球赔率校准总进球期望"""
    if not sina or not sina.get('goal_line'):
        return lambda_h, lambda_a, []
    
    reasons = []
    gl = sina['goal_line']
    over_odds = sina.get('over_odds')
    under_odds = sina.get('under_odds')
    
    # 解析goalline: 如 "2/2.5|2.5|3" 取中间的标准线
    lines = gl.split('|')
    # 找最接近2.5的线
    target_line = 2.5
    best_line = 2.5
    if lines:
        for l in lines:
            try:
                f = float(l.replace('/', '').replace('2','2'))
            except:
                continue
            # 解析"2/2.5"风格
            if '/' in l:
                parts = l.split('/')
                best_line = (float(parts[0]) + float(parts[1])) / 2
            else:
                try: best_line = float(l)
                except: continue
    
    # 用赔率估算市场期望总进球
    if over_odds and over_odds > 0 and under_odds and under_odds > 0:
        # 去抽水
        fair_over = 1.0 / over_odds
        fair_under = 1.0 / under_odds
        total_implied = fair_over + fair_under
        if total_implied > 0:
            over_prob = fair_over / total_implied
            # 如果over概率>0.55，市场预期大球
            if over_prob > 0.55:
                total_goals = lambda_h + lambda_a
                # 市场预期总进球比模型高
                # 用over_prob粗略估算市场总进球
                # 对于over 2.5 @ 1.80 (~53%), 总进球期望≈2.8-3.0
                # 对于over 2.5 @ 1.60 (~60%), 总进球期望≈3.2-3.5
                market_total = 2.5 + 3.0 * (over_prob - 0.50)  # 经验公式
                if market_total > total_goals * 1.15:
                    ratio = market_total / total_goals
                    ratio = max(1.05, min(1.30, ratio))
                    lambda_h *= ratio
                    lambda_a *= ratio
                    reasons.append(f'大球(over@{over_odds:.2f}→{over_prob:.0%})λ×{ratio:.2f}')
            elif over_prob < 0.40:
                total_goals = lambda_h + lambda_a
                market_total = 2.5 + 3.0 * (over_prob - 0.50)
                if market_total < total_goals * 0.85:
                    ratio = market_total / total_goals
                    ratio = max(0.70, min(0.95, ratio))
                    lambda_h *= ratio
                    lambda_a *= ratio
                    reasons.append(f'小球(under@{under_odds:.2f})λ×{ratio:.2f}')
    
    return lambda_h, lambda_a, reasons

def calibrate_with_handicap(lambda_h, lambda_a, sina):
    """用让球盘口校准主客分配"""
    if not sina or not sina.get('handicap_line'):
        return lambda_h, lambda_a, []
    
    reasons = []
    hdc = sina['handicap_line']
    hdc_home_odds = sina.get('hdc_home_odds')
    hdc_away_odds = sina.get('hdc_away_odds')
    
    try:
        hdc_val = float(hdc)
    except:
        return lambda_h, lambda_a, []
    
    # 让球盘解读
    # 让-0.5: 平手盘无倾向
    # 让-1.0: 看好主队赢1球+
    # 让+0.5: 看好客队不败
    delta = lambda_h - lambda_a
    
    # 如果让球盘倾向和模型λ差方向一致，不修正
    # 如果不一致，根据盘口修正
    if hdc_val < -1.0 and delta < 0.5:  # 深盘但模型不看好主队
        lambda_h *= 1.15
        reasons.append(f'让球盘{hdc}但λ偏客→主+15%')
    elif hdc_val > 0.5 and delta > -0.5:  # 深盘客让但模型不看好客队
        lambda_a *= 1.15
        reasons.append(f'让球盘+{hdc}但λ偏主→客+15%')
    
    return lambda_h, lambda_a, reasons

# ── 防御性规则 ──
def apply_defensive_rules(lambda_h, lambda_a, sina, h_stats, a_stats):
    """应用防御性硬修正规则"""
    reasons = []
    
    if not sina:
        return lambda_h, lambda_a, reasons
    
    fd = sina.get('fd', 0)
    c1, r1, c3, r3 = sina.get('c1', 0), sina.get('r1', 0), sina.get('c3', 0), sina.get('r3', 0)
    rh, ra = sina.get('rank_h', 0), sina.get('rank_a', 0)
    
    # ① 主场狗防守: 弱主(排名差≥3)面对强客+市场买客(r3≥30)+o3低 → 主队死守
    if rh > ra and fd >= 3 and r3 >= 30:
        lambda_h = max(lambda_h, 0.6)  # 不给太低，至少进1球机会
        lambda_a = min(lambda_a, lambda_h * 1.8)  # 压缩客队优势
        reasons.append(f'主场狗防御(#{rh}vs#{ra}+买客r3={r3})λ客≤{lambda_a:.2f}')
    
    # ② 极端比分保护: λ差>3.0时 — 防止过度自信
    if lambda_h > lambda_a * 3.0:
        lambda_h = lambda_h * 0.90
        reasons.append(f'极端大热→λ主×0.90')
    elif lambda_a > lambda_h * 3.0:
        lambda_a = lambda_a * 0.90
        reasons.append(f'极端大热→λ客×0.90')
    
    # ③ 平局保护: 当c1+r3都高(市场分歧)且排名差小
    if fd <= 3 and c1 >= 25 and r3 >= 25:
        # 市场在打架——走平局
        avg_l = (lambda_h + lambda_a) / 2
        lambda_h = avg_l
        lambda_a = avg_l
        reasons.append(f'市场分歧(c1={c1}/r3={r3})+排名差{fd}→平局均衡λ')
    
    # ④ 双方进攻型: 两队avg_gf都>1.5时，大比分
    if h_stats.get('avg_gf', 0) >= 1.5 and a_stats.get('avg_gf', 0) >= 1.5:
        lambda_h *= 1.10
        lambda_a *= 1.10
        h_gf = h_stats.get('avg_gf', 0)
        a_gf = a_stats.get('avg_gf', 0)
        reasons.append(f'双方进攻型(主{h_gf}/客{a_gf})λ×1.10')
    
    # ⑤ 主场龙: 主队近5场好+排名高+市场买主
    if rh < ra and c1 >= 20 and h_stats.get('avg_gf', 0) >= a_stats.get('avg_gf', 0):
        lambda_h *= 1.08
        reasons.append(f'主场龙(c1={c1}+#排名#)λ主×1.08')
    
    return lambda_h, lambda_a, reasons

def predict_match_enhanced(home_name, away_name, mid=None, league='芬超', half_life=6):
    """高级预测管线: Dixon-Coles + 大小球校准 + 让球 + 负二项"""
    # 1. 采集历史
    all_matches = fetch_league_results(league)
    
    # 2. 球队统计
    h_stats = compute_team_stats(all_matches, home_name)
    a_stats = compute_team_stats(all_matches, away_name)
    
    # 3. Dixon-Coles流水线
    pipe_h = dc.full_lambda_pipeline(
        recent_goals_for=h_stats['recent_gf'], recent_goals_against=h_stats['recent_ga'],
        season_avg_for=h_stats['avg_gf'], season_avg_against=h_stats['avg_ga'],
        league=league, half_life=half_life, n_games_season=max(h_stats['n_games'], 1))
    pipe_a = dc.full_lambda_pipeline(
        recent_goals_for=a_stats['recent_gf'], recent_goals_against=a_stats['recent_ga'],
        season_avg_for=a_stats['avg_gf'], season_avg_against=a_stats['avg_ga'],
        league=league, half_life=half_life, n_games_season=max(a_stats['n_games'], 1))
    
    ml = dc.compute_match_lambdas(
        attack_home=pipe_h['attack_lambda'], defense_home=pipe_h['defense_lambda'],
        attack_away=pipe_a['attack_lambda'], defense_away=pipe_a['defense_lambda'],
        league_avg=dc.get_league_prior(league)[0])
    
    base_h = ml['lambda_home']
    base_a = ml['lambda_away']
    
    # 4. 拉取基本盘
    sina = fetch_all_sina_data(mid) if mid else None
    
    # 5. 应用层层修正
    all_reasons = []
    
    # 5a. 欧赔市场修正（从v1.0）
    if sina:
        base_h_v1, base_a_v1, r1 = apply_euro_market(base_h, base_a, sina)
        all_reasons.extend(r1)
        base_h, base_a = base_h_v1, base_a_v1
    
    # 5b. 大小球校准
    if sina:
        base_h, base_a, r2 = calibrate_with_over_under(base_h, base_a, sina)
        all_reasons.extend(r2)
    
    # 5c. 让球校准
    if sina:
        base_h, base_a, r3 = calibrate_with_handicap(base_h, base_a, sina)
        all_reasons.extend(r3)
    
    # 5d. 防御性规则
    if sina:
        base_h, base_a, r4 = apply_defensive_rules(base_h, base_a, sina, h_stats, a_stats)
        all_reasons.extend(r4)
    
    # 6. 用负二项分布预测比分
    result = predict_with_nbinom(base_h, base_a, max_goals=5, theta=1.5)
    
    return {
        'home': home_name, 'away': away_name,
        'lambda_h': base_h, 'lambda_a': base_a,
        'base_h': ml['lambda_home'], 'base_a': ml['lambda_away'],
        'top_scores': result['top_scores'],
        'win_prob': result['win_prob'], 'draw_prob': result['draw_prob'], 'loss_prob': result['loss_prob'],
        'reasons': all_reasons, 'sina': sina,
        'n_matches': len(all_matches),
    }

def apply_euro_market(lambda_h, lambda_a, sina):
    """欧赔市场信号修正（原apply_fundamentals改进版）"""
    if not sina: return lambda_h, lambda_a, []
    reasons = []
    o1, o3 = sina['o1'], sina['o3']
    c1, r1, c3, r3 = sina['c1'], sina['r1'], sina['c3'], sina['r3']
    rh, ra = sina['rank_h'], sina['rank_a']
    
    # 市场买主
    if c1 >= 30 and o1 < 2.0:
        lambda_h *= 1.10
        reasons.append(f'买主(c1={c1})λ×1.10')
    
    # 市场买客
    if r3 >= 30 and o3 < 2.0:
        lambda_a *= 1.10
        reasons.append(f'买客(r3={r3})λ×1.10')
    
    # 排名确认
    if rh > 0 and ra > 0:
        if rh < ra and o1 < o3:
            lambda_h *= 1.05
            reasons.append(f'#{rh}<#{ra}+赔率确认λ×1.05')
        elif rh > ra and o3 < o1:
            lambda_a *= 1.05
            reasons.append(f'#{ra}<#{rh}+赔率确认λ×1.05')
    
    # 排名矛盾→跟市场
    if rh > 0 and ra > 0:
        if rh < ra and o3 < o1 and r3 >= 20:
            lambda_h *= 0.95; lambda_a *= 1.05
            reasons.append(f'#{rh}好但市场不买客→客+5%')
        elif rh > ra and o1 < o3 and c1 >= 20:
            lambda_h *= 1.15
            reasons.append(f'#{rh}差但市场买主→主+15%')
    
    return lambda_h, lambda_a, reasons


# ── 主入口：回测 ──
if __name__ == '__main__':
    test_matches = [
        (3635516, '拉赫蒂', 'TP图尔库', '0:0'),
        (3635515, '古比斯', '埃尔维斯', '4:3'),
        (3635517, 'VPS瓦萨', '奥卢', '5:1'),
        (3635519, '查路', '格尼斯坦', '1:1'),
        (3635518, '国际图尔库', '塞那乔其', '1:1'),
        (3635520, '玛丽港', '赫尔辛基', '0:4'),
    ]
    
    # 额外测试: 更多芬超场次
    extra_matches = [
        # 更多场次可从竞彩官方API获取
    ]
    
    print("=" * 80)
    print("芬超6场回测 v2.0 — Dixon-Coles + 大小球校准 + 负二项分布")
    print(f"联赛先验: {dc.get_league_prior('芬超')}")
    print("=" * 80)
    
    total = exact = poisson_exact = 0
    all_exact_missed = []
    
    for mid, h_name, a_name, ok_score in test_matches:
        # 增强版
        result = predict_match_enhanced(h_name, a_name, mid=mid)
        top = result['top_scores']
        
        sh, sa = int(ok_score.split(':')[0]), int(ok_score.split(':')[1])
        hit = any(int(s.split('-')[0])==sh and int(s.split('-')[1])==sa for s,_ in top[:2])
        
        # 也跑泊松版本对比
        poisson_result = dc.predict_match_scores(result['lambda_h'], result['lambda_a'], league='芬超', max_goals=5)
        poisson_top = poisson_result['top_scores']
        poisson_hit = any(int(s.split('-')[0])==sh and int(s.split('-')[1])==sa for s,_ in poisson_top[:2])
        
        if hit: exact += 1
        if poisson_hit: poisson_exact += 1
        total += 1
        
        s1, p1 = top[0]
        s2, p2 = top[1] if len(top) > 1 else ('?-?', 0)
        st = '✅' if hit else '❌'
        
        reason_str = ' | '.join(result['reasons']) if result['reasons'] else '无修正'
        print(f"\n{st} {h_name:<8}vs{a_name:<8} 实际{ok_score}")
        print(f"   λ₁={result['lambda_h']:.3f} λ₂={result['lambda_a']:.3f}(基{result['base_h']:.2f}/{result['base_a']:.2f}) | "
              f"胜{result['win_prob']:.1%}平{result['draw_prob']:.1%}负{result['loss_prob']:.1%}")
        print(f"   Top: {s1}({p1:.1%}) {s2}({p2:.1%}) | NB命中{hit} | 泊松命中{poisson_hit}")
        print(f"   修正: {reason_str}")
        
        if not hit:
            ps1 = poisson_top[0][0]; ps2 = poisson_top[1][0]
            all_exact_missed.append(f"  {h_name}vs{a_name}: NB→{s1}/{s2} Poiss→{ps1}/{ps2} 实际{ok_score}")
        
        if result.get('sina'):
            s = result['sina']
            gl_over = s.get('over_odds',0)
            gl_under = s.get('under_odds',0)
            gl_info = f"大小球:{s.get('goal_line','无')} O@{gl_over:.2f}/U@{gl_under:.2f}" if s.get('goal_line') else "大小球:无数据"
            hdc_info = f"让球:{s.get('handicap_line','无')}" if s.get('handicap_line') else "让球:无数据"
            print(f"   基本盘: o1={s['o1']} o3={s['o3']} r1/c1={s['r1']}/{s['c1']} r3/c3={s['r3']}/{s['c3']} | "
                  f"#{s['rank_h']}vs#{s['rank_a']} | {gl_info} | {hdc_info}")
    
    print(f"\n{'='*80}")
    print(f"结果: {exact}/{total} = {100*exact/total:.1f}% (负二项Top2命中)")
    print(f"泊松对比: {poisson_exact}/{total} = {100*poisson_exact/total:.1f}% (泊松Top2命中)")
    print(f"\n未命中明细:")
    for m in all_exact_missed:
        print(m)
