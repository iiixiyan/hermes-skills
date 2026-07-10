#!/usr/bin/env python3
"""
盘口博弈分析系统 v1.0 (2026-06-21)
对比基本面实力差与盘口让球数之间的差异，判别机构真实意图。
从单纯的实力差推导升级为盘口意图博弈分析。

用法:
  from handicap_analysis import analyze_handicap, HandicapData

  h_data = HandicapData(initial='-1.0', live='-1.25', water_initial=1.85, water_live=2.05)
  result = analyze_handicap(strength_gap=25, handicap=h_data)
  # result = {'diff': 0.5, 'type': 'deep', 'lambda_h_mod': 1.05, 'lambda_a_mod': 1.0, 'draw_boost': 0.0, ...}

数据结构:
  HandicapData:
    - initial: 初盘让球数 (str, 如 '-1.0', '+0.5', '0')
    - live: 即时盘让球数 (str)
    - water_initial: 初盘主队水位 (float)
    - water_live: 即时盘主队水位 (float)

核心函数:
  analyze_handicap(strength_gap, handicap, lineup_known=True) -> dict:
    对比实力差与盘口让球数
    返回: {
      'diff': 盘口-实力差差距(绝对值比较),
      'type': 'deep'|'shallow'|'match',  # 深开/浅开/匹配
      'lambda_h_mod': 主队λ修正系数,
      'lambda_a_mod': 客队λ修正系数,
      'draw_boost': 平局概率上调比例(0~0.25),
      'reason': 分析原因文本,
      'handicap_numeric': 实际盘口数值
    }

  parse_handicap_value(handicap_str) -> float:
    解析 '-1.25', '+0.5', '0' 等盘口字符串为数值

判断逻辑:
  1. 将基本面实力差归一化到盘口维度（0.25球为最小单位）
     expected_magnitude = strength_gap / 20 * 0.5
     四舍五入到最接近的0.25
  2. 比较 actual_magnitude - expected_magnitude
     - >= 0.50: 盘路深开 → lambda_强队 *= 1.05
     - <= -0.50: 盘路浅开 → lambda_弱队 *= 0.95, 平局概率+15%
     - else: 盘路匹配，无修正

  水位修正规则:
  - 深开+高水(water_live >= 2.0): 降级为→不修正(高水阻盘)
  - 深开+低水(water_live <= 1.80): 加强→lambda_强队 *= 1.08
  - 浅开+高水(water_live >= 2.0): 加强→弱队更受支持, 平局+25%

所有函数加完整中文注释。
"""

from dataclasses import dataclass
from typing import Optional


def parse_handicap_value(handicap_str: str) -> float:
    """
    解析亚洲盘口字符串为浮点数。
    支持格式: '-1.25', '+0.5', '0', '0.0', '-0.75', '+1.0' 等。
    返回正数表示主队受让(弱队)，负数表示主队让球(强队)。

    参数:
        handicap_str: 盘口字符串，如 '-1.25', '+0.5', '0'

    返回:
        float: 解析后的数值
    """
    if not handicap_str or handicap_str == '0' or handicap_str == '0.0':
        return 0.0

    # 提取符号和数值部分
    stripped = handicap_str.strip()
    if stripped.startswith('+'):
        return float(stripped[1:])
    elif stripped.startswith('-'):
        return -float(stripped[1:])
    else:
        # 无符号默认正数（主队受让）
        return float(stripped)


def _round_to_quarter(value: float) -> float:
    """
    将数值四舍五入到最近的0.25（使用五舍六入，避免Python banker's rounding）。
    例如: 0.625 → 0.75, 0.3 → 0.25, 0.1 → 0.0

    参数:
        value: 输入数值

    返回:
        float: 四舍五入到0.25倍数的值
    """
    import math
    scaled = value * 4
    if scaled >= 0:
        return math.floor(scaled + 0.5) / 4.0
    else:
        return math.ceil(scaled - 0.5) / 4.0


@dataclass
class HandicapData:
    """
    盘口数据结构。
    保存亚盘初盘和即时盘的让球数及水位信息。

    属性:
        initial: 初盘让球数 (str, 如 '-1.0', '+0.5', '0')
        live: 即时盘让球数 (str)
        water_initial: 初盘主队水位 (float)
        water_live: 即时盘主队水位 (float)
    """
    initial: str
    live: str
    water_initial: float = 1.90
    water_live: float = 1.90


