#!/usr/bin/env python3
"""
锁定当前新浪API的世界杯比赛数据，生成确定性固定测试集
用法: python3 freeze_testset.py
输出: /tmp/fixed_testset.py（导入用）

注意：Sina API matchID会定期回收，建议每次重要回测前重新锁定
"""
import json, urllib.request, re, sys, os

SINA_BASE = 'https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000'
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# 世界杯matchId范围（随API更新可能变化）
ALL_MIDS = list(range(3625106, 3625134)) + [3623424, 3625083]

def fetch_detail(mid):
    url = f"{SINA_BASE}&cat1=footballMatchDetail&matchId={mid}"
    req = urllib.request.Request(url, headers=HEADERS)
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    d = resp.get('result', {}).get('data', {})
    return d if isinstance(d, dict) else {}

def fetch_odds(mid):
    url = f"{SINA_BASE}&cat1=footballMatchOddsEuro&matchId={mid}"
    req = urllib.request.Request(url, headers=HEADERS)
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    odds = resp.get('result',{}).get('data',[])
    if not odds: return None
    o1s=[float(o.get('o1New',0)) for o in odds if o.get('o1New')]
    o3s=[float(o.get('o3New',0)) for o in odds if o.get('o3New')]
    return {
        'o1': round(sum(o1s)/len(o1s),4), 'o3': round(sum(o3s)/len(o3s),4),
        'r1': sum(1 for o in odds if float(o.get('o1New',0))>float(o.get('o1Ini',0))),
        'c1': sum(1 for o in odds if float(o.get('o1New',0))<float(o.get('o1Ini',0))),
        'r2': sum(1 for o in odds if float(o.get('o2New',0))>float(o.get('o2Ini',0))),
        'c2': sum(1 for o in odds if float(o.get('o2New',0))<float(o.get('o2Ini',0))),
        'r3': sum(1 for o in odds if float(o.get('o3New',0))>float(o.get('o3Ini',0))),
        'c3': sum(1 for o in odds if float(o.get('o3New',0))<float(o.get('o3Ini',0))),
    }

DATA = {}
for mid in ALL_MIDS:
    d = fetch_detail(mid)
    league = d.get('league', '')
    if '世界杯' not in str(league) and 'World Cup' not in str(league):
        continue
    sh, sa = d.get('score1', ''), d.get('score2', '')
    if sh == '' or sa == '': continue
    odds = fetch_odds(mid)
    if not odds: continue
    env = d.get('environment', '')
    mt = re.search(r'(\d+)°C', str(env))
    DATA[mid] = {
        'h': d.get('team1', '?'), 'g': d.get('team2', '?'),
        'fh': int(d.get('team1Position', 0)), 'fa': int(d.get('team2Position', 0)),
        'rd': int(d.get('round', 1)), 'sh': int(sh), 'sa': int(sa),
        **odds,
        'weather': int(d.get('weather', 0)),
        'temp': int(mt.group(1)) if mt else 0,
        'neutral': int(d.get('isNeutral', 0)),
        'env': env,
    }

with open('/tmp/fixed_testset.py', 'w') as f:
    f.write("# 固定测试集 — 确定性回测用\n")
    f.write(f"# 生成时间: {__import__('datetime').datetime.now()}\n")
    f.write("FIXED_MATCHES = {\n")
    for mid, d in sorted(DATA.items()):
        f.write(f"    {mid}: {json.dumps(d, ensure_ascii=False)},\n")
    f.write("}\n")

print(f"✅ 已锁定 {len(DATA)} 场比赛到 /tmp/fixed_testset.py")
