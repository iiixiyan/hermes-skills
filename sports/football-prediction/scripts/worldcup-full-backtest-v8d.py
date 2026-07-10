#!/usr/bin/env python3
"""世界杯31场全量回测 v10.8d — 含积分驱动MUSTWIN"""
import sys, json, urllib.request, importlib.util
sys.path.insert(0, '.')

spec = importlib.util.spec_from_file_location('wcp', 'worldcup-predict-v10.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SINA = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000"
HDR = {'User-Agent': 'Mozilla/5.0 (Linux; Android 14)'}

# (mid, h, a, sh, sa, rd, fh, fa)
MATCHES = [
    (3623416,"墨西哥","南非",2,0,1,13,61),
    (3625112,"韩国","捷克",2,1,1,22,7),
    (3623420,"加拿大","波黑",1,1,1,32,34),
    (3623423,"美国","巴拉圭",4,1,1,8,32),
    (3625115,"卡塔尔","瑞士",1,1,1,37,22),
    (3625082,"巴西","摩洛哥",1,1,1,1,2),
    (3625118,"海地","苏格兰",0,1,1,71,30),
    (3625121,"澳大利亚","土耳其",2,0,1,27,22),
    (3625088,"德国","库拉索",7,1,1,5,77),
    (3625091,"荷兰","日本",2,2,1,10,20),
    (3625124,"科特迪瓦","厄瓜多尔",1,0,1,23,33),
    (3625127,"瑞典","突尼斯",5,1,1,19,26),
    (3625097,"西班牙","佛得角",0,0,1,2,67),
    (3625094,"比利时","埃及",1,1,1,6,26),
    (3625133,"沙特","乌拉圭",1,1,1,58,13),
    (3625130,"伊朗","新西兰",2,2,1,22,87),
    (3625100,"法国","塞内加尔",3,1,1,1,13),
    (3625141,"伊拉克","挪威",1,4,1,55,29),
    (3625103,"阿根廷","阿尔及利亚",3,0,1,4,31),
    (3625144,"奥地利","约旦",3,1,1,18,57),
    (3625106,"葡萄牙","刚果金",1,1,1,7,58),
    (3625109,"英格兰","克罗地亚",4,2,1,4,13),
    (3625150,"加纳","巴拿马",1,0,1,73,34),
    (3625147,"乌兹别克","哥伦比亚",1,3,2,77,12),
    (3625113,"捷克","南非",1,1,2,7,61),
    (3625116,"瑞士","波黑",4,1,2,22,63),
    (3623421,"加拿大","卡塔尔",1,1,2,32,49),
    (3623417,"墨西哥","韩国",1,0,2,13,22),
    (3625092,"荷兰","瑞典",5,1,2,10,34),
    (3625089,"德国","科特迪瓦",1,0,2,5,33),
    (3625125,"厄瓜多尔","库拉索",0,0,2,33,77),
]

# ===== 计算积分 =====
def compute_points(matches):
    pts = {}
    r1_matches = [m for m in matches if m[5] == 1]
    for mid, h, a, sh, sa, rd, fh, fa in r1_matches:
        if h not in pts: pts[h] = 0
        if a not in pts: pts[a] = 0
        if sh > sa: pts[h] += 3
        elif sh < sa: pts[a] += 3
        else:
            pts[h] += 1
            pts[a] += 1
    return pts

points = compute_points(MATCHES)

# 已知但不在MATCHES表内的R1积分（一些比赛R1结果在采集范围外）
KNOWN_POINTS = {
    '乌兹别克': 0,   # R1负于挪威
    '哥伦比亚': 3,   # R1击败厄瓜多尔
}
# 补充已知积分
for team, pt in KNOWN_POINTS.items():
    if team not in points:
        points[team] = pt

def fetch_odds(mid):
    """从新浪API获取欧赔 (对所有公司平均+变盘计数)"""
    url = f"{SINA}&cat1=footballMatchOddsEuro&matchId={mid}"
    req = urllib.request.Request(url, headers=HDR)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        odds = data.get('result', {}).get('data', [])
        if not odds:
            return None
        o1s = [float(o.get('o1New',0)) for o in odds if o.get('o1New')]
        o3s = [float(o.get('o3New',0)) for o in odds if o.get('o3New')]
        return {
            'o1': round(sum(o1s)/len(o1s), 4) if o1s else 0,
            'o3': round(sum(o3s)/len(o3s), 4) if o3s else 0,
            'r1': sum(1 for o in odds if float(o.get('o1New',0)) > float(o.get('o1Ini',0))),
            'c1': sum(1 for o in odds if float(o.get('o1New',0)) < float(o.get('o1Ini',0))),
            'r2': sum(1 for o in odds if float(o.get('o2New',0)) > float(o.get('o2Ini',0))),
            'c2': sum(1 for o in odds if float(o.get('o2New',0)) < float(o.get('o2Ini',0))),
            'r3': sum(1 for o in odds if float(o.get('o3New',0)) > float(o.get('o3Ini',0))),
            'c3': sum(1 for o in odds if float(o.get('o3New',0)) < float(o.get('o3Ini',0))),
        }
    except:
        return None

# ===== 全量回测 =====
hits = 0
total = 0
dir_hits = 0
dev1 = 0
dev2plus = 0
deviations = []

for mid, h, a, sh, sa, rd, fh, fa in MATCHES:
    total += 1
    od = fetch_odds(mid)
    if not od:
        print(f"  ⚠️  跳过 {h}vs{a} (mid={mid}): 无欧赔数据")
        continue
    o1, o3 = od['o1'], od['o3']
    r1, c1, r2, c2, r3, c3 = od['r1'], od['c1'], od['r2'], od['c2'], od['r3'], od['c3']
    
    # 积分
    pts_h = points.get(h, -1)
    pts_a = points.get(a, -1)
    # R1不用积分; R2有积分数据才传
    if pts_h == -1 or pts_a == -1 or rd == 1:
        pt_h, pt_a = -1, -1
    else:
        pt_h, pt_a = pts_h, pts_a
    
    h_pred, a_pred, rule, conf = mod.predict(
        h=h, g=a, fh=fh, fa=fa,
        o1=o1, o3=o3,
        r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3,
        rd=rd,
        pts_h=pt_h, pts_a=pt_a
    )
    
    exact = (h_pred == sh and a_pred == sa)
    dir_ok = (sh > sa and h_pred > a_pred) or (sh < sa and h_pred < a_pred) or (sh == sa and h_pred == a_pred)
    deviation = abs(h_pred - sh) + abs(a_pred - sa)
    
    if exact: hits += 1
    if dir_ok: dir_hits += 1
    if deviation <= 1: dev1 += 1
    else:
        dev2plus += 1
        deviations.append((h, a, sh, sa, h_pred, a_pred, deviation, rule))
    
    status = "✅" if exact else ("🟡" if deviation <= 1 else "❌")
    mk = f"{status} {h:<8} {sh}-{sa} | 预测 {h_pred}-{a_pred} | {rule} | "
    mk += f"方向{'✓' if dir_ok else '✗'} | 偏差{deviation}球"
    if pt_h >= 0:
        mk += f" [积分:{pts_h}vs{pts_a}]"
    print(mk)

print()
print(f"{'='*50}")
print(f"全量回测报告 (v10.8d, {total}场)")
print(f"{'='*50}")
print(f"精确命中:  {hits}/{total} = {100*hits/total:.1f}%")
print(f"方向正确:  {dir_hits}/{total} = {100*dir_hits/total:.1f}%")
print(f"偏差≤1球:  {dev1}/{total} = {100*dev1/total:.1f}%")
print(f"偏差≥2球:  {dev2plus}/{total} = {100*dev2plus/total:.1f}%")
if deviations:
    print(f"\n偏差明细:")
    for h, a, sh, sa, hp, ap, dv, rule in deviations:
        print(f"  ❌ {h}vs{a}: 实际{sh}-{sa} 预测{hp}-{ap} (偏差{dv}球) [{rule}]")
