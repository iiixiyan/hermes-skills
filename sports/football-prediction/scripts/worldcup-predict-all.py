#!/usr/bin/env python3
"""
世界杯一键全流程预测 v3.0 (2026-06-20)
工作流:
  1. 新浪API → 比赛列表+欧赔+亚盘+FIFA排名
  2. 基本面侦察兵 → 59itou综合实力 → form_signal
  3. v10.5引擎 → 预测比分 (含基本面注入)
  4. 格式化输出 → 保存到文件 + 推送微信

用法:
  python3 worldcup-predict-all.py --date 2026-06-20
  python3 worldcup-predict-all.py --date 2026-06-20 --fundamental  # 强制基本面采集
  python3 worldcup-predict-all.py --date 2026-06-20 --save
"""

import json, sys, os, urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 缓存层
sys.path.insert(0, os.path.dirname(__file__))
from cache_layer import cache_get, cache_set, cache_clear, cache_stats

# 爆冷预警2.0 + 盘口博弈 (v7.0)
COLD_PATH = os.path.join(os.path.dirname(__file__), "cold_model_trainer.py")
HANDICAP_PATH = os.path.join(os.path.dirname(__file__), "handicap_analysis.py")

# 引擎导入
V10_PATH = os.path.join(os.path.dirname(__file__), "worldcup-predict-v10.py")
V9_PATH = os.path.join(os.path.dirname(__file__), "worldcup-predict-v9.py")
SCOUT_PATH = os.path.join(os.path.dirname(__file__), "fundamental_scout.py")

# 新浪API基础 (必须带3参数)
SINA_BASE = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000"
SINA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
    'Referer': 'https://mix.lottery.sina.com.cn/',
}

# ========== 世界杯matchId→队名对照 (v10东道主检测用) ==========
# 格式: matchId -> (主队, 客队, FIFA主, FIFA客, 轮次)
# 新浪API jczqMatches 返回的matchId (注意与59itou match_id2不同)
WORLDCUP_SINA_MATCHES = {
    # Round 1 (D1-D7)
    3625106: ("墨西哥", "南非", 13, 61, 1),
    3625107: ("韩国", "捷克", 22, 7, 1),  # 实际2-1
    3625108: ("加拿大", "波黑", 32, 34, 1),
    3625109: ("美国", "巴拉圭", 8, 32, 1),
    3625110: ("卡塔尔", "瑞士", 37, 22, 1),
    3625111: ("巴西", "摩洛哥", 1, 2, 1),
    3625112: ("海地", "苏格兰", 71, 30, 1),
    3625113: ("澳大利亚", "土耳其", 27, 22, 1),
    3625114: ("德国", "库拉索", 5, 77, 1),
    3625115: ("荷兰", "日本", 10, 20, 1),
    3625116: ("科特迪瓦", "厄瓜多尔", 23, 33, 1),
    3625117: ("瑞典", "突尼斯", 19, 26, 1),
    3625118: ("西班牙", "佛得角", 2, 67, 1),
    3625119: ("比利时", "埃及", 6, 26, 1),
    3625120: ("沙特", "乌拉圭", 58, 13, 1),
    3625121: ("伊朗", "新西兰", 22, 87, 1),
    3625122: ("法国", "塞内加尔", 1, 13, 1),
    3625123: ("伊拉克", "挪威", 55, 29, 1),
    3625124: ("阿根廷", "阿尔及利亚", 4, 31, 1),
    3625125: ("奥地利", "约旦", 18, 57, 1),
    3625126: ("葡萄牙", "民主刚果", 7, 47, 1),
    3625127: ("英格兰", "克罗地亚", 4, 11, 1),
    3625128: ("加纳", "巴拿马", 73, 34, 1),
    3625129: ("乌兹别克", "哥伦比亚", 58, 21, 1),
    # Round 2 (D8-D12)
    3625130: ("捷克", "南非", 7, 61, 2),
    3625131: ("瑞士", "波黑", 22, 63, 2),
    3625132: ("加拿大", "卡塔尔", 32, 49, 2),
    3625133: ("墨西哥", "韩国", 13, 22, 2),
    3625134: ("美国", "澳大利亚", 8, 27, 2),
    3625135: ("苏格兰", "摩洛哥", 30, 2, 2),
    3625136: ("巴西", "海地", 1, 71, 2),
    3625137: ("土耳其", "巴拉圭", 22, 32, 2),
    3625138: ("荷兰", "瑞典", 10, 19, 2),
    3625139: ("德国", "科特迪瓦", 5, 23, 2),
    3625140: ("厄瓜多尔", "库拉索", 33, 77, 2),
    3625141: ("突尼斯", "日本", 26, 20, 2),
    3625142: ("西班牙", "沙特", 2, 58, 2),
    3625143: ("比利时", "伊朗", 6, 22, 2),
    3625144: ("乌拉圭", "新西兰", 13, 87, 2),
    3625145: ("埃及", "佛得角", 26, 67, 2),
    3625146: ("法国", "葡萄牙", 1, 7, 2),
    3625147: ("挪威", "英格兰", 29, 4, 2),
    3625148: ("阿根廷", "加纳", 4, 73, 2),
    3625149: ("哥伦比亚", "奥地利", 21, 18, 2),
}

