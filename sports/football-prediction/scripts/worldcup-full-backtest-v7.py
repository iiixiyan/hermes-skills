#!/usr/bin/env python3
"""
世界杯全量回溯预测 v7.0 (2026-06-21)
完整集成: v10引擎+爆冷预警2.0+盘口博弈+时效性衰减+缓存
仅运行一次已验证的28场全量回测
"""
import json, urllib.request, sys, os, importlib.util
from datetime import datetime

SINA_BASE = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36'}
SCRIPTS = os.path.dirname(__file__)

# 28场已验证比赛
MATCHES = {
    3623416: ("墨西哥","南非",13,61,1),
    3625112: ("韩国","捷克",22,7,1),
    3623420: ("加拿大","波黑",32,34,1),
    3623423: ("美国","巴拉圭",8,32,1),
    3625115: ("卡塔尔","瑞士",37,22,1),
    3625082: ("巴西","摩洛哥",1,2,1),
    3625118: ("海地","苏格兰",71,30,1),
    3625121: ("澳大利亚","土耳其",27,22,1),
    3625088: ("德国","库拉索",5,77,1),
    3625091: ("荷兰","日本",10,20,1),
    3625124: ("科特迪瓦","厄瓜多尔",23,33,1),
    3625127: ("瑞典","突尼斯",19,26,1),
    3625097: ("西班牙","佛得角",2,67,1),
    3625094: ("比利时","埃及",6,26,1),
    3625133: ("沙特","乌拉圭",58,13,1),
    3625130: ("伊朗","新西兰",22,87,1),
    3625100: ("法国","塞内加尔",1,13,1),
    3625141: ("伊拉克","挪威",55,29,1),
    3625103: ("阿根廷","阿尔及利亚",4,31,1),
    3625144: ("奥地利","约旦",18,57,1),
    3625106: ("葡萄牙","刚果金",7,47,1),
    3625109: ("英格兰","克罗地亚",4,11,1),
    3625150: ("加纳","巴拿马",73,34,1),
    3625147: ("乌兹别克","哥伦比亚",58,21,1),
    3625113: ("捷克","南非",7,61,2),
    3625116: ("瑞士","波黑",22,63,2),
    3623421: ("加拿大","卡塔尔",32,49,2),
    3623417: ("墨西哥","韩国",13,22,2),
}

RESULTS = {
    3623416: (2,0), 3625112: (2,1), 3623420: (1,1), 3623423: (4,1),
    3625115: (1,1), 3625082: (1,1), 3625118: (0,1), 3625121: (2,0),
    3625088: (7,1), 3625091: (2,2), 3625124: (1,0), 3625127: (5,1),
    3625097: (0,0), 3625094: (1,1), 3625133: (1,1), 3625130: (2,2),
    3625100: (3,1), 3625141: (1,4), 3625103: (3,0), 3625144: (3,1),
    3625106: (1,1), 3625109: (4,2), 3625150: (1,0), 3625147: (1,3),
    3625113: (1,1), 3625116: (4,1), 3623421: (6,0), 3623417: (1,0),
}

def fetch_odds(mid):
    try:
        url = f"{SINA_BASE}&cat1=footballMatchOddsEuro&matchId={mid}"
        resp = json.loads(urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=15).read())
        odds = resp.get('result',{}).get('data',[])
        if not odds: return None
        o1s=[float(o.get('o1New',0)) for o in odds if o.get('o1New')]
        o3s=[float(o.get('o3New',0)) for o in odds if o.get('o3New')]
        return {
            'o1':round(sum(o1s)/len(o1s),4) if o1s else 0,
            'o3':round(sum(o3s)/len(o3s),4) if o3s else 0,
            'r1':sum(1 for o in odds if float(o.get('o1New',0))>float(o.get('o1Ini',0))),
            'c1':sum(1 for o in odds if float(o.get('o1New',0))<float(o.get('o1Ini',0))),
            'r2':sum(1 for o in odds if float(o.get('o2New',0))>float(o.get('o2Ini',0))),
            'c2':sum(1 for o in odds if float(o.get('o2New',0))<float(o.get('o2Ini',0))),
            'r3':sum(1 for o in odds if float(o.get('o3New',0))>float(o.get('o3Ini',0))),
            'c3':sum(1 for o in odds if float(o.get('o3New',0))<float(o.get('o3Ini',0))),
        }
    except: return None

