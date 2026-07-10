#!/usr/bin/env python3
"""
L2全自动管线 v2.1 — 稳定版
Playwright→titan007→form_signal→v10引擎
集成到worldcup-predict-all.py的--browser模式

用法:
  from automated_l2 import collect_l2_data, predict_with_l2
  t7 = collect_l2_data(browser, schedule_id)
  h, a, rule, conf = predict_with_l2(h, g, ..., t7_data=t7)
"""
import os, sys, re, json, importlib.util
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/usr/bin'

SCRIPTS_DIR = "/root/.hermes/skills/sports/football-prediction/scripts"

# ============================================================
#  核心函数
# ============================================================

def fetch_titan007(browser, analysis_id, timeout=10000):
    """Playwright导航到titan007分析页，提取全部基本盘数据"""
    page = browser.new_page()
    page.set_extra_http_headers({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })
    
    url = f"https://info.titan007.com/analysis/{analysis_id}cn.htm"
    resp = page.goto(url, timeout=timeout, wait_until='domcontentloaded')
    
    if not resp or resp.status != 200:
        page.close()
        return None
    
    title = page.title()
    body = page.inner_text('body')
    page.close()
    
    if len(body) < 200:
        return None
    
    # 从title提取队名: "澳大利亚 VS 土耳其(2026赛季世界杯)..."
    title_m = re.match(r'^(.+?)\s*VS\s*(.+?)\(', title)
    
    data = {
        'analysis_id': analysis_id,
        'title': title,
        't7_h': title_m.group(1).strip() if title_m else None,
        't7_a': title_m.group(2).strip() if title_m else None,
        'body_length': len(body),
    }
    
    # 比分
    sm = re.search(r'(\d+)\s*完\s*\((\d+-\d+)\)\s*(\d+)', body)
    if sm:
        data['h_score'] = int(sm.group(1))
        data['a_score'] = int(sm.group(3))
        data['ht_score'] = sm.group(2)
    
    # 天气场地
    m = re.search(r'场地[：:]\s*(.+?)\s*天气[：:]\s*(.+?)\s*温度[：:]\s*(\S+)', body)
    if m:
        data['venue'] = m.group(1).strip()
        data['weather'] = m.group(2).strip()
        data['temperature'] = m.group(3).strip()
    
    # 杯赛积分排名
    idx = body.find('杯赛积分排名')
    if idx >= 0:
        data['group_standings'] = body[idx:idx+800]
    
    # 球员评分
    avg_ratings = re.findall(r'平均评分\s*(\d+\.?\d*)', body)
    if len(avg_ratings) >= 2:
        data['h_avg_rating'] = float(avg_ratings[0])
        data['a_avg_rating'] = float(avg_ratings[1])
        data['avg_rating_diff'] = round(data['h_avg_rating'] - data['a_avg_rating'], 2)
    
    # 首发评分
    starters = re.findall(r'(\d+)\t([\u4e00-\u9fff\s]+)\t([\u4e00-\u9fff\s]+)\t\*\t(\d+\.?\d*)', body)
    if starters:
        data['starters_count'] = len(starters)
        ratings = [float(s[3]) for s in starters if s[3]]
        data['avg_starter_rating'] = round(sum(ratings) / len(ratings), 2) if ratings else 0
    
    # 伤停
    idx = body.find('阵容情况')
    if idx >= 0:
        section = body[idx:idx+800]
        data['injury_impact_h'] = min(len(re.findall(r'主队.*?(?:伤|缺|疑)', section)), 2)
        data['injury_impact_a'] = min(len(re.findall(r'客队.*?(?:伤|缺|疑)', section)), 2)
        data['has_injury_data'] = True
    
    # 近期战绩
    m = re.search(r'近(\d+)场,胜(\d+)平(\d+)负(\d+),\s*胜率:(\d+)%', body)
    if m:
        data['recent'] = {
            'total': int(m.group(1)), 'w': int(m.group(2)),
            'd': int(m.group(3)), 'l': int(m.group(4)),
            'win_rate': int(m.group(5))
        }
    
    # 场均进球
    m = re.search(r'场均进球\s*([\d.]+)\s*场均进球\s*([\d.]+)', body)
    if m:
        data['h_avg_goals'] = float(m.group(1))
        data['a_avg_goals'] = float(m.group(2))
    
    # 对赛往绩
    idx = body.find('对赛往绩')
    if idx >= 0:
        data['h2h'] = body[idx:idx+400]
    
    return data