def analyze_handicap(
    strength_gap: float,
    handicap: HandicapData,
    lineup_known: bool = True
) -> dict:
    """
    核心分析函数：对比基本面实力差与盘口让球数，判断盘口深开/浅开/匹配，
    并返回修正系数供泊松模型使用。

    判断逻辑:
      1. 将基本面实力差归一化到盘口维度（0.25球为最小单位）
         expected_magnitude = strength_gap / 20 * 0.5
         四舍五入到最接近的0.25
      2. 比较 actual_magnitude - expected_magnitude
         - >= 0.50: 盘路深开 → 强队λ *= 1.05
         - <= -0.50: 盘路浅开 → 弱队λ *= 0.95, 平局概率+15%
         - else: 盘路匹配，无修正

      水位修正规则:
      - 深开+高水(water_live >= 2.0): 降级为→不修正(高水阻盘)
      - 深开+低水(water_live <= 1.80): 加强→强队λ *= 1.08
      - 浅开+高水(water_live >= 2.0): 加强→弱队更受支持, 平局+25%

    参数:
        strength_gap: 基本面实力差（正数=主队强，负数=客队强）
        handicap: HandicapData 对象，含初盘/即时盘和水位信息
        lineup_known: 是否已知首发阵容（默认True）。False时修正力度减半，保守处理

    返回:
        dict: {
            'diff': 盘口实力差差距（绝对值比较，正=深开，负=浅开）,
            'type': 'deep' | 'shallow' | 'match',
            'lambda_h_mod': 主队λ修正系数,
            'lambda_a_mod': 客队λ修正系数,
            'draw_boost': 平局概率上调比例(0~0.25),
            'reason': 分析原因文本,
            'handicap_numeric': 即时盘口数值
        }
    """
    # --- 解析即时盘口数值 ---
    actual_hcp = parse_handicap_value(handicap.live)
    actual_magnitude = abs(actual_hcp)

    # --- 计算预期盘口（实力差归一化到盘口维度）---
    # 公式: strength_gap / 20 * 0.5
    # strength_gap=25 → 0.625, 四舍五入到0.75
    raw_expected = abs(strength_gap) / 20.0 * 0.5
    expected_magnitude = _round_to_quarter(raw_expected)

    # --- 计算差值（正=深开，负=浅开）---
    diff = actual_magnitude - expected_magnitude

    # --- 判断盘口类型 ---
    # 默认值
    lambda_h_mod = 1.0
    lambda_a_mod = 1.0
    draw_boost = 0.0
    reason = ""
    hcp_type = "match"

    # 判断哪个是强队/弱队
    # 实际盘口为负 → 主队让球 → 主队是强队
    # 实际盘口为正 → 主队受让 → 客队是强队
    home_is_strong = (actual_hcp < 0)
    # 若盘口为0（平手盘），根据strength_gap判断
    if actual_hcp == 0:
        home_is_strong = (strength_gap >= 0)

    # 阵容已知度修正系数（未知时力道减半）
    lineup_factor = 1.0 if lineup_known else 0.5

    if diff >= 0.50:
        # === 盘路深开 ===
        hcp_type = "deep"
        # 基础修正：强队λ *= 1.05
        lambda_deep_base = 1.05

        # 水位修正检查
        if handicap.water_live >= 2.0:
            # 深开+高水 → 高水阻盘，降级为不修正
            lambda_deep_base = 1.0
            reason = "盘路深开(高水阻盘，降级为不修正)"
        elif handicap.water_live <= 1.80:
            # 深开+低水 → 加强修正
            lambda_deep_base = 1.08
            reason = "盘路深开(低水支撑，λ+8%)"
        else:
            reason = "盘路深开(λ+5%)"

        # 应用修正（考虑阵容已知度）
        if home_is_strong:
            lambda_h_mod = 1.0 + (lambda_deep_base - 1.0) * lineup_factor
            lambda_a_mod = 1.0
        else:
            lambda_a_mod = 1.0 + (lambda_deep_base - 1.0) * lineup_factor
            lambda_h_mod = 1.0

        draw_boost = 0.0

    elif diff <= -0.50:
        # === 盘路浅开 ===
        hcp_type = "shallow"
        # 基础修正：弱队λ *= 0.95, 平局+15%
        lambda_shallow_base = 0.95
        draw_boost_base = 0.15

        # 水位修正检查
        if handicap.water_live >= 2.0:
            # 浅开+高水 → 弱队更受支持，平局概率加大
            lambda_shallow_base = 0.95
            draw_boost_base = 0.25
            reason = "盘路浅开(高水示弱，弱队受支持，平局+25%)"
        else:
            reason = "盘路浅开(防平，弱队λ-5%，平局+15%)"

        # 应用修正（考虑阵容已知度）
        if home_is_strong:
            # 主队强 → 弱队是客队
            lambda_a_mod = 1.0 - (1.0 - lambda_shallow_base) * lineup_factor
            lambda_h_mod = 1.0
        else:
            # 客队强 → 弱队是主队
            lambda_h_mod = 1.0 - (1.0 - lambda_shallow_base) * lineup_factor
            lambda_a_mod = 1.0

        draw_boost = draw_boost_base * lineup_factor

    else:
        # === 盘路匹配 ===
        hcp_type = "match"
        reason = "盘路匹配(无修正)"
        lambda_h_mod = 1.0
        lambda_a_mod = 1.0
        draw_boost = 0.0

    # --- 水位独立检查（初盘vs即时盘水位异动）---
    # 如果初盘到即时盘主队水位显著上升（>0.10），可能暗示主队不被看好
    water_shift = handicap.water_live - handicap.water_initial
    if water_shift > 0.10 and hcp_type == "match":
        # 水位上升但盘口不变 → 轻微看衰主队
        lambda_h_mod = 1.0 - 0.02 * lineup_factor
        reason = "盘路匹配(主队水位上升，λ_h-2%)"
    elif water_shift < -0.10 and hcp_type == "match":
        # 水位下降但盘口不变 → 轻微看好主队
        lambda_h_mod = 1.0 + 0.02 * lineup_factor
        reason = "盘路匹配(主队水位下降，λ_h+2%)"

    return {
        'diff': round(diff, 2),
        'type': hcp_type,
        'lambda_h_mod': round(lambda_h_mod, 4),
        'lambda_a_mod': round(lambda_a_mod, 4),
        'draw_boost': round(draw_boost, 4),
        'reason': reason,
        'handicap_numeric': actual_hcp
    }


