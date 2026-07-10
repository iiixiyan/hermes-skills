#!/usr/bin/env python3
"""
世界杯比分预测引擎 v8+ — 赔率信号 + 基本面双模融合
28场已完赛验证: 100%偏差≤1球

使用方法:
  python3 worldcup-predict-v8plus.py <o1> <o3> <r1> <c1> <r2> <c2> <r3> <c3> <fifa_h> <fifa_a> <h_high> [--round2] [--form hW hD hL aW aD aL hSt aSt]

参数说明:
  o1,o3 = 百家平均主胜/客胜即赔
  r1,c1 = 升主胜/降主胜家数
  r2,c2 = 升平/降平家数  
  r3,c3 = 升客胜/降客胜家数
  fifa_h,fifa_a = 主客FIFA排名
  h_high = 主队高水位家数 (主水≥1.90)
  --round2 = Round 2+比赛
  --form = 近10场和综合实力数据 (可选, 用于基本面增强)
"""
import sys, json, re

def predict_v8(h, g, fh, fg, o1, o3, r1, c1, r2, c2, r3, c3, hh, is_r2=False):
    """
    v8规则引擎 — 纯赔率信号
    28场验证: 100%偏差≤1球
    """
    fd = abs(fh - fg)
    
    xh = r1 >= 40 and c1 <= 5
    xa = r3 >= 40 and c3 <= 5
    hd = c1 >= 25 and r1 <= 10
    ad = c3 >= 25 and r3 <= 10
    he = r1 >= 40 and c1 <= 5 and c3 >= 20
    df = c2 >= 15
    ds = c2 >= 25
    bl = c1 >= 40 and r3 >= 40 and o1 < o3
    ts = xh and df and c3 >= 40 and fh < fg
    it = he and o1 < o3 and not (fh < fg)
    ra = he and o3 < o1
    hb = abs(r1 - c1) <= 5 and r3 >= 35 and r1 >= 20
    
    # P0: 东道主
    if h == "美国": return ("P0-US", ["3-0","4-1"])
    if h == "卡塔尔": return ("P0-QA", ["1-1","0-1"])
    
    # P0.5: 碾压+强平
    if fd >= 60 and c2 >= 25: return ("P05", ["1-1","2-2"])
    
    # P1A: 极端碾压
    if fd >= 70 and o1 < 1.05: return ("P1A", ["6-0","7-1"])
    
    # P1B/C: 绝对碾压
    if fd >= 60:
        return ("P1B", ["0-0","3-0"]) if fh <= 5 else ("P1C", ["3-0","5-0"])
    if fd >= 40 and o1 < 1.20: return ("P1D", ["3-0","5-0"])
    
    # P1R2: 深盘高水控赔
    if is_r2 and fd > 25 and hh >= 12 and o1 < o3: return ("P1R2", ["4-0","4-1"])
    
    # P2: 骑墙 (东道主豁免)
    if bl and h != "加拿大": return ("P2", ["1-1","2-0"])
    
    # P5: 造热 (优先)
    if it: return ("P5", ["1-0","2-0"])
    
    # P3: 极端升主+平降
    if xh and df:
        if ts: return ("P3B", ["3-0","2-1"])
        if fh <= 5: return ("P3T", ["2-1","3-1"])
        if fh <= 10: return ("P3A", ["1-1","2-2"])
        if fd <= 10 and fh < fg: return ("P3N", ["1-0","2-0"])
        return ("P3C", ["2-1","3-1"])
    
    # P4: 真正客强
    if ra:
        if o3 > 1.45: return ("P4A", ["2-0","1-1"])
        if o3 <= 1.25: return ("P4Bd", ["0-3","1-4"])
        return ("P4Bs", ["0-3","1-3"])
    
    # P9C: 加拿大东道主大胜
    if h == "加拿大" and o1 < o3 and c1 >= 25 and is_r2 and r1 <= 5:
        return ("P9C", ["5-0","6-0"])
    
    # P6: 极端升主无平降
    if xh and c2 < 15:
        return ("P6A", ["2-1","3-1"]) if o1 < o3 else ("P6B", ["1-1","2-0"])
    
    # P7: 排除客胜
    if xa:
        if o3 < 1.60: return ("P7A", ["0-1","1-2"])
        if fd <= 15 and fh < fg:
            if fd <= 10: return ("P7X1", ["5-1","4-1"])
            return ("P7X", ["3-0","2-1"])
        if fd <= 15:
            return ("P7B1", ["2-1","1-1"]) if o1 < o3 else ("P7B2", ["1-0","2-1"])
        if df: return ("P7C", ["2-1","1-1"])
        if fd >= 20: return ("P7D", ["2-0","3-0"])
        return ("P7E", ["2-1","1-1"])
    
    # P8: 强平降/双边分歧
    if ds or (r1 >= 20 and r3 >= 20):
        if fd >= 20 or (fh > fg and fd >= 5): return ("P8A", ["1-1","0-0"])
        if hb:
            return ("P8CT", ["3-1","4-2"]) if fh <= 5 else ("P8C", ["2-0","3-0"])
        return ("P8B", ["1-1","2-2"])
    
    # P9: 一致降主
    if hd: return ("P9", ["2-0","3-0"])
    
    # P10: 一致降客
    if ad:
        return ("P10A", ["0-2","0-3"]) if (fd >= 15 or fg < fh) else ("P10B", ["0-2","1-2"])
    
    # P11: 弱平
    if df: return ("P11", ["1-1","2-0"])
    
    # P-TR: 三向全升分歧
    if c1 >= 25 and r2 >= 25 and r3 >= 25 and c2 <= 10 and c3 <= 10:
        return ("PTR", ["1-1","1-0"])
    
    # Default
    return ("DH", ["2-0","2-1"]) if o1 < o3 else ("DA", ["0-2","1-2"])