# 反向: 队名→matchId (东道主检测)
TEAM_TO_MATCH = {}
for mid, (h, g, fh, fa, rd) in WORLDCUP_SINA_MATCHES.items():
    TEAM_TO_MATCH[(h, g, rd)] = mid


def sina_fetch(cat1, **params):
    """拉取新浪API数据"""
    url = f"{SINA_BASE}&cat1={cat1}"
    for k, v in params.items():
        url += f"&{k}={v}"
    
    req = urllib.request.Request(url, headers=SINA_HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        return data.get('result', {}).get('data', [])
    except Exception as e:
        print(f"⚠️ 新浪API请求失败 {cat1}: {e}")
        return []


def get_matches_for_date(date_str):
    """获取某一天比赛列表"""
    matches = sina_fetch("jczqMatches", gameTypes="spf", date=date_str, isAll=1, dpc=1)
    if not matches:
        print(f"⚠️ {date_str} 无比赛数据 (新浪API)")
        return []
    return matches


def parse_match_data(match):
    """从新浪API比赛列表解析世界杯比赛"""
    mid = match.get('matchId', '')
    h_name = match.get('team1', match.get('hostName', ''))
    g_name = match.get('team2', match.get('guestName', ''))
    league = match.get('league', match.get('leagueName', ''))
    
    # 只处理世界杯比赛
    if '世界杯' not in league and 'WorldCup' not in league:
        return None
    
    # 从对照表获取FIFA排名
    round_num = 2  # 默认Round 2+
    fh, fa = 0, 0
    for _mid, (_h, _g, _fh, _fa, _rd) in WORLDCUP_SINA_MATCHES.items():
        if h_name in _h or _h in h_name:
            fh, fa, round_num = _fh, _fa, _rd
            break
    
    return {
        'matchId': mid,
        'home': h_name,
        'away': g_name,
        'fifa_h': fh,
        'fifa_a': fa,
        'round': round_num,
    }


def get_odds(match_id):
    """获取欧赔数据"""
    odds = sina_fetch("footballMatchOddsEuro", matchId=match_id)
    if not odds:
        return None
    
    # 百家平均
    o1s_new = [float(o.get('o1New', 0)) for o in odds if o.get('o1New')]
    o3s_new = [float(o.get('o3New', 0)) for o in odds if o.get('o3New')]
    o1s_ini = [float(o.get('o1Ini', 0)) for o in odds if o.get('o1Ini')]
    o3s_ini = [float(o.get('o3Ini', 0)) for o in odds if o.get('o3Ini')]
    
    if not o1s_new:
        return None
    
    r1 = sum(1 for o in odds if float(o.get('o1New',0)) > float(o.get('o1Ini',0)))
    c1 = sum(1 for o in odds if float(o.get('o1New',0)) < float(o.get('o1Ini',0)))
    r2 = sum(1 for o in odds if float(o.get('o2New',0)) > float(o.get('o2Ini',0)))
    c2 = sum(1 for o in odds if float(o.get('o2New',0)) < float(o.get('o2Ini',0)))
    r3 = sum(1 for o in odds if float(o.get('o3New',0)) > float(o.get('o3Ini',0)))
    c3 = sum(1 for o in odds if float(o.get('o3New',0)) < float(o.get('o3Ini',0)))
    
    return {
        'o1': round(sum(o1s_new) / len(o1s_new), 4),
        'o3': round(sum(o3s_new) / len(o3s_new), 4),
        'r1': r1, 'c1': c1,
        'r2': r2, 'c2': c2,
        'r3': r3, 'c3': c3,
    }


def get_asian(match_id):
    """获取亚盘数据"""
    asian = sina_fetch("footballMatchOddsAsia", matchId=match_id)
    if not asian:
        return {'hh': 0}
    
    hh = sum(1 for o in asian if float(o.get('o1New', 1)) >= 1.90)
    return {'hh': hh}


def run_v10_prediction(odds, asian, match_info):
    """运行v10引擎"""
    try:
        # 动态导入v10
        sys.path.insert(0, os.path.dirname(V10_PATH))
        import importlib.util
        spec = importlib.util.spec_from_file_location("v10_engine", V10_PATH)
        v10 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v10)
        
        h_pred, a_pred, rule, conf = v10.predict(
            h=match_info['home'], g=match_info['away'],
            fh=match_info['fifa_h'], fa=match_info['fifa_a'],
            o1=odds['o1'], o3=odds['o3'],
            r1=odds['r1'], c1=odds['c1'],
            r2=odds['r2'], c2=odds['c2'],
            r3=odds['r3'], c3=odds['c3'],
            rd=match_info['round']
        )
        return v10.format_result(h_pred, a_pred, rule, conf)
    except Exception as e:
        print(f"⚠️ v10引擎错误: {e}")
        return None


