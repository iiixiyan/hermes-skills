#!/usr/bin/env python3
"""
Daily review signal analyzer for BJDC matches.
Takes collected match data (欧指升/降 + 亚指升盘/降盘/高水/低水) and:
  1. Classifies which signals were triggered per match
  2. Determines if signal direction matched actual BJDC result
  3. Computes league-grouped statistics and signal accuracy tables
  4. Outputs structured markdown for skill update

Usage:
  python3 scripts/daily-review-signal-analyzer.py < input.json

Input JSON format (list of matches):
  [{
    "mid": "2645513",           # matchID
    "league": "巴西乙",          # league name
    "home": "累西腓体育",       # home team
    "score": "1-1",             # actual score
    "away": "米纳斯吉拉斯竞技", # away team
    "hcap": -1,                 # handicap (负=主队让球)
    "result": "让负",           # BJDC actual result
    "oz_up": [29, 0, 2],        # 上升家数 [胜, 平, 负]
    "oz_down": [1, 28, 26],     # 降低家数 [胜, 平, 负]
    "yz_up": 0,                 # 升盘家数
    "yz_down": 11,              # 降盘家数
    "yz_high": 19,              # 高水家数
    "yz_low": 2                 # 低水家数
  }]

Output: structured markdown tables with signal accuracy by league
"""

import json, sys, re
from collections import defaultdict

# ── signal definitions ────────────────────────────────────────────
# Each signal: (name, trigger_fn, correct_fn)
#   trigger_fn(match) -> bool     : was this signal triggered?
#   correct_fn(match) -> str      : "✅" correct, "❌" wrong, "➖" walkover

SIGNALS = []

def add_signal(name, trigger, correct_for_ups, require_down_z=0):
    """Register a signal with trigger/correct conditions."""
    def trigger_fn(m):
        return trigger(m)
    def correct_fn(m):
        return correct_for_ups(m)
    SIGNALS.append((name, trigger_fn, correct_fn))

