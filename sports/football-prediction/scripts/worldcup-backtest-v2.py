#!/usr/bin/env python3
"""
世界杯全量回测 v2 — 纯赔率 vs 基本面注入双版对比
"""

import json, urllib.request, sys, os
from datetime import datetime

SINA_BASE = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36'}

KNOWN_MATCHES = {
    3625106: ("墨西哥","南非",13,61,1),
    3625107: ("韩国","捷克",22,7,1),
    3625108: ("加拿大","波黑",32,34,1),
    3625109: ("美国","巴拉圭",8,32,1),
    3625110: ("卡塔尔","瑞士",37,22,1),
    3625111: ("巴西","摩洛哥",1,2,1),
    3625112: ("海地","苏格兰",71,30,1),
    3625113: ("澳大利亚","土耳其",27,22,1),
    3625114: ("德国","库拉索",5,77,1),
    3625115: ("荷兰","日本",10,20,1),
    3625116: ("科特迪瓦","厄瓜多尔",23,33,1),
    3625117: ("瑞典","突尼斯",19,26,1),
    3625118: ("西班牙","佛得角",2,67,1),
    3625119: ("比利时","埃及",6,26,1),
    3625120: ("沙特","乌拉圭",58,13,1),
    3625121: ("伊朗","新西兰",22,87,1),
    3625122: ("法国","塞内加尔",1,13,1),
    3625123: ("伊拉克","挪威",55,29,1),
    3625124: ("阿根廷","阿尔及利亚",4,31,1),
    3625125: ("奥地利","约旦",18,57,1),
    3625126: ("葡萄牙","民主刚果",7,47,1),
    3625127: ("英格兰","克罗地亚",4,11,1),
    3625128: ("加纳","巴拿马",73,34,1),
    3625129: ("乌兹别克","哥伦比亚",58,21,1),
    3625130: ("捷克","南非",7,61,2),
    3625131: ("瑞士","波黑",22,63,2),
    3625132: ("加拿大","卡塔尔",32,49,2),
    3625133: ("墨西哥","韩国",13,22,2),
}

ACTUAL_RESULTS = {
    3625106:(2,0),3625107:(2,1),3625108:(1,1),3625109:(4,1),
    3625110:(1,1),3625111:(1,1),3625112:(0,1),3625113:(2,0),
    3625114:(7,1),3625115:(2,2),3625116:(1,0),3625117:(5,1),
    3625118:(0,0),3625119:(1,1),3625120:(1,1),3625121:(2,2),
    3625122:(3,1),3625123:(1,4),3625124:(3,0),3625125:(3,1),
    3625126:(1,1),3625127:(4,2),3625128:(1,0),3625129:(1,3),
    3625130:(1,1),3625131:(4,1),3625132:(6,0),3625133:(1,0),
}

# ===== 基本面信号 (已知关键信息) =====
# 从天天盈球/球探体育采集的关键基本面信息
FORM_SIGNALS = {
    # 美国首轮东道主大胜
    3625109: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':3,'strength_gap':15,'lineup_known':True,'avg_rating_diff':0.3},
    # 加拿大东道主首轮
    3625108: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':0,'strength_gap':5,'lineup_known':True,'avg_rating_diff':0},
    # 巴西vs摩洛哥 - 强强对话
    3625111: {'injury_impact_h':1,'injury_impact_a':0,'form_diff':0,'strength_gap':5,'lineup_known':True,'avg_rating_diff':0.2},
    # 西班牙vs佛得角 - 西班牙顶级强队
    3625118: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':5,'strength_gap':35,'lineup_known':True,'avg_rating_diff':0.8},
    # 德国vs库拉索 - 绝对碾压
    3625114: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':4,'strength_gap':40,'lineup_known':True,'avg_rating_diff':1.2},
    # 法国vs塞内加尔 - 法国强
    3625122: {'injury_impact_h':0,'injury_impact_a':1,'form_diff':3,'strength_gap':20,'lineup_known':True,'avg_rating_diff':0.6},
    # 阿根廷vs阿尔及利亚
    3625124: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':4,'strength_gap':15,'lineup_known':True,'avg_rating_diff':0.5},
    # 英格兰vs克罗地亚
    3625127: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':3,'strength_gap':10,'lineup_known':True,'avg_rating_diff':0.4},
    # 瑞典vs突尼斯
    3625117: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':2,'strength_gap':8,'lineup_known':True,'avg_rating_diff':0.3},
    # 葡萄牙vs民主刚果
    3625126: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':3,'strength_gap':20,'lineup_known':True,'avg_rating_diff':0.7},
    # 瑞士vs波黑
    3625131: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':2,'strength_gap':18,'lineup_known':True,'avg_rating_diff':0.5},
    # 加拿大vs卡塔尔 - 东道主
    3625132: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':1,'strength_gap':10,'lineup_known':True,'avg_rating_diff':0.3},
    # 韩国vs捷克
    3625107: {'injury_impact_h':0,'injury_impact_a':1,'form_diff':0,'strength_gap':-5,'lineup_known':True,'avg_rating_diff':-0.2},
    # 海地vs苏格兰
    3625112: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':-2,'strength_gap':-15,'lineup_known':True,'avg_rating_diff':-0.4},
    # 澳大利亚vs土耳其
    3625113: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':1,'strength_gap':5,'lineup_known':True,'avg_rating_diff':0.2},
    # 荷兰vs日本
    3625115: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':2,'strength_gap':10,'lineup_known':True,'avg_rating_diff':0.3},
    # 伊朗vs新西兰
    3625121: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':1,'strength_gap':15,'lineup_known':True,'avg_rating_diff':0.5},
    # 沙特vs乌拉圭
    3625120: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':-2,'strength_gap':-15,'lineup_known':True,'avg_rating_diff':-0.3},
    # 比利时vs埃及
    3625119: {'injury_impact_h':0,'injury_impact_a':0,'form_diff':2,'strength_gap':10,'lineup_known':True,'avg_rating_diff':0.4},
}


