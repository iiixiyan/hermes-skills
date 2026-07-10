#!/usr/bin/env python3
"""
世界杯全量回溯预测系统 v2.0 (2026-06-20)
修正: matchId正确映射自jczqMatches API
新增: FDV基本面数据校验 (赔率方向 vs FIFA排名方向矛盾检测)
工作流:
  1. 遍历正确matchId
  2. 新浪API拉取实时欧赔/亚盘
  3. v10引擎预测 (含FDV基本面校验)
  4. 对比实际赛果
  5. 统计命中率

用法: python3 worldcup-full-backtest.py
"""
import json, urllib.request, sys, os
from datetime import datetime

SINA_BASE = "https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36'}

# 正确matchId (从jczqMatches API验证)
# 格式: matchId: (主队, 客队, FIFA主, FIFA客, 轮次)
MATCHES = {
    # D1 - 6/11
    3623416: ("墨西哥","南非",13,61,1),
    3625112: ("韩国","捷克",22,7,1),  # 韩国主场 vs 捷克
    # D2 - 6/12
    3623420: ("加拿大","波黑",32,34,1),
    3623423: ("美国","巴拉圭",8,32,1),
    # D3 - 6/13
    3625115: ("卡塔尔","瑞士",37,22,1),
    3625082: ("巴西","摩洛哥",1,2,1),
    3625118: ("海地","苏格兰",71,30,1),
    3625121: ("澳大利亚","土耳其",27,22,1),  # 赛程在6/14彩票日
    # D4 - 6/14
    3625088: ("德国","库拉索",5,77,1),
    3625091: ("荷兰","日本",10,20,1),
    3625124: ("科特迪瓦","厄瓜多尔",23,33,1),
    3625127: ("瑞典","突尼斯",19,26,1),
    # D5 - 6/15
    3625097: ("西班牙","佛得角",2,67,1),
    3625094: ("比利时","埃及",6,26,1),
    3625133: ("沙特","乌拉圭",58,13,1),
    3625130: ("伊朗","新西兰",22,87,1),
    # D6 - 6/16
    3625100: ("法国","塞内加尔",1,13,1),
    3625141: ("伊拉克","挪威",55,29,1),
    3625103: ("阿根廷","阿尔及利亚",4,31,1),
    # D7 - 6/17
    3625144: ("奥地利","约旦",18,57,1),
    3625106: ("葡萄牙","刚果金",7,47,1),
    3625109: ("英格兰","克罗地亚",4,11,1),
    3625150: ("加纳","巴拿马",73,34,1),
    3625147: ("乌兹别克","哥伦比亚",58,21,1),
    # D8 - 6/18 (Round 2)
    3625113: ("捷克","南非",7,61,2),
    3625116: ("瑞士","波黑",22,63,2),
    3623421: ("加拿大","卡塔尔",32,49,2),
    3623417: ("墨西哥","韩国",13,22,2),
}

# 实际赛果 (从jczqMatches API score1/score2验证)
RESULTS = {
    3623416: (2,0),  # 墨西哥2-0南非
    3625112: (2,1),  # 韩国2-1捷克
    3623420: (1,1),  # 加拿大1-1波黑
    3623423: (4,1),  # 美国4-1巴拉圭
    3625115: (1,1),  # 卡塔尔1-1瑞士
    3625082: (1,1),  # 巴西1-1摩洛哥
    3625118: (0,1),  # 海地0-1苏格兰
    3625121: (2,0),  # 澳大利亚2-0土耳其
    3625088: (7,1),  # 德国7-1库拉索
    3625091: (2,2),  # 荷兰2-2日本
    3625124: (1,0),  # 科特迪瓦1-0厄瓜多尔
    3625127: (5,1),  # 瑞典5-1突尼斯
    3625097: (0,0),  # 西班牙0-0佛得角
    3625094: (1,1),  # 比利时1-1埃及
    3625133: (1,1),  # 沙特1-1乌拉圭
    3625130: (2,2),  # 伊朗2-2新西兰
    3625100: (3,1),  # 法国3-1塞内加尔
    3625141: (1,4),  # 伊拉克1-4挪威
    3625103: (3,0),  # 阿根廷3-0阿尔及利亚
    3625144: (3,1),  # 奥地利3-1约旦
    3625106: (1,1),  # 葡萄牙1-1刚果金
    3625109: (4,2),  # 英格兰4-2克罗地亚
    3625150: (1,0),  # 加纳1-0巴拿马
    3625147: (1,3),  # 乌兹别克1-3哥伦比亚
    3625113: (1,1),  # 捷克1-1南非
    3625116: (4,1),  # 瑞士4-1波黑
    3623421: (6,0),  # 加拿大6-0卡塔尔
    3623417: (1,0),  # 墨西哥1-0韩国
}