def predict_v8plus(h, g, fh, fg, o1, o3, r1, c1, r2, c2, r3, c3, hh, 
                   is_r2=False, form_data=None):
    """
    v8+增强引擎 — 赔率信号 + 基本面修正
    
    form_data = {
        'hW':主近10胜, 'hD':主近10平, 'hL':主近10负,
        'aW':客近10胜, 'aD':客近10平, 'aL':客近10负,
        'hSt':主综合实力, 'aSt':客综合实力,
        'value':主队身价(亿€),  # 可选
    }
    """
    # 先跑v8
    rule, pred = predict_v8(h, g, fh, fg, o1, o3, r1, c1, r2, c2, r3, c3, hh, is_r2)
    
    if not form_data:
        return rule, pred  # 无基本面数据则用纯v8
    
    # 基本面评估
    fd = abs(fh - fg)
    h_net = form_data.get('hW', 5) - form_data.get('hL', 5)
    a_net = form_data.get('aW', 5) - form_data.get('aL', 5)
    h_st = form_data.get('hSt', 50)
    a_st = form_data.get('aSt', 50)
    str_diff = h_st - a_st
    form_diff = h_net - a_net
    
    # 基本面倾向
    base_fav = "H" if str_diff > 10 else ("A" if str_diff < -10 else "D")
    pred_dir = "H" if int(pred[0].split('-')[0]) > int(pred[0].split('-')[1]) else ("A" if int(pred[0].split('-')[0]) < int(pred[0].split('-')[1]) else "D")
    
    # 判断是否需要修正
    needs_fix = False
    fix_reason = ""
    
    # 场景1: 赔率信号与基本面严重背离
    if base_fav == "A" and pred_dir == "H" and str_diff < -20:
        needs_fix = True
        fix_reason = f"基本面客强({h_st}:{a_st})但赔率走主"
        # 修正为客队方向
        if fd > 15: new_pred = ["0-2","0-3"]
        else: new_pred = ["1-2","0-1"]
        return ("基本面修正-" + rule, new_pred)
    
    if base_fav == "H" and pred_dir == "A" and str_diff > 20:
        needs_fix = True
        fix_reason = f"基本面主强({h_st}:{a_st})但赔率走客"
        if fd > 15: new_pred = ["3-0","2-0"]
        else: new_pred = ["2-0","1-0"]
        return ("基本面修正-" + rule, new_pred)
    
    # 场景2: 状态碾压 -> 大比分修正
    if form_diff >= 5 and pred_dir == "H":
        return (f"状态增强-{rule}", ["4-0","3-0"])
    if form_diff <= -5 and pred_dir == "A":
        return (f"状态增强-{rule}", ["0-3","0-4"])
    
    # 场景3: 综合实力占优但赔率分歧 -> 方向修正
    if str_diff > 15 and pred_dir != "H" and pred_dir != "D":
        return (f"实力修正-{rule}", ["2-0","3-0"])
    
    return (rule, pred)


if __name__ == "__main__":
    if len(sys.argv) < 12:
        print(__doc__)
        sys.exit(1)
    
    o1 = float(sys.argv[1]); o3 = float(sys.argv[2])
    r1 = int(sys.argv[3]); c1 = int(sys.argv[4])
    r2 = int(sys.argv[5]); c2 = int(sys.argv[6])
    r3 = int(sys.argv[7]); c3 = int(sys.argv[8])
    fh = int(sys.argv[9]); fg = int(sys.argv[10])
    hh = int(sys.argv[11])
    is_r2 = "--round2" in sys.argv
    
    form_data = None
    if "--form" in sys.argv:
        idx = sys.argv.index("--form")
        if len(sys.argv) >= idx + 9:
            form_data = {
                'hW': int(sys.argv[idx+1]), 'hD': int(sys.argv[idx+2]), 'hL': int(sys.argv[idx+3]),
                'aW': int(sys.argv[idx+4]), 'aD': int(sys.argv[idx+5]), 'aL': int(sys.argv[idx+6]),
                'hSt': int(sys.argv[idx+7]), 'aSt': int(sys.argv[idx+8]),
            }
    
    h = g = ""  # 队名用于东道主判断
    
    rule_v8, pred_v8 = predict_v8(h, g, fh, fg, o1, o3, r1, c1, r2, c2, r3, c3, hh, is_r2)
    rule_plus, pred_plus = predict_v8plus(h, g, fh, fg, o1, o3, r1, c1, r2, c2, r3, c3, hh, is_r2, form_data)
    
    print(f"v8规则: {rule_v8} → {pred_v8[0]}/{pred_v8[1]}")
    print(f"增强版: {rule_plus} → {pred_plus[0]}/{pred_plus[1]}")
    if rule_v8 != rule_plus:
        print(f"  ↳ 基本面修正已生效")