def format_predictions(result_list, date_str):
    """格式化预测输出"""
    lines = []
    lines.append(f"# 🔮 世界杯预测 ({date_str}) — v10引擎")
    lines.append(f"> {datetime.now().strftime('%Y-%m-%d %H:%M')} 实时数据\n")
    
    for r in result_list:
        lines.append(f"### {r['home']} vs {r['away']}（第{r['round']}轮）")
        lines.append(f"FIFA {r['fifa_h']} vs {r['fifa_a']}（差{abs(r['fifa_h']-r['fifa_a'])}）")
        lines.append(f"欧指 {r['odds']['o1']} → {r['odds']['o3']} | 升{r['odds']['r1']}/降{r['odds']['c1']} 主")
        lines.append(f"       升{r['odds']['r2']}/降{r['odds']['c2']} 平")
        lines.append(f"       升{r['odds']['r3']}/降{r['odds']['c3']} 客")
        lines.append(f"📌 {r['rule']}")
        lines.append(f"🎯 {r['score1']}/{r['score2']} {r['stars']}")
        lines.append("")
    
    # 汇总
    lines.append("---")
    lines.append(f"共 {len(result_list)} 场 | 引擎: v10 | 数据: 新浪API实时")
    
    return "\n".join(lines)


def save_predictions(text, date_str, push_target=None):
    """保存预测到文件，可选推送"""
    # 确保目录存在
    pred_dir = os.path.expanduser(f"~/.hermes/predictions/worldcup/")
    os.makedirs(pred_dir, exist_ok=True)
    
    # 保存
    filepath = os.path.join(pred_dir, f"{date_str}.md")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"✅ 已保存到 {filepath}")
    
    # 推送
    if push_target:
        print(f"📤 推送至 {push_target}")
        print("[请在Hermes中执行: send_message]")
    
    return filepath


