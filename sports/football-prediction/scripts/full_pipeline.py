#!/usr/bin/env python3
"""
全数据源预测管线 v1.0 (2026-06-20)
每次预测自动采集: 新浪API欧赔 + 59itou综合实力 + titan007基本盘 + 500彩票网
→ 汇聚form_signal → v10.6引擎 → 比分预测

用法:
  from full_pipeline import predict_with_all_sources
  result = predict_with_all_sources(h, g, fh, fa, rd, match_id)
  
Hermes浏览器模式:
  1. browser_navigate(titan007分析页) → 获取innerText
  2. browser_navigate(500彩票网shuju页) → 获取innerText  
  3. 调用本管线解析+预测
"""
import sys, os, json, importlib.util

SCRIPTS_DIR = "/root/.hermes/skills/sports/football-prediction/scripts"

# 懒加载引擎
_v10 = None
_scout = None
_collector = None
_cold_model = None
_handicap = None

def _load_engine():
    global _v10
    if _v10 is None:
        spec = importlib.util.spec_from_file_location("v10", f"{SCRIPTS_DIR}/worldcup-predict-v10.py")
        _v10 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_v10)
    return _v10

def _load_scout():
    global _scout
    if _scout is None:
        spec = importlib.util.spec_from_file_location("scout", f"{SCRIPTS_DIR}/fundamental_scout.py")
        _scout = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_scout)
    return _scout

def _load_collector():
    global _collector
    if _collector is None:
        spec = importlib.util.spec_from_file_location("collector", f"{SCRIPTS_DIR}/all_sources_collector.py")
        _collector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_collector)
    return _collector


def _load_cold_model():
    """懒加载爆冷预警2.0模块"""
    global _cold_model
    if _cold_model is None:
        spec = importlib.util.spec_from_file_location("cold", f"{SCRIPTS_DIR}/cold_model_trainer.py")
        _cold_model = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_cold_model)
    return _cold_model


def _load_handicap():
    """懒加载盘口博弈分析模块"""
    global _handicap
    if _handicap is None:
        spec = importlib.util.spec_from_file_location("handicap", f"{SCRIPTS_DIR}/handicap_analysis.py")
        _handicap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_handicap)
    return _handicap