def fetch_odds(match_id):
    """从新浪API获取实时欧赔信号"""
    try:
        url = f"{SINA_BASE}&cat1=footballMatchOddsEuro&matchId={match_id}"
        req = urllib.request.Request(url, headers=HEADERS)
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
        odds = resp.get('result', {}).get('data', [])
        if not odds:
            return None
        o1s = [float(o.get('o1New',0)) for o in odds if o.get('o1New')]
        o3s = [float(o.get('o3New',0)) for o in odds if o.get('o3New')]
        return {
            'o1': round(sum(o1s)/len(o1s), 4) if o1s else 0,
            'o3': round(sum(o3s)/len(o3s), 4) if o3s else 0,
            'r1': sum(1 for o in odds if float(o.get('o1New',0))>float(o.get('o1Ini',0))),
            'c1': sum(1 for o in odds if float(o.get('o1New',0))<float(o.get('o1Ini',0))),
            'r2': sum(1 for o in odds if float(o.get('o2New',0))>float(o.get('o2Ini',0))),
            'c2': sum(1 for o in odds if float(o.get('o2New',0))<float(o.get('o2Ini',0))),
            'r3': sum(1 for o in odds if float(o.get('o3New',0))>float(o.get('o3Ini',0))),
            'c3': sum(1 for o in odds if float(o.get('o3New',0))<float(o.get('o3Ini',0))),
        }
    except Exception as e:
        return None

def run_v10(h, g, fh, fa, o1, o3, r1, c1, r2, c2, r3, c3, hh, rd):
    """调用v10引擎"""
    v10_path = os.path.join(os.path.dirname(__file__), "worldcup-predict-v10.py")
    sys.path.insert(0, os.path.dirname(v10_path))
    import importlib.util
    spec = importlib.util.spec_from_file_location("v10", v10_path)
    v10 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v10)
    h_pred, a_pred, rule, conf = v10.predict(
        h=h, g=g, fh=fh, fa=fa,
        o1=o1, o3=o3,
        r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3,
        rd=rd
    )
    return h_pred, a_pred, rule, conf

def main():
    print("=" * 60)
    print(f"🌍 世界杯全量回溯预测 v2.0 — {datetime.now().strftime('%m-%d %H:%M')}")
    print(f"   修正matchId正确映射 | FDV基本面校验")
    print("=" * 60)
    
    exact_hits, dir_hits, total = 0, 0, 0
    misses, regressions = [], []
    
    for mid, (h, g, fh, fa, rd) in sorted(MATCHES.items()):
        actual = RESULTS.get(mid)
        if not actual:
            continue
        
        odds = fetch_odds(mid)
        if not odds:
            print(f"  ❌ {h} vs {g} — 赔率数据不可用")
            continue
        
        total += 1
        h_pred, a_pred, rule, conf = run_v10(
            h, g, fh, fa,
            odds['o1'], odds['o3'],
            odds['r1'], odds['c1'],
            odds['r2'], odds['c2'],
            odds['r3'], odds['c3'],
            0, rd  # hh=0简化
        )
        
        a_h, a_a = actual
        exact = (h_pred == a_h and a_pred == a_a)
        dir_ok = abs(h_pred - a_h) <= 1 and abs(a_pred - a_a) <= 1
        
        if exact: exact_hits += 1
        if dir_ok:
            dir_hits += 1
        else:
            misses.append((h, g, rule, h_pred, a_pred, a_h, a_a))
        
        status = "✅" if exact else ("⚠️" if dir_ok else "❌")
        print(f"  {status} {h} vs {g}: {rule} → {h_pred}-{a_pred} 实际{a_h}-{a_a}")
    
    print("\n" + "=" * 60)
    print(f"📊 回溯结果汇总 ({total}场) — 正确matchId映射")
    print(f"  精确命中: {exact_hits}/{total} = {exact_hits/total*100:.1f}%")
    print(f"  偏差≤1球: {dir_hits}/{total} = {dir_hits/total*100:.1f}%")
    print(f"  偏差≥2球: {total-dir_hits}/{total} = {(total-dir_hits)/total*100:.1f}%")
    
    if misses:
        print(f"\n❌ 偏差≥2球场次 ({len(misses)}场):")
        for h, g, rule, ph, pa, ah, aa in misses:
            print(f"  {h} vs {g}: {rule} → {ph}-{pa} 实际{ah}-{aa} (偏差{abs(ph-ah)+abs(pa-aa)}球)")
    
    print("\n" + "=" * 60)
    return misses, dir_hits, total

if __name__ == "__main__":
    main()