def titan007_to_form_signal(t7_data):
    """titan007数据 → form_signal字典（直接合并到L1信号）"""
    if not t7_data:
        return {}
    
    sig = {}
    if 'avg_rating_diff' in t7_data:
        sig['avg_rating_diff'] = t7_data['avg_rating_diff']
        sig['form_diff'] = int(t7_data['avg_rating_diff'] * 5)
    if t7_data.get('has_injury_data'):
        sig['injury_impact_h'] = t7_data.get('injury_impact_h', 0)
        sig['injury_impact_a'] = t7_data.get('injury_impact_a', 0)
    if t7_data.get('starters_count', 0) > 0:
        sig['lineup_known'] = True
    if t7_data.get('temperature'):
        sig['temperature'] = t7_data['temperature']
        sig['weather'] = t7_data.get('weather', '')
    if 'h_avg_goals' in t7_data and 'a_avg_goals' in t7_data:
        sig['goal_diff'] = int((t7_data['h_avg_goals'] - t7_data['a_avg_goals']) * 10)
    sig['sources_used'] = ['titan007']
    return sig


def collect_l2_data(browser, schedule_id, h_name, a_name, scan_range=(2906740, 2906810)):
    """
    自动采集L2数据: 扫描titan007分析页找到匹配比赛 → 提取数据
    返回: (t7_data_dict, match_found_bool)
    """
    for aid in range(scan_range[0], scan_range[1]):
        t7 = fetch_titan007(browser, aid)
        if not t7 or not t7.get('t7_h'):
            continue
        
        t7_h = t7['t7_h']
        # 双向匹配: 我们的队名包含titan007的片断 或 vice versa
        if (h_name[:2] in t7_h or t7_h[:2] in h_name or 
            h_name[:3] in t7_h or (len(h_name) >= 4 and h_name[:4] in t7_h)):
            return t7, True
    
    return None, False


# ============================================================
#  引擎加载
# ============================================================

def _load_engine():
    spec = importlib.util.spec_from_file_location("_v10", f"{SCRIPTS_DIR}/worldcup-predict-v10.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _load_scout():
    spec = importlib.util.spec_from_file_location("_scout", f"{SCRIPTS_DIR}/fundamental_scout.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def predict_with_l2(h, g, fh, fa, rd, o1, o3, r1, c1, r2, c2, r3, c3, t7_data=None):
    """L1(API) + L2(titan007) → v10引擎预测"""
    engine = _load_engine()
    scout = _load_scout()
    
    # L1
    l1_signal, _ = scout.scout_and_build(h, g, fh, fa)
    
    # L2
    l2_signal = titan007_to_form_signal(t7_data) if t7_data else {}
    
    # 合并 (L2叠加到L1上，不覆盖L1已存在的字段)
    final = dict(l1_signal or {})
    if l2_signal:
        for k, v in l2_signal.items():
            if v is not None and v != 0 and v != '' and v != []:
                if k == 'sources_used':
                    final['sources_used'] = final.get('sources_used', []) + v
                else:
                    final[k] = v
    
    h_pred, a_pred, rule, conf = engine.predict(
        h=h, g=g, fh=fh, fa=fa,
        o1=o1, o3=o3, r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3,
        rd=rd, form_signal=final if final.get('sources_used') else None
    )
    return h_pred, a_pred, rule, conf, final


if __name__ == "__main__":
    print("L2自动管线 v2.1")
    print()
    print("集成方式:")
    print("  在worldcup-predict-all.py中:") 
    print("  from automated_l2 import collect_l2_data, predict_with_l2")
    print()
    print("  1. browser = playwright.chromium.launch(...)")
    print("  2. t7_data, found = collect_l2_data(browser, sid, h_name, a_name)")
    print("  3. h, a, rule, conf, sig = predict_with_l2(h, g, ..., t7_data=t7_data)")
    print("  4. browser.close()")
