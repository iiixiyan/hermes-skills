#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞足复盘·比分命中率分析器
==========================
用于每日10:00复盘任务。核心流程：
1. 从 prediction-tracker DB 读取昨天预测记录（如无则从cron输出文件解析）
2. 采集开奖结果页实际赛果
3. 逐场对比，生成比分命中率分析报告
4. 更新 tracker DB

依赖：
    python3 + playwright
    from prediction_tracker import get_tracker

用法：
    python3 review-score-analyzer.py [--date 2026-05-23]

    不带参数 => 自动分析昨天
    带 --date YYYY-MM-DD => 分析指定日期
    带 --date latest => 分析最新有数据的日期
"""

import os
import sys
import re
import json
import glob
import argparse
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

# 添加父目录到路径以便导入 prediction_tracker
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

# scripts 目录无 __init__.py，直接加其父目录到 path
sys.path.insert(0, SCRIPT_DIR)

from prediction_tracker import get_tracker

# ============================================================
# 常量
# ============================================================
CRON_OUTPUT_DIR = os.path.expanduser("~/.hermes/cron/output")

# 竞足预测任务的 job IDs
PREDICTION_JOBS = {
    '11am': 'ffd6606df141',   # 竞足第一次预测
    '17pm': '9ac2f7874ec8',   # 竞足第二次预测
    '2030': 'cd0456f2c803',   # 竞足综合复盘分析
}

# 开奖结果页
PRIZE_URL = "https://kt.59itou.com/jingcai/prize/"

# ============================================================
# 策略1：从 prediction-tracker DB 读取预测记录
# ============================================================

def load_predictions_from_db(target_date: str) -> List[Dict]:
    """
    从 prediction-tracker DB 读取指定日期的预测记录。
    返回按 match_num 去重后的列表（优先保留最新预测）。
    """
    tracker = get_tracker()
    if not tracker:
        return []

    conn = tracker._get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM predictions WHERE date = ? AND hit_status = -1
        ORDER BY id ASC
    ''', (target_date,))

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return []

    # 按 match_num 去重，保留最后一条（最新预测）
    seen = {}
    for row in rows:
        seen[row['match_num']] = row  # 后面的覆盖前面的，取最新

    return list(seen.values())


# ============================================================
# 策略2：从 cron 输出文件解析预测记录
# ============================================================

def find_cron_output_files(job_id: str, target_date: str) -> List[str]:
    """查找指定 job 在指定日期的 cron 输出文件"""
    job_dir = os.path.join(CRON_OUTPUT_DIR, job_id)
    if not os.path.isdir(job_dir):
        return []

    # 匹配当天文件：2026-05-23_*.md
    pattern = f"{target_date}_*.md"
    files = sorted(glob.glob(os.path.join(job_dir, pattern)))
    return files


def parse_predictions_from_cron_output(filepath: str) -> List[Dict]:
    """
    从 cron 输出文件解析比分预测记录。
    """
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    predictions = []

    # 模式1：解析〖竞足-XXXX〗格式
    match_header = re.findall(
        r'\u3016\u7ade\u8db3[-_\u2014\u2013](\d+)\u3017\s*([^\s]+)\s*[Vv][Ss]\s*([^\s(\uFF08]+)',
        content
    )

    for m in match_header:
        match_num = m[0]
        home_team = m[1].strip()
        away_team = m[2].strip()

        # 查找该场比赛后面的比分预测
        match_start = content.find(f"\u3016\u7ade\u8db3-{match_num}\u3017")
        if match_start < 0:
            # 尝试其他分隔符
            for sep in ['\u3016\u7ade\u8db3\u2014', '\u3016\u7ade\u8db3\u2013']:
                match_start = content.find(f"{sep}{match_num}\u3017")
                if match_start >= 0:
                    break

        if match_start < 0:
            continue

        # 找下一场或文件结尾
        remaining = content[match_start + 50:]
        next_match_search = re.search(r'\u3016\u7ade\u8db3[-_\u2014\u2013]\d+\u3017', remaining)
        if next_match_search:
            match_content = content[match_start:match_start + 50 + next_match_search.start()]
        else:
            match_content = content[match_start:]

        pred = parse_match_predictions(match_content, match_num, home_team, away_team)
        if pred:
            predictions.append(pred)

    # 模式2：解析表格格式（复盘或汇总中的比分对比）
    if not predictions:
        predictions = parse_table_format(content)

    # 模式3：解析自由格式
    if not predictions:
        predictions = parse_free_format(content)

    return predictions


def parse_match_predictions(text: str, match_num: str, home_team: str,
                            away_team: str) -> Optional[Dict]:
    """从一段文本中解析单场比赛的比分预测"""
    result = {
        'match_num': match_num,
        'home_team': home_team,
        'away_team': away_team,
        'league': '',
        'pred_normal_1': None,
        'pred_normal_2': None,
        'pred_abnormal_1': None,
        'pred_abnormal_2': None,
        'confidence': None,
    }

    # 查找正常比分 🟢 第一组（正常比分）：2-0 / 3-0
    normal_section = re.search(
        r'🟢?\s*第一组[（(]?\s*正常比分\s*[）)]?\s*[：:]\s*([\d]+[-–—][\d]+)\s*/\s*([\d]+[-–—][\d]+)',
        text
    )
    if normal_section:
        result['pred_normal_1'] = normalize_score(normal_section.group(1))
        result['pred_normal_2'] = normalize_score(normal_section.group(2))

    if not normal_section:
        # 尝试 🛜 标记
        normal_section = re.search(
            r'🛜\s*([\d]+[-–—][\d]+)\s*/\s*([\d]+[-–—][\d]+)',
            text
        )
        if normal_section:
            result['pred_normal_1'] = normalize_score(normal_section.group(1))
            result['pred_normal_2'] = normalize_score(normal_section.group(2))

    # 查找异常比分 🔴 第二组（异常比分）：1-1 / 1-2
    abnormal_section = re.search(
        r'🔴?\s*第二组[（(]?\s*异常比分\s*[）)]?\s*[：:]\s*([\d]+[-–—][\d]+)\s*/\s*([\d]+[-–—][\d]+)',
        text
    )
    if abnormal_section:
        result['pred_abnormal_1'] = normalize_score(abnormal_section.group(1))
        result['pred_abnormal_2'] = normalize_score(abnormal_section.group(2))

    if not abnormal_section:
        abnormal_section = re.search(
            r'🔥\s*([\d]+[-–—][\d]+)\s*/\s*([\d]+[-–—][\d]+)',
            text
        )
        if abnormal_section:
            result['pred_abnormal_1'] = normalize_score(abnormal_section.group(1))
            result['pred_abnormal_2'] = normalize_score(abnormal_section.group(2))

    # 查找信心评级（格式：⭐ 信心评级：★★★☆☆ 或 信心：★★★★☆）
    confidence = re.search(r'(?:⭐\s*)?信心(?:评级)?[：:]\s*(★+)', text)
    if confidence:
        stars = confidence.group(1).count('★')
        result['confidence'] = stars

    # 必须有至少2个比分才返回
    scores = [result['pred_normal_1'], result['pred_normal_2'],
              result['pred_abnormal_1'], result['pred_abnormal_2']]
    non_none = [s for s in scores if s]
    if len(non_none) < 2:
        return None

    return result


def normalize_score(s: str) -> str:
    """标准化比分格式为 'X-Y'"""
    return s.replace('\u2013', '-').replace('\u2014', '-').replace('_', '-')


def parse_table_format(content: str) -> List[Dict]:
    """解析表格格式的预测数据"""
    predictions = []

    # 查找包含 🛜 和 🔥 标记的表格行
    table_rows = re.findall(
        r'\|\s*(\d+)\s*\|\s*([^\|]+?)\s*\|\s*🛜\s*'
        r'([\d-]+)\s*/\s*([\d-]+)\s*🔥\s*([\d-]+)\s*/\s*([\d-]+)\s*\|',
        content
    )

    for row in table_rows:
        team_info = row[1].strip()
        home_team = team_info.split('vs')[0].strip() if 'vs' in team_info else ''
        away_team = team_info.split('vs')[1].strip() if 'vs' in team_info else ''
        predictions.append({
            'match_num': row[0],
            'home_team': home_team,
            'away_team': away_team,
            'league': '',
            'pred_normal_1': normalize_score(row[2]),
            'pred_normal_2': normalize_score(row[3]),
            'pred_abnormal_1': normalize_score(row[4]),
            'pred_abnormal_2': normalize_score(row[5]),
            'confidence': None,
        })

    return predictions


def parse_free_format(content: str) -> List[Dict]:
    """解析自由格式的比分预测"""
    predictions = []

    # 查找 "场次：3001" 后的比分
    matches = re.findall(
        r'(?:\u573a\u6b21|\u7f16\u53f7|Match)[\uff1a:]\s*(\d+).*?'
        r'(?:[\u9884\u6d4b\uff1a:]\s*)?([\d]+[-_\u2014\u2013][\d]+)\s*/\s*([\d]+[-_\u2014\u2013][\d]+)',
        content
    )

    for m in matches:
        predictions.append({
            'match_num': m[0],
            'home_team': '',
            'away_team': '',
            'league': '',
            'pred_normal_1': normalize_score(m[1]),
            'pred_normal_2': normalize_score(m[2]),
            'pred_abnormal_1': None,
            'pred_abnormal_2': None,
            'confidence': None,
        })

    return predictions


def parse_all_yesterday_predictions(target_date: str) -> List[Dict]:
    """
    综合两种策略获取昨天的预测记录。
    优先从 tracker DB 读取，失败则从 cron 输出文件解析。
    """
    # 策略1：从 DB 读取
    predictions = load_predictions_from_db(target_date)
    if predictions:
        print(f"[INFO] 从 tracker DB 读取到 {len(predictions)} 条预测记录")
        return predictions

    # 策略2：从 cron 输出文件解析
    print(f"[INFO] DB 无数据，尝试从 cron 输出文件解析...")

    all_predictions = []

    # 优先用 20:30 的预测（最接近比赛时间的预测 = 最准确）
    for job_key in ['2030', '17pm', '11am']:
        job_id = PREDICTION_JOBS[job_key]
        files = find_cron_output_files(job_id, target_date)

        for filepath in files:
            preds = parse_predictions_from_cron_output(filepath)
            if preds:
                for p in preds:
                    p['_source'] = job_key
                    p['_source_file'] = filepath
                all_predictions.extend(preds)
                print(f"[INFO] 从 {job_key} ({os.path.basename(filepath)}) 解析到 {len(preds)} 条")

    # 去重（后出现的覆盖前面的 = 20:30 > 17:00 > 11:00）
    seen = {}
    for p in all_predictions:
        key = p['match_num']
        seen[key] = p  # 后面的覆盖前面的
    result = list(seen.values())
    print(f"[INFO] 共获取 {len(result)} 条预测记录（去重后）")
    return result


# ============================================================
# 采集实际赛果
# ============================================================

def fetch_actual_results(target_date: str) -> List[Dict]:
    """
    从开奖结果页采集实际赛果。
    使用 Playwright 获取实时数据。
    """
    try:
        from playwright.async_api import async_playwright
        import asyncio

        async def _fetch():
            results = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # 访问开奖结果页
                await page.goto(PRIZE_URL, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)

                # 尝试切换到指定日期
                date_found = await page.evaluate(f"""
                    (function() {{
                        var tabs = document.querySelectorAll('.van-tab, [class*="tab"], [class*="date"]');
                        var targetDate = '{target_date}';
                        for (var i = 0; i < tabs.length; i++) {{
                            var txt = tabs[i].textContent.trim();
                            var parts = targetDate.split('-');
                            var shortDate = parts[1] + '-' + parts[2];
                            if (txt === targetDate || txt === shortDate ||
                                txt.includes(shortDate) || txt.includes(targetDate.replace('2026-', ''))) {{
                                tabs[i].click();
                                return 'clicked: ' + txt;
                            }}
                        }}
                        return 'not found';
                    }})()
                """)

                print(f"[FETCH] 日期选择: {date_found}")
                await page.wait_for_timeout(2000)

                # 获取完整页面文本
                inner_text = await page.evaluate("document.body.innerText")

                # 获取 matchID
                items = await page.evaluate("""
                    (function() {
                        var items = document.querySelectorAll('[class*="item"]');
                        var ids = [];
                        for (var i = 0; i < items.length; i++) {
                            if (items[i].id) {
                                ids.push(items[i].id);
                            }
                        }
                        return ids;
                    })()
                """)

                print(f"[FETCH] 找到 {len(items)} 个比赛item")

                # 解析 innerText 中的赛果
                lines = inner_text.split('\n')
                current_match = {}
                weekday_pattern = re.compile(
                    r'(\u5468\u4e94|\u5468\u516d|\u5468\u65e5|\u5468\u4e00|'
                    r'\u5468\u4e8c|\u5468\u4e09|\u5468\u56db)\d+'
                )

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    match = weekday_pattern.search(line)
                    if match:
                        if current_match.get('match_num'):
                            results.append(current_match)

                        current_match = {'raw_line': line}
                        match_num_search = weekday_pattern.search(line)
                        if match_num_search:
                            current_match['match_num'] = match_num_search.group(0)[2:]

                        score_search = re.search(r'(\d+)[-_\u2014\u2013](\d+)', line)
                        if score_search:
                            current_match['score'] = f"{score_search.group(1)}-{score_search.group(2)}"
                            current_match['home_goals'] = int(score_search.group(1))
                            current_match['away_goals'] = int(score_search.group(2))

                            # 解析队伍
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if weekday_pattern.search(part):
                                    if i + 1 < len(parts):
                                        current_match['home_team'] = parts[i + 1]
                                    if i + 3 < len(parts) and re.match(r'^\d+[-]\d+$', parts[i + 2]):
                                        current_match['away_team'] = parts[i + 3]
                                    break

                if current_match.get('match_num'):
                    results.append(current_match)

                await browser.close()

            return results

        results = asyncio.run(_fetch())
        print(f"[FETCH] 成功获取 {len(results)} 场比赛实际赛果")
        return results

    except Exception as e:
        print(f"[FETCH ERROR] {e}")
        return []


# ============================================================
# 命中判定逻辑
# ============================================================

def determine_hit_status(pred: Dict, actual: Dict) -> Dict:
    """
    逐场判定命中状态。
    """
    actual_score = actual.get('score', '')
    home_goals = actual.get('home_goals')
    away_goals = actual.get('away_goals')

    if not actual_score or home_goals is None:
        return {'exact_hit': False, 'direction_hit': False, 'abnormal_hit': False,
                'hit_score': '', 'deviation': '\u65e0\u5b9e\u9645\u8d5b\u679c\u6570\u636e'}

    normal_scores = [pred.get('pred_normal_1'), pred.get('pred_normal_2')]
    abnormal_scores = [pred.get('pred_abnormal_1'), pred.get('pred_abnormal_2')]
    all_scores = [s for s in normal_scores + abnormal_scores if s]

    # 实际胜负方向
    if home_goals > away_goals:
        actual_dir = '\u80dc'
    elif home_goals == away_goals:
        actual_dir = '\u5e73'
    else:
        actual_dir = '\u8d1f'

    exact_hit = False
    hit_score = ''
    abnormal_hit_exact = False

    for s in normal_scores:
        if s and s == actual_score:
            exact_hit = True
            hit_score = f"\u6b63\u5e38\u6bd4\u5206 {s} \u2705"
            break

    if not exact_hit:
        for s in abnormal_scores:
            if s and s == actual_score:
                exact_hit = True
                abnormal_hit_exact = True
                hit_score = f"\u5f02\u5e38\u6bd4\u5206 {s} \u2705"
                break

    direction_hit = False
    abnormal_dir_hit = False

    if not exact_hit:
        for s in all_scores:
            try:
                parts = s.split('-')
                ph, pa = int(parts[0]), int(parts[1])
                if (ph > pa and actual_dir == '\u80dc') or \
                   (ph == pa and actual_dir == '\u5e73') or \
                   (ph < pa and actual_dir == '\u8d1f'):
                    direction_hit = True
                    hit_score = f"\u65b9\u5411\u547d\u4e2d\uff08\u9884\u6d4b{s}\u2192\u5b9e\u9645{actual_score}\uff09"
                    if s in abnormal_scores:
                        abnormal_dir_hit = True
                    break
            except:
                continue

    deviation = compute_deviation(all_scores, actual_score, home_goals, away_goals)

    return {
        'exact_hit': exact_hit,
        'direction_hit': direction_hit or exact_hit,
        'abnormal_hit': abnormal_hit_exact or abnormal_dir_hit,
        'hit_score': hit_score,
        'deviation': deviation,
    }


def compute_deviation(pred_scores: List[str], actual_score: str,
                      home_goals: int, away_goals: int) -> str:
    """计算预测偏差"""
    if not pred_scores or not actual_score:
        return '\u65e0\u6570\u636e'

    min_diff = 999
    closest_pred = ''

    for s in pred_scores:
        try:
            parts = s.split('-')
            ph, pa = int(parts[0]), int(parts[1])
            diff = abs(ph - home_goals) + abs(pa - away_goals)
            if diff < min_diff:
                min_diff = diff
                closest_pred = s
        except:
            continue

    if min_diff == 0:
        return '\u7cbe\u786e\u547d\u4e2d'
    elif min_diff == 1:
        return f'\u5dee1\u7403\uff08\u9884\u6d4b{closest_pred}\u2192\u5b9e\u9645{actual_score}\uff09'
    elif min_diff >= 2:
        try:
            cp = closest_pred.split('-')
            cph, cpa = int(cp[0]), int(cp[1])
            if (cph > cpa and home_goals > away_goals) or \
               (cph == cpa and home_goals == away_goals) or \
               (cph < cpa and home_goals < away_goals):
                return f'\u5dee{min_diff}\u7403\uff0c\u65b9\u5411\u5bf9\uff08\u9884\u6d4b{closest_pred}\u2192\u5b9e\u9645{actual_score}\uff09'
            else:
                return f'\u5dee{min_diff}\u7403\uff0c\u65b9\u5411\u9519\uff08\u9884\u6d4b{closest_pred}\u2192\u5b9e\u9645{actual_score}\uff09'
        except:
            return f'\u5dee{min_diff}\u7403'

    return f'\u5dee{min_diff}\u7403'


# ============================================================
# 生成报告
# ============================================================

def generate_score_report(target_date: str, predictions: List[Dict],
                          actual_results: List[Dict]) -> str:
    """生成比分命中率分析报告"""
    if not predictions:
        return ("## \U0001F3AF \u6bd4\u5206\u547d\u4e2d\u7387\u590d\u76d8\n\n"
                "\u274c \u65e0\u9884\u6d4b\u6570\u636e\uff0c\u65e0\u6cd5\u8fdb\u884c\u6bd4\u5206\u547d\u4e2d\u7387\u5206\u6790")

    result_lookup = {}
    for r in actual_results:
        mn = r.get('match_num', '')
        if mn:
            result_lookup[mn] = r

    matches = []
    exact_count = 0
    direction_count = 0
    abnormal_count = 0
    deviation_1 = 0
    deviation_2plus = 0
    direction_wrong = 0

    for pred in predictions:
        mn = pred['match_num']
        actual = result_lookup.get(mn, {})

        status = determine_hit_status(pred, actual)

        h = pred.get('home_team', '?')
        a = pred.get('away_team', '?')
        team_info = f"{h} vs {a}"

        p1 = pred.get('pred_normal_1', '?')
        p2 = pred.get('pred_normal_2', '?')
        p3 = pred.get('pred_abnormal_1', '?')
        p4 = pred.get('pred_abnormal_2', '?')
        pred_str = f"\U0001F6DC{p1}"
        if p2:
            pred_str += f"/{p2}"
        pred_str += f" \U0001F525{p3}"
        if p4:
            pred_str += f"/{p4}"

        actual_score = actual.get('score', '?')

        if status['exact_hit']:
            result_icon = '\u2705'
            exact_count += 1
            direction_count += 1
        elif status['direction_hit']:
            result_icon = '\u25B3'
            direction_count += 1
            if '\u5dee1\u7403' in status['deviation']:
                deviation_1 += 1
            else:
                deviation_2plus += 1
        else:
            result_icon = '\u274C'
            direction_wrong += 1

        if status['abnormal_hit']:
            abnormal_count += 1

        matches.append({
            'match_num': mn,
            'team_info': team_info,
            'pred_str': pred_str,
            'actual_score': actual_score,
            'result_icon': result_icon,
            'status': status,
            'confidence': pred.get('confidence', ''),
            'league': pred.get('league', ''),
        })

    total = len(matches)

    lines = []
    lines.append(f"## \U0001F3AF \u6bd4\u5206\u547d\u4e2d\u7387\u590d\u76d8\uff08{target_date}\uff09")
    lines.append("")
    lines.append(f"### \u7cbe\u786e\u547d\u4e2d\u7387\uff1a{exact_count}/{total} = {exact_count/total*100:.1f}%")
    if direction_count > 0:
        lines.append(f"### \u65b9\u5411\u547d\u4e2d\u7387\uff08\u542b\u7cbe\u786e\uff09\uff1a{direction_count}/{total} = {direction_count/total*100:.1f}%")
    lines.append(f"### \u5f02\u5e38\u6bd4\u5206\u547d\u4e2d\uff1a{abnormal_count}/{total}")
    lines.append("")

    # 逐场对比表
    lines.append("### \U0001F4CB \u9010\u573a\u5bf9\u6bd4")
    lines.append("")
    lines.append("| \u573a\u6b21 | \u5bf9\u9635 | \u9884\u6d4b\uff08\u6b63\u5e38/\u5f02\u5e38\uff09 | \u5b9e\u9645 | \u7ed3\u679c | \u504f\u5dee\u8bf4\u660e |")
    lines.append("|:---:|:----|:-----------------|:---:|:---:|:--------|")

    for m in matches:
        lines.append(
            f"| {m['match_num']} | {m['team_info']} | {m['pred_str']} | "
            f"**{m['actual_score']}** | {m['result_icon']} | {m['status']['deviation']} |"
        )

    lines.append("")

    # 偏差分布
    lines.append("### \U0001F4CA \u504f\u5dee\u5206\u5e03")
    lines.append("")
    lines.append(f"| \u7c7b\u522b | \u6570\u91cf | \u5360\u6bd4 |")
    lines.append(f"|:----|:---:|:---:|")
    lines.append(f"| \u2705 \u7cbe\u786e\u547d\u4e2d | {exact_count} | {exact_count/total*100:.1f}% |")
    lines.append(f"| \u25B3 \u5dee1\u7403\uff08\u65b9\u5411\u5bf9\uff09 | {deviation_1} | {deviation_1/total*100:.1f}% |")
    l2_label = "\u25B3 \u5dee\u22652\u7403\uff08\u65b9\u5411\u5bf9\uff09"
    lines.append(f"| {l2_label} | {deviation_2plus} | {deviation_2plus/total*100:.1f}% |")
    lines.append(f"| \u274C \u65b9\u5411\u9519\u8bef | {direction_wrong} | {direction_wrong/total*100:.1f}% |")
    lines.append("")

    # 精确命中场次
    exact_matches = [m for m in matches if m['status']['exact_hit']]
    if exact_matches:
        lines.append("### \U0001F3C6 \u7cbe\u786e\u547d\u4e2d\u573a\u6b21")
        for m in exact_matches:
            lines.append(f"- **{m['match_num']}** {m['team_info']} \u2192 {m['actual_score']} {m['status']['hit_score']}")
        lines.append("")

    # 异常比分命中
    abnormal_matches = [m for m in matches if m['status']['abnormal_hit']]
    if abnormal_matches:
        lines.append("### \U0001F525 \u5f02\u5e38\u6bd4\u5206\u547d\u4e2d")
        for m in abnormal_matches:
            as_ = m['actual_score']
            lines.append(f"- **{m['match_num']}** {m['team_info']} \u2192 \u5b9e\u9645 {as_}\uff08\u5f02\u5e38\u65b9\u5411\u6355\u6349\u6210\u529f\uff09")
        lines.append("")

    # 方向错误场次
    wrong_matches = [m for m in matches if not m['status']['direction_hit']]
    if wrong_matches:
        lines.append("### \u26A0\uFE0F \u65b9\u5411\u9519\u8bef\u573a\u6b21\uff08\u91cd\u70b9\u5206\u6790\uff09")
        for m in wrong_matches:
            lines.append(f"- **{m['match_num']}** {m['team_info']}")
            lines.append(f"  - \u9884\u6d4b\uff1a{m['pred_str']} \u2192 \u5b9e\u9645\uff1a**{m['actual_score']}**")
            lines.append(f"  - \u504f\u5dee\uff1a{m['status']['deviation']}")
            if m['league']:
                lines.append(f"  - \u8054\u8d5b\uff1a{m['league']}")
        lines.append("")

    # 核心缺陷分析
    lines.append("### \U0001F50D \u6838\u5fc3\u7f3a\u9677\u5206\u6790")

    if deviation_1 > 0:
        d1_matches = [m for m in matches if '\u5dee1\u7403' in m['status']['deviation']]
        lines.append(f"- **\u6bd4\u5206\u504f\u5dee+/-1\u7403\uff08{deviation_1}\u573a\uff09**\uff1a\u5dee1\u7403\u8bf4\u660e\u80dc\u8d1f\u65b9\u5411\u5224\u65ad\u6b63\u786e\uff0c"
                     f"\u4f46\u8fdb\u7403\u6570\u4f30\u9884\u504f\u5dee\u3002\u53ef\u80fd\u539f\u56e0\uff1a\u5f31\u961f\u4e3b\u573a\u8fdb\u7403\u4f4e\u4f30\u3001\u5f3a\u961f\u8fdb\u653b\u72b6\u6001\u6ce2\u52a8\u7b49")
        for m in d1_matches[:3]:
            lines.append(f"  - {m['match_num']} {m['team_info']}\uff1a{m['status']['deviation']}")

    if direction_wrong > 0:
        lines.append(f"- **\u65b9\u5411\u5224\u65ad\u9519\u8bef\uff08{direction_wrong}\u573a\uff09**\uff1a\u80dc\u8d1f\u5e73\u65b9\u5411\u5b8c\u5168\u6253\u53cd\uff0c\u9700\u8981\u91cd\u70b9\u590d\u76d8")
        for m in wrong_matches[:3]:
            lines.append(f"  - {m['match_num']} {m['team_info']}\uff1a{m['status']['deviation']}")

    if abnormal_count > 0:
        lines.append(f"- **\u5f02\u5e38\u6bd4\u5206\u6355\u6349\uff08{abnormal_count}\u573a\u547d\u4e2d\uff09**\uff1a\u53cc\u8f68\u6bd4\u5206\u7b56\u7565\u6709\u6548")
    else:
        lines.append("- **\u5f02\u5e38\u6bd4\u5206\u6355\u6349**\uff1a\u672c\u8f6e\u65e0\u5f02\u5e38\u6bd4\u5206\u547d\u4e2d")

    if not wrong_matches and deviation_1 == 0 and deviation_2plus == 0:
        lines.append("- \U0001F389 \u672c\u8f6e\u5168\u90e8\u7cbe\u786e\u547d\u4e2d\uff0c\u65e0\u660e\u663e\u7f3a\u9677\uff01")

    lines.append("")

    return "\n".join(lines)


def update_tracker_db(target_date: str, predictions: List[Dict],
                      actual_results: List[Dict]) -> int:
    """将实际结果更新到 prediction-tracker DB"""
    try:
        from prediction_tracker import get_tracker

        tracker = get_tracker()
        if not tracker:
            return 0

        result_lookup = {}
        for r in actual_results:
            mn = r.get('match_num', '')
            if mn:
                result_lookup[mn] = r

        updated = 0
        for pred in predictions:
            mn = pred['match_num']
            actual = result_lookup.get(mn)
            if not actual or not actual.get('score'):
                continue

            conn = tracker._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id FROM predictions WHERE match_num = ? AND date = ? AND hit_status = -1',
                (mn, target_date)
            )
            existing = cursor.fetchone()
            conn.close()

            if existing:
                tracker.update_result(
                    match_num=mn,
                    actual_score=actual['score'],
                    home_goals=actual.get('home_goals', 0),
                    away_goals=actual.get('away_goals', 0)
                )
                updated += 1

        print(f"[TRACKER] 更新了 {updated} 条记录")
        return updated

    except Exception as e:
        print(f"[TRACKER ERROR] {e}")
        return 0


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='\u7ade\u8db3\u6bd4\u5206\u547d\u4e2d\u7387\u590d\u76d8\u5206\u6790')
    parser.add_argument('--date', help='\u5206\u6790\u65e5\u671f (YYYY-MM-DD)\uff0c\u9ed8\u8ba4\u6628\u5929')
    parser.add_argument('--output', help='\u8f93\u51fa\u6587\u4ef6\u8def\u5f84\uff0c\u9ed8\u8ba4\u6253\u5370\u5230 stdout')
    parser.add_argument('--update-db', action='store_true', default=True,
                       help='\u66f4\u65b0 prediction-tracker DB')
    parser.add_argument('--skip-html', action='store_true',
                       help='\u8df3\u8fc7 Playwright \u91c7\u96c6\uff08\u4ec5\u7528 DB \u6570\u636e\uff09')
    args = parser.parse_args()

    if args.date:
        target_date = args.date
    else:
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"[START] \u7ade\u8db3\u6bd4\u5206\u547d\u4e2d\u7387\u590d\u76d8 - \u5206\u6790\u65e5\u671f: {target_date}")
    print("=" * 50)

    # Step 1: 获取预测记录
    predictions = parse_all_yesterday_predictions(target_date)
    print(f"[STEP 1] \u83b7\u53d6\u5230 {len(predictions)} \u6761\u9884\u6d4b\u8bb0\u5f55")

    if not predictions:
        report = (f"## \U0001F3AF \u6bd4\u5206\u547d\u4e2d\u7387\u590d\u76d8\uff08{target_date}\uff09\n\n"
                  "\u274c \u672a\u627e\u5230\u9884\u6d4b\u6570\u636e\uff0c\u65e0\u6cd5\u8fdb\u884c\u6bd4\u5206\u547d\u4e2d\u7387\u5206\u6790\n\n"
                  "\u53ef\u80fd\u539f\u56e0\uff1a\n"
                  "1. \u9884\u6d4b\u4efb\u52a1\uff0811:00/17:00/20:30\uff09\u5f53\u65e5\u672a\u6267\u884c\n"
                  "2. cron \u8f93\u51fa\u6587\u4ef6\u672a\u4fdd\u5b58\n"
                  "3. \u89e3\u6790\u683c\u5f0f\u4e0d\u5339\u914d")
        print(report)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
        return report

    # Step 2: 采集实际赛果
    actual_results = []
    if not args.skip_html:
        print(f"[STEP 2] \u91c7\u96c6\u5b9e\u9645\u8d5b\u679c...")
        actual_results = fetch_actual_results(target_date)
        print(f"[STEP 2] \u83b7\u53d6\u5230 {len(actual_results)} \u573a\u5b9e\u9645\u8d5b\u679c")

    # Step 3: 更新 tracker DB
    if args.update_db and actual_results:
        print(f"[STEP 3] \u66f4\u65b0 prediction-tracker DB...")
        updated = update_tracker_db(target_date, predictions, actual_results)
        print(f"[STEP 3] DB \u66f4\u65b0\u5b8c\u6210: {updated} \u6761")

    # Step 4: 生成报告
    print(f"[STEP 4] \u751f\u6210\u6bd4\u5206\u547d\u4e2d\u7387\u62a5\u544a...")
    report = generate_score_report(target_date, predictions, actual_results)
    print("=" * 50)
    print(report)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n[OUTPUT] \u62a5\u544a\u5df2\u4fdd\u5b58\u5230: {args.output}")

    return report


if __name__ == '__main__':
    main()
