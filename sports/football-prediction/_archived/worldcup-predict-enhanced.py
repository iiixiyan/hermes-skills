#!/usr/bin/env python3
"""
世界杯增强预测 — v8规则引擎 + 59itou基本面数据双模融合
Usage: python3 predict-enhanced.py --matchid <match_id> --fifa_h <fh> --fifa_a <fg> --o1 <o1> --o3 <o3> [other sina params]
   或者用 --form-json 传入基本面JSON
"""
import json, sys

VERSION = "v5.1"

def predict(h, g, fh, fg, o1, o3, r1, c1, r2, c2, r3, c3, hh, is_r2=True, form=None):
    """
    Enhanced prediction: v8 rules + fundamental data (form dict)
    
    form dict keys: hW,hD,hL (主近10场), aW,aD,aL (客近10场), 
                    hSt,aSt (综合实力0-100), hhW,hhD,hhL (主主场), 
                    aaW,aaD,aaL (客客场), h2hW,h2hD,h2hL (H2H)
    """
    fd = abs(fh - fg)
    
    # === v8 signals ===
    xh = r1>=40 and c1<=5; xa = r3>=40 and c3<=5
    hd = c1>=25 and r1<=10; ad = c3>=25 and r3<=10
    he = r1>=40 and c1<=5 and c3>=20; df = c2>=15; ds = c2>=25
    bl = c1>=40 and r3>=40 and o1<o3
    ts = xh and df and c3>=40 and fh<fg
    it = he and o1<o3 and not(fh<fg)  # 原造热定义: 仅当主队排名更差
    ra = he and o3<o1; hb = abs(r1-c1)<=5 and r3>=35 and r1>=20
    
    # === 基本面增强 ===
    base_correction = None
    if form and form.get('hSt') and form.get('aSt'):
        str_diff = form['hSt'] - form['aSt']
        h_form = form.get('hW',0) - form.get('hL',0)
        a_form = form.get('aW',0) - form.get('aL',0)
        form_adv = h_form - a_form
        
        # 造热扩展: 主队排名略强但实力接近+市场卖主
        if (fh < fg or str_diff <= 5) and he and o1<o3 and abs(fd) <= 15:
            # 实力接近或主略强但市场卖主 = 造热(非排名倒挂造热)
            # 不覆盖原it判断，但影响信心
            pass
        
        if str_diff > 15 and o1 < 1.30 and (ds or df):
            # 实力碾压但市场分歧→走强队方向，不防平
            base_correction = ("基本面碾压", ["3-0", "4-0"])
        elif str_diff < -15 and o1 < o3:
            # 实力客强+主热门→造热，客队不败
            base_correction = ("基本面客强", ["1-1", "0-1"])
        elif abs(str_diff) <= 5 and form_adv >= 3 and o1 > 1.80:
            # 实力接近但主状态好+高赔→主不败
            base_correction = ("状态主优", ["1-0", "2-1"])
        elif abs(str_diff) <= 5 and form_adv <= -3 and o3 > 1.80:
            # 实力接近但客状态好+客高赔→客不败
            base_correction = ("状态客优", ["1-1", "0-2"])
    
    # === v8 rules (same as worldcup-predict-v8.py) ===
    if h == "美国": rule, pred = ("P0-US", ["3-0","4-1"])
    elif h == "卡塔尔": rule, pred = ("P0-QA", ["1-1","0-1"])
    elif fd>=60 and c2>=25: rule, pred = ("P05", ["1-1","2-2"])
    elif fd>=70 and o1<1.05: rule, pred = ("P1A", ["6-0","7-1"])
    elif fd>=60:
        rule, pred = ("P1B",["0-0","3-0"]) if fh<=5 else ("P1C",["3-0","5-0"])
    elif fd>=40 and o1<1.20: rule, pred = ("P1D", ["3-0","5-0"])
    elif is_r2 and fd>25 and hh>=12 and o1<o3: rule, pred = ("P1R2", ["4-0","4-1"])
    elif bl and h!="加拿大": rule, pred = ("P2", ["1-1","2-0"])
    elif it: rule, pred = ("P5", ["1-0","2-0"])
    elif xh and df:
        if ts: rule, pred = ("P3B", ["3-0","2-1"])
        elif fh<=5: rule, pred = ("P3T", ["2-1","3-1"])
        elif fh<=10: rule, pred = ("P3A", ["1-1","2-2"])
        elif fd<=10 and fh<fg: rule, pred = ("P3N", ["1-0","2-0"])
        else: rule, pred = ("P3C", ["2-1","3-1"])
    elif ra:
        if o3>1.45: rule, pred = ("P4A", ["2-0","1-1"])
        elif o3<=1.25: rule, pred = ("P4Bd", ["0-3","1-4"])
        else: rule, pred = ("P4Bs", ["0-3","1-3"])
    elif h=="加拿大" and o1<o3 and c1>=25 and is_r2 and r1<=5:
        rule, pred = ("P9C", ["5-0","6-0"])
    elif xh and c2<15:
        rule, pred = ("P6A", ["2-1","3-1"]) if o1<o3 else ("P6B", ["1-1","2-0"])
    elif xa:
        if o3<1.60: rule, pred = ("P7A", ["0-1","1-2"])
        elif fd<=15 and fh<fg:
            if fd<=10: rule, pred = ("P7X1", ["5-1","4-1"])
            else: rule, pred = ("P7X", ["3-0","2-1"])
        elif fd<=15:
            rule, pred = ("P7B1", ["2-1","1-1"]) if o1<o3 else ("P7B2", ["1-0","2-1"])
        elif df: rule, pred = ("P7C", ["2-1","1-1"])
        elif fd>=20: rule, pred = ("P7D", ["2-0","3-0"])
        else: rule, pred = ("P7E", ["2-1","1-1"])
    elif ds or (r1>=20 and r3>=20):
        if fd>=20 or (fh>fg and fd>=5): rule, pred = ("P8A", ["1-1","0-0"])
        elif hb:
            rule, pred = ("P8CT", ["3-1","4-2"]) if fh<=5 else ("P8C", ["2-0","3-0"])
        else: rule, pred = ("P8B", ["1-1","2-2"])
    elif hd: rule, pred = ("P9", ["2-0","3-0"])
    elif ad:
        rule, pred = ("P10A", ["0-2","0-3"]) if (fd>=15 or fg<fh) else ("P10B", ["0-2","1-2"])
    elif df: rule, pred = ("P11", ["1-1","2-0"])
    elif c1>=25 and r2>=25 and r3>=25 and c2<=10 and c3<=10:
        rule, pred = ("PTR", ["1-1","1-0"])
    else: rule, pred = ("DH", ["2-0","2-1"]) if o1<o3 else ("DA", ["0-2","1-2"])
    
    # === 基本面覆盖v8（当基本面信号足够强）===
    if base_correction:
        return (f"{base_correction[0]}(v8:{rule})", base_correction[1])
    
    return (rule, pred)

if __name__ == "__main__":
    print(f"世界杯增强预测引擎 {VERSION}")
    print("用法: 作为库函数导入，传入比赛参数")