def load_v10():
    p = os.path.join(SCRIPTS,"worldcup-predict-v10.py")
    spec = importlib.util.spec_from_file_location("v10",p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

print("="*70)
print(f"🌍 世界杯全量回溯预测 v7.0 — {datetime.now().strftime('%m-%d %H:%M')}")
print("   引擎: v10.8c (爆冷预警2.0内置) + 缓存层")
print("="*70)

v10 = load_v10()
exact, dir_ok, total = 0, 0, 0
misses, details = [], []

for mid,(h,g,fh,fa,rd) in sorted(MATCHES.items()):
    actual = RESULTS.get(mid)
    if not actual: continue
    total += 1
    odds = fetch_odds(mid)
    if not odds:
        details.append((mid,h,g,"❌ API无数据","-","-",actual))
        misses.append((mid,h,g,"API无数据"))
        continue
    
    try:
        h_pred, a_pred, rule, conf = v10.predict(
            h=h, g=g, fh=fh, fa=fa,
            o1=odds['o1'], o3=odds['o3'],
            r1=odds['r1'], c1=odds['c1'],
            r2=odds['r2'], c2=odds['c2'],
            r3=odds['r3'], c3=odds['c3'],
            rd=rd
        )
    except Exception as e:
        details.append((mid,h,g,f"❌ 引擎",f"{h_pred if 'h_pred' in dir() else '?'}-{a_pred if 'a_pred' in dir() else '?'}",actual))
        misses.append((mid,h,g,str(e)[:50]))
        continue
    
    a_h, a_a = actual
    dev = max(abs(h_pred-a_h), abs(a_pred-a_a))
    is_exact = h_pred==a_h and a_pred==a_a
    is_dir = (h_pred > a_pred and a_h > a_a) or (h_pred < a_pred and a_h < a_a) or (h_pred == a_pred and a_h == a_a)
    
    if is_exact: exact += 1
    if is_dir: dir_ok += 1
    
    tag = "✅" if is_exact else ("⚠️" if dev <= 1 else "❌")
    details.append((mid,h,g,tag,rule,f"{h_pred}-{a_pred}",actual,f"{a_h}-{a_a}",dev,conf))
    
    if dev >= 2:
        misses.append((mid,h,g,f"偏差{dev}球: {h_pred}-{a_pred} → 实际{a_h}-{a_a} ({rule})"))

# ====== 输出报告 ======
print(f"\n{'='*70}")
print(f"📊 回溯结果汇总 ({total}场) — v7.0引擎")
print(f"  ✅ 精确命中: {exact}/{total} = {exact/total*100:.1f}%")
print(f"  ⚠️ 方向正确: {dir_ok}/{total} = {dir_ok/total*100:.1f}%")
dev_le_1 = sum(1 for d in details if len(d)>8 and d[8]<=1)
print(f"  偏差≤1球: {dev_le_1}/{total}")
print(f"{'='*70}")

if misses:
    print(f"\n❌ 偏差≥2球场次 ({len(misses)}场):")
    for m in misses: print(f"  {m[0]} {m[1]} vs {m[2]}: {m[3]}")

# 逐场明细
print(f"\n{'='*70}")
print("🔬 逐场明细:")
print(f"{'#':>4} {'主队':<10} {'客队':<10} {'结果':>6} {'规则':<22} {'比分':>8}")
print("-"*70)
for i,d in enumerate(details):
    if len(d) >= 9:
        stars = '★' * d[9] if d[9] else ''
        print(f"{i+1:>3} {d[1]:<10} {d[2]:<10} {d[3]:>4} {d[4]:<22} {d[5]:>8} 实{d[7]:>6} 偏{d[8]:>2} {stars}")
    else:
        print(f"{i+1:>3} {d[1]:<10} {d[2]:<10} {d[3]:>4} {d[4]:<22}")