def save_prediction_record(match_id, date_str, h_name, a_name, fh, fa, rd,
                           odds, form_signal, h_pred, a_pred, rule, conf,
                           s1, s2, stars):
    """
    保存结构化预测记录到 ~/.hermes/predictions/records/{match_id}.json
    供 model_retrainer.py 后续分析误差使用。
    """
    records_dir = os.path.expanduser("~/.hermes/predictions/records/")
    os.makedirs(records_dir, exist_ok=True)

    # 从odds中提取升降数据构建信号变量
    r1, c1, r2, c2, r3, c3 = odds.get('r1', 0), odds.get('c1', 0), odds.get('r2', 0), odds.get('c2', 0), odds.get('r3', 0), odds.get('c3', 0)
    xh = r1 >= 40 and c1 <= 5
    xa = r3 >= 40 and c3 <= 5
    hd = c1 >= 25 and r1 <= 10
    ds = c2 >= 25

    # 构建特征字典
    features = {
        'strength_gap': fh - fa,
        'market_consistency': round(len([o for o in [xh, xa, hd, ds] if o]) / 4.0, 2) if any([xh, xa, hd, ds]) else 0.5,
        'motivation_gap': 0,  # 暂无来源, default
        'injury_impact_h': form_signal.get('injury_impact_h', 0) if form_signal else 0,
        'injury_impact_a': form_signal.get('injury_impact_a', 0) if form_signal else 0,
        'temperature': 0,  # 外部传入, default 0
        'weather': '',
        'handicap_diff': odds.get('o1', 0) - odds.get('o3', 0),
        'half_life_form_h': form_signal.get('form_diff', 0) / 10.0 + 0.5 if form_signal else 0.5,
        'half_life_form_a': 0.5,
    }
    # 从form_signal补充
    if form_signal:
        features['motivation_gap'] = form_signal.get('form_diff', 0)

    # 预测结构
    prediction = {
        'scores': [s1, s2],
        'direction': '胜' if h_pred > a_pred else ('平' if h_pred == a_pred else '负'),
        'confidence': conf,
        'lambda_h': round(h_pred * 0.85, 2) if h_pred > 0 else 0.5,
        'lambda_a': round(a_pred * 0.85, 2) if a_pred > 0 else 0.5,
    }

    record = {
        'match_id': str(match_id),
        'date': date_str,
        'features': features,
        'prediction': prediction,
        'actual': {},  # 待赛果录入
        'metadata': {
            'home': h_name,
            'away': a_name,
            'fifa_h': fh,
            'fifa_a': fa,
            'round': rd,
            'rule': rule,
            'engine_version': 'v10',
        }
    }

    fpath = os.path.join(records_dir, f"{match_id}.json")
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return fpath