def predict_with_all_sources(h, g, fh, fa, rd, o1, o3, r1, c1, r2, c2, r3, c3,
                             titan007_text=None, text_500=None, text_zgzcw=None, text_okooo=None):
    """
    全数据源预测
    
    Args:
        h, g: 主客队名
        fh, fa: FIFA排名
        rd: 轮次
        o1/o3: 百家平均赔率
        r1/c1/r2/c2/r3/c3: 指数变化
        titan007_text: 从titan007分析页获取的innerText
        text_500: 从500彩票网shuju页获取的innerText
        text_zgzcw: 从中国足彩网获取的innerText
        text_okooo: 从澳客网获取的innerText
    
    Returns:
        (主场进球, 客场进球, 规则名, 信心, form_signal)
    """
    engine = _load_engine()
    
    # Step 1: 59itou综合实力 (API自动)
    scout = _load_scout()
    api_signal, _ = scout.scout_and_build(h, g, fh, fa)
    
    # Step 2: 全站基本盘 (浏览器采集)
    all_sources = {}
    if titan007_text:
        collector = _load_collector()
        all_sources['titan007'] = collector.parse_titan007(titan007_text)
    if text_500:
        collector = _load_collector()
        all_sources['500'] = collector.parse_500(text_500)
    if text_zgzcw:
        collector = _load_collector()
        all_sources['zgzcw'] = collector.parse_zgzcw(text_zgzcw)
    if text_okooo:
        collector = _load_collector()
        all_sources['okooo'] = collector.parse_okooo(text_okooo)
    
    # Step 3: 汇聚
    collector = _load_collector()
    merged = collector.merge_to_form_signal(all_sources) if all_sources else None
    
    # Step 4: 合并59itou数据和全站数据
    final_signal = api_signal or {}
    if merged:
        for k, v in merged.items():
            if v or v == 0:
                final_signal[k] = v
    
    # Step 5: 预测
    h_pred, a_pred, rule, conf = engine.predict(
        h=h, g=g, fh=fh, fa=fa,
        o1=o1, o3=o3,
        r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3,
        rd=rd, form_signal=final_signal if final_signal.get('sources_used') else None
    )

    # Step 6: 爆冷预警2.0 (条件触发)
    cold_warning = ""
    if o1 and o3 and abs(fh - fa) >= 15:
        try:
            cold = _load_cold_model()
            cold_result = cold.analyze_match_cold(
                h_fifa=fh, a_fifa=fa, h_name=h, a_name=g,
                o1=o1, o3=o3,
                r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3,
                rd=rd,
                h_goals=h_pred, a_goals=a_pred, rule=rule, conf_level=conf
            )
            if cold_result.get('warning'):
                cold_warning = cold_result['warning']
                h_pred, a_pred = cold_result['h_goals'], cold_result['a_goals']
                rule = cold_result['rule']
                conf = cold_result['conf_level']
        except Exception:
            pass  # 爆冷模块失败不影响主流程

    # Step 7: 盘口博弈分析 (条件触发)
    handicap_reason = ""
    asian_data = all_sources.get('asian')\
        if isinstance(all_sources, dict) else None
    strength_gap = (final_signal or {}).get('strength_gap', fh - fa)

    if strength_gap and abs(strength_gap) >= 5:
        try:
            hcp = _load_handicap()
            # 从亚盘数据构造 HandicapData (如有)
            if asian_data and asian_data.get('initial'):
                hcp_data = hcp.HandicapData(
                    initial=str(asian_data.get('initial', '0')),
                    live=str(asian_data.get('live', '0')),
                    water_initial=float(asian_data.get('water_ini', 1.90)),
                    water_live=float(asian_data.get('water_live', 1.90)),
                )
            else:
                # 无真实亚盘时，用欧赔差近似
                hcp_diff = round((o3 - o1) / 2.0, 2) if o1 and o3 else 0
                hcp_str = f"-{hcp_diff}" if hcp_diff > 0 else f"+{abs(hcp_diff)}"
                hcp_data = hcp.HandicapData(
                    initial=hcp_str, live=hcp_str,
                    water_initial=1.90, water_live=1.90,
                )

            hcp_result = hcp.analyze_handicap(
                strength_gap=strength_gap,
                handicap=hcp_data,
                lineup_known=bool(final_signal and final_signal.get('lineup_known'))
            )
            if hcp_result['type'] != 'match':
                handicap_reason = hcp_result['reason']
                # 应用λ修正（盘口分析作用于原始λ，此处仅记录归因）
                if hcp_result['lambda_h_mod'] != 1.0:
                    h_pred = max(0, round(h_pred * hcp_result['lambda_h_mod']))
                if hcp_result['lambda_a_mod'] != 1.0:
                    a_pred = max(0, round(a_pred * hcp_result['lambda_a_mod']))
        except Exception:
            pass  # 盘口模块失败不影响主流程

    return h_pred, a_pred, rule, conf, final_signal, cold_warning, handicap_reason


def format_prediction(h_pred, a_pred, rule, conf, signal, cold_warning="", handicap_reason=""):
    """格式化输出"""
    engine = _load_engine()
    s1, s2, stars = engine.format_result(h_pred, a_pred, rule, conf)

    sources = signal.get('sources_used', []) if signal else []
    fbs = '|'.join(sources) if sources else 'api_only'

    line = f"🎯 {s1}/{s2} | {rule} | 数据源: {fbs}"
    if signal:
        if signal.get('avg_rating_diff'):
            line += f" | 评分差={signal['avg_rating_diff']}"
        if signal.get('temperature'):
            line += f" | 天气={signal['temperature']}℃"
    if cold_warning:
        line += f" | ❄️{cold_warning}"
    if handicap_reason:
        line += f" | ⚡{handicap_reason}"

    return line


if __name__ == "__main__":
    print("="*60)
    print("全数据源预测管线 v1.0")
    print("="*60)
    print()
    print("采集方法:")
    print("  1. browser_navigate → titan007分析页")
    print("     console提取innerText → parse_titan007()")
    print("  2. browser_navigate → 500彩票网shuju页") 
    print("     console提取innerText → parse_500()")
    print("  3. browser_navigate → 中国足彩网比赛页")
    print("     console提取innerText → parse_zgzcw()")
    print("  4. browser_navigate → 澳客网比赛详情")
    print("     console提取innerText → parse_okooo()")
    print("  5. merge_to_form_signal() → form_signal")
    print("  6. predict(form_signal=signal) → 🎯 比分")
