#!/usr/bin/env python3
"""
L2+L3全自动采集 v1.0
一次性采集: titan007(L2) + 500彩票网(L3) + 澳客网(L3) → form_signal → v10引擎

用法:
  from automated_all import collect_all, predict_all
  with sync_playwright() as p:
      browser = p.chromium.launch(...)
      sig = collect_all(browser, h_name, a_name, schedule_id)
      h, a, rule, conf = predict_all(h, g, ..., browser_data=sig)
"""
import os, sys, re, importlib.util

SCRIPTS_DIR = "/root/.hermes/skills/sports/football-prediction/scripts"

# ============================================================
#  导入子模块函数
# ============================================================
# L2
from automated_l2 import (
    fetch_titan007, titan007_to_form_signal
)
# L3
from automated_l3 import (
    find_500_id, find_okooo_id, parse_500, parse_okooo,
    l3_to_form_signal
)
from playwright.sync_api import sync_playwright


def collect_all(browser, h_name, a_name, schedule_id=None):
    """
    全自动L2+L3采集
    返回: {titan007, '500', okooo, form_signal}
    """
    result = {'sources_found': [], 'form_signal': {}}
    
    # ===== L2: titan007 =====
    print(f"\n📡 L2 titan007: 匹配 {h_name} vs {a_name}...", end=' ')
    
    # 只扫描小范围(20个)，优先用500.com ID或直接搜
    scan_ids = [schedule_id] if schedule_id else []
    scan_ids += range(2906740, 2906760)  # 只扫20个
    
    for aid in scan_ids:
        try:
            t7 = fetch_titan007(browser, aid, timeout=5000)
        except:
            continue
        if t7 and t7.get('body_length', 0) > 500:
            found = False
            if t7.get('t7_h'):
                if h_name[:2] in t7['t7_h'] or t7['t7_h'][:2] in h_name:
                    found = True
            if not found and t7.get('h_score') is not None:
                # 用比分辅助判断
                pass  # skip for now
            if found or (t7.get('body_length', 0) > 500 and not result.get('titan007')):
                result['titan007'] = t7
                result['sources_found'].append('titan007')
                print(f"✅ aid={aid} ({t7['body_length']}c)")
                break
    else:
        print("❌")
    
    # ===== L3: 500彩票网 =====
    print(f"📡 L3 500彩票网: 匹配 {h_name} vs {a_name}...", end=' ')
    mid_500, body_500 = find_500_id(browser, h_name, a_name)
    if mid_500 and body_500:
        result['500'] = parse_500(body_500)
        result['500']['match_id'] = mid_500
        result['sources_found'].append('500')
        print(f"✅ ID={mid_500} ({len(body_500)}c)")
    else:
        print("❌")
    
    # ===== L3: 澳客网 =====
    print(f"📡 L3 澳客网: 匹配 {h_name} vs {a_name}...", end=' ')
    mid_ok, body_ok = find_okooo_id(browser, h_name, a_name)
    if mid_ok and body_ok:
        result['okooo'] = parse_okooo(body_ok)
        result['okooo']['match_id'] = mid_ok
        result['sources_found'].append('okooo')
        print(f"✅ ID={mid_ok} ({len(body_ok)}c)")
    else:
        print("❌")
    
    # ===== 汇聚form_signal =====
    all_sources_for_merge = {}
    l2_sig = {}
    l3_sig = {}
    
    if 'titan007' in result['sources_found']:
        l2_sig = titan007_to_form_signal(result['titan007'])
        all_sources_for_merge['titan007'] = result['titan007']
    
    if '500' in result['sources_found'] or 'okooo' in result['sources_found']:
        l3_sig = l3_to_form_signal(result)
    
    # 合并
    merged = {}
    for d in [l2_sig, l3_sig]:
        for k, v in d.items():
            if v is not None and v != 0 and v != '' and v != []:
                if k == 'sources_used':
                    merged['sources_used'] = merged.get('sources_used', []) + v
                else:
                    merged[k] = v
    
    result['form_signal'] = merged
    result['signal_summary'] = ', '.join(merged.get('sources_used', ['none']))
    return result


def predict_with_all(h, g, fh, fa, rd, o1, o3, r1, c1, r2, c2, r3, c3, browser_data=None):
    """L1+L2+L3全数据预测"""
    spec = importlib.util.spec_from_file_location("_v10", f"{SCRIPTS_DIR}/worldcup-predict-v10.py")
    v10 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v10)
    
    spec2 = importlib.util.spec_from_file_location("_scout", f"{SCRIPTS_DIR}/fundamental_scout.py")
    scout = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(scout)
    
    # L1
    l1_signal, _ = scout.scout_and_build(h, g, fh, fa)
    
    # L2+L3
    browser_sig = browser_data.get('form_signal', {}) if browser_data else {}
    
    # 合并
    final = dict(l1_signal or {})
    for k, v in browser_sig.items():
        if v is not None and v != 0 and v != '' and v != []:
            if k == 'sources_used':
                final['sources_used'] = final.get('sources_used', []) + v
            else:
                final[k] = v
    
    h_pred, a_pred, rule, conf = v10.predict(
        h=h, g=g, fh=fh, fa=fa,
        o1=o1, o3=o3, r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3,
        rd=rd, form_signal=final if final.get('sources_used') else None
    )
    
    return h_pred, a_pred, rule, conf, final


def format_signal_summary(sig):
    """form_signal → 可读摘要"""
    if not sig:
        return "L1-only"
    parts = []
    src = sig.get('sources_used', [])
    parts.append(f"src={'+'.join(src)}")
    if sig.get('temperature'):
        parts.append(f"🌡{sig['temperature']}")
    if sig.get('avg_rating_diff'):
        parts.append(f"⭐{sig['avg_rating_diff']:+.1f}")
    if sig.get('injury_impact_h', 0) > 0 or sig.get('injury_impact_a', 0) > 0:
        parts.append(f"🩹H{sig['injury_impact_h']}A{sig['injury_impact_a']}")
    if sig.get('macau_tip'):
        parts.append("🏷澳门")
    if sig.get('market_values'):
        parts.append("💰身价")
    return ' | '.join(parts)


if __name__ == "__main__":
    print("="*70)
    print("L2+L3全自动采集管线 v1.0")
    print("="*70)
    
    if len(sys.argv) >= 3:
        h_name, a_name = sys.argv[1], sys.argv[2]
    else:
        h_name, a_name = "荷兰", "瑞典"
    
    print(f"\n比赛: {h_name} vs {a_name}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path='/usr/bin/chromium-browser',
            headless=True,
            args=['--no-sandbox']
        )
        
        data = collect_all(browser, h_name, a_name)
        
        print(f"\n{'='*70}")
        print(f"📊 采集结果:")
        print(f"   数据源: {', '.join(data['sources_found']) or 'none'}")
        print(f"   form_signal: {format_signal_summary(data['form_signal'])}")
        
        # 测试预测 (用demo数据)
        print(f"\n   🎯 预测结果: (demo数据)")
        # 荷兰(FIFA7) vs 瑞典(FIFA25) Round2
        h_pred, a_pred, rule, conf, sig = predict_with_all(
            h_name, a_name, 7, 25, 2,
            1.49, 5.84, 29, 2, 23, 1, 5, 37,
            browser_data=data
        )
        print(f"      {h_name} {h_pred}-{a_pred} {a_name} [{rule}] {format_signal_summary(sig)}")
        
        browser.close()