def predict_single_match(mid, h, g, fh, fa, rd, args, form_signal=None, thread_local=None):
    """
    单场比赛预测函数 (线程安全)。
    由 ThreadPoolExecutor 的 worker 调用，每个 worker 独立运行。
    
    参数:
        mid: matchId
        h, g: 主客队名
        fh, fa: 主客场FIFA排名
        rd: 轮次
        args: 命令行参数 (argparse.Namespace)
        form_signal: 基本面信号 (可选)
        thread_local: threading.local() 对象，用于线程本地浏览器实例
    
    返回:
        dict 包含预测结果，或 None (预测失败)
    """
    # 动态导入 v10 引擎 (每个线程独立导入)
    sys.path.insert(0, os.path.dirname(V10_PATH))
    import importlib.util
    spec = importlib.util.spec_from_file_location("v10", V10_PATH)
    v10_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v10_mod)

    # 使用缓存获取欧赔
    odds = cache_get(f"sina_odds_{mid}", category='sina_api')
    if odds is None:
        odds = get_odds(mid)
        if odds:
            cache_set(f"sina_odds_{mid}", odds, category='sina_api')
    if not odds:
        return None

    # 使用缓存获取亚盘
    asian = cache_get(f"sina_asian_{mid}", category='sina_api')
    if asian is None:
        asian = get_asian(mid)
        if asian:
            cache_set(f"sina_asian_{mid}", asian, category='sina_api')

    # 基本面侦察
    current_form_signal = form_signal

    if args.browser and thread_local is not None:
        # 线程本地浏览器
        browser = getattr(thread_local, 'browser', None)
        playwright_obj = getattr(thread_local, 'playwright_obj', None)
        if browser is None:
            try:
                from playwright.sync_api import sync_playwright
                _p = sync_playwright()
                playwright_obj = _p.start()
                browser = playwright_obj.chromium.launch(
                    executable_path='/usr/bin/chromium-browser',
                    headless=True,
                    args=['--no-sandbox']
                )
                thread_local.browser = browser
                thread_local.playwright_obj = playwright_obj
            except Exception as e:
                print(f"    ⚠️ 线程本地浏览器初始化失败: {e}")
                browser = None

        if browser:
            try:
                sys.path.insert(0, os.path.dirname(__file__))
                from automated_all import collect_all
                bdata = collect_all(browser, h, g, mid)
                if bdata.get('sources_found'):
                    current_form_signal = bdata.get('form_signal')
                    print(f"    🌐 浏览器数据: {'+'.join(bdata['sources_found'])}")
            except Exception as e:
                if args.verbose:
                    print(f"    ⚠️ L2+L3采集: {e}")

    elif not current_form_signal and hasattr(args, 'fundamental') and args.fundamental:
        try:
            sys.path.insert(0, os.path.dirname(SCOUT_PATH))
            spec = importlib.util.spec_from_file_location("scout_mod", SCOUT_PATH)
            sm = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sm)
            signal, _ = sm.scout_and_build(h, g, fh, fa)
            if signal:
                current_form_signal = signal
        except Exception:
            pass

    # 运行 v10 预测
    try:
        h_pred, a_pred, rule, conf = v10_mod.predict(
            h=h, g=g, fh=fh, fa=fa,
            o1=odds['o1'], o3=odds['o3'],
            r1=odds['r1'], c1=odds['c1'],
            r2=odds['r2'], c2=odds['c2'],
            r3=odds['r3'], c3=odds['c3'],
            rd=rd,
            form_signal=current_form_signal,
        )
        s1, s2, stars = v10_mod.format_result(h_pred, a_pred, rule, conf)

        # v7.0: 爆冷预警2.0 条件触发
        if abs(fh - fa) >= 15:
            try:
                cold_mod = importlib.util.module_from_spec(
                    importlib.util.spec_from_file_location("cold_mod", COLD_PATH)
                )
                cold_mod.spec.loader.exec_module(cold_mod)
                cold_res = cold_mod.analyze_match_cold(
                    h_fifa=fh, a_fifa=fa, h_name=h, a_name=g,
                    o1=odds['o1'], o3=odds['o3'],
                    r1=odds['r1'], c1=odds['c1'],
                    r2=odds['r2'], c2=odds['c2'],
                    r3=odds['r3'], c3=odds['c3'],
                    rd=rd, h_goals=h_pred, a_goals=a_pred,
                    rule=rule, conf_level=conf,
                )
                if cold_res.get('warning'):
                    h_pred, a_pred = cold_res['h_goals'], cold_res['a_goals']
                    rule = cold_res['rule']
                    conf = cold_res['conf_level']
                    s1, s2, stars = v10_mod.format_result(h_pred, a_pred, rule, conf)
                    stars += " ❄️冷" if not stars.endswith("冷") else ""
            except Exception:
                pass

        # v7.0: 盘口博弈分析
        try:
            hcp_mod = importlib.util.module_from_spec(
                importlib.util.spec_from_file_location("hcp_mod", HANDICAP_PATH)
            )
            hcp_mod.spec.loader.exec_module(hcp_mod)
            strength_gap = (current_form_signal or {}).get('strength_gap', fh - fa)
            if abs(strength_gap) >= 5:
                hcp_diff = round((odds['o3'] - odds['o1']) / 2.0, 2)
                hcp_str = f"-{hcp_diff}" if hcp_diff > 0 else f"+{abs(hcp_diff)}"
                hcp_data = hcp_mod.HandicapData(initial=hcp_str, live=hcp_str)
                hcp_res = hcp_mod.analyze_handicap(
                    strength_gap=strength_gap, handicap=hcp_data,
                    lineup_known=bool(current_form_signal and current_form_signal.get('lineup_known'))
                )
                if hcp_res['type'] != 'match' and hcp_res['reason']:
                    rule = f"{rule}|{hcp_res['reason']}"
        except Exception:
            pass
    except Exception as e:
        print(f"    ⚠️ v10预测失败 [{h} vs {g}]: {e}")
        return None

    result = {
        'home': h, 'away': g,
        'fifa_h': fh, 'fifa_a': fa,
        'round': rd,
        'odds': odds,
        'asian': asian,
        'score1': s1, 'score2': s2,
        'rule': rule,
        'stars': stars,
    }

    # 保存结构化预测记录
    try:
        save_prediction_record(
            match_id=mid, date_str=args.date,
            h_name=h, a_name=g, fh=fh, fa=fa, rd=rd,
            odds=odds, form_signal=current_form_signal,
            h_pred=h_pred, a_pred=a_pred, rule=rule, conf=conf,
            s1=s1, s2=s2, stars=stars,
        )
    except Exception as e:
        if args.verbose:
            print(f"    ⚠️ 保存预测记录失败: {e}")

    return result


