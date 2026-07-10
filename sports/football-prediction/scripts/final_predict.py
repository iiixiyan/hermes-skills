#!/usr/bin/env python3
"""Get comprehensive predictions with proper dual picks for all matches"""
import sys, importlib.util, json
sys.path.insert(0, '.')

# Load WC engine
spec = importlib.util.spec_from_file_location('wcp', 'worldcup-predict-v10.py')
wcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wcp)

# World Cup matches
wc_matches = [
    ('6067', '克罗地亚', '加纳', 11, 73, 1.897, 4.777, 46, 1, 0, 47, 18, 27, 3, '多云有雨', 25, 1),
    ('6068', '巴拿马', '英格兰', 34, 4, 15.510, 1.161, 38, 7, 42, 3, 13, 31, 3, '阴', 26, 1),
    ('6069', '哥伦比亚', '葡萄牙', 13, 5, 3.513, 2.000, 30, 13, 46, 0, 9, 35, 3, '局部有云', 29, 1),
    ('6070', '刚果金', '乌兹别克', 46, 50, 1.610, 5.442, 0, 47, 46, 0, 47, 0, 3, '局部有云', 30, 1),
    ('6071', '阿尔及利', '奥地利', 28, 24, 4.082, 2.887, 45, 1, 0, 47, 46, 1, 3, '局部有云', 28, 1),
    ('6072', '约旦', '阿根廷', 63, 1, 17.416, 1.146, 38, 6, 42, 3, 12, 30, 3, '阴有雨', 23, 1),
]

print("=== World Cup R3 Predictions ===")
for num, home, away, fh, fa, o1, o3, r1, c1, r2, c2, r3, c3, rd, weather, temp, neutral in wc_matches:
    h, a, rule, conf = wcp.predict(
        h=home, g=away, fh=fh, fa=fa, rd=rd,
        o1=o1, o3=o3,
        r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3,
        weather=weather, temp=temp, neutral=neutral,
        pts_h=-1, pts_a=-1
    )
    fmt = wcp.format_result(h, a, rule, conf)
    print(f'\n{num} {home}({fh}) vs {away}({fa})')
    print(f'  规则={rule} 比分1={fmt[0]} 比分2={fmt[1]} 信心={conf}★({fmt[2]})')

# Also get from predict_with_basics
print("\n\n=== Same with format_result details ===")
for num, home, away, fh, fa, o1, o3, r1, c1, r2, c2, r3, c3, rd, weather, temp, neutral in wc_matches:
    h, a, rule, conf = wcp.predict(
        h=home, g=away, fh=fh, fa=fa, rd=rd,
        o1=o1, o3=o3,
        r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3,
        weather=weather, temp=temp, neutral=neutral,
        pts_h=-1, pts_a=-1
    )
    fmt = wcp.format_result(h, a, rule, conf)
    print(f'〖{num}〗{home} VS {away} | {fmt[0]}/{fmt[1]} | {fmt[2]} | {rule}')
