#!/usr/bin/env python3
"""
世界杯全量回测 v3 — 基于titan007真实数据的验证
"""

import json, urllib.request, sys, os
from datetime import datetime

SINA_BASE = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

KNOWN_MATCHES = {
    3625106:("墨西哥","南非",13,61,1),3625107:("韩国","捷克",22,7,1),
    3625108:("加拿大","波黑",32,34,1),3625109:("美国","巴拉圭",8,32,1),
    3625110:("卡塔尔","瑞士",37,22,1),3625111:("巴西","摩洛哥",1,2,1),
    3625112:("海地","苏格兰",71,30,1),3625113:("澳大利亚","土耳其",27,22,1),
    3625114:("德国","库拉索",5,77,1),3625115:("荷兰","日本",10,20,1),
    3625116:("科特迪瓦","厄瓜多尔",23,33,1),3625117:("瑞典","突尼斯",19,26,1),
    3625118:("西班牙","佛得角",2,67,1),3625119:("比利时","埃及",6,26,1),
    3625120:("沙特","乌拉圭",58,13,1),3625121:("伊朗","新西兰",22,87,1),
    3625122:("法国","塞内加尔",1,13,1),3625123:("伊拉克","挪威",55,29,1),
    3625124:("阿根廷","阿尔及利亚",4,31,1),3625125:("奥地利","约旦",18,57,1),
    3625126:("葡萄牙","民主刚果",7,47,1),3625127:("英格兰","克罗地亚",4,11,1),
    3625128:("加纳","巴拿马",73,34,1),3625129:("乌兹别克","哥伦比亚",58,21,1),
    3625130:("捷克","南非",7,61,2),3625131:("瑞士","波黑",22,63,2),
    3625132:("加拿大","卡塔尔",32,49,2),3625133:("墨西哥","韩国",13,22,2),
}

ACTUAL = {
    3625106:(2,0),3625107:(2,1),3625108:(1,1),3625109:(4,1),
    3625110:(1,1),3625111:(1,1),3625112:(0,1),3625113:(2,0),
    3625114:(7,1),3625115:(2,2),3625116:(1,0),3625117:(5,1),
    3625118:(0,0),3625119:(1,1),3625120:(1,1),3625121:(2,2),
    3625122:(3,1),3625123:(1,4),3625124:(3,0),3625125:(3,1),
    3625126:(1,1),3625127:(4,2),3625128:(1,0),3625129:(1,3),
    3625130:(1,1),3625131:(4,1),3625132:(6,0),3625133:(1,0),
}

# 从titan007采集的真实伤停数据
TITAN007_INJURIES = {
    # matchId: (injury_h, injury_a) 0=none, 1=minor, 2=key
    3625106: (0, 1),  # 南非后卫疑似伤病
    3625107: (0, 0),  # 无伤停
}

# 无titan007伤停数据的用经验默认值
def get_form_signal(mid):
    """获取基本面信号（titan007真实数据优先，无则退化为经验值）"""
    inj = TITAN007_INJURIES.get(mid)
    if inj:
        return {
            'injury_impact_h': inj[0],
            'injury_impact_a': inj[1],
            'form_diff': 0,
            'strength_gap': 0,
            'lineup_known': False,
            'avg_rating_diff': 0,
        }
    return None

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

def run(mode):
    v10_path = os.path.join(os.path.dirname(__file__), "worldcup-predict-v10.py")
    sys.path.insert(0, os.path.dirname(v10_path))
    import importlib.util
    spec = importlib.util.spec_from_file_location("v10", v10_path)
    v10 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v10)
    
    exact, dir_ok, total = 0, 0, 0
    print(f"\n{'='*50}")
    print(f"{'🅰 纯赔率' if mode=='pure' else '🅱 titan007基本面'}")
    print(f"{'='*50}")
    
    for mid, (h,g,fh,fa,rd) in sorted(KNOWN_MATCHES.items()):
        act = ACTUAL.get(mid)
        if not act: continue
        odds = fetch_odds(mid)
        if not odds: continue
        total += 1
        
        if mode == 'pure':
            h_pred, a_pred, rule, conf = v10.predict(h,g,fh,fa,
                odds['o1'],odds['o3'],odds['r1'],odds['c1'],
                odds['r2'],odds['c2'],odds['r3'],odds['c3'],rd)
        else:
            fs = get_form_signal(mid)
            if fs:
                h_pred, a_pred, rule, conf = v10.predict_with_basics(fs, h,g,fh,fa,
                    odds['o1'],odds['o3'],odds['r1'],odds['c1'],
                    odds['r2'],odds['c2'],odds['r3'],odds['c3'],rd)
            else:
                h_pred, a_pred, rule, conf = v10.predict(h,g,fh,fa,
                    odds['o1'],odds['o3'],odds['r1'],odds['c1'],
                    odds['r2'],odds['c2'],odds['r3'],odds['c3'],rd)
        
        ah, aa = act
        e = (h_pred==ah and a_pred==aa)
        d = abs(h_pred-ah)<=1 and abs(a_pred-aa)<=1
        if e: exact+=1
        if d: dir_ok+=1
        s = "✅" if e else ("⚠️" if d else "❌")
        print(f"  {s} {h} vs {g}: {rule} → {h_pred}-{a_pred} 实际{ah}-{aa}")
    
    acc = dir_ok/total*100
    print(f"\n  偏差≤1球: {dir_ok}/{total} = {acc:.1f}%")
    return acc

if __name__ == "__main__":
    print(f"🏆 世界杯全量回测 v3 — 真实titan007数据验证")
    print(f"⏱️ {datetime.now().strftime('%m-%d %H:%M')}")
    
    a1 = run('pure')
    a2 = run('titan007')
    
    print(f"\n{'='*50}")
    print(f"📊 最终结论")
    print(f"{'='*50}")
    print(f"  纯赔率版:     {a1:.1f}%")
    print(f"  titan007基本面: {a2:.1f}%")
    print(f"")
    print(f"  ⚠️ titan007历史比赛球员评分为空")
    print(f"  ⚠️ 仅伤停数据可用(28场中2场有)")
    print(f"  ✅ 模型对未来比赛的基本面修正管线已就绪")
    print(f"  ✅ predict_with_basics() 可直接用于赛前预测")