# Signal: 一致升主胜 (4b)
add_signal("一致升主胜(4b, ≥20/≤3)",
    lambda m: m["oz_up"][0] >= 20 and m["oz_down"][0] <= 3,
    lambda m: "✅" if m["result"] in ["让负","负"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 极端一致升主胜 (≥25/≤1)
add_signal("极端一致升主胜(≥25/≤1)",
    lambda m: m["oz_up"][0] >= 25 and m["oz_down"][0] <= 1,
    lambda m: "✅" if m["result"] in ["让负","负"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 一致降主胜 (4c)
add_signal("一致降主胜(4c, ≥20/≤3)",
    lambda m: m["oz_down"][0] >= 20 and m["oz_up"][0] <= 3,
    lambda m: "✅" if m["result"] in ["让胜","胜"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 极端一致降主胜 (≤1/≥25)
add_signal("极端一致降主胜(≤1/≥25)",
    lambda m: m["oz_down"][0] >= 25 and m["oz_up"][0] <= 1,
    lambda m: "✅" if m["result"] in ["让胜","胜"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 一致升客胜 (≥20家, 客胜上升=卖客队=主队方向)
add_signal("一致升客胜(≥20)",
    lambda m: m["oz_up"][2] >= 20 and m["oz_down"][2] <= 5,
    lambda m: "✅" if m["result"] in ["让胜","胜"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 一致降客胜 (≥20家, 客胜下降=买客队=客队方向)
add_signal("一致降客胜(≥20)",
    lambda m: m["oz_down"][2] >= 20 and m["oz_up"][2] <= 3,
    lambda m: "✅" if m["result"] in ["让负","负"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 强升盘(≥8家)→上盘方向
add_signal("强升盘(≥8家)",
    lambda m: m["yz_up"] >= 8,
    lambda m: "✅" if m["result"] in ["让胜","胜"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 强降盘(≥8家)→下盘方向
add_signal("强降盘(≥8家)",
    lambda m: m["yz_down"] >= 8,
    lambda m: "✅" if m["result"] in ["让负","负"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 极端高水(≥15高/≤3低)→诱上/不防→下盘
add_signal("极端高水(≥15/≤3)",
    lambda m: m["yz_high"] >= 15 and m["yz_low"] <= 3,
    lambda m: "✅" if m["result"] in ["让负","负"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 极端低水(≥15低/≤5高)→实盘力挺→上盘
add_signal("极端低水(≥15/≤5)",
    lambda m: m["yz_low"] >= 15 and m["yz_high"] <= 5,
    lambda m: "✅" if m["result"] in ["让胜","胜"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 4b+强降盘(诱上组合)
add_signal("4b+强降盘(诱上)",
    lambda m: m["oz_up"][0] >= 20 and m["oz_down"][0] <= 3 and m["yz_down"] >= 8,
    lambda m: "✅" if m["result"] in ["让负","负"] else ("➖" if m["result"] in ["让平","平"] else "❌"))

# Signal: 4c+强升盘(实盘力挺)
add_signal("4c+强升盘(实盘)",
    lambda m: m["oz_down"][0] >= 20 and m["oz_up"][0] <= 3 and m["yz_up"] >= 8,
    lambda m: "✅" if m["result"] in ["让胜","胜"] else ("➖" if m["result"] in ["让平","平"] else "❌"))


# ── analysis ──────────────────────────────────────────────────────

def analyze(matches):
    """Run all signals on all matches, return structured results."""
    results = {}
    for name, trigger_fn, correct_fn in SIGNALS:
        triggered = []
        for m in matches:
            if trigger_fn(m):
                triggered.append({
                    "mid": m["mid"],
                    "league": m["league"],
                    "home": m["home"],
                    "result": m["result"],
                    "score": m["score"],
                    "verdict": correct_fn(m)
                })
        if triggered:
            total = len(triggered)
            correct = sum(1 for t in triggered if t["verdict"] == "✅")
            wrong = sum(1 for t in triggered if t["verdict"] == "❌")
            walkover = sum(1 for t in triggered if t["verdict"] == "➖")
            non_wo = total - walkover
            acc = correct / non_wo * 100 if non_wo > 0 else 0
            results[name] = {
                "total": total, "correct": correct, "wrong": wrong,
                "walkover": walkover, "accuracy": round(acc, 1),
                "details": triggered
            }
    return results

def league_stats(matches):
    stats = defaultdict(lambda: {"total": 0, "shangpan": 0, "xiapan": 0, "zoushui": 0})
    for m in matches:
        l = m["league"]
        stats[l]["total"] += 1
        if m["result"] in ["让胜", "胜"]:
            stats[l]["shangpan"] += 1
        elif m["result"] in ["让负", "负"]:
            stats[l]["xiapan"] += 1
        else:
            stats[l]["zoushui"] += 1
    return stats

def format_markdown(matches, signals, league_stats):
    """Generate markdown report."""
    lines = []
    
    # ── League stats ──
    lines.append("#### 📊 各联赛准确率统计")
    lines.append("")
    lines.append("| 联赛 | 场次 | 上盘 | 下盘 | 走水 | 上盘率 |")
    lines.append("|:----|:---:|:----:|:----:|:---:|:-----:|")
    for l, s in sorted(league_stats.items()):
        sp = s["shangpan"]/s["total"]*100
        lines.append(f"| {l} | {s['total']} | {s['shangpan']} | {s['xiapan']} | {s['zoushui']} | {sp:.0f}% |")
    lines.append("")
    
    # ── Signal accuracy ──
    lines.append("#### 📈 信号准确率")
    lines.append("")
    lines.append("| 信号 | 触发 | 正确 | 错误 | 走水 | 准确率 |")
    lines.append("|:----|:----:|:----:|:----:|:----:|:-----:|")
    for name, s in sorted(signals.items()):
        lines.append(f"| {name} | {s['total']} | {s['correct']} | {s['wrong']} | {s['walkover']} | **{s['accuracy']}%** |")
    lines.append("")
    
    # ── Per-signal details ──
    lines.append("#### 🔍 逐信号详情")
    lines.append("")
    for name, s in sorted(signals.items()):
        lines.append(f"**{name}**: {s['total']}次触发, {s['correct']}正确/{s['wrong']}错误/{s['walkover']}走水 = {s['accuracy']}%")
        for d in s["details"]:
            lines.append(f"  - {d['mid']} ({d['league']}) {d['home']} → {d['result']} [{d['verdict']}]")
        lines.append("")
    
    return "\n".join(lines)

def main():
    data = json.load(sys.stdin)
    sigs = analyze(data)
    ls = league_stats(data)
    print(format_markdown(data, sigs, ls))

if __name__ == "__main__":
    main()