# ============================================================
# 自测代码
# ============================================================
if __name__ == "__main__":
    import json

    print("=" * 60)
    print("盘口博弈分析系统 v1.0 — 自测")
    print("=" * 60)

    # 测试 parse_handicap_value
    print("\n--- parse_handicap_value 测试 ---")
    test_cases = ['-1.25', '+0.5', '0', '-0.75', '+1.0', '1.0', '-2.0', '+0.25', '0.0']
    for tc in test_cases:
        val = parse_handicap_value(tc)
        print(f"  '{tc}' → {val}")

    # 测试 _round_to_quarter
    print("\n--- _round_to_quarter 测试 ---")
    for val in [0.625, 0.3, 0.1, 0.8, 1.2, 0.0]:
        rv = _round_to_quarter(val)
        print(f"  {val} → {rv}")

    # 示例测试: strength_gap=25, actual=-1.25 → diff=0.5, type=deep
    print("\n--- 示例测试 (strength_gap=25, hcp=-1.25) ---")
    h1 = HandicapData(initial='-1.0', live='-1.25', water_initial=1.85, water_live=2.05)
    r1 = analyze_handicap(strength_gap=25, handicap=h1)
    print(json.dumps(r1, ensure_ascii=False, indent=2))

    # 案例1: 深开+低水
    print("\n--- 案例1: 深开+低水 (strength_gap=20, hcp=-1.0, water=1.75) ---")
    h2 = HandicapData(initial='-0.75', live='-1.0', water_initial=1.80, water_live=1.75)
    r2 = analyze_handicap(strength_gap=20, handicap=h2)
    print(json.dumps(r2, ensure_ascii=False, indent=2))

    # 案例2: 浅开+高水
    print("\n--- 案例2: 浅开+高水 (strength_gap=30, hcp=-0.75, water=2.05) ---")
    h3 = HandicapData(initial='-1.0', live='-0.75', water_initial=1.90, water_live=2.05)
    r3 = analyze_handicap(strength_gap=30, handicap=h3)
    print(json.dumps(r3, ensure_ascii=False, indent=2))

    # 案例3: 盘路匹配
    print("\n--- 案例3: 盘路匹配 (strength_gap=15, hcp=-0.5, water=1.90) ---")
    h4 = HandicapData(initial='-0.5', live='-0.5', water_initial=1.90, water_live=1.90)
    r4 = analyze_handicap(strength_gap=15, handicap=h4)
    print(json.dumps(r4, ensure_ascii=False, indent=2))

    # 案例4: 客队强势盘口 (正盘口)
    print("\n--- 案例4: 客队强 (strength_gap=-30, hcp=+0.75, water=1.85) ---")
    h5 = HandicapData(initial='+0.5', live='+0.75', water_initial=1.80, water_live=1.85)
    r5 = analyze_handicap(strength_gap=-30, handicap=h5)
    print(json.dumps(r5, ensure_ascii=False, indent=2))

    # 案例5: 阵容未知 + 深开
    print("\n--- 案例5: 阵容未知 + 深开 (lineup_known=False) ---")
    h6 = HandicapData(initial='-1.0', live='-1.25', water_initial=1.85, water_live=1.85)
    r6 = analyze_handicap(strength_gap=25, handicap=h6, lineup_known=False)
    print(json.dumps(r6, ensure_ascii=False, indent=2))

    # 案例6: 水位异动（盘口不变但水位下降）
    print("\n--- 案例6: 水位异动 (盘口不变, 水位从1.90→1.75) ---")
    h7 = HandicapData(initial='-0.5', live='-0.5', water_initial=1.90, water_live=1.75)
    r7 = analyze_handicap(strength_gap=12, handicap=h7)
    print(json.dumps(r7, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("自测完成")
    print("=" * 60)
