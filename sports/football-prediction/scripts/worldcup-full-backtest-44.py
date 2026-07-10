#!/usr/bin/env python3
"""世界杯44场全量回测 v10.8h — 从零拉取实时数据，不参考历史预测"""
import sys, json, urllib.request, importlib.util
sys.path.insert(0, '/root/.hermes/skills/sports/football-prediction/scripts')

spec = importlib.util.spec_from_file_location(
    'wcp', '/root/.hermes/skills/sports/football-prediction/scripts/worldcup-predict-v10.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SINA = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000"
HDR = {'User-Agent': 'Mozilla/5.0 (Linux; Android 14)'}

# ===== 完整44场 =====
# (mid, h, a, sh, sa, rd, fh, fa, 官方match_num)
MATCHES = [
    # === Round 1 (24 matches, #4001-#4024) ===
    (3623416,"墨西哥","南非",2,0,1,13,61,4001),
    (3625112,"韩国","捷克",2,1,1,22,7,4002),
    (3623420,"加拿大","波黑",1,1,1,32,34,4003),
    (3623423,"美国","巴拉圭",4,1,1,8,32,4004),
    (3625115,"卡塔尔","瑞士",1,1,1,37,22,4005),
    (3625082,"巴西","摩洛哥",1,1,1,1,2,4006),
    (3625118,"海地","苏格兰",0,1,1,71,30,4007),
    (3625121,"澳大利亚","土耳其",2,0,1,27,22,4008),
    (3625088,"德国","库拉索",7,1,1,5,77,4009),
    (3625091,"荷兰","日本",2,2,1,10,20,4010),
    (3625124,"科特迪瓦","厄瓜多尔",1,0,1,23,33,4011),
    (3625127,"瑞典","突尼斯",5,1,1,19,26,4012),
    (3625097,"西班牙","佛得角",0,0,1,2,67,4013),
    (3625094,"比利时","埃及",1,1,1,6,26,4014),
    (3625133,"沙特","乌拉圭",1,1,1,58,13,4015),
    (3625130,"伊朗","新西兰",2,2,1,22,87,4016),
    (3625100,"法国","塞内加尔",3,1,1,1,13,4017),
    (3625141,"伊拉克","挪威",1,4,1,55,29,4018),
    (3625103,"阿根廷","阿尔及利亚",3,0,1,4,31,4019),
    (3625144,"奥地利","约旦",3,1,1,18,57,4020),
    (3625106,"葡萄牙","刚果金",1,1,1,7,58,4021),
    (3625109,"英格兰","克罗地亚",4,2,1,4,13,4022),
    (3625150,"加纳","巴拿马",1,0,1,73,34,4023),
    (3625147,"乌兹别克","哥伦比亚",1,3,1,77,12,4024),
    # === Round 2 (12 matches, #4025-#4036) ===
    (3625113,"捷克","南非",1,1,2,7,61,4025),
    (3625116,"瑞士","波黑",4,1,2,22,63,4026),
    (3623421,"加拿大","卡塔尔",6,0,2,32,49,4027),
    (3623417,"墨西哥","韩国",1,0,2,13,22,4028),
    (3623424,"美国","澳大利亚",2,0,2,8,27,4029),
    (3625119,"苏格兰","摩洛哥",0,1,2,30,6,4030),
    (3625083,"巴西","海地",3,0,2,1,85,4031),
    (3625122,"土耳其","巴拉圭",0,1,2,22,42,4032),
    (3625092,"荷兰","瑞典",5,1,2,10,34,4033),
    (3625089,"德国","科特迪瓦",2,1,2,5,33,4034),
    (3625125,"厄瓜多尔","库拉索",0,0,2,33,77,4035),
    (3625128,"突尼斯","日本",0,4,2,19,20,4036),
    # === Round 3 (8 matches, #4037-#4044) ===
    (3625098,"西班牙","沙特",4,0,3,2,53,4037),
    (3625095,"比利时","伊朗",0,0,3,6,22,4038),
    (3625139,"乌拉圭","佛得角",2,2,3,13,63,4039),
    (3625131,"新西兰","埃及",1,3,3,83,28,4040),
    (3625104,"阿根廷","奥地利",2,0,3,4,28,4041),
    (3625101,"法国","伊拉克",3,0,3,1,57,4042),
    (3625142,"挪威","塞内加尔",3,2,3,29,13,4043),
    (3625145,"约旦","阿尔及利亚",1,2,3,57,31,4044),
]

# ===== 计算积分（R1结果 → 用于R2/R3）=====
def compute_points(matches):
    pts = {}
    for mid, h, a, sh, sa, rd, fh, fa, mn in matches:
        if rd != 1: continue
        if h not in pts: pts[h] = 0
        if a not in pts: pts[a] = 0
        if sh > sa: pts[h] += 3
        elif sh < sa: pts[a] += 3
        else:
            pts[h] += 1
            pts[a] += 1
    return pts

points = compute_points(MATCHES)

def fetch_odds(mid):
    """从新浪API获取欧赔"""
    url = f"{SINA}&cat1=footballMatchOddsEuro&matchId={mid}"
    req = urllib.request.Request(url, headers=HDR)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        odds = data.get('result', {}).get('data', [])
        if not odds:
            return None
        o1s = [float(o.get('o1New',0)) for o in odds if o.get('o1New')]
        o2s = [float(o.get('o2New',0)) for o in odds if o.get('o2New')]
        o3s = [float(o.get('o3New',0)) for o in odds if o.get('o3New')]
        return {
            'o1': round(sum(o1s)/len(o1s), 4) if o1s else 0,
            'o2': round(sum(o2s)/len(o2s), 4) if o2s else 0,
            'o3': round(sum(o3s)/len(o3s), 4) if o3s else 0,
            'r1': sum(1 for o in odds if float(o.get('o1New',0)) > float(o.get('o1Ini',0))),
            'c1': sum(1 for o in odds if float(o.get('o1New',0)) < float(o.get('o1Ini',0))),
            'r2': sum(1 for o in odds if float(o.get('o2New',0)) > float(o.get('o2Ini',0))),
            'c2': sum(1 for o in odds if float(o.get('o2New',0)) < float(o.get('o2Ini',0))),
            'r3': sum(1 for o in odds if float(o.get('o3New',0)) > float(o.get('o3Ini',0))),
            'c3': sum(1 for o in odds if float(o.get('o3New',0)) < float(o.get('o3Ini',0))),
        }
    except Exception as e:
        print(f"  ⚠️ mid={mid} 采集失败: {e}")
        return None

# ===== 全量回测 =====
print("="*60)
print("世界杯44场全量回测 — 实时数据拉取")
print("="*60)

hits = 0
total = 0
dir_hits = 0
dev1 = 0
dev2plus = 0
deviations = []
all_results = []
missing_odds = 0

for mid, h, a, sh, sa, rd, fh, fa, mn in MATCHES:
    total += 1
    od = fetch_odds(mid)
    if not od:
        print(f"  ⚠️  跳过 #{mn} {h}vs{a}: 无欧赔数据")
        missing_odds += 1
        continue
    
    o1, o2, o3 = od['o1'], od['o2'], od['o3']
    r1, c1, r2, c2, r3, c3 = od['r1'], od['c1'], od['r2'], od['c2'], od['r3'], od['c3']
    
    # 积分
    pts_h = points.get(h, -1)
    pts_a = points.get(a, -1)
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
    dir_ok = ((sh > sa and h_pred > a_pred) or 
              (sh < sa and h_pred < a_pred) or 
              (sh == sa and h_pred == a_pred))
    deviation = abs(h_pred - sh) + abs(a_pred - sa)
    
    if exact: hits += 1
    if dir_ok: dir_hits += 1
    if deviation <= 1: dev1 += 1
    else:
        dev2plus += 1
        deviations.append((h, a, sh, sa, h_pred, a_pred, deviation, rule, mn))
    
    status = "🎯" if exact else ("🟡" if deviation <= 1 else "❌")
    all_results.append((mn, h, a, sh, sa, h_pred, a_pred, deviation, rule, status, dir_ok))
    
    mk = f"#{mn} {status} {h:<10} {sh}-{sa} | 预测 {h_pred}-{a_pred} | {rule:<30} | "
    mk += f"偏差{deviation}球 | 方向{'✓' if dir_ok else '✗'}"
    if pt_h >= 0:
        mk += f" [积{pts_h}:{pts_a}]"
    print(mk)

print()
print("="*60)
print(f"世界杯44场全量回测报告 (当前引擎)")
print(f"总场次: {total} | 有数据: {total-missing_odds} | 缺数据: {missing_odds}")
print("="*60)
print(f"🎯 精确命中:  {hits}/{total-missing_odds} = {100*hits/(total-missing_odds):.1f}%")
print(f"📊 方向正确:  {dir_hits}/{total-missing_odds} = {100*dir_hits/(total-missing_odds):.1f}%")
print(f"✅ 偏差≤1球:  {dev1}/{total-missing_odds} = {100*dev1/(total-missing_odds):.1f}%")
print(f"❌ 偏差≥2球:  {dev2plus}/{total-missing_odds} = {100*dev2plus/(total-missing_odds):.1f}%")

if deviations:
    print(f"\n偏差明细 (偏差≥2球):")
    for h, a, sh, sa, hp, ap, dv, rule, mn in sorted(deviations, key=lambda x: -x[6]):
        print(f"  ❌ #{mn} {h}vs{a}: 实际{sh}-{sa} 预测{hp}-{ap} (偏差{dv}球) [{rule}]")

# 按轮次分析
print(f"\n按轮次分析:")
for rd_label, rd_val in [("R1", 1), ("R2", 2), ("R3", 3)]:
    rd_matches = []
    for idx, r in enumerate(all_results):
        mn_found = r[0]
        for m in MATCHES:
            if m[8] == mn_found and m[5] == rd_val:
                rd_matches.append(r)
                break
    if not rd_matches: continue
    rd_exact = sum(1 for r in rd_matches if r[3] == r[5] and r[4] == r[6])
    rd_dev1 = sum(1 for r in rd_matches if abs(r[3]-r[5])+abs(r[4]-r[6]) <= 1)
    rd_dir = sum(1 for r in rd_matches if r[10])
    print(f"  {rd_label} ({len(rd_matches)}场): 精确{rd_exact}/{len(rd_matches)}={100*rd_exact/len(rd_matches):.1f}% | 偏差≤1{rd_dev1}/{len(rd_matches)}={100*rd_dev1/len(rd_matches):.1f}% | 方向{rd_dir}/{len(rd_matches)}={100*rd_dir/len(rd_matches):.1f}%")

# 输出CSV格式用于对比
print(f"\nCSV逐场明细:")
print("match_num,home,away,actual_h,actual_a,pred_h,pred_a,deviation,rule,status")
for mn, h, a, sh, sa, hp, ap, dv, rule, st, _ in all_results:
    print(f"{mn},{h},{a},{sh},{sa},{hp},{ap},{dv},{rule},{st}")