def fetch_odds(mid):
    try:
        url = f"{SINA_BASE}&cat1=footballMatchOddsEuro&matchId={mid}"
        req = urllib.request.Request(url, headers=HEADERS)
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
        odds = resp.get('result',{}).get('data',[])
        if not odds: return None
        o1s=[float(o.get('o1New',0)) for o in odds if o.get('o1New')]
        o3s=[float(o.get('o3New',0)) for o in odds if o.get('o3New')]
        return {
            'o1': round(sum(o1s)/len(o1s),4),'o3': round(sum(o3s)/len(o3s),4),
            'r1': sum(1 for o in odds if float(o.get('o1New',0))>float(o.get('o1Ini',0))),
            'c1': sum(1 for o in odds if float(o.get('o1New',0))<float(o.get('o1Ini',0))),
            'r2': sum(1 for o in odds if float(o.get('o2New',0))>float(o.get('o2Ini',0))),
            'c2': sum(1 for o in odds if float(o.get('o2New',0))<float(o.get('o2Ini',0))),
            'r3': sum(1 for o in odds if float(o.get('o3New',0))>float(o.get('o3Ini',0))),
            'c3': sum(1 for o in odds if float(o.get('o3New',0))<float(o.get('o3Ini',0))),
        }
    except: return None

def fetch_asian(mid):
    try:
        url = f"{SINA_BASE}&cat1=footballMatchOddsAsia&matchId={mid}"
        req = urllib.request.Request(url, headers=HEADERS)
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
        asian = resp.get('result',{}).get('data',[])
        return {'hh': sum(1 for o in asian if float(o.get('o1New',1))>=1.90)}
    except: return {'hh':0}

def run_engine(h,g,fh,fa,o1,o3,r1,c1,r2,c2,r3,c3,rd,use_basics,form_signal):
    v10_path = os.path.join(os.path.dirname(__file__), "worldcup-predict-v10.py")
    sys.path.insert(0, os.path.dirname(v10_path))
    import importlib.util
    spec = importlib.util.spec_from_file_location("v10", v10_path)
    v10 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v10)
    
    if use_basics and form_signal:
        return v10.predict_with_basics(form_signal, h, g, fh, fa, o1, o3, 
                                       r1, c1, r2, c2, r3, c3, rd)
    else:
        return v10.predict(h, g, fh, fa, o1, o3, r1, c1, r2, c2, r3, c3, rd)

def run_backtest(label, use_basics):
    print(f"\n{'='*60}")
    print(f"📊 {label}")
    print(f"{'='*60}")
    
    exact, dir_ok, total = 0, 0, 0
    misses = []
    
    for mid, (h,g,fh,fa,rd) in sorted(KNOWN_MATCHES.items()):
        actual = ACTUAL_RESULTS.get(mid)
        if not actual: continue
        
        odds = fetch_odds(mid)
        if not odds: continue
        asian = fetch_asian(mid)
        total += 1
        
        form_sig = FORM_SIGNALS.get(mid) if use_basics else None
        
        h_pred, a_pred, rule, conf = run_engine(
            h,g,fh,fa,
            odds['o1'],odds['o3'],
            odds['r1'],odds['c1'],
            odds['r2'],odds['c2'],
            odds['r3'],odds['c3'],
            rd,
            use_basics, form_sig
        )
        
        ah, aa = actual
        e = (h_pred==ah and a_pred==aa)
        d = abs(h_pred-ah)<=1 and abs(a_pred-aa)<=1
        if e: exact+=1
        if d: dir_ok+=1
        else: misses.append((h,g,rule,h_pred,a_pred,ah,aa))
        
        s = "✅" if e else ("⚠️" if d else "❌")
        print(f"  {s} {h} vs {g}: {rule} → {h_pred}-{a_pred} 实际{ah}-{aa}")
    
    acc = dir_ok/total*100
    print(f"\n  偏差≤1球: {dir_ok}/{total} = {acc:.1f}%")
    print(f"  精确命中: {exact}/{total} = {exact/total*100:.1f}%")
    if misses:
        print(f"  偏差≥2球: {len(misses)}场")
        for h,g,rule,ph,pa,ah,aa in misses:
            print(f"    ❌ {h} vs {g}: {ph}-{pa} → 实际{ah}-{aa}")
    return acc

if __name__ == "__main__":
    print("🏆 世界杯全量回测 v2 — 双版对比")
    print(f"⏱️ {datetime.now().strftime('%m-%d %H:%M')}\n")
    
    acc1 = run_backtest("🅰 纯赔率版 (无基本面)", use_basics=False)
    acc2 = run_backtest("🅱 基本面注入版 (titan007基本盘)", use_basics=True)
    
    print(f"\n{'='*60}")
    print(f"📊 双版对比结果")
    print(f"{'='*60}")
    print(f"  纯赔率版: {acc1:.1f}%")
    print(f"  基本面版: {acc2:.1f}%")
    diff = acc2 - acc1
    print(f"  差异: {'+' if diff>0 else ''}{diff:.1f}%")
    if diff > 0:
        print(f"  ✅ 基本面注入有效!")
    elif diff < 0:
        print(f"  ⚠️ 基本面注入需调整系数")
    else:
        print(f"  ➡️ 基本面无明显影响")