# ==================== CLI ====================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="世界杯一键全流程预测")
    parser.add_argument("--date", type=str, required=True, help="日期 YYYY-MM-DD")
    parser.add_argument("--engine", type=str, default="v10", choices=["v9", "v10"])
    parser.add_argument("--save", action="store_true", help="保存到文件")
    parser.add_argument("--push", type=str, help="推送目标 (weixin等)")
    parser.add_argument("--verbose", action="store_true", help="显示详细数据")
    parser.add_argument("--browser", action="store_true", help="启用L2+L3浏览器数据采集 (titan007+500彩票网+澳客网)")
    parser.add_argument("--parallel", action="store_true", help="并行处理多场比赛")
    parser.add_argument("--workers", type=int, default=4, help="并行工作线程数 (默认: 4)")
    
    args = parser.parse_args()
    
    # 浏览器模式初始化
    browser = None
    playwright_obj = None
    if args.browser:
        try:
            from playwright.sync_api import sync_playwright
            _p = sync_playwright()
            playwright_obj = _p.start()
            browser = playwright_obj.chromium.launch(
                executable_path='/usr/bin/chromium-browser',
                headless=True,
                args=['--no-sandbox']
            )
            print(f"🌐 浏览器模式已启动")
        except Exception as e:
            print(f"⚠️ 浏览器模式初始化失败: {e}")
            browser = None
    
    print(f"🌍 世界杯一键预测 ({args.date})")
    print(f"⚙️ 引擎: {args.engine}\n")
    
    # Step 1: 获取比赛列表
    print("📡 Step 1/3: 新浪API采集...")
    matches = get_matches_for_date(args.date)
    
    if not matches:
        print("⚠️ 新浪API无数据，尝试59itou备用数据源...")
        # 从对照表中找该日比赛
        for mid, (h, g, fh, fa, rd) in WORLDCUP_SINA_MATCHES.items():
            # 只找该日比赛 (走全量)
            pass
    
    results = []
    for m in matches:
        info = parse_match_data(m)
        if not info:
            continue
        
        mid = m.get('matchId', '')
        print(f"  🏟 {info['home']} vs {info['away']} (Round {info['round']})")
        
        # Step 2: 获取欧赔+亚盘
        odds = get_odds(mid)
        if not odds:
            print(f"    ⚠️ 欧赔数据获取失败")
            continue
        
        asian = get_asian(mid)
        info['odds'] = odds
        info['asian'] = asian
        
        # 基本面采集 (v3.0新增)
        form_signal = None
        if hasattr(args, 'fundamental') and args.fundamental:
            try:
                sys.path.insert(0, os.path.dirname(SCOUT_PATH))
                import importlib.util
                spec = importlib.util.spec_from_file_location("scout", SCOUT_PATH)
                scout_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(scout_mod)
                signal, _ = scout_mod.scout_and_build(h, g, fh, fa)
                if signal:
                    form_signal = signal
                    print(f"    📊 基本面: 实力差={signal.get('strength_gap')} 状态差={signal.get('form_diff')}")
            except Exception as e:
                if args.verbose:
                    print(f"    ⚠️ 基本面采集: {e}")
        
        if args.verbose:
            print(f"    欧赔: {odds['o1']} → {odds['o3']}")
            print(f"    升降: 主{odds['r1']}升/{odds['c1']}降 平{odds['r2']}升/{odds['c2']}降 客{odds['r3']}升/{odds['c3']}降")
            print(f"    亚高水: {asian['hh']}家")
        
        # Step 3: 运行引擎
        pred_result = run_v10_prediction(odds, asian, info)
        if pred_result:
            s1, s2, stars = pred_result
            info['score1'] = s1
            info['score2'] = s2
            info['stars'] = stars
            info['rule'] = pred_result  # tuple too, get rule from somewhere
            
            # Hmm, format_result returns (score1, score2, stars) not rule
            # Let me fix: run prediction directly
            print(f"    🎯 预测中...")
        else:
            print(f"    ⚠️ 预测失败")
    
    # Re-run more cleanly with direct import
    print(f"\n⚙️ Step 2/3: v10引擎预测...")
    
    sys.path.insert(0, os.path.dirname(V10_PATH))
    import importlib.util
    spec = importlib.util.spec_from_file_location("v10", V10_PATH)
    v10_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v10_mod)
    
    results = []

    # ========== 并行模式 ==========
    if args.parallel:
        print(f"⚡ 并行模式: {args.workers} workers")
        thread_local = threading.local()
        match_tasks = list(WORLDCUP_SINA_MATCHES.items())

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_map = {}
            for mid, (h, g, fh, fa, rd) in match_tasks:
                future = executor.submit(
                    predict_single_match, mid, h, g, fh, fa, rd, args,
                    form_signal=None, thread_local=thread_local
                )
                future_map[future] = (mid, h, g)

            for future in as_completed(future_map):
                mid, h, g = future_map[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        print(f"  ✅ {h} vs {g}: {result['rule']} → 🎯 {result['score1']}/{result['score2']} ({result['stars']})")
                    else:
                        print(f"  ⚠️ {h} vs {g}: 预测失败")
                except Exception as e:
                    print(f"  ❌ {h} vs {g}: 异常 - {e}")

        # 清理线程本地浏览器
        browser_obj = getattr(thread_local, 'browser', None)
        pw_obj = getattr(thread_local, 'playwright_obj', None)
        if browser_obj:
            try:
                browser_obj.close()
            except:
                pass
        if pw_obj:
            try:
                pw_obj.stop()
            except:
                pass

        # 缓存统计
        if args.verbose:
            s = cache_stats()
            total_files = sum(c['files'] for c in s['categories'].values())
            total_hits = sum(c['hits'] for c in s['categories'].values())
            total_misses = sum(c['misses'] for c in s['categories'].values())
            total_req = total_hits + total_misses
            hr = f"{total_hits/total_req*100:.1f}%" if total_req > 0 else "N/A"
            print(f"📊 缓存: {total_files} 文件, 命中率 {hr} ({total_hits}/{total_req})")

    # ========== 串行模式 (默认) ==========
    else:
        for mid, (h, g, fh, fa, rd) in WORLDCUP_SINA_MATCHES.items():
            # 使用缓存获取欧赔
            odds = cache_get(f"sina_odds_{mid}", category='sina_api')
            if odds is None:
                odds = get_odds(mid)
                if odds:
                    cache_set(f"sina_odds_{mid}", odds, category='sina_api')
            if not odds:
                continue

            # 使用缓存获取亚盘
            asian = cache_get(f"sina_asian_{mid}", category='sina_api')
            if asian is None:
                asian = get_asian(mid)
                if asian:
                    cache_set(f"sina_asian_{mid}", asian, category='sina_api')

            # 基本面侦察 (v3.0)
            form_signal = None

            # 浏览器模式: 采集L2+L3数据
            if browser:
                try:
                    sys.path.insert(0, os.path.dirname(__file__))
                    from automated_all import collect_all
                    bdata = collect_all(browser, h, g, mid)
                    if bdata.get('sources_found'):
                        form_signal = bdata.get('form_signal')
                        print(f"    🌐 浏览器数据: {'+'.join(bdata['sources_found'])}")
                except Exception as e:
                    if args.verbose:
                        print(f"    ⚠️ L2+L3采集: {e}")

            # 非浏览器模式: 仅L1
            if not form_signal and '--fundamental' in sys.argv:
                try:
                    sys.path.insert(0, os.path.dirname(SCOUT_PATH))
                    spec = importlib.util.spec_from_file_location("scout_mod", SCOUT_PATH)
                    sm = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(sm)
                    signal, _ = sm.scout_and_build(h, g, fh, fa)
                    if signal: form_signal = signal
                except: pass

            h_pred, a_pred, rule, conf = v10_mod.predict(
                h=h, g=g, fh=fh, fa=fa,
                o1=odds['o1'], o3=odds['o3'],
                r1=odds['r1'], c1=odds['c1'],
                r2=odds['r2'], c2=odds['c2'],
                r3=odds['r3'], c3=odds['c3'],
                rd=rd,
                form_signal=form_signal
            )

            s1, s2, stars = v10_mod.format_result(h_pred, a_pred, rule, conf)

            # v7.0: 爆冷预警2.0 (串行模式)
            if abs(fh - fa) >= 15:
                try:
                    cold_mod = importlib.util.module_from_spec(
                        importlib.util.spec_from_file_location("cold_mod_s", COLD_PATH)
                    )
                    cold_mod.spec.loader.exec_module(cold_mod)
                    cold_res = cold_mod.analyze_match_cold(
                        h_fifa=fh, a_fifa=fa, h_name=h, a_name=g,
                        o1=odds['o1'], o3=odds['o3'],
                        r1=odds['r1'], c1=odds['c1'],
                        r2=odds['r2'], c2=odds['c2'],
                        r3=odds['r3'], c3=odds['c3'],
                        rd=rd, h_goals=h_pred, a_goals=a_pred, rule=rule, conf_level=conf,
                    )
                    if cold_res.get('warning'):
                        h_pred, a_pred = cold_res['h_goals'], cold_res['a_goals']
                        rule = cold_res['rule']; conf = cold_res['conf_level']
                        s1, s2, stars = v10_mod.format_result(h_pred, a_pred, rule, conf)
                        stars += " ❄️冷" if not stars.endswith("冷") else ""
                except Exception:
                    pass

            # v7.0: 盘口博弈分析 (串行模式)
            try:
                hcp_mod = importlib.util.module_from_spec(
                    importlib.util.spec_from_file_location("hcp_mod_s", HANDICAP_PATH)
                )
                hcp_mod.spec.loader.exec_module(hcp_mod)
                sg = (form_signal or {}).get('strength_gap', fh - fa)
                if abs(sg) >= 5:
                    hcp_diff = round((odds['o3'] - odds['o1']) / 2.0, 2)
                    hcp_str = f"-{hcp_diff}" if hcp_diff > 0 else f"+{abs(hcp_diff)}"
                    hcp_res = hcp_mod.analyze_handicap(
                        strength_gap=sg,
                        handicap=hcp_mod.HandicapData(initial=hcp_str, live=hcp_str),
                        lineup_known=bool(form_signal and form_signal.get('lineup_known'))
                    )
                    if hcp_res['type'] != 'match' and hcp_res['reason']:
                        rule = f"{rule}|{hcp_res['reason']}"
            except Exception:
                pass

            results.append({
                'home': h, 'away': g,
                'fifa_h': fh, 'fifa_a': fa,
                'round': rd,
                'odds': odds,
                'asian': asian,
                'score1': s1, 'score2': s2,
                'rule': rule,
                'stars': stars,
            })

            print(f"  {h} vs {g}: {rule} → 🎯 {s1}/{s2} ({stars})")

            # 保存结构化预测记录 (供model_retrainer误差分析)
            try:
                save_prediction_record(
                    match_id=mid, date_str=args.date,
                    h_name=h, a_name=g, fh=fh, fa=fa, rd=rd,
                    odds=odds, form_signal=form_signal,
                    h_pred=h_pred, a_pred=a_pred, rule=rule, conf=conf,
                    s1=s1, s2=s2, stars=stars,
                )
            except Exception as e:
                if args.verbose:
                    print(f"    ⚠️ 保存预测记录失败: {e}")
    
    if results:
        # 格式化输出
        output = format_predictions(results, args.date)
        print(f"\n{'='*50}")
        print(output)
        
        if args.save:
            save_predictions(output, args.date, args.push)
    else:
        print(f"⚠️ {args.date} 无世界杯比赛数据")
    
    # 清理浏览器
    if browser:
        try:
            browser.close()
            if playwright_obj:
                playwright_obj.stop()
            print("🌐 浏览器已关闭")
        except:
            pass
